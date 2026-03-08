import tempfile
import os
import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture()
def app_client():
    """TestClient backed by a fresh temporary DB file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        fastapi_app = create_app(db_path=db_path)
        with TestClient(fastapi_app, raise_server_exceptions=True) as client:
            yield client
    finally:
        os.unlink(db_path)


@pytest.fixture()
def auth_client(app_client):
    """TestClient with a registered + logged-in user."""
    app_client.post("/register", data={
        "username": "testuser",
        "password": "testpass1",
        "password2": "testpass1",
    })
    app_client.post("/login", data={"username": "testuser", "password": "testpass1"})
    return app_client
