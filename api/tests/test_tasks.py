from datetime import date, timedelta

from tests.conftest import register_and_login


def _create(client, auth, project_id, **fields):
    payload = {"title": "Tarea", **fields}
    r = client.post(f"/api/projects/{project_id}/tasks", json=payload, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def test_task_crud_and_move_on_board(client, auth, project):
    task = _create(client, auth, project["id"], title="Configurar Docker", priority="high")
    assert task["status"] == "todo"

    r = client.patch(f"/api/tasks/{task['id']}", json={"status": "in_progress"}, headers=auth)
    assert r.status_code == 200 and r.json()["status"] == "in_progress"

    assert client.delete(f"/api/tasks/{task['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/tasks/{task['id']}", headers=auth).status_code == 404


def test_filters(client, auth, project):
    pid = project["id"]
    _create(client, auth, pid, title="Tarea A", priority="high")
    _create(client, auth, pid, title="Tarea B", priority="low", status="done")
    _create(client, auth, pid, title="Tarea C", priority="high", status="done")

    url = f"/api/projects/{pid}/tasks"
    assert len(client.get(url, headers=auth).json()) == 3
    assert len(client.get(url, params={"priority": "high"}, headers=auth).json()) == 2
    done_high = client.get(url, params={"status_filter": "done", "priority": "high"}, headers=auth).json()
    assert [t["title"] for t in done_high] == ["Tarea C"]


def test_assignee_must_be_member(client, auth, project):
    _, _ = register_and_login(client, email="externo@test.com", name="Externo")
    r = client.post(
        f"/api/projects/{project['id']}/tasks", json={"title": "Sin permiso", "assignee_id": 2}, headers=auth
    )
    assert r.status_code == 400

    client.post(f"/api/projects/{project['id']}/members", json={"email": "externo@test.com"}, headers=auth)
    task = _create(client, auth, project["id"], title="Ahora sí", assignee_id=2)
    assert task["assignee"]["email"] == "externo@test.com"


def test_non_member_cannot_touch_tasks(client, auth, project):
    task = _create(client, auth, project["id"])
    other, _ = register_and_login(client, email="otro@test.com", name="Otro")
    assert client.get(f"/api/tasks/{task['id']}", headers=other).status_code == 404
    assert client.patch(f"/api/tasks/{task['id']}", json={"status": "done"}, headers=other).status_code == 404


def test_stats(client, auth, project):
    pid = project["id"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _create(client, auth, pid, status="done")
    _create(client, auth, pid, status="in_progress", due_date=yesterday)  # vencida
    _create(client, auth, pid, status="done", due_date=yesterday)  # terminada: no cuenta
    _create(client, auth, pid, priority="high")

    s = client.get(f"/api/projects/{pid}/stats", headers=auth).json()
    assert s["total"] == 4
    assert s["by_status"] == {"todo": 1, "in_progress": 1, "done": 2}
    assert s["by_priority"]["high"] == 1
    assert s["overdue"] == 1
    assert s["progress_pct"] == 50.0


def test_comments(client, auth, project):
    task = _create(client, auth, project["id"])
    r = client.post(f"/api/tasks/{task['id']}/comments", json={"content": "Primer avance"}, headers=auth)
    assert r.status_code == 201 and r.json()["author"]["full_name"] == "Ana"
    comments = client.get(f"/api/tasks/{task['id']}/comments", headers=auth).json()
    assert len(comments) == 1
    assert client.get(f"/api/tasks/{task['id']}", headers=auth).json()["comment_count"] == 1
