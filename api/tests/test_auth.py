from tests.conftest import register_and_login


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["database"]["status"] == "ok"


def test_register_login_me(client):
    headers, _ = register_and_login(client, email="Luis@Test.com", name="Luis")
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "luis@test.com"  # se normaliza a minúsculas


def test_duplicate_email(client):
    register_and_login(client)
    r = client.post(
        "/api/auth/register", json={"email": "ana@test.com", "full_name": "Otra", "password": "123456"}
    )
    assert r.status_code == 409


def test_wrong_password(client):
    register_and_login(client)
    r = client.post("/api/auth/login", data={"username": "ana@test.com", "password": "malapass"})
    assert r.status_code == 401


def test_requires_token(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_validation(client):
    r = client.post("/api/auth/register", json={"email": "no-es-correo", "full_name": "X", "password": "1"})
    assert r.status_code == 422
