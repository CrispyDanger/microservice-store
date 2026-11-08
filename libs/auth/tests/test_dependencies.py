from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth import AccessClaims, JWTAuth


@pytest.fixture
def client(keys) -> TestClient:
    """A tiny app that uses the lib the same way a real service would."""
    auth = JWTAuth(keys[1])
    CurrentClaims = Annotated[AccessClaims, Depends(auth)]
    app = FastAPI()

    @app.get("/whoami")
    async def whoami(claims: CurrentClaims):
        return {"user_id": str(claims.user_id), "role": claims.role}

    @app.get("/admin", dependencies=[Depends(auth.require_role("admin"))])
    async def admin():
        return {"ok": True}

    return TestClient(app)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_reaches_the_endpoint(client, make_token):
    user_id = str(uuid4())

    resp = client.get("/whoami", headers=bearer(make_token(sub=user_id)))

    assert resp.status_code == 200
    assert resp.json() == {"user_id": user_id, "role": "user"}


def test_missing_header_is_401_with_bearer_challenge(client):
    resp = client.get("/whoami")

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_wrong_scheme_is_401(client, make_token):
    resp = client.get("/whoami", headers={"Authorization": f"Basic {make_token()}"})

    assert resp.status_code == 401


def test_invalid_token_is_401_with_bearer_challenge(client):
    resp = client.get("/whoami", headers=bearer("not-a-jwt"))

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"
    assert resp.json() == {"detail": "Invalid or expired token"}


def test_token_from_another_issuer_is_401(client, other_keys, make_token):
    resp = client.get("/whoami", headers=bearer(make_token(private_key=other_keys[0])))

    assert resp.status_code == 401


def test_require_role_lets_the_right_role_in(client, make_token):
    resp = client.get("/admin", headers=bearer(make_token(role="admin")))

    assert resp.status_code == 200


def test_require_role_is_403_for_other_roles(client, make_token):
    resp = client.get("/admin", headers=bearer(make_token(role="user")))

    assert resp.status_code == 403
    assert resp.json() == {"detail": "Not enough permissions"}


def test_require_role_is_401_without_a_token(client):
    resp = client.get("/admin")

    assert resp.status_code == 401
