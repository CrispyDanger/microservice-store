import json
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from events.orders import ORDERS_TOPIC
from order.models import Order, OrderItem, OrderStatus

from tests.conftest import OTHER_PRIVATE_KEY


async def test_place_order_requires_a_token(client, order_payload):
    resp = await client.post("/orders", json=order_payload)

    assert resp.status_code == 401
    assert await Order.all().count() == 0


async def test_place_order_rejects_a_token_signed_by_another_key(client, make_token, order_payload):
    token = make_token(private_key=OTHER_PRIVATE_KEY)

    resp = await client.post(
        "/orders", json=order_payload, headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 401


async def test_place_order_rejects_an_expired_token(client, make_token, order_payload):
    token = make_token(expires_in=timedelta(minutes=-1))

    resp = await client.post(
        "/orders", json=order_payload, headers={"Authorization": f"Bearer {token}"}
    )

    assert resp.status_code == 401


async def test_place_order_returns_the_pending_order(client, auth_headers, user_id, order_payload):
    resp = await client.post("/orders", json=order_payload, headers=auth_headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["user_id"] == str(user_id)
    assert body["status"] == "pending"
    assert body["total"] == "29.97"
    assert body["cancel_reason"] is None
    assert body["items"] == sorted(order_payload["items"], key=lambda i: i["product_id"])
    UUID(body["id"])


async def test_place_order_saves_the_order_and_its_items(
    client, auth_headers, user_id, order_payload
):
    resp = await client.post("/orders", json=order_payload, headers=auth_headers)

    order = await Order.get(id=resp.json()["id"])
    assert order.user_id == user_id
    assert order.status == OrderStatus.PENDING
    assert order.total == Decimal("29.97")
    items = await OrderItem.filter(order=order).order_by("quantity")
    assert [(str(i.product_id), i.quantity) for i in items] == [
        (order_payload["items"][1]["product_id"], 1),
        (order_payload["items"][0]["product_id"], 2),
    ]


async def test_place_order_publishes_order_created(
    client, producer, auth_headers, user_id, order_payload
):
    resp = await client.post("/orders", json=order_payload, headers=auth_headers)
    order_id = resp.json()["id"]

    assert len(producer.sent) == 1
    topic, key, value = producer.sent[0]
    assert topic == ORDERS_TOPIC
    assert key == order_id.encode()
    event = json.loads(value)
    assert event["type"] == "OrderCreated"
    assert event["order_id"] == order_id
    assert event["user_id"] == str(user_id)
    assert event["items"] == order_payload["items"]
    assert event["total"] == "29.97"


async def test_place_order_rejects_the_same_product_twice(client, auth_headers, order_payload):
    product_id = order_payload["items"][0]["product_id"]
    payload = {
        **order_payload,
        "items": [
            {"product_id": product_id, "quantity": 2},
            {"product_id": product_id, "quantity": 1},
        ],
    }

    resp = await client.post("/orders", json=payload, headers=auth_headers)

    assert resp.status_code == 422
    assert await Order.all().count() == 0


@pytest.mark.parametrize(
    "change",
    [
        {"items": []},
        {"items": [{"product_id": "00000000-0000-4000-8000-000000000001", "quantity": 0}]},
        {"items": [{"product_id": "not-a-uuid", "quantity": 1}]},
        {"total": "0"},
        {"total": "-5"},
        {"total": "1.999"},
    ],
)
async def test_place_order_rejects_invalid_input(
    client, producer, auth_headers, order_payload, change
):
    resp = await client.post("/orders", json={**order_payload, **change}, headers=auth_headers)

    assert resp.status_code == 422
    assert await Order.all().count() == 0
    assert producer.sent == []
