# Microservices

A learning project: a small shop split into FastAPI services that work together through Kafka events. Each service owns its own Postgres database, and an order is processed as a **saga**: a chain of events between services, with no shared database and no distributed transaction.

## Services

| Service | Port | Database | What it does |
|---|---|---|---|
| `user` | 8001 | `user-db` (5433) | Registration, login, RS256 access and refresh tokens |
| `order` | 8000 | `order-db` (5434) | Places, lists and cancels orders; drives the saga |
| `inventory` | 8002 | `inventory-db` (5435) | Products and stock; reserves and releases stock for orders |
| `payment` | 8003 | `payment-db` (5436) | Charges and refunds orders through a fake gateway |
| `notifications` | none | none | Not built yet |

Also running:
- **Kafka** on `localhost:9092`
- **Kafka UI** at http://localhost:8080

Database ports are the ones exposed on your machine.

Shared code lives in `libs/`:
- `libs/events`: the event contracts (Pydantic models) every service imports.
- `libs/auth`: access-token checking. Services only get the public key, so they can check tokens but can't create them.

## How an order flows

Each service publishes to its own topic: `orders`, `inventory` and `payments`.

```mermaid
sequenceDiagram
    participant C as Client
    participant O as order
    participant I as inventory
    participant P as payment

    C->>O: POST /orders
    O-->>I: OrderCreated
    alt enough stock
        I-->>O: StockReserved (total, unit prices)
        I-->>P: StockReserved
        alt charge accepted
            P-->>O: PaymentSucceeded
            O-->>O: order confirmed (OrderConfirmed)
        else charge declined
            P-->>O: PaymentFailed
            O-->>I: OrderCancelled → stock released
        end
    else out of stock
        I-->>O: StockRejected
        O-->>O: order cancelled (OrderCancelled)
    end
```

The order service decides when an order is done:
- It **confirms** the order on `PaymentSucceeded`.
- It **cancels** the order when any of these happen:
  - `StockRejected` arrives
  - `PaymentFailed` arrives
  - the user cancels it
  - it has been `pending` for more than 15 minutes

Every cancel publishes `OrderCancelled`. Inventory then gives the reserved stock back, and payment refunds the order if it was already charged.

## Getting started

You need Docker, `make`, and [uv](https://docs.astral.sh/uv/) if you want to run code outside Docker.

1. Create the RS256 key pair the user service signs tokens with (the `keys` folders are git-ignored):

   ```sh
   mkdir -p services/user/keys
   openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out services/user/keys/private.pem
   openssl rsa -in services/user/keys/private.pem -pubout -out services/user/keys/public.pem
   ```

2. Create `.env` in the repo root. These are the values the containers use:

   ```env
   USER_DATABASE_URL=postgres://user:user@user-db:5432/user
   USER_JWT_PRIVATE_KEY_PATH=/keys/private.pem
   USER_JWT_PUBLIC_KEY_PATH=/keys/public.pem
   USER_ACCESS_TOKEN_MINUTES=5
   USER_REFRESH_TOKEN_DAYS=7

   ORDER_DATABASE_URL=postgres://order:order@order-db:5432/order
   ORDER_JWT_PUBLIC_KEY_PATH=/keys/public.pem

   INVENTORY_DATABASE_URL=postgres://inventory:inventory@inventory-db:5432/inventory
   INVENTORY_JWT_PUBLIC_KEY_PATH=/keys/public.pem

   PAYMENT_DATABASE_URL=postgres://payment:payment@payment-db:5432/payment
   ```

3. Start everything. This also creates the topics and applies migrations:

   ```sh
   make up
   ```

Each service's interactive API docs are at `http://localhost:<port>/docs`.

## Trying it out

1. Register and log in with the user service: `POST /auth/register`, then `POST /auth/login`.
2. Create a product with inventory's `POST /products`. This needs an admin, and the API can't make one yet, so promote your user in the database:
   ```sh
   make psql s=user
   UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
   ```
   Log in again afterwards so the new role is in your token.
3. Place an order with `POST /orders`. It needs a `Bearer` token and an `Idempotency-Key` header.
4. Read it back with `GET /orders/{id}`. It goes from `pending` to `confirmed`, or to `cancelled` with a reason.

Payment declines any order whose total is over `PAYMENT_DECLINE_OVER` (default 1000), so you can try the failure path too.

To watch the events, run `make consume topic=orders` (or `inventory`, `payments`), or open Kafka UI.

## Commands

Run `make help` for the full list. The main ones:

| Command | What it does |
|---|---|
| `make up` / `make up s=order` | Build and start everything, or one service |
| `make down` | Stop containers, keep data |
| `make reset` | Stop everything and **delete** all databases and Kafka data |
| `make logs s=order` | Follow a service's logs |
| `make test s=order` | Run a service's tests in its container (`args="-k cancel -x"` to filter) |
| `make test-all` | Run every test suite |
| `make makemigrations s=order` | Generate a migration from model changes |
| `make migrate s=order` | Apply pending migrations |
| `make psql s=order` | Open `psql` on a service's database |
| `make topics` / `make consume topic=orders` | List topics / print a topic's messages |
| `make sync` | Install all workspace packages into the local `.venv` |

Tests run against each service's real Postgres, so the containers need to be running.

## Layout

```
libs/
  auth/          access-token checking shared by services
  events/        event contracts shared by services
services/<name>/
  src/<name>/
    api/         FastAPI routes, one file per endpoint
    services/    business logic and event handlers
    models/      Tortoise ORM models
    migrations/
    consuming.py Kafka consumer and event routing
    publishing.py outbox relay
    cleaning.py  hourly cleanup
  tests/
docs/kanban.md   what's done, what's next, open decisions
```

The consumer and relay code is copied into each service on purpose, rather than shared in `libs/`. Each service can change its own copy without affecting the others.
