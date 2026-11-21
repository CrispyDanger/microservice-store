export MSYS_NO_PATHCONV := 1

DC := docker compose
DB_SERVICES := user order inventory
s ?=
topic ?= orders
args ?=

require-s = $(if $(filter $(s),$(DB_SERVICES)),,$(error pass s=<$(DB_SERVICES)>, e.g. make $@ s=order))

.DEFAULT_GOAL := help
.PHONY: help up down reset build ps logs restart shell test test-auth test-all \
        makemigrations migrate psql topics consume sync

help: ## List the commands
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Build and start everything (or one: s=order)
	$(DC) up -d --build $(s)

down: ## Stop and remove containers, keep data
	$(DC) down

reset: ## Stop everything and DELETE all volumes (databases, Kafka data)
	$(DC) down -v

build: ## Rebuild images (or one: s=order)
	$(DC) build $(s)

ps: ## Show container status
	$(DC) ps -a

logs: ## Follow logs (or one: s=order)
	$(DC) logs -f --tail 100 $(s)

restart: ## Restart a service: s=order
	$(require-s)
	$(DC) restart $(s)

shell: ## Open a shell in a service container: s=order
	$(require-s)
	$(DC) exec $(s) sh

test: ## Run a service's tests: s=order [args="-k cancel -x"]
	$(require-s)
	$(DC) exec -w /app/services/$(s) $(s) pytest -q $(args)

test-auth: ## Run libs/auth tests (inside the user container)
	$(DC) exec -w /app/libs/auth user pytest -q $(args)

test-all: ## Run every test suite
	$(MAKE) test s=user
	$(MAKE) test s=order
	$(MAKE) test s=inventory
	$(MAKE) test-auth

makemigrations: ## Generate a migration from model changes: s=order
	$(require-s)
	$(DC) run --rm $(s)-migrate tortoise -c $(s).db.TORTOISE_ORM makemigrations

migrate: ## Apply pending migrations: s=order
	$(require-s)
	$(DC) run --rm $(s)-migrate

psql: ## Open psql on a service's database: s=order
	$(require-s)
	$(DC) exec $(s)-db psql -U $(s) -d $(s)

topics: ## List Kafka topics
	$(DC) exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

consume: ## Print all messages on a topic: [topic=orders]
	$(DC) exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 \
		--topic $(topic) --from-beginning --timeout-ms 5000

sync: ## Install all workspace packages into the local .venv
	uv sync --all-packages
