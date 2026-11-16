import asyncio
from uuid import uuid4

import pytest
from tortoise.transactions import in_transaction

from order.models import IdempotencyKey, Order
from order.schemas.order import PlaceOrderInput
from order.services.place_order import hash_request


@pytest.fixture
def key_headers(auth_headers) -> dict:
    return {**auth_headers, "Idempotency-Key": str(uuid4())}


async def test_place_order_requires_an_idempotency_key(client, auth_headers, order_payload):
    resp = await client.post("/orders", json=order_payload, headers=auth_headers)

    assert resp.status_code == 422
    assert resp.json()["detail"][0]["loc"] == ["header", "idempotency-key"]
    assert await Order.all().count() == 0


async def test_place_order_rejects_a_non_uuid_key(client, auth_headers, order_payload):
    headers = {**auth_headers, "Idempotency-Key": "abc"}

    resp = await client.post("/orders", json=order_payload, headers=headers)

    assert resp.status_code == 422


async def test_retry_with_the_same_key_returns_the_same_order(
    client, producer, key_headers, order_payload
):
    first = await client.post("/orders", json=order_payload, headers=key_headers)
    retry = await client.post("/orders", json=order_payload, headers=key_headers)

    assert first.status_code == retry.status_code == 201
    assert retry.json() == first.json()
    assert await Order.all().count() == 1
    assert len(producer.sent) == 1


async def test_retry_with_reordered_items_counts_as_the_same_request(
    client, key_headers, order_payload
):
    first = await client.post("/orders", json=order_payload, headers=key_headers)
    reordered = {**order_payload, "items": list(reversed(order_payload["items"]))}

    retry = await client.post("/orders", json=reordered, headers=key_headers)

    assert retry.status_code == 201
    assert retry.json()["id"] == first.json()["id"]


async def test_same_key_with_a_different_body_is_rejected(
    client, producer, key_headers, order_payload
):
    await client.post("/orders", json=order_payload, headers=key_headers)

    resp = await client.post(
        "/orders", json={**order_payload, "total": "1.00"}, headers=key_headers
    )

    assert resp.status_code == 422
    assert resp.json() == {"detail": "Idempotency-Key was already used with a different request"}
    assert await Order.all().count() == 1
    assert len(producer.sent) == 1


async def test_the_same_key_from_different_users_creates_two_orders(
    client, make_token, order_payload
):
    key = str(uuid4())
    for _ in range(2):
        headers = {"Authorization": f"Bearer {make_token()}", "Idempotency-Key": key}
        resp = await client.post("/orders", json=order_payload, headers=headers)
        assert resp.status_code == 201

    assert await Order.all().count() == 2


async def test_a_request_racing_an_uncommitted_one_returns_its_order(
    client, producer, user_id, key_headers, order_payload
):
    key = key_headers["Idempotency-Key"]
    request_hash = hash_request(PlaceOrderInput.model_validate(order_payload))
    inserted, release = asyncio.Event(), asyncio.Event()
    winner: dict = {}

    async def first_request_mid_transaction():
        async with in_transaction():
            order = await Order.create(user_id=user_id, total="29.97")
            await IdempotencyKey.create(
                user_id=user_id, key=key, request_hash=request_hash, order=order
            )
            winner["id"] = str(order.id)
            inserted.set()
            await release.wait()

    first = asyncio.create_task(first_request_mid_transaction())
    await inserted.wait()
    second = asyncio.create_task(client.post("/orders", json=order_payload, headers=key_headers))
    await asyncio.sleep(0.3)
    assert not second.done()

    release.set()
    await first
    resp = await second

    assert resp.status_code == 201
    assert resp.json()["id"] == winner["id"]
    assert await Order.all().count() == 1
    assert producer.sent == []
