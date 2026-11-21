import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ADMIN_DB_URL = "postgres://inventory:inventory@inventory-db:5432/inventory"
TEST_DB_NAME = "inventory_test"


def _keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return private, public


PRIVATE_KEY, PUBLIC_KEY = _keypair()

with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
    f.write(PUBLIC_KEY)

os.environ["INVENTORY_DATABASE_URL"] = (
    f"postgres://inventory:inventory@inventory-db:5432/{TEST_DB_NAME}"
)
os.environ["INVENTORY_JWT_PUBLIC_KEY_PATH"] = f.name

from httpx import ASGITransport, AsyncClient  # noqa: E402
from tortoise import Tortoise  # noqa: E402

from inventory.db import TORTOISE_ORM  # noqa: E402
from inventory.main import app  # noqa: E402


async def _ensure_test_db() -> None:
    conn = await asyncpg.connect(ADMIN_DB_URL)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def db():
    await _ensure_test_db()
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    yield
    await Tortoise.close_connections()


@pytest.fixture(autouse=True)
async def clean_tables():
    conn = Tortoise.get_connection("default")
    await conn.execute_script(
        "TRUNCATE products, stock_reservations, stock_reservation_items, events, processed_events"
        " CASCADE"
    )


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bytes, bytes]] = []

    async def send_and_wait(self, topic: str, key: bytes, value: bytes) -> None:
        self.sent.append((topic, key, value))


@pytest.fixture
def producer() -> FakeProducer:
    return FakeProducer()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def make_token() -> Callable[..., str]:
    def _make(user_id: UUID | None = None, *, role: str = "user") -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": str(user_id or uuid4()),
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        }
        return jwt.encode(claims, PRIVATE_KEY, algorithm="RS256")

    return _make


@pytest.fixture
def auth_headers(make_token) -> dict:
    return {"Authorization": f"Bearer {make_token()}"}


@pytest.fixture
def admin_headers(make_token) -> dict:
    return {"Authorization": f"Bearer {make_token(role='admin')}"}
