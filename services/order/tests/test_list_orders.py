import pytest

from tests.conftest import with_new_key


@pytest.fixture
def place(client, order_payload):
    async def _place(headers: dict) -> dict:
        resp = await client.post("/orders", json=order_payload, headers=with_new_key(headers))
        assert resp.status_code == 201
        return resp.json()

    return _place


async def test_list_orders_requires_a_token(client):
    resp = await client.get("/orders")

    assert resp.status_code == 401


async def test_list_orders_is_empty_for_a_new_user(client, auth_headers):
    resp = await client.get("/orders", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == {"orders": [], "count": 0, "limit": 20, "offset": 0}


async def test_list_orders_returns_only_the_users_own_orders(
    client, make_token, auth_headers, place
):
    mine = await place(auth_headers)
    await place({"Authorization": f"Bearer {make_token()}"})

    resp = await client.get("/orders", headers=auth_headers)

    body = resp.json()
    assert body["count"] == 1
    assert body["orders"] == [mine]


async def test_list_orders_returns_newest_first(client, auth_headers, place):
    first = await place(auth_headers)
    second = await place(auth_headers)
    third = await place(auth_headers)

    resp = await client.get("/orders", headers=auth_headers)

    assert [o["id"] for o in resp.json()["orders"]] == [third["id"], second["id"], first["id"]]


async def test_list_orders_pages_with_limit_and_offset(client, auth_headers, place):
    placed = [await place(auth_headers) for _ in range(5)]
    newest_first = [o["id"] for o in reversed(placed)]

    resp = await client.get("/orders", params={"limit": 2, "offset": 2}, headers=auth_headers)

    body = resp.json()
    assert body["count"] == 5
    assert body["limit"] == 2
    assert body["offset"] == 2
    assert [o["id"] for o in body["orders"]] == newest_first[2:4]


async def test_list_orders_past_the_end_is_empty(client, auth_headers, place):
    await place(auth_headers)

    resp = await client.get("/orders", params={"offset": 10}, headers=auth_headers)

    assert resp.json()["orders"] == []
    assert resp.json()["count"] == 1


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "abc"}]
)
async def test_list_orders_rejects_invalid_paging(client, auth_headers, params):
    resp = await client.get("/orders", params=params, headers=auth_headers)

    assert resp.status_code == 422
