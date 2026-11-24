import os

import asyncpg
import pytest

ADMIN_DB_URL = "postgres://payment:payment@payment-db:5432/payment"
TEST_DB_NAME = "payment_test"

os.environ["PAYMENT_DATABASE_URL"] = f"postgres://payment:payment@payment-db:5432/{TEST_DB_NAME}"

from httpx import ASGITransport, AsyncClient  # noqa: E402
from tortoise import Tortoise  # noqa: E402

from payment.db import TORTOISE_ORM  # noqa: E402
from payment.main import app  # noqa: E402


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
    await conn.execute_script("TRUNCATE payments CASCADE")


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
