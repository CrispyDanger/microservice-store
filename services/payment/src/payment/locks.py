from uuid import UUID

from tortoise.backends.base.client import BaseDBAsyncClient


async def lock_order(conn: BaseDBAsyncClient, order_id: UUID) -> None:
    key = int.from_bytes(order_id.bytes[:8], "big", signed=True)
    await conn.execute_query("SELECT pg_advisory_xact_lock($1)", [key])
