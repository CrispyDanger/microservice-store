import asyncio
from decimal import Decimal
from uuid import uuid4

from inventory.models import Product


async def make_product(name: str = "Mug", price: str = "9.99", stock: int = 5) -> Product:
    return await Product.create(name=name, price=Decimal(price), stock=stock)


async def test_anyone_can_list_products(client):
    await make_product("Teapot")
    await make_product("Cup")

    resp = await client.get("/products")

    assert resp.status_code == 200
    body = resp.json()
    assert [p["name"] for p in body["products"]] == ["Cup", "Teapot"]
    assert body["count"] == 2


async def test_list_products_is_paginated(client):
    for name in ["A", "B", "C"]:
        await make_product(name)

    resp = await client.get("/products", params={"limit": 2, "offset": 1})

    body = resp.json()
    assert [p["name"] for p in body["products"]] == ["B", "C"]
    assert body["count"] == 3
    assert (body["limit"], body["offset"]) == (2, 1)


async def test_anyone_can_get_a_product(client):
    product = await make_product(price="12.50", stock=3)

    resp = await client.get(f"/products/{product.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(product.id)
    assert body["price"] == "12.50"
    assert body["stock"] == 3


async def test_get_unknown_product_returns_404(client):
    resp = await client.get(f"/products/{uuid4()}")

    assert resp.status_code == 404
    assert resp.json() == {"detail": "Product not found"}


async def test_admin_creates_product(client, admin_headers):
    resp = await client.post(
        "/products", json={"name": "Mug", "price": "9.99", "stock": 10}, headers=admin_headers
    )

    assert resp.status_code == 201
    body = resp.json()
    assert (body["name"], body["price"], body["stock"]) == ("Mug", "9.99", 10)
    assert await Product.filter(id=body["id"]).exists()


async def test_created_product_starts_with_no_stock_by_default(client, admin_headers):
    resp = await client.post(
        "/products", json={"name": "Mug", "price": "9.99"}, headers=admin_headers
    )

    assert resp.json()["stock"] == 0


async def test_create_rejects_invalid_input(client, admin_headers):
    for body in [
        {"name": "", "price": "9.99"},
        {"name": "Mug", "price": "0"},
        {"name": "Mug", "price": "9.999"},
        {"name": "Mug", "price": "9.99", "stock": -1},
    ]:
        resp = await client.post("/products", json=body, headers=admin_headers)
        assert resp.status_code == 422, body


async def test_regular_user_cannot_create_product(client, auth_headers):
    resp = await client.post(
        "/products", json={"name": "Mug", "price": "9.99"}, headers=auth_headers
    )

    assert resp.status_code == 403
    assert not await Product.exists()


async def test_anonymous_user_cannot_create_product(client):
    resp = await client.post("/products", json={"name": "Mug", "price": "9.99"})

    assert resp.status_code == 401


async def test_admin_restocks_product(client, admin_headers):
    product = await make_product(stock=5)

    resp = await client.post(
        f"/products/{product.id}/restock", json={"quantity": 7}, headers=admin_headers
    )

    assert resp.status_code == 200
    assert resp.json()["stock"] == 12
    await product.refresh_from_db()
    assert product.stock == 12


async def test_restock_requires_positive_quantity(client, admin_headers):
    product = await make_product()

    resp = await client.post(
        f"/products/{product.id}/restock", json={"quantity": 0}, headers=admin_headers
    )

    assert resp.status_code == 422


async def test_restock_unknown_product_returns_404(client, admin_headers):
    resp = await client.post(
        f"/products/{uuid4()}/restock", json={"quantity": 1}, headers=admin_headers
    )

    assert resp.status_code == 404


async def test_regular_user_cannot_restock(client, auth_headers):
    product = await make_product(stock=5)

    resp = await client.post(
        f"/products/{product.id}/restock", json={"quantity": 1}, headers=auth_headers
    )

    assert resp.status_code == 403
    await product.refresh_from_db()
    assert product.stock == 5


async def test_concurrent_restocks_are_all_counted(client, admin_headers):
    product = await make_product(stock=0)

    await asyncio.gather(
        *[
            client.post(
                f"/products/{product.id}/restock", json={"quantity": 1}, headers=admin_headers
            )
            for _ in range(10)
        ]
    )

    await product.refresh_from_db()
    assert product.stock == 10
