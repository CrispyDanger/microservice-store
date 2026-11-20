# Kanban

Last updated: 2026-11-20

## To do

### Order service

- [ ] **Cleanup of old rows.** Runs in the `expiring.py` loop.
  - Delete published `events` rows older than 7 days.
  - Delete `processed_events` rows older than 14 days. This must stay longer than Kafka's retention (7 days by default), or a redelivered event slips past the duplicate check.
  - Delete `idempotency_keys` rows older than 24 hours.
  - Tests for each table: old rows go, recent rows stay, unpublished `events` rows are never deleted.
- [ ] **Logging setup.** The app configures no logging, so info lines such as "Cancelled N orders stuck in pending" never reach `docker compose logs`. Configure the root logger at startup, with the level from a setting.
- [ ] **Relay lag check.** Expose the age of the oldest unpublished `events` row, for example in `/health` or as a metric, so a stuck relay gets noticed.

## Backlog

### Inventory service

- [ ] Persistence and Docker, same layout as the order service.
- [ ] `Product` model: id, name, price, stock on hand, stock reserved.
- [ ] Product API: list and get products; admin-only create and restock.
- [ ] Consume `OrderCreated`: reserve every item in one transaction, locking the product rows; all items or none.
- [ ] Record `StockReserved` or `StockRejected(reason)` through an outbox, like `publishing.py` in the order service.
- [ ] Consume `OrderCancelled`: release the reserved stock for that order.
- [ ] `processed_events` duplicate check in the same transaction as each handler.
- [ ] Tests, including two orders racing for the last unit of stock.

### Payment service

- [ ] Persistence and Docker.
- [ ] Consume `OrderCreated`: store a pending payment with the order's amount.
- [ ] Consume `StockReserved`: charge through a fake gateway, then record `PaymentSucceeded` or `PaymentFailed`.
- [ ] Consume `OrderCancelled`: refund if the payment already succeeded. Covers a user cancel or a timeout that lands after the charge.
- [ ] Outbox and `processed_events`, same as order.

### Notifications service

- [ ] Consume `OrderConfirmed` and `OrderCancelled`.
- [ ] Send a notification to the user. Start with a log line or a fake email sender.

### Cross-cutting

- [ ] Shared relay and consumer code. Inventory and payment need the same outbox relay and consumer loop as order. Move them into a library under `libs/` once the second service needs them.
- [ ] Configure flake8 with `max-line-length = 100` to match the code.
- [ ] End-to-end test of the full saga across all services in Docker.

## Open decisions

- [ ] **Who sets the price.** Today the client sends `total`. Proposal: inventory owns prices, and the order service fetches them or inventory confirms the amount in `StockReserved`.
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
