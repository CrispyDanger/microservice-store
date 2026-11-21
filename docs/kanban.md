# Kanban

Last updated: 2026-11-20

## To do

### Order service

- Nothing left. Next up: inventory service.

## Backlog

### Inventory service

- [x] Persistence and Docker, same layout as the order service (port 8002).
- [x] `Product` model: id, name, price, stock (one column: quantity available to reserve).
- [x] Product API: public list and get; admin-only create and restock.
- [x] `StockReservation` (order_id, status, total, reject_reason) and `StockReservationItem` (product_id, quantity, unit_price).
- [x] Consume `OrderCreated`: lock the product rows sorted by id, reserve every item or none, compute the total from product prices.
- [x] Record `StockReserved(total, item prices)` or `StockRejected(reason)` through an outbox (copy of the order service's `publishing.py`).
- [x] Consume `OrderCancelled`: return the stock of a `reserved` reservation and mark it `released`.
- [x] `processed_events` duplicate check in the same transaction as each handler.
- [ ] Consumer and relay loops in `lifespan`, plus hourly cleanup.
- [x] Tests, including two orders racing for the last unit of stock.
- [ ] Order service follow-up: drop `total` from `POST /orders` and `OrderCreated`; save the total and unit prices from `StockReserved`.

### Payment service

- [ ] Persistence and Docker.
- [ ] Consume `StockReserved`: charge its `total` through a fake gateway, then record `PaymentSucceeded` or `PaymentFailed`.
- [ ] Consume `OrderCancelled`: refund if the payment already succeeded. Covers a user cancel or a timeout that lands after the charge.
- [ ] Outbox and `processed_events`, same as order.

### Notifications service

- [ ] Consume `OrderConfirmed` and `OrderCancelled`.
- [ ] Send a notification to the user. Start with a log line or a fake email sender.

### Cross-cutting

- [ ] Shared relay and consumer code. Inventory and payment need the same outbox relay and consumer loop as order. Inventory gets a copy; move them into a library under `libs/` when payment needs them too.
- [ ] Configure flake8 with `max-line-length = 100` to match the code.
- [ ] End-to-end test of the full saga across all services in Docker.

## Open decisions

- [ ] **Admin access to orders.** Should admins see and cancel other users' orders? Today every order endpoint is owner-only.
- [ ] **`?status=` filter** on `GET /orders`.
- [ ] **Running more than one relay.** Two relays can send events for the same order out of order. Keep one relay per service, or split the work by key, before scaling out.

## Done

### Order service

- [x] Persistence, migrations and Docker Compose setup.
- [x] API: place, get, list (offset pagination) and cancel orders, with RS256 JWT auth.
- [x] Required `Idempotency-Key` on `POST /orders`.
- [x] Transactional outbox: `Event` table and the relay in `publishing.py`.
- [x] Saga event contracts in `libs/events`; `order_id` typed as `UUID`.
- [x] Saga handlers in `services/finalize_order.py` with `processed_events` duplicate check.
- [x] Kafka consumer in `consuming.py` for the `inventory` and `payments` topics.
- [x] Saga timeout: `PENDING` orders older than 15 minutes are cancelled (`expiring.py`).
- [x] Hourly cleanup (`cleaning.py`): published `events` after 7 days, `processed_events` after 14 days (longer than Kafka's 7-day retention), `idempotency_keys` after 24 hours.
- [x] Logging setup (`logs.py`): root logger configured at startup, level from `ORDER_LOG_LEVEL` (default `INFO`).
- [x] Relay lag check: `GET /health/relay` reports the age of the oldest unpublished event and returns 503 past 60 seconds. `/health` stays 200 so a Kafka outage doesn't restart the container.
