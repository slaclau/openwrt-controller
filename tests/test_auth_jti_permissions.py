import sys
import pathlib
import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

# Ensure backend package is importable
ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ROOT / "site-manager" / "backend"
sys.path.insert(0, str(BACKEND))

from app.main import app, create_db_and_tables
from app.dependencies import engine
from app.users.model import UserInDb
import app.auth.main as auth_main
from app.auth.main import PermissionChecker


def setup_module():
    # Create database and tables for tests
    create_db_and_tables()


def test_refresh_malformed_jti(monkeypatch):
    username = "testuser"
    # add user to DB
    with Session(engine) as s:
        user = UserInDb(
            username=username,
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            permissions="",
        )
        user.hashed_password = "notahash"
        s.add(user)
        s.commit()

    # monkeypatch jwt.decode to return a payload with a malformed jti
    def fake_decode(token, key, algorithms=None, options=None, **kwargs):
        return {
            "sub": username,
            "jti": "not-a-uuid",
            "exp": int(datetime.datetime.now().timestamp()) + 3600,
        }

    monkeypatch.setattr(auth_main.jwt, "decode", fake_decode)

    client = TestClient(app)
    # Provide a dummy refresh_token cookie; the patched decode ignores its value
    resp = client.post("/auth/refresh", cookies={"refresh_token": "dummy"})
    assert resp.status_code == 401


def test_permission_checker_normalization():
    user = UserInDb(
        username="permuser",
        email="perm@example.com",
        full_name="Perm User",
        disabled=False,
        permissions="  read:user:*   ",
    )
    checker = PermissionChecker(action="read", resource_type="user")

    class Req:
        path_params = {}

    assert checker(Req(), user) is True
