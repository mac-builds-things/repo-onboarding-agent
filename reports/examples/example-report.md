# Onboarding Report: inventory-api

Generated: 2026-04-24T22:37:00Z

## Overview

`inventory-api` is a RESTful HTTP service built with **FastAPI** that manages product inventory for an e-commerce platform. It exposes CRUD endpoints for products, stock levels, warehouses, and purchase orders. The service persists data to a PostgreSQL database via SQLAlchemy ORM with Alembic handling schema migrations. It also integrates with an external supplier API to sync stock replenishment orders.

The codebase is approximately 8,000 lines of Python across ~60 files and has been in production since 2023. Test coverage sits around 72% (measured by pytest-cov). CI runs on GitHub Actions and deploys to AWS ECS via Terraform.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Web framework | FastAPI | 0.111 |
| ASGI server | Uvicorn | 0.29 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13 |
| Database | PostgreSQL | 15 |
| Validation | Pydantic v2 | 2.7 |
| Auth | JWT via `python-jose` | 3.3 |
| HTTP client | httpx | 0.27 |
| Testing | pytest + pytest-asyncio | 8.x |
| Linting | ruff | 0.4 |
| Type checking | mypy | 1.10 |
| Containerisation | Docker / Docker Compose | — |
| CI | GitHub Actions | — |
| IaC | Terraform (AWS ECS + RDS) | 1.8 |

---

## Directory Map

```
inventory-api/
├── alembic/                  # Migration scripts
│   ├── env.py                # Alembic runtime config (reads DATABASE_URL)
│   └── versions/             # Timestamped migration files
├── app/
│   ├── api/
│   │   ├── deps.py           # FastAPI dependency injection (DB session, current user)
│   │   ├── v1/
│   │   │   ├── products.py   # /v1/products CRUD router
│   │   │   ├── warehouses.py # /v1/warehouses router
│   │   │   ├── orders.py     # /v1/orders router
│   │   │   └── auth.py       # /v1/auth login + token refresh
│   ├── core/
│   │   ├── config.py         # Settings (pydantic-settings, reads .env)
│   │   ├── security.py       # JWT encode/decode, password hashing ⚠️
│   │   └── logging.py        # Structured JSON logging setup
│   ├── db/
│   │   ├── base.py           # SQLAlchemy declarative base
│   │   ├── session.py        # Async engine + session factory
│   │   └── models/           # ORM models (Product, Warehouse, Order, User)
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/
│   │   ├── inventory.py      # Business logic for stock adjustments
│   │   ├── supplier.py       # External supplier API client ⚠️
│   │   └── notifications.py  # Webhook dispatch on low-stock events
│   └── main.py               # FastAPI app factory, lifespan, middleware
├── tests/
│   ├── conftest.py           # Async test DB setup, fixtures
│   ├── api/                  # Route-level integration tests
│   └── services/             # Unit tests for service layer
├── docker-compose.yml        # Local dev: app + postgres + pgadmin
├── Dockerfile
├── Makefile                  # Developer shortcuts (see Key Commands)
├── pyproject.toml
└── .env.example
```

---

## Key Commands

| Name | Command | Description |
|---|---|---|
| **dev** | `uvicorn app.main:app --reload --port 8000` | Start dev server with hot-reload |
| **dev (docker)** | `docker compose up` | Full local stack (app + Postgres) |
| **test** | `pytest` | Run full test suite |
| **test:cov** | `pytest --cov=app --cov-report=term-missing` | Tests with coverage report |
| **test:fast** | `pytest -m "not slow"` | Skip slow integration tests |
| **migrate** | `alembic upgrade head` | Apply all pending migrations |
| **migrate:new** | `alembic revision --autogenerate -m "description"` | Generate a new migration |
| **migrate:down** | `alembic downgrade -1` | Roll back one migration |
| **lint** | `ruff check .` | Run linter |
| **format** | `ruff format .` | Auto-format code |
| **typecheck** | `mypy app` | Run type checker |
| **db:reset** | `make db-reset` | Drop + recreate local DB and re-migrate |
| **shell** | `python -c "from app.db.session import engine; ..."` | Quick DB inspection |

> **Prerequisite:** Copy `.env.example` to `.env` and fill in `DATABASE_URL`, `SECRET_KEY`, and `SUPPLIER_API_KEY` before running anything.

---

## Test Setup

Tests use `pytest-asyncio` in `auto` mode. An in-process PostgreSQL instance is created per session via the `conftest.py` fixture using `asyncpg` against a test database (`DATABASE_URL` is overridden to `...db_test`).

```
# Run all tests
pytest

# Run only unit tests (no DB)
pytest tests/services/ -m "not integration"

# Run with verbose output and stop on first failure
pytest -x -v
```

Fixtures of note (in `tests/conftest.py`):
- `async_client` — an `httpx.AsyncClient` wired to the FastAPI app
- `db_session` — a clean async DB session per test (rolls back after each test)
- `auth_headers` — pre-authenticated headers for a test user (role: `admin`)
- `sample_product` — a `Product` row pre-inserted for read tests

---

## Risky Areas

### 1. Auth Middleware — `app/core/security.py` + `app/api/deps.py`
**Risk level:** HIGH

JWT tokens are validated in `get_current_user` inside `deps.py`, which is injected as a FastAPI dependency on protected routes. The token secret is read from `settings.SECRET_KEY` at import time. Two concerns:

- Token expiry is set to **7 days** (`ACCESS_TOKEN_EXPIRE_MINUTES = 10080`) — longer than typical, meaning compromised tokens stay valid a long time.
- There is no token revocation mechanism (no blocklist). Logging out only removes the token client-side.

**Recommendation:** Before touching auth flows, read `security.py` end-to-end and trace the full request lifecycle with a debugger or `print`-tracing. Any change here affects every authenticated endpoint. Add an integration test before and after any modification.

---

### 2. Database Migrations — `alembic/versions/`
**Risk level:** HIGH

There are 34 migration files. Several early migrations were written by hand (not autogenerated) and include raw SQL for data backfills. Running `alembic upgrade head` on a database with existing data will execute these data migrations. The migration `0019_backfill_sku_codes.py` has a known issue noted in a code comment: it times out on tables with >500k rows and must be run in batches manually.

**Recommendation:** Never run `alembic upgrade head` directly against the production database. Read `alembic/env.py` and the last 5 migration files before generating a new revision. Always test migrations against a production-size snapshot first.

---

### 3. External Supplier API Client — `app/services/supplier.py`
**Risk level:** MEDIUM

`supplier.py` wraps a third-party REST API with no retry logic, no circuit breaker, and a hardcoded 30-second timeout. If the supplier API is slow, this will block async workers and degrade the entire service. The integration also has the fewest tests (2 tests, both mock the HTTP call entirely).

**Recommendation:** Do not extend `supplier.py` without adding at least one real integration test gated by a `SUPPLIER_API_KEY` environment variable in CI. Consider adding `tenacity` retry logic before adding new calls.

---

### 4. No-test Zone — `app/services/notifications.py`
**Risk level:** MEDIUM

The webhook notification service (`notifications.py`, ~300 lines) has **zero test coverage**. It dispatches HTTP POST requests to customer-configured webhook URLs when stock drops below a threshold. The dispatch logic uses a background `asyncio.Task` which can silently swallow exceptions.

**Recommendation:** Treat this file as fragile. Read it fully before any modifications. Any change should be accompanied by at least a basic unit test using `respx` to mock outbound HTTP.

---

## Entry Points

### 1. `app/main.py` — FastAPI application factory
This is the top-level entry point. It creates the `FastAPI` app instance, registers all routers under `/v1`, attaches middleware (CORS, request-id injection, structured logging), and defines the `lifespan` context manager that opens/closes the database engine. **Start here** when you want to understand the request pipeline.

### 2. `app/api/v1/products.py` — Products router
The most complete and well-tested router (~400 lines, 85% coverage). A good first file to read because it demonstrates the full pattern used across all routers: dependency injection for auth + DB session, Pydantic schema validation, service-layer delegation, and consistent error handling with `HTTPException`.

### 3. `alembic/env.py` — Migration runtime
If you need to work with the database schema, read this first. It shows how Alembic connects to the database, which models it imports for autogenerate, and how the async engine is configured.

---

## First Good Tasks

### Task 1 — Add pagination to `GET /v1/products` (Complexity: Low, ~2 hours)
The products list endpoint currently returns all rows (no limit). Adding `limit` + `offset` query parameters following the pattern already used in `GET /v1/warehouses` is a self-contained, well-tested area. Good way to learn the router → service → ORM → schema pipeline.

**Files to touch:** `app/api/v1/products.py`, `app/services/inventory.py`, `app/schemas/product.py`, `tests/api/test_products.py`

---

### Task 2 — Add a `GET /v1/products/{id}/stock-history` endpoint (Complexity: Medium, ~1 day)
A `StockEvent` model exists in `app/db/models/stock_event.py` but has no API exposure. Adding a read endpoint for it is bounded, touches the full stack, and has a clear acceptance criterion. The model already has an index on `product_id`.

**Files to touch:** `app/api/v1/products.py`, `app/schemas/stock_event.py` (new), `app/services/inventory.py`, `tests/api/test_products.py`

---

### Task 3 — Add retry logic to `supplier.py` using `tenacity` (Complexity: Medium, ~half day)
Wrapping the two outbound `httpx` calls in `@retry` decorators from `tenacity` (already in `requirements.txt` but unused) is a contained improvement with a clear before/after. Write a unit test using `respx` that asserts the call is retried on a 503 response.

**Files to touch:** `app/services/supplier.py`, `tests/services/test_supplier.py`

---

## Open Questions

1. **Token revocation strategy** — Is there a planned approach for invalidating JWTs on logout (e.g., Redis blocklist)? The current 7-day expiry with no revocation is a potential security gap. Worth discussing before any auth-related work.

2. **Migration batching for large tables** — Migration `0019` has a known timeout issue on large datasets. Is there a runbook for applying this in production? Is the production table already past 500k rows?

3. **Notification webhook reliability** — `notifications.py` uses fire-and-forget `asyncio.Task` with no persistence. If the app restarts mid-dispatch, webhook deliveries are silently lost. Is this intentional (best-effort), or is there a planned move to a proper job queue (e.g., Celery, ARQ)?
