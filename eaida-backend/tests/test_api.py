"""Smoke tests: health, auth, RBAC."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

P = settings.API_V1_PREFIX


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _admin_token(client) -> str:
    res = client.post(f"{P}/auth/login", json={
        "email": settings.FIRST_ADMIN_EMAIL, "password": settings.FIRST_ADMIN_PASSWORD})
    assert res.status_code == 200
    return res.json()["access_token"]


def test_health(client):
    res = client.get(f"{P}/health")
    assert res.status_code == 200 and res.json()["status"] == "ok"


def test_login_and_me(client):
    token = _admin_token(client)
    res = client.get(f"{P}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200 and res.json()["role"] == "admin"


def test_protected_route_requires_auth(client):
    assert client.get(f"{P}/datasets").status_code == 401


def test_viewer_cannot_upload(client):
    admin = _admin_token(client)
    client.post(f"{P}/auth/register", json={
        "email": "viewer@test.com", "full_name": "V", "password": "Viewer@12345"})
    token = client.post(f"{P}/auth/login", json={
        "email": "viewer@test.com", "password": "Viewer@12345"}).json()["access_token"]
    res = client.post(f"{P}/datasets/upload",
                      headers={"Authorization": f"Bearer {token}"},
                      files={"file": ("a.csv", b"a,b\n1,2\n", "text/csv")})
    assert res.status_code == 403
    assert admin