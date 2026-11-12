# Operations service

Owns order intake, dispatch/planning, loading, delivery, receipts, proof metadata and their
transactional audit/reliability records. Identity and network rows in this database are local
projections. Independently deployed identity/network services own their authoritative data.

Runtime: `uvicorn app.main:app --host 0.0.0.0 --port 8000` with `SERVICE_MODE=operations`
and `IDENTITY_URL` set. Apply `alembic -c alembic.ini upgrade head` from a dedicated migration
job before serving traffic. API replicas never migrate or seed on startup.

Workers: `python -m app.workers.publisher`, `python -m app.workers.events`, and
`python -m app.workers.planning`. They use the same owner DB, isolated queues and task roles.

The `legacy` mode exists for preserved tests/backward-compatible maintenance only. Never
use legacy authentication/reference ownership as a deployed substitute for the isolated stack.
See [backend README](../../README.md) and [architecture](../../docs/architecture.md).
