# Executed validation — 2026-11-12

The implementation was validated with Python 3.13, native PostgreSQL 15, Node 22.23.3,
and Docker Desktop. The complete Docker stack uses PostgreSQL 16 and LocalStack 3.8.1.
All data used for validation was synthetic. No AWS account or cloud resource was used.
Machine-readable measurements: [validation-results.json](validation-results.json).

## Actual results

| Check | Actual result |
|---|---|
| Unchanged original backend baseline | 60 passed, 1 dataset-dependent skip; 63 existing Ruff errors |
| Final complete pytest suite | **91 passed, 1 skipped**, 44.90 seconds |
| Backend lint / format | Ruff passed; all Python source formatted |
| Backend type check | Mypy passed for 22 domain, port and contract modules; application/ORM integration is tested, not claimed fully statically typed |
| Backend architecture / compilation | Ownership, pure-domain and application-to-API dependency checks passed; compileall passed |
| Dependency consistency / security | pip check passed; pip-audit of the locked runtime dependencies found no known vulnerabilities |
| Frontend tests | **128 passed across 16 files** |
| Frontend static validation | TypeScript, ESLint, Prettier and architecture checks passed; architecture checker tests passed |
| Frontend production build | Passed; largest JS chunk 278.43 kB (86.46 kB gzip); no chunk-size warning |
| API compatibility | All 59 legacy operations covered; path/method/status/parameter/body-field/response-shape comparison passed |
| Docker images / startup | All four service images, seed image, migrations, APIs, seven publisher/consumer/planning processes, ingress and frontend started successfully |
| HTTP workflow through Docker | Five account logins; order/closure; real SQS planning job; publication; driver reassignment; shortage/release; departure/arrival; private S3 POD; duplicate offline replay and cursor-based recovery; repeated receipt; actual scoped notifications passed |
| Existing full demo Playwright suite | **50 passed / 49 failed**, identical failing cases to untouched HEAD; unchanged-HEAD comparison described below |
| Browser against migrated Docker APIs | Dispatcher, loader, driver, manager and administrator logins reached expected workspaces; no uncaught JS or API errors on those pages |
| Local AWS transport | EventBridge → dedicated SQS queue, private S3 roundtrip, DLQ redrive and same-body replay passed; temporary smoke resources cleaned up |
| Migrations | Four isolated non-superuser owner histories applied and repeated; correct heads and idempotent second upgrade verified |
| Data transfer / restore | Dry-run/apply/rerun passed; original IDs/password hash retained; source counts unchanged; cross-owner DB connection denied; pg_dump restored to another isolated DB with all table counts/checksums matching |

The single skip is the original demand-forecast test requiring an unavailable authorized CSV
file; it was retained. The single warning is Starlette's TestClient HTTPX deprecation warning.
No tests were deleted or skipped to make the migration pass. Original tests were moved with
the implementation; security fixtures now explicitly assign drivers and use valid image headers.
The lifecycle scenario freezes its before-cutoff time, avoiding dependence on the machine wall
clock. Separate late-cutoff tests continue to verify rejection.

Property tests generate 60 adversarial allocation cases per run. Added integration tests cover
resource scope, suspension/reset invalidation, cutoff/calendar bypass attempts, window alerts,
receipt replay, incremental sync recovery/paging and cross-actor denial, pending job cancellation, scheduler closure, transaction rollback, duplicate inbox
processing, stale projections, and concurrent publication. Frontend replay tests cover arrival
versus delivery, interrupted syncing, delay and unchanged photo/signature references
after a lost acknowledgement, cached routes after an offline restart, queued departure without
arrival, partial handoffs, renewed sign-off and manager receipts through their authorized endpoint. A restarted handler after commit/before acknowledgement creates
one notification and one delivery log. The Docker workflow exercises the actual queue and S3
adapters rather than mocking their business effects.

## Measured performance and limits

On the native real PostgreSQL test database, 120 synthetic outlets, 60 vehicles and 120 orders
produced 79 served / 41 explained deferrals in **0.063 seconds**. The order-list API p95 was
**47.99 ms across 20 requests**. Identity was reached through an in-process HTTP test transport;
these figures exclude network/cloud latency and do not establish allocation optimality.

Three sequential real Docker workflows completed three planning jobs with queue-to-completion
times **2.064, 2.047 and 2.068 seconds**. All three complete workflows took **10.949 seconds**,
observing **16.44 successful jobs/minute including workflow overhead**. This bounded sequential
measurement is not a saturation benchmark or a promised worker capacity. Repeat with representative
production data and concurrent producers before choosing ECS scaling limits.

## Reproduce

Follow [the backend README](../README.md) for the venv, PYTHONPATH, disposable test databases
and environment variables. From the repository root:

```sh
.venv/bin/python -m pytest -c backend/pytest.ini backend -q
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend
(cd backend && ../.venv/bin/mypy --config-file mypy.ini)
.venv/bin/python backend/scripts/verify/architecture.py
.venv/bin/python backend/scripts/verify/export_contracts.py
.venv/bin/python -m compileall -q backend
.venv/bin/pip check
(cd frontend && npm test && npm run typecheck && npm run lint && npm run format:check && npm run check:architecture && npm run test:architecture && npm run build)
docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env up -d --build
```

Provide DEMO_PASSWORD via the environment without printing it. Against the default local stack:

```sh
API_BASE_URL=http://localhost:8000 .venv/bin/python backend/scripts/verify/http_workflow.py
API_BASE_URL=http://localhost:8000 .venv/bin/python backend/scripts/verify/queue_benchmark.py --samples 3
node backend/scripts/verify/browser_roles.mjs
docker compose --env-file backend/.env run --rm --no-deps seed python scripts/verify/local_aws.py
```

The browser check uses the frontend's installed Playwright package and installed Chromium;
PLAYWRIGHT_CHROMIUM_EXECUTABLE can select an existing binary. Override FRONTEND_BASE_URL /
API_BASE_URL when using alternative local ports and include that frontend origin in CORS.
Write smokes refuse non-local hosts. Repeated workflows choose unused future operating dates
and retain prior records. LocalStack smoke resources use random names and are removed in finally
blocks; application queues and evidence are never purged.

Set IDENTITY_TEST_DATABASE_URL, NETWORK_TEST_DATABASE_URL, OPERATIONS_TEST_DATABASE_URL and
NOTIFICATIONS_TEST_DATABASE_URL to dedicated disposable databases, then run
`python backend/scripts/verify/migrations.py`. It refuses names without `_test`, upgrades each
owner twice and checks the exact head. For transfer, backup and checksum verification follow
[the migration runbook](runbooks/migration.md). The actual run used isolated `_owned_test`
databases with non-superuser credentials and a separate legacy/restore pair; no application DB
was reset. The temporary Docker validation project used alternate ports and was isolated from
other projects. Shutdown retains its volumes; no `down -v` is required.

For S1, run `scripts/verify/s1.py --help` with the operations PYTHONPATH. Provide authorized
CSV inputs explicitly and an output outside the repository. Unit/property tests use independent
synthetic values; no competition dataset results or Datathon accuracy claims are made.

## Remaining validation and product limits

- AWS IAM denial rules, API Gateway/Lambda authorizer/stage rewrite, private network/TLS,
  real S3 presigned URL expiry, Multi-AZ failover, PITR, cross-AZ costs and ECS stop/scaling
  behavior require the deployment owner's AWS acceptance tests. LocalStack does not prove them.
- In-app notifications are implemented. WebPush/SMTP/SMS providers are unconfigured; push
  subscription requests explicitly return 501. There is no claim of background browser delivery.
- Correlation/W3C context and JSON request timing logs are implemented. An OpenTelemetry
  exporter/collector and cloud dashboards are deployment follow-ups.
- The historical demand estimator remains optional and reports missing data explicitly. No
  proprietary prediction API or invented ML integration was added.
- Generic allocation is deterministic and feasible, not optimal. Actual fuel receipt/accounting
  integration is absent from the original application; cumulative planning checks use the owned
  quota/weekly-usage snapshot. Do not interpret that as measured fuel settlement.
- The final full demo Playwright run has 50 passed and 49 failed, with exactly the same
  failing cases as untouched HEAD. An initial additional route failure passed its isolated
  recheck and the final full run. The complete baseline
  comparison and failure inventory are in [browser-validation.md](browser-validation.md).
  The five role entry workspaces passed against the actual migrated Docker APIs. The four-role
  business lifecycle passed PostgreSQL integration and real Docker HTTP workflows.
- Local queued records created before actor attribution remain preserved; ownership must be
  reconciled before replay. The migration does not guess an author or delete that evidence.
- Orders/planning/loading/delivery remain one transactional operations deployment. Independent
  extraction requires the read models and consistency work described in the ADR; it is not
  misrepresented as eight independently owned databases.

No CI/CD, infrastructure-as-code or live AWS provisioning was implemented.
