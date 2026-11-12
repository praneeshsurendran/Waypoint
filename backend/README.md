# Waypoint backend

The working FastAPI implementation has moved from `api/` into the operations service.
The frontend retains its existing URLs. Identity, network/fleet, and notifications own
separate databases; orders, dispatch, warehouse, delivery and analytics remain together
inside operations for their existing transactional response contracts. Planning execution
and durable event publication/consumption run as separate worker processes.

## Implemented tree

```text
backend/
  services/
    identity-access/     # users, authentication, scoped administration
    network-fleet/       # outlets, depots, fleet, calendar, availability
    operations/          # orders, planning, loading, delivery, receipts, analytics
    notifications/       # inbox, scoped notices, read receipts
  packages/              # contracts, security, observability, messaging
  tests/                 # contract, e2e, resilience, performance
  scripts/               # seed, migrate, verify
  docs/                  # design, decisions, evidence, recovery runbooks
  local/                 # local-only DB/AWS initialization and Nginx
  docker-compose.yml
```

Each service contains its Dockerfile, pinned project metadata, migration history, source
package and preserved/added tests. Operations retains its original `alembic/` history;
new owner histories live under `migrations/`. No empty placeholder service directories exist.

## Local stack

```sh
cp backend/.env.example backend/.env
# Review local credentials. The defaults are synthetic development credentials only.
docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env up --build
```

Frontend: `http://localhost:5173`; API ingress: `http://localhost:8000/api/v1`.
Synthetic logins: `dispatcher`, `loader`, `driver`, `manager`, `admin`; password is
`DEMO_PASSWORD` from the local environment. No challenge CSV files are copied into images.
Seeding is idempotent and never resets existing rows or passwords. It creates 120 independently
generated outlets, 60 vehicles, calendar rows and representative orders.

Each context has a one-shot migration container. API replicas never run migrations at
startup. Do not delete Docker volumes to upgrade or reseed. Existing legacy volumes need
the reviewed transfer procedure in [migration.md](docs/runbooks/migration.md); the new local
Compose volume is intentionally different from the old monolith volume.

LocalStack supplies EventBridge/SQS/S3 locally. The pinned 3.8.1 image passed local fan-out,
DLQ redrive/replay and private-object tests, and the complete Docker workflow passed.
No AWS account is needed for local validation.
Nginx is a local substitute for API Gateway/ALB path routing, not an application gateway.

## Native validation

Use Python 3.12+ (validated with Python 3.13) and PostgreSQL 15+.

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.lock
export PYTHONPATH="$PWD/backend/services/operations/src:$PWD/backend/services/identity-access/src:$PWD/backend/services/network-fleet/src:$PWD/backend/services/notifications/src:$PWD/backend/packages/contracts:$PWD/backend/packages/security:$PWD/backend/packages/observability:$PWD/backend/packages/messaging"
export DATABASE_URL='postgresql+psycopg://TEST_USER:TEST_PASSWORD@localhost:5432/waypoint_operations_test'
export TEST_DATABASE_URL="$DATABASE_URL"
export JWT_SECRET='local-test-only-secret-with-at-least-32-characters'
export UPLOAD_DIR='/tmp/waypoint-test-uploads'
```

Provision **disposable** databases `waypoint_operations_test`, `waypoint_identity_services_test`,
`waypoint_network_services_test`, `waypoint_operations_services_test`,
`waypoint_notifications_services_test`, and `waypoint_concurrency_test` for the test user.
Tests refuse DDL unless the configured database ends in `_test`. Fixture creation/drop is
restricted to these test databases; never point tests at application databases.

```sh
.venv/bin/python -m pytest -c backend/pytest.ini backend -q
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend
(cd backend && ../.venv/bin/mypy --config-file mypy.ini)
.venv/bin/python backend/scripts/verify/architecture.py
.venv/bin/python -m compileall -q backend
docker compose config --quiet
cd frontend && npm run typecheck && npm run lint && npm test && npm run check:architecture && npm run build
```

All deployed services have `Dockerfile`, `pyproject.toml`, their own Alembic history,
`src/<package>/main.py`, transport routers, use cases, persistence and tests. The operations
package retains the `app` import namespace for existing deployment/test compatibility.
Shared packages contain API/event DTOs, identity verification, request tracing and AWS
transport adapters; they contain no shared ORM models.

See [architecture](docs/architecture.md), [API compatibility](docs/api-compatibility.md),
[data ownership](docs/data-ownership.md), [event catalog](docs/events.md),
[AWS deployment reference](docs/aws-architecture.md), and [validation results](docs/testing.md).
