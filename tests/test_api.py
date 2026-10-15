"""API regression tests for Emergency Blood Release auth and stores."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("BLOOD_DATA_DIR", str(data))
    monkeypatch.setenv("BLOOD_TOKEN_SECRET", "test-secret-not-for-prod")
    monkeypatch.setenv("BLOOD_ADMIN_USER", "admin")
    monkeypatch.setenv("BLOOD_ADMIN_PASSWORD", "admin123")
    # Import after env so DATA_DIR resolves correctly.
    import importlib
    import server

    importlib.reload(server)
    return TestClient(server.app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_success_and_me(client):
    r = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    token = r.json()["session_token"]
    assert token.startswith("v1.")
    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "admin"


def test_login_failure(client):
    r = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_history_requires_auth(client):
    assert client.get("/api/history").status_code == 401


def test_history_roundtrip(client):
    token = client.post("/api/login", json={"username": "admin", "password": "admin123"}).json()[
        "session_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    rec = {"time": "2026-01-01 10:00", "name": "TEST PATIENT", "file": "F1", "unit": "U1"}
    r = client.post("/api/history", headers=headers, json={"records": [rec]})
    assert r.status_code == 200
    assert any(x.get("unit") == "U1" for x in r.json()["records"])
    g = client.get("/api/history", headers=headers)
    assert g.status_code == 200
    assert any(x.get("unit") == "U1" for x in g.json()["records"])


def test_users_admin_only(client):
    token = client.post("/api/login", json={"username": "admin", "password": "admin123"}).json()[
        "session_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/users",
        headers=headers,
        json={"username": "techx", "password": "tech1234", "role": "user"},
    )
    assert created.status_code == 200
    tech_token = client.post(
        "/api/login", json={"username": "techx", "password": "tech1234"}
    ).json()["session_token"]
    denied = client.get("/api/users", headers={"Authorization": f"Bearer {tech_token}"})
    assert denied.status_code == 403
