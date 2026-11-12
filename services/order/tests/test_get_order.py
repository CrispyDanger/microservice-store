from uuid import uuid4

import pytest


@pytest.fixture
async def placed(client, auth_headers, order_payload) -> dict:
    resp = await client.post("/orders", json=order_payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


async def test_get_order_requires_a_token(client, placed):
    resp = await client.get(f"/orders/{placed['id']}")

    assert resp.status_code == 401


async def test_get_order_returns_the_owners_order(client, auth_headers, placed):
    resp = await client.get(f"/orders/{placed['id']}", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == placed


async def test_get_order_hides_other_users_orders(client, make_token, placed):
    other = {"Authorization": f"Bearer {make_token()}"}

    resp = await client.get(f"/orders/{placed['id']}", headers=other)

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Order not found"}


async def test_get_order_returns_404_for_an_unknown_id(client, auth_headers):
    resp = await client.get(f"/orders/{uuid4()}", headers=auth_headers)

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Order not found"}


async def test_get_order_rejects_a_malformed_id(client, auth_headers):
    resp = await client.get("/orders/not-a-uuid", headers=auth_headers)

    assert resp.status_code == 422
