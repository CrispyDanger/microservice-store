from user.models import RefreshToken
from user.security.tokens import hash_refresh_token


async def logout(client, raw):
    return await client.post("/auth/logout", json={"refresh_token": raw})


async def test_logout_returns_204(client, tokens):
    resp = await logout(client, tokens["refresh_token"])

    assert resp.status_code == 204
    assert resp.content == b""


async def test_logout_then_refresh_fails(client, tokens):
    await logout(client, tokens["refresh_token"])

    resp = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert resp.status_code == 401


async def test_logout_revokes_the_row_but_keeps_it(client, tokens):
    await logout(client, tokens["refresh_token"])

    row = await RefreshToken.get(token_hash=hash_refresh_token(tokens["refresh_token"]))
    assert row.revoked_at is not None  # kept, so a later reuse can still be detected


async def test_logout_ends_only_this_session(client, user_payload, registered, tokens):
    phone = (
        await client.post(
            "/auth/login",
            json={"email": user_payload["email"], "password": user_payload["password"]},
        )
    ).json()

    await logout(client, tokens["refresh_token"])

    resp = await client.post("/auth/refresh", json={"refresh_token": phone["refresh_token"]})
    assert resp.status_code == 200


async def test_logout_with_unknown_token_is_still_204(client):
    resp = await logout(client, "made-up-token")

    assert resp.status_code == 204


async def test_logout_twice_is_harmless(client, tokens):
    assert (await logout(client, tokens["refresh_token"])).status_code == 204
    assert (await logout(client, tokens["refresh_token"])).status_code == 204


async def test_logout_twice_keeps_the_first_revocation_time(client, tokens):
    await logout(client, tokens["refresh_token"])
    first = await RefreshToken.get(token_hash=hash_refresh_token(tokens["refresh_token"]))

    await logout(client, tokens["refresh_token"])
    second = await RefreshToken.get(token_hash=hash_refresh_token(tokens["refresh_token"]))

    assert first.revoked_at == second.revoked_at
