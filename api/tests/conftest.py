"""Las pruebas usan SQLite en memoria: no necesitan el contenedor de PostgreSQL."""
import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEED_DATA"] = "false"
os.environ["JWT_SECRET"] = "secreto-de-pruebas"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def register_and_login(client, email="ana@test.com", name="Ana", password="secreto123"):
    r = client.post("/api/auth/register", json={"email": email, "full_name": name, "password": password})
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r


@pytest.fixture()
def auth(client):
    headers, _ = register_and_login(client)
    return headers


@pytest.fixture()
def project(client, auth):
    r = client.post("/api/projects", json={"name": "Proyecto CI", "description": "demo"}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()
