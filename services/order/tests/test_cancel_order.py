import asyncio
from uuid import uuid4

import pytest
from tortoise.transactions import in_transaction

from events.orders import ORDERS_TOPIC
from order.models import Event, Order, OrderStatus

from tests.conftest import with_new_key


@pytest.fixture
async def placed(client, auth_headers, order_payload) -> dict:
    resp = await client.post("/orders", json=order_payload, headers=with_new_key(auth_headers))
    assert resp.status_code == 201
    await Event.all().delete()
    return resp.json()


async def test_cancel_order_requires_a_token(client, placed):
    resp = await client.post(f"/orders/{placed['id']}/cancel")

    assert resp.status_code == 401


async def test_cancel_order_without_a_body_uses_the_default_reason(client, auth_headers, placed):
    resp = await client.post(f"/orders/{placed['id']}/cancel", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancel_reason"] == "cancelled by user"
    assert body["items"] == placed["items"]


async def test_cancel_order_saves_the_given_reason(client, auth_headers, placed):
    resp = await client.post(
        f"/orders/{placed['id']}/cancel",
        json={"reason": "changed my mind"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    order = await Order.get(id=placed["id"])
    assert order.status == OrderStatus.CANCELLED
    assert order.cancel_reason == "changed my mind"


async def test_cancel_order_records_order_cancelled(client, auth_headers, placed):
    await client.post(
        f"/orders/{placed['id']}/cancel", json={"reason": "too slow"}, headers=auth_headers
    )

    [row] = await Event.all()
    assert row.topic == ORDERS_TOPIC
    assert row.key == placed["id"]
    event = row.payload
    assert event["type"] == "OrderCancelled"
    assert event["order_id"] == placed["id"]
    assert event["reason"] == "too slow"


async def test_cancel_order_hides_other_users_orders(client, make_token, placed):
    other = {"Authorization": f"Bearer {make_token()}"}

    resp = await client.post(f"/orders/{placed['id']}/cancel", headers=other)

    assert resp.status_code == 404
    assert (await Order.get(id=placed["id"])).status == OrderStatus.PENDING
    assert await Event.all().count() == 0


async def test_cancel_order_returns_404_for_an_unknown_id(client, auth_headers):
    resp = await client.post(f"/orders/{uuid4()}/cancel", headers=auth_headers)

    assert resp.status_code == 404


async def test_cancel_order_twice_is_rejected(client, auth_headers, placed):
    await client.post(f"/orders/{placed['id']}/cancel", headers=auth_headers)
    await Event.all().delete()

    resp = await client.post(f"/orders/{placed['id']}/cancel", headers=auth_headers)

    assert resp.status_code == 409
    assert resp.json() == {"detail": "Only pending orders can be cancelled"}
    assert await Event.all().count() == 0


async def test_cancel_order_rejects_a_confirmed_order(client, auth_headers, placed):
    await Order.filter(id=placed["id"]).update(status=OrderStatus.CONFIRMED)

    resp = await client.post(f"/orders/{placed['id']}/cancel", headers=auth_headers)

    assert resp.status_code == 409
    assert (await Order.get(id=placed["id"])).status == OrderStatus.CONFIRMED
    assert await Event.all().count() == 0


@pytest.mark.parametrize("reason", ["", "x" * 256])
async def test_cancel_order_rejects_an_invalid_reason(client, auth_headers, placed, reason):
    resp = await client.post(
        f"/orders/{placed['id']}/cancel", json={"reason": reason}, headers=auth_headers
    )

    assert resp.status_code == 422


async def test_cancel_waits_for_a_concurrent_confirm_and_then_loses(
    client, auth_headers, placed
):
    locked, release = asyncio.Event(), asyncio.Event()

    async def confirm_while_holding_the_lock():
        async with in_transaction():
            await Order.select_for_update().get(id=placed["id"])
            locked.set()
            await release.wait()
            await Order.filter(id=placed["id"]).update(status=OrderStatus.CONFIRMED)

    confirm = asyncio.create_task(confirm_while_holding_the_lock())
    await locked.wait()
    cancel = asyncio.create_task(
        client.post(f"/orders/{placed['id']}/cancel", headers=auth_headers)
    )
    await asyncio.sleep(0.3)
    assert not cancel.done()

    release.set()
    await confirm
    resp = await cancel

    assert resp.status_code == 409
    assert (await Order.get(id=placed["id"])).status == OrderStatus.CONFIRMED
    assert await Event.all().count() == 0
