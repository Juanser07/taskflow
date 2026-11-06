from tests.conftest import register_and_login


def test_create_and_list_projects(client, auth, project):
    r = client.get("/api/projects", headers=auth)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Proyecto CI"
    assert data[0]["my_role"] == "owner"


def test_non_member_cannot_see_project(client, project):
    other, _ = register_and_login(client, email="intruso@test.com", name="Intruso")
    assert client.get(f"/api/projects/{project['id']}", headers=other).status_code == 404
    assert client.get("/api/projects", headers=other).json() == []


def test_add_member_and_permissions(client, auth, project):
    luis, _ = register_and_login(client, email="luis@test.com", name="Luis")
    r = client.post(f"/api/projects/{project['id']}/members", json={"email": "luis@test.com"}, headers=auth)
    assert r.status_code == 201
    assert r.json()["role"] == "member"

    # Ahora Luis ve el proyecto, pero no puede administrar miembros ni borrarlo
    assert client.get(f"/api/projects/{project['id']}", headers=luis).status_code == 200
    r = client.post(f"/api/projects/{project['id']}/members", json={"email": "ana@test.com"}, headers=luis)
    assert r.status_code == 403
    assert client.delete(f"/api/projects/{project['id']}", headers=luis).status_code == 403

    members = client.get(f"/api/projects/{project['id']}/members", headers=auth).json()
    assert {m["user"]["email"] for m in members} == {"ana@test.com", "luis@test.com"}


def test_add_member_errors(client, auth, project):
    url = f"/api/projects/{project['id']}/members"
    assert client.post(url, json={"email": "nadie@test.com"}, headers=auth).status_code == 404
    assert client.post(url, json={"email": "ana@test.com"}, headers=auth).status_code == 409


def test_cannot_remove_owner(client, auth, project):
    me = client.get("/api/auth/me", headers=auth).json()
    r = client.delete(f"/api/projects/{project['id']}/members/{me['id']}", headers=auth)
    assert r.status_code == 400


def test_update_and_delete_project(client, auth, project):
    r = client.patch(f"/api/projects/{project['id']}", json={"name": "Nuevo nombre"}, headers=auth)
    assert r.status_code == 200 and r.json()["name"] == "Nuevo nombre"
    assert client.delete(f"/api/projects/{project['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/projects/{project['id']}", headers=auth).status_code == 404
