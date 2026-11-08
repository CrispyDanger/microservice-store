import os

# Must run BEFORE anything imports user.*: settings are read when user.config is imported,
# and a variable set in the process wins over the one from env_file. Tests never touch the dev DB.
os.environ["USER_DATABASE_URL"] = "postgres://user:user@user-db:5432/user_test"

import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from user.db import TORTOISE_ORM
from user.main import app


@pytest.fixture(scope="session", autouse=True)
async def db():
    """Connect once per test run and create the tables in the throwaway test DB."""
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)  # safe=True: only creates missing tables
    yield
    await Tortoise.close_connections()


@pytest.fixture(autouse=True)
async def clean_tables():
    """Every test starts with empty tables, so tests don't depend on each other."""
    conn = Tortoise.get_connection("default")
    await conn.execute_script("TRUNCATE users, refresh_tokens CASCADE")


@pytest.fixture
async def client():
    """HTTP client that calls the app in memory: no server, no port.

    ASGITransport does not run the app's lifespan, which is why the db fixture
    initializes Tortoise itself.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def user_payload() -> dict:
    """A valid registration body. Tests copy it and change one field: {**user_payload, ...}."""
    return {
        "email": "artem@example.com",
        "password": "password123",
        "first_name": "Artem",
        "last_name": "Yakovenko",
    }


@pytest.fixture
async def registered(client, user_payload) -> dict:
    """A user that already exists; returns the register response body."""
    resp = await client.post("/auth/register", json=user_payload)
    assert resp.status_code == 201
    return resp.json()

@pytest.fixture
async def tokens(client, user_payload, registered) -> dict:
    """Logged-in user; returns {access_token, refresh_token, token_type}."""
    resp = await client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
def auth_headers(tokens) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
