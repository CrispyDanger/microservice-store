import asyncio
from datetime import UTC, datetime, timedelta

from user.models import RefreshToken, User
from user.security.tokens import decode_access_token, hash_refresh_token


async def refresh(client, raw):
    return await client.post("/auth/refresh", json={"refresh_token": raw})


async def active_sessions(user_id) -> int:
    return await RefreshToken.filter(user_id=user_id, revoked_at=None).count()


# --- Happy path -------------------------------------------------------------------


async def test_refresh_returns_a_new_pair(client, registered, tokens):
    resp = await refresh(client, tokens["refresh_token"])

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["refresh_token"] != tokens["refresh_token"]
    assert decode_access_token(body["access_token"])["sub"] == registered["id"]


async def test_new_access_token_works(client, registered, tokens):
    new = (await refresh(client, tokens["refresh_token"])).json()

    resp = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {new['access_token']}"}
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == registered["id"]


async def test_rotation_chain_keeps_working(client, tokens):
    raw = tokens["refresh_token"]
    for _ in range(3):  # A -> B -> C -> D
        resp = await refresh(client, raw)
        assert resp.status_code == 200
        raw = resp.json()["refresh_token"]


async def test_rotation_revokes_old_and_stores_new(client, registered, tokens):
    new = (await refresh(client, tokens["refresh_token"])).json()

    old_row = await RefreshToken.get(token_hash=hash_refresh_token(tokens["refresh_token"]))
    new_row = await RefreshToken.get(token_hash=hash_refresh_token(new["refresh_token"]))
    assert old_row.revoked_at is not None
    assert new_row.revoked_at is None
    assert await active_sessions(registered["id"]) == 1


# --- Rejections -------------------------------------------------------------------


async def test_refresh_token_works_only_once(client, tokens):
    await refresh(client, tokens["refresh_token"])

    resp = await refresh(client, tokens["refresh_token"])

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


async def test_unknown_refresh_token_is_rejected(client):
    resp = await refresh(client, "made-up-token")

    assert resp.status_code == 401


async def test_access_token_cannot_be_used_as_refresh_token(client, tokens):
    resp = await refresh(client, tokens["access_token"])

    assert resp.status_code == 401


async def test_expired_refresh_token_is_rejected(client, tokens):
    await RefreshToken.filter(token_hash=hash_refresh_token(tokens["refresh_token"])).update(
        expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )

    resp = await refresh(client, tokens["refresh_token"])

    assert resp.status_code == 401


async def test_inactive_user_cannot_refresh(client, registered, tokens):
    await User.filter(id=registered["id"]).update(is_active=False)

    resp = await refresh(client, tokens["refresh_token"])

    assert resp.status_code == 401


async def test_missing_body_is_422(client):
    resp = await client.post("/auth/refresh", json={})

    assert resp.status_code == 422


# --- Reuse detection --------------------------------------------------------------


async def test_reuse_revokes_every_session(client, registered, tokens):
    new = (await refresh(client, tokens["refresh_token"])).json()  # A -> B

    reuse = await refresh(client, tokens["refresh_token"])  # A again: reuse detected
    assert reuse.status_code == 401
    assert await active_sessions(registered["id"]) == 0  # the revocation was committed

    resp = await refresh(client, new["refresh_token"])  # B must be dead too
    assert resp.status_code == 401


async def test_reuse_also_kills_sessions_on_other_devices(client, user_payload, registered, tokens):
    phone = (
        await client.post(
            "/auth/login",
            json={"email": user_payload["email"], "password": user_payload["password"]},
        )
    ).json()
    await refresh(client, tokens["refresh_token"])

    await refresh(client, tokens["refresh_token"])  # reuse

    assert (await refresh(client, phone["refresh_token"])).status_code == 401


async def test_reuse_does_not_touch_other_users(client, tokens):
    other = {
        "email": "other@example.com",
        "password": "password123",
        "first_name": "Other",
        "last_name": "Person",
    }
    await client.post("/auth/register", json=other)
    other_tokens = (
        await client.post(
            "/auth/login", json={"email": other["email"], "password": other["password"]}
        )
    ).json()
    await refresh(client, tokens["refresh_token"])

    await refresh(client, tokens["refresh_token"])  # reuse by the first user

    assert (await refresh(client, other_tokens["refresh_token"])).status_code == 200


# --- Concurrency ------------------------------------------------------------------


async def test_concurrent_refresh_with_same_token_succeeds_once(client, tokens):
    # select_for_update makes the requests take turns; without it, several could read
    # revoked_at=None at the same moment and all get new tokens.
    responses = await asyncio.gather(
        *(refresh(client, tokens["refresh_token"]) for _ in range(5))
    )

    codes = sorted(r.status_code for r in responses)
    assert codes == [200, 401, 401, 401, 401]
