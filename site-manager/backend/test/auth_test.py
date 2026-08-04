# from pytest_mock import MockFixture

import datetime
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.testclient import TestClient
from httpx2 import Response
import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
import pytest
from sqlalchemy import Engine
from sqlmodel import Session, StaticPool, create_engine, SQLModel

from app.main import app

from app.dependencies import SessionDep, get_session

from app.auth import token
from app.auth.authentication import authenticate_user, password_hash
from app.auth.main import get_current_user, get_current_active_user
from app.auth.token import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    public_key,
    private_key,
    mint_tokens,
    get_tokens,
)

# db model imports
from app.auth.oidc import RemoteUser
from app.auth.token import RefreshTokenData
from app.sites import Site, SiteAccessRelationship
from app.users.model import User, UserInDb

NOW = datetime.datetime.now(tz=datetime.timezone.utc)
print(f"setting NOW to {NOW}")


class MockDatetime:
    @staticmethod
    def now(tz: datetime.tzinfo | None = None):
        if tz:
            return NOW.astimezone(tz)
        return NOW.replace(tzinfo=None)


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(
    test_engine: Engine, test_user_in_db: UserInDb, inactive_user_in_db: Any
):
    SQLModel.metadata.create_all(test_engine)

    # Use a single continuous session context
    with Session(test_engine) as session:
        session.add(test_user_in_db)
        session.add(inactive_user_in_db)
        session.commit()

        yield session

    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def test_user():
    return User(
        username="test",
        email="test@example.com",
        full_name="Test User from example.com",
        disabled=False,
        permissions="",
    )


@pytest.fixture
def test_user_in_db(test_user: User):
    return UserInDb(
        **test_user.model_dump(), hashed_password=password_hash.hash("test_password")
    )


@pytest.fixture
def inactive_user_in_db(test_user_in_db: UserInDb):
    return test_user_in_db.model_copy(
        update={"username": "disabled_user", "disabled": True}
    )


def test_create_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(token, "datetime", MockDatetime)
    payload = {"sub": "example"}

    encoded = create_access_token(payload)

    decoded = jwt.decode(encoded, public_key, algorithms=["EdDSA"])

    assert payload == decoded

    encoded_with_expiry = create_access_token(
        payload, expires_delta=datetime.timedelta(hours=1)
    )

    decoded_with_expiry = jwt.decode(
        encoded_with_expiry, public_key, algorithms=["EdDSA"]
    )

    expiry = decoded_with_expiry.pop("exp")
    assert payload == decoded_with_expiry

    expected_expiry = int(
        (
            MockDatetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=1)
        ).timestamp()
    )
    assert expected_expiry == expiry


@pytest.mark.asyncio
async def test_mint_tokens(
    test_session: Session, test_user: User, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(token, "datetime", MockDatetime)

    access_token, refresh_token = await mint_tokens(
        test_user, test_session, "test_provider", "test_sid"
    )

    decoded_access_token = jwt.decode(access_token, public_key, algorithms=["EdDSA"])
    decoded_refresh_token = jwt.decode(refresh_token, public_key, algorithms=["EdDSA"])

    assert decoded_access_token["type"] == "access"
    assert decoded_refresh_token["type"] == "refresh"

    for decoded_token in [decoded_access_token, decoded_refresh_token]:
        assert decoded_token["sub"] == test_user.username
        assert decoded_token["us_iss"] == "test_provider"
        assert decoded_token["us_sid"] == "test_sid"

    assert datetime.datetime.fromtimestamp(
        decoded_access_token["exp"], tz=datetime.timezone.utc
    ) - NOW.replace(microsecond=0) == datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    assert datetime.datetime.fromtimestamp(
        decoded_refresh_token["exp"], tz=datetime.timezone.utc
    ) - NOW.replace(microsecond=0) == datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


def test_authenticate_user(
    test_session: Session, test_user: User, test_user_in_db: UserInDb
):
    assert test_user_in_db == authenticate_user(
        username=test_user.username, password="test_password", session=test_session
    )

    with pytest.raises(
        HTTPException, check=lambda e: e.status_code == status.HTTP_401_UNAUTHORIZED
    ):
        authenticate_user(
            username="wrong_user", password="wrong_password", session=test_session
        )

    with pytest.raises(
        HTTPException, check=lambda e: e.status_code == status.HTTP_401_UNAUTHORIZED
    ):
        authenticate_user(
            username=test_user.username, password="wrong_password", session=test_session
        )

    old_hasher = PasswordHash(hashers=[Argon2Hasher(time_cost=1)])
    test_user_in_db.hashed_password = old_hasher.hash("test_password")
    test_session.commit()

    assert test_user_in_db == authenticate_user(
        username=test_user.username, password="test_password", session=test_session
    )


@pytest.mark.asyncio
async def test_get_current_user(
    test_session: Session, test_user: User, test_user_in_db: UserInDb
):
    access_token = create_access_token(
        {"sub": test_user.username}
    )  # Verify with correct user
    assert test_user_in_db == await get_current_user(access_token, test_session)

    access_token = create_access_token(
        {"sub": "fake_user"}
    )  # Try with wrong user as sub
    with pytest.raises(
        HTTPException, check=lambda e: e.status_code == status.HTTP_401_UNAUTHORIZED
    ):
        await get_current_user(access_token, test_session)

    access_token = create_access_token({})  # Try with no sub
    with pytest.raises(
        HTTPException, check=lambda e: e.status_code == status.HTTP_401_UNAUTHORIZED
    ):
        await get_current_user(access_token, test_session)

    access_token = "fake_token"  # Try with a fake token
    with pytest.raises(
        HTTPException, check=lambda e: e.status_code == status.HTTP_401_UNAUTHORIZED
    ):
        await get_current_user(access_token, test_session)


def test_get_current_active_user(
    test_session: Session, test_user_in_db: UserInDb, inactive_user_in_db: Any
):
    user = test_session.get(UserInDb, test_user_in_db.username)
    assert user == get_current_active_user(user)  # Verify with active user

    with pytest.raises(
        HTTPException, check=lambda e: e.status_code == status.HTTP_400_BAD_REQUEST
    ):  # Try with disabled user
        get_current_active_user(inactive_user_in_db)


@pytest.fixture
def test_client(test_session: Session):
    # Fix: Yield the exact same session instance inside the dependency override loop
    def get_test_session_override():
        try:
            yield test_session
        finally:
            pass

    app.dependency_overrides[get_session] = get_test_session_override

    with TestClient(app) as client:
        yield client

    # Clean up overrides so they don't break other test modules
    app.dependency_overrides.clear()


def test_login(test_client: TestClient, test_user_in_db: UserInDb):
    response: Response = test_client.post(
        "/auth/login",
        data={"username": test_user_in_db.username, "password": "test_password"},
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    access_token = response.json()["access_token"]
    refresh_token = response.cookies.get("refresh_token")

    decoded_access_token = jwt.decode(access_token, public_key, algorithms=["EdDSA"])
    decoded_refresh_token = jwt.decode(refresh_token, public_key, algorithms=["EdDSA"])

    assert decoded_access_token["type"] == "access"
    assert decoded_refresh_token["type"] == "refresh"


@pytest.mark.asyncio
async def test_refresh(
    test_client: TestClient,
    test_session: Session,
    test_user_in_db: UserInDb,
    inactive_user_in_db: UserInDb,
):
    response: Response = test_client.post(  # Try without refresh cookie
        "/auth/refresh",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    _, original_refresh_token = await mint_tokens(test_user_in_db, test_session)
    test_client.cookies.set("refresh_token", original_refresh_token)
    response: Response = test_client.post(
        "/auth/refresh",
    )
    assert response.status_code == status.HTTP_200_OK
    access_token = response.json()["access_token"]
    refresh_token = response.cookies.get("refresh_token")

    decoded_access_token = jwt.decode(access_token, public_key, algorithms=["EdDSA"])
    decoded_refresh_token = jwt.decode(refresh_token, public_key, algorithms=["EdDSA"])

    assert decoded_access_token["type"] == "access"
    assert decoded_refresh_token["type"] == "refresh"

    test_client.cookies.set(
        "refresh_token", original_refresh_token
    )  # Try reusing refresh cookie
    response: Response = test_client.post(
        "/auth/refresh",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    _, inactive_refresh_token = await mint_tokens(inactive_user_in_db, test_session)
    test_client.cookies.set("refresh_token", inactive_refresh_token)
    response: Response = test_client.post(
        "/auth/refresh",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    invalid_jwt = "fake_token"
    test_client.cookies.set(
        "refresh_token", invalid_jwt
    )  # Try with a non decodable jwt
    response: Response = test_client.post(
        "/auth/refresh",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    fake_token = jwt.encode({}, private_key, algorithm="EdDSA")
    test_client.cookies.set(
        "refresh_token", fake_token
    )  # Try with a valid jwt missing sub
    response: Response = test_client.post(
        "/auth/refresh",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_logout(
    test_client: TestClient, test_user_in_db: UserInDb, test_session: Session
):
    response: Response = test_client.post(  # Try without token
        "/auth/logout",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    access_token, refresh_token = await mint_tokens(test_user_in_db, test_session)
    response: Response = test_client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == status.HTTP_200_OK

    test_client.cookies.set("refresh_token", refresh_token)  # Verify logged out
    response: Response = test_client.post(
        "/auth/refresh",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    invalid_jwt = "fake_token"
    response: Response = test_client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {invalid_jwt}"}
    )  # Try with a non decodable jwt
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    fake_token = jwt.encode({}, private_key, algorithm="EdDSA")
    response: Response = test_client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {fake_token}"}
    )  # Try with a valid jwt missing sub
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    missing_jti = jwt.encode(
        {"sub": test_user_in_db.username}, private_key, algorithm="EdDSA"
    )
    response: Response = test_client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {missing_jti}"}
    )  # Try with a valid jwt missing sub
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    invalid_jti = jwt.encode(
        {"sub": test_user_in_db.username}, private_key, algorithm="EdDSA"
    )
    response: Response = test_client.post(
        "/auth/logout", headers={"Authorization": f"Bearer {invalid_jti}"}
    )  # Try with a valid jwt missing sub
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
