# Waypoint

Delivery planning for Fresh, Style and Tech: store managers place orders, dispatchers plan
and publish runs, loaders prepare vehicles, drivers deliver with offline replay, and stores
confirm receipts or report issues.

| Part | Implementation |
|---|---|
| `backend/` | FastAPI APIs and workers; separately owned PostgreSQL databases; Alembic; JWT authorization; EventBridge/SQS adapters; private S3 evidence |
| `frontend/` | React/TypeScript/Vite; atomic components and feature pages; TanStack Query; Dexie offline evidence and exact event replay |
| `docs/` | Challenge, audit, architecture and deployment references |

## Run locally

```sh
cp backend/.env.example backend/.env
docker compose --env-file backend/.env up --build
```

Frontend: http://localhost:5173. API ingress: http://localhost:8000/api/v1.
The local stack uses synthetic data, one-shot migrations, separate service credentials and
LocalStack for EventBridge/SQS/S3. Logins are `dispatcher`, `loader`, `driver`, `manager`,
`admin`, using `DEMO_PASSWORD` from the local environment. Keep production credentials and
original competition datasets outside images and public repositories.

Do not reset or delete existing database/upload volumes to migrate. The original source and
new owner data need the [backup/transfer runbook](backend/docs/runbooks/migration.md).

## Development and validation

- [Backend startup, native tests and migration commands](backend/README.md)
- [Frontend development](frontend/README.md)
- [Repository audit and compatibility findings](docs/backend-audit.md)
- [Implemented architecture](backend/docs/architecture.md)
- [API ownership and preserved contracts](backend/docs/api-compatibility.md)
- [Data ownership](backend/docs/data-ownership.md) and [event contracts](backend/docs/events.md)
- [AWS deployment reference](backend/docs/aws-architecture.md)
- [Executed checks and limitations](backend/docs/testing.md)

The former monolith code/tests now live in `backend/services/operations`. Identity,
network/fleet and notifications are independent services; order/dispatch/loading/delivery
remain co-owned in operations to preserve working transactional contracts. Planning has a
separate asynchronous worker and a synchronous compatibility endpoint for the current UI.
No CI/CD, infrastructure-as-code or live AWS resources are implemented here.

The original deployment links, fixture-specific accounts, dates and judge walkthrough are
preserved in [the archived walkthrough](backend/docs/legacy-walkthrough.md). They describe the
previous demo and are not current local startup instructions.
