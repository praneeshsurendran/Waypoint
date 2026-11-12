# Codex Task — Audit, Complete, and Refactor the Waypoint FastAPI Backend into Microservices

## 0. Mission and scope

You are working in an existing **Waypoint Delivery Management System** monorepo. The **React + TypeScript + Vite frontend is implemented and must remain functionally intact**, while the **Python FastAPI backend is incomplete and requires substantial refactoring**.

**Your job is to inspect the ACTUAL repository, produce an evidence-based bounded-context design, and then IMPLEMENT the backend migration and missing critical behavior**, not merely describe an architecture. Preserve functional frontend API contracts unless a backward-compatible adapter is unavoidable. Use the challenge specification and existing frontend behavior as complementary inputs; make discrepancies explicit. Do not invent pre-existing code or claim unexecuted tests passed.

Do not write CI/CD, Terraform, CloudFormation, CDK, Pulumi, Helm charts, GitHub Actions workflows, or AWS provisioning scripts. I will handle CI/CD and infrastructure-as-code. Do prepare Dockerfiles, `docker-compose.yml`, runtime settings, health checks, local supporting services and deployment documentation.

Read `docs/aws-architecture.md` if provided. If it is not in this checkout, use the AWS target architecture below and write the document yourself. Inspect any original challenge brief, design specification, seed data and README that are actually present. Do not assume attachments from a separate chat are physically available in the repo.

## 1. Mandatory repository audit — FIRST

Inspect every existing backend directory and its structure, FastAPI app initialization, routers, dependencies, request/response schemas, ORM models, migrations, authentication, authorization, business services, algorithms, background tasks, storage, database configuration, datasets/seeding, test fixtures and external integrations. Inspect frontend route modules, `src/api`, `src/queries`, schemas, role flows and actual HTTP usage to identify **all endpoints the completed frontend expects**.

Before moving files, write `docs/backend-audit.md` with:

1. Complete current route inventory: HTTP method, path, body/query shape, response, auth/role, consuming frontend page/hook, implementation status, business owner and proposed new service.
2. Existing database tables, foreign keys, migrations, data ownership and shared DB coupling.
3. Business features that work, are incomplete, are hardcoded/stubbed or are broken; show evidence and prioritized remediation.
4. Existing event/background logic, performance bottlenecks, blocking I/O and concurrency hazards.
5. Test/build baseline: real commands, failures and causes (including pre-existing ones).
6. Dependency map and proposed bounded contexts, with justification for which ones should be separate deployments now vs later.
7. A migration/compatibility matrix and data migration/rollback plan, including a no-data-loss constraint.

Do not introduce microservices solely to have more services. Keep independently deployable boundaries around real business capabilities.

## 2. Target bounded contexts

Validate these initial candidates against the code and adjust only with clearly documented rationale:

- **Identity & Access:** dispatcher, loader, driver and store manager roles; outlet/depot scoped permissions; use an existing secure identity implementation or managed IdP integration rather than replacing authentication gratuitously.
- **Network & Fleet:** outlets, depots, vehicles, vehicle availability, refrigeration, van-only capability, weight/volume limits, fuel quotas and operating calendar.
- **Order Management:** order entry, validation, confirmation, next-day cutoff at 16:00 Asia/Colombo, closure snapshots, order state and history.
- **Dispatch & Planning:** capacity-constrained allocation, routes, stop order, plan versions, deferrals, fairness, manual/assisted allocation, optimization jobs, validation and publication.
- **Warehouse & Loading:** loading manifests, sequence and readiness, discrepancies, damage, shortages and release to driver.
- **Delivery & Tracking:** trip state, driver stop completion, offline event replay, proof-of-delivery, delivery exceptions, store manager receipt/issues.
- **Notifications:** consuming business events; dispatch/deferral/loading/delivery/ETA alerts and delivery log. May initially run as a worker process instead of an independent public API.
- **Forecasting & Intelligence (optional):** service duration, lateness risk and future depot/brand demand forecast; only separate if the repo contains functioning related logic or integration is explicitly needed. The Datathon ML system was not required to be integrated with the Hackathon system.

Do not create business features absent from both the challenge and current frontend simply to fill out the service map. Keep feature ownership and data ownership explicit.

## 3. Essential business invariants — these are testable acceptance criteria

Use the actual challenge booklet and repository data to resolve all ambiguities. The brief describes 120 outlets (80 Fresh, 25 Style, 15 Tech), 60 vehicles across Peliyagoda and Kandy; 12 refrigerated trucks and 4 refrigerated vans among the fleet. The four roles are dispatcher, loader, driver and store manager.

- Every route respects vehicle **weight AND volume** limits; chilled/frozen orders require a reefer; reefers may carry ambient goods; van-only outlets require vans.
- Vehicles serve their assigned depots; consider unavailable/workshop vehicles, store receiving windows, malls, weekly fuel quotas and at most **two trips per vehicle per operating day**.
- Fresh needs arrival before its stores open at 08:00, subject to the specific outlet window; use Monday–Saturday / `calendar.csv` operating-day flags as appropriate.
- Next-day orders close at **16:00 Asia/Colombo**; late submissions must not be silently admitted to the closed run.
- An order may be deferred, but a deferment must include a durable reason, actor/decision trace, consequences and repeat-deferral history. Never silently drop an order from allocation results.
- Preserve whole-order identity. Multiple orders can belong to the same outlet on a day. Never use `outlet_id` as a unique order key.
- Loading lists reflect planned stop sequence. Record shortages/damage before departure and keep a trace of any resulting replan.
- Driver actions are usable offline and safely replayed: idempotency key/device event ID, monotonic per-device ordering where relevant, deduplication, reconciliation policy, durable audit trail, conflict response and sync cursor.
- Proof-of-delivery and store receipt are distinct workflow actions; record status/history without losing the offline original.

**Special Task 2B scenario S1 — keep scenario-specific rules explicit:** Each vehicle/trip contains ONE brand and ONE district; every scenario order keyed by `order_ref` is `served` or `deferred`; no splitting; exclude `in_workshop`; at most 2 trips/vehicle; trip time = depot-to-district freeflow + inter-stop freeflow × (order count - 1) + sum of brand/dock service allowances. DO NOT add return time for S1. Per-vehicle Fresh total ≤270 min in the 03:30–08:00 window; combined Style+Tech total ≤480 min in their operating window. An order marked served must have a vehicle_id and trip_id ∈ {1,2}; deferred has neither. These S1 checks do not automatically override distinct generic production planning policies.

If predictions are integrated, make model interfaces swappable and versioned. Do not call proprietary pretrained prediction APIs or silently violate competition dataset/model constraints. Do not treat forecast output as guaranteed actual demand.

## 4. Mandatory monorepo backend structure

Adopt an appropriate version of this structure; keep existing repo naming only where it is demonstrably better. Do not build directories containing no code:

```text
backend/
├── services/
│   ├── identity-access/                 # If not completely managed via IdP
│   ├── network-fleet/
│   ├── order-management/
│   ├── dispatch-planning/
│   ├── warehouse-loading/
│   ├── delivery-tracking/
│   ├── notifications/
│   └── forecasting/                     # Optional
├── packages/
│   ├── contracts/                       # Versioned API/event schema contracts only
│   ├── observability/                   # Generic logging, tracing, metrics
│   ├── security/                        # Common validation utilities, NOT blanket auth
│   └── test-support/                    # Shared test factories/helpers
├── tests/
│   ├── e2e/                             # Cross-service, four-role workflows
│   ├── contract/                        # Frontend compatibility + event schemas
│   ├── performance/
│   └── resilience/
├── scripts/
│   ├── seed/                             # Allowed demo/synthetic seeding
│   ├── migrate/                          # Safe migration/verification/rollback scripts
│   └── verify/                           # Local check commands
├── docs/
│   ├── backend-audit.md
│   ├── architecture.md
│   ├── aws-architecture.md
│   ├── data-ownership.md
│   ├── api-compatibility.md
│   ├── events.md
│   ├── testing.md
│   ├── runbooks/
│   └── adr/
├── docker-compose.yml
├── .env.example
└── README.md
```

**Every independently deployed FastAPI service** must follow this template with clean boundaries:

```text
services/<service-name>/
├── Dockerfile
├── pyproject.toml
├── alembic.ini                         # If it owns relational persistence
├── migrations/
├── src/<python_service_package>/
│   ├── main.py                         # App factory, lifespan, health probes
│   ├── bootstrap.py                    # Dependency injection / adapters wiring
│   ├── api/
│   │   ├── v1/routers/                # Thin FastAPI route handlers
│   │   ├── dependencies.py
│   │   ├── requests/                   # Pydantic input DTOs
│   │   ├── responses/                  # Output DTOs
│   │   └── exception_handlers.py
│   ├── application/
│   │   ├── services/
│   │   ├── use_cases/
│   │   ├── commands/
│   │   ├── queries/
│   │   └── interfaces/                 # Protocols / ABC ports
│   ├── domain/
│   │   ├── models/                     # Domain entities and aggregates
│   │   ├── value_objects/
│   │   ├── events/
│   │   ├── rules/                      # Invariants / specifications
│   │   └── exceptions.py
│   ├── infrastructure/
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   ├── models/                 # SQLAlchemy ORM models, separate from domain
│   │   │   └── repositories/
│   │   ├── messaging/
│   │   │   ├── publisher.py
│   │   │   ├── consumers.py
│   │   │   ├── outbox.py
│   │   │   └── inbox.py
│   │   ├── clients/                     # Typed external/other-service clients
│   │   ├── storage/
│   │   └── security/
│   ├── workers/                         # Optional SQS consumers/job handlers
│   └── core/                            # Settings, logging, tracing, error mapping
└── tests/
    ├── unit/
    ├── integration/
    └── contract/
```

### Architecture rules

1. `api` handles transport only, calls use cases and maps schemas/errors; no business rules in routers.
2. `application` orchestrates use cases and defines repository/external interfaces. Use typed dependency inversion (`Protocol`/`ABC`) where useful.
3. `domain` contains business invariants, value objects, entities and state transitions; no FastAPI/ORM/AWS dependencies.
4. `infrastructure/db/models` contains persistence ORM mappings; **do not confuse API DTOs, domain models and SQLAlchemy models**.
5. `infrastructure` implements repositories, SQL/S3/SQS/HTTP adapters and external communication.
6. `workers` host background consumers/jobs separately from HTTP handlers.
7. Each service owns its tables/migrations/credentials. No shared SQLAlchemy entity package, cross-service foreign keys or direct access to another service's tables.
8. Extract only genuinely reusable technical code to `packages`. Avoid a large 'shared' service or packages that couple contexts.
9. Use a **repository pattern**, **unit of work** for multi-record local transactions, **dependency injection**, **factory/adapters**, **strategy + specification** for planning constraints, **state machines** for workflow, **outbox + inbox/idempotent consumer** for durable events; **CQRS** only where read/write needs differ. Use sagas/process managers only for real cross-service workflows.
10. Prefer SQLAlchemy 2.x, Alembic, Pydantic v2, and pytest only after checking existing dependencies. Pin compatible dependency versions and use lint/type checks. Avoid redundant layering on simple CRUD.

## 5. Gateway, synchronous calls and frontend API stability

Use **Amazon API Gateway REST API** (public regional API, WAF and authentication) → **VPC Link V2** → internal ALB → private ECS Fargate service target groups. The gateway is AWS-managed; **do not create an unnecessary custom FastAPI API gateway**.

- Preserve current frontend endpoint URLs, request schemas, response shapes, HTTP statuses, error codes, pagination, CORS, refresh/auth flows and protected routes. Introduce versioned API routes or a compatibility facade only where necessary, with corresponding contract tests.
- Implement per-role AND per-outlet/depot authorization checks **inside services**; do not trust client-submitted role or forwarded unverified identity headers.
- Define OpenAPI contracts and a route-to-service matrix. Namespace backend internal routes where helpful without forcing frontend rewrites.
- Only use synchronous service-to-service HTTP for low-latency calls requiring an immediate answer; bound timeouts/retries, use circuit-breaker-like behavior where justified and do not form deep call chains. Use event-driven projections or explicit consistent snapshots for most cross-domain state.
- Authentication: inspect existing auth; keep it if secure, otherwise propose/manage a Cognito/OIDC adapter that is compatible with the frontend. Document exact authorizer plan, claims, key rotation and authorization checks. Do not silently replace auth and break login.

## 6. Asynchronous messaging — reliable by design

Use a **custom EventBridge bus** for published domain/integration events. Route events to **one dedicated SQS queue per consuming service/handler** (with DLQ). Use a separate SQS job queue for expensive route optimization. These are architecture requirements, not optional TODOs.

Implement:

- Durable event envelopes: `event_id`, `event_type`, `version`, `occurred_at` in UTC, `aggregate_id`, `source`, `correlation_id`, `data` and optional causation metadata.
- Transactional outbox: business state change + outbox record in one local DB transaction; retrying publisher; no publishing before commit.
- Idempotent consumer/inbox: store processed event IDs, commit event effects in a local transaction, acknowledge only after success, retry transient failures, DLQ poison messages, document manual replay.
- Tolerate at-least-once delivery and out-of-order arrival; do not promise exactly-once transport.
- Correlation IDs and distributed trace propagation across HTTP and event boundaries.
- Versioned events and consumer contract tests. Avoid blindly importing producer Python ORM classes into consumers.
- Typed interfaces for local testing; where LocalStack/other emulators are used, verify support before depending on them. Do not hard-wire AWS credentials in source.

Design and implement event flows for at least:

`order.confirmed` → planning visibility; `orders.closed` → planning job; `plan.published` → loading and delivery read models; `order.deferred` → manager notification/history; `load.shortfall_reported` → dispatch coordination; `load.completed` → driver readiness; `delivery.started`/`stop.completed`/`delivery.failed` → tracking/notification; `proof_of_delivery.recorded` → outlet receipt; `receipt.confirmed`/`receipt.issue_reported` → final status/audit.

Choose exact event names based on code and document the contract/catalog in `docs/events.md`.

## 7. Database and storage architecture

- Use PostgreSQL, locally via Docker Compose and in AWS via **RDS PostgreSQL**. Start with one RDS instance if appropriate for cost, but give each context a dedicated database or schema, migration history and least-privileged DB user. **No cross-service SQL joins**. Use events, APIs or read projections to obtain other context's state.
- Migrate existing data safely. Do not drop tables/truncate/reset datasets, corrupt primary keys, or re-seed production/test data destructively. Create backups, integrity checks, dry-run migrations and rollback instructions before invasive changes.
- Use bounded DB pools, short-lived sessions, transaction scopes, indexes and pagination. Explicitly handle concurrent plan updates and race conditions with versioning/locking.
- Implement private S3 object storage adapter for proof-of-delivery and permitted imports/exports. Store only metadata/key references in PostgreSQL. Use presigned URLs when appropriate, enforce ownership, expiration, size/type/key restrictions; do not place proof objects in public frontend S3.
- Optional Redis only if measured performance/read projection/coordination needs justify it; no unnecessary new infrastructure.

## 8. Planning and optimization engine

The planning service must be an actual testable engine, not fake/demo-only allocation. Analyze existing algorithms and preserve working behavior before enhancing them.

- Separate **constraint validation**, **priority/deferral policy**, **assignment strategy/optimizer**, **plan persistence**, **manual adjustment**, and **explainability**.
- Use deterministic feasibility checking independent of any optimization solver. Implement OR-Tools or another justified optimization approach if helpful; wrap it behind a typed strategy interface. Provide a deterministic fallback that still produces a **valid** served/deferred result, never an invalid route.
- Validate both aggregate trip capacity and every individual assignment; use `order_ref` not `outlet_id` for scenario S1. Do not allow two workers to publish contradictory plans for the same run.
- Long-running planning requests should create an async job and return `202 Accepted`/job ID while a worker computes, unless existing frontend contracts require an adapter. Expose status, validation errors, cancellation behavior and final plans through stable endpoints.
- Make deferrals explainable with reason codes (vehicle unavailable, reefer shortage, volume/weight, window, fuel, capacity or priority) and policy rationale. Include unit and property tests generating adversarial combinations.
- Keep service-time/lateness forecasts **advisory** unless explicitly stated by the rule set; hard constraints must remain enforced regardless of prediction.

## 9. Offline and recovery requirements

The challenge expects offline mobile driver workflows. Do not assume online-only CRUD is sufficient.

Implement a compatible server-side sync protocol matched to the existing frontend implementation:

- Batched mutations with stable `device_event_id`/idempotency key, actor, aggregate and client timestamp, server receive time and optional expected aggregate version.
- Per-event accepted/rejected/conflict results and a server cursor for incremental pull; no lost updates on retry.
- Clear conflict rules: keep immutable history, preserve driver-entered delivery evidence, reject or reconcile stale route assignments, and surface user-visible reconciliation feedback via existing API shapes.
- Multiple retries and out-of-order event deliveries cannot double-complete an order or create duplicate POD records.
- Network interruption/reconnect, duplicate uploads, partially completed sync, and service restart tests.
- Keep user interaction safe; no requirement for drivers to operate while moving.

## 10. AWS deployment architecture document — REQUIRED FILE

Create/update `docs/aws-architecture.md` as an **implementation-oriented Markdown document with Mermaid diagrams**. Must include:

1. Architecture decision record comparing ECS Fargate with EKS (choose Fargate baseline unless actual code/resource requirements favor EKS), REST API vs HTTP API including accurate WAF limitations, and EventBridge+SQS vs broker alternatives.
2. Region choice (e.g. evaluate ap-south-1 for Sri Lanka) with checked service availability/cost/latency; no invented prices or assurances.
3. VPC design, two Availability Zones, example CIDRs, public/NAT, private app, isolated data subnets, Internet Gateway, routing tables, VPC Link ENIs, ingress and egress.
4. Security groups with explicit allowed directions and ports; NACL strategy with stateless return/ephemeral port handling; no public RDS, ECS task or internal ALB endpoints.
5. Route 53 + ACM + Regional API Gateway REST API + WAF + VPC Link V2 + internal ALB + ECS Fargate service target groups and API route mapping.
6. ECR repositories, ECS API tasks and independent worker tasks, health/liveness/readiness, scaling rules, bounded worker concurrency, graceful shutdown, SQS autoscaling from backlog-per-task.
7. RDS PostgreSQL instance/subnet group, isolation per service, read/write access matrix, encryption, TLS, backup/PITR, production Multi-AZ vs demo Single-AZ, RDS Proxy only if needed.
8. EventBridge rules, SQS consumer queues and DLQs, visibility timeouts, retry/backoff, outbox/inbox transaction logic, replay procedures.
9. Private S3 frontend bucket (CloudFront OAC), separate private POD bucket, imports/exports and lifecycle/retention, signed URL flows, bucket policy, SSE and KMS decisions.
10. Secrets Manager, IAM execution/task roles, least-privilege service access, audit logging, CloudWatch metrics, tracing, alerts, operational dashboards.
11. S3 Gateway endpoints and interface endpoints for used AWS services where cost-effective; tradeoffs with NAT gateways and cross-AZ costs.
12. Demo vs reliable-production environment profiles and explicit cost/availability tradeoffs (no unverified numeric cost claims).
13. Threat model: endpoint abuse, role escalation, cross-outlet data access, proof upload abuse, queue poison messages, data loss, credential leakage and offline conflict handling.
14. Recovery objectives (propose RTO/RPO as assumptions, do not fabricate committed SLAs), DB restore exercises, runbooks, failure modes and verification checklist.
15. Local development mapping from Docker Compose dependencies to AWS managed services.

DO NOT provision actual AWS resources or write infrastructure-as-code; keep this as documentation and app-level deployment readiness.

## 11. Runtime deployment readiness

- Use environment-driven Pydantic settings with validated required configuration; separate local/test/prod settings without hardcoded credentials. Provide `.env.example` only with safe placeholders.
- Dockerize each deployable service with reasonably small, non-root production images, deterministic dependency locking, no development secrets, and correct startup commands; avoid running schema migrations concurrently from all replicas.
- Add `/health/live` and `/health/ready`, graceful SIGTERM handling, bounded outbound retries and worker visibility-timeout management.
- Structured JSON logs with request/correlation IDs, UTC timestamps; consistent error envelopes; OpenTelemetry traces/metrics where practical. Avoid logging tokens, raw proof contents or private user data.
- ASGI async endpoints should not run blocking optimizer/model/CPU tasks; use workers. Correctly bound SQL connection pools, concurrency, memory and timeouts.
- Add secure CORS, input limits, output filtering, server-side pagination, resource-level authorization, SQL index reviews, explicit dependency constraints, and resilience to transient AWS/DB failures.
- Compose must start a complete local stack with PostgreSQL, services, queue and S3-compatible test adapters/emulators where practical, deterministic migrations, permitted synthetic seed data and usable role accounts. Do not assume a paid AWS account is required to execute tests.

## 12. Testing — implement and actually run

Adopt pytest, pytest-asyncio/anyio, HTTPX ASGI transport, Testcontainers for PostgreSQL or equivalent real integration DB, and Hypothesis/property tests where suitable, respecting existing libraries. Keep tests **inside each service** under `tests/unit`, `tests/integration`, `tests/contract`; cross-service workflows under `backend/tests/e2e`, `contract`, `resilience` and `performance`.

Minimum acceptance suites:

- Unit: domains, state transitions, permissions and scope, order cutoff/calendar logic, trip max count, weight/volume/reefer/van/depots/windows/fuel, deferrals, S1 time/brand/district policies, deterministic allocation.
- Property-based: every input order exactly once served/deferred; no order split; every served route respects all configured invariants, even when generated input cannot be fully served.
- API contract: every frontend-used endpoint, method/path, request/response/error envelope, auth behavior, filtering, sorting, pagination, upload URLs and job-status behavior remains compatible or is adapted explicitly.
- DB integration: migrated schemas, foreign keys within ownership, transactional commits/rollbacks, outbox atomicity, inbox/idempotent handling, concurrent publish/replan and seed rerun.
- Messaging: duplicate event deliveries, out-of-order delivery, worker crash after commit/before ack, transient failures, DLQ routing and safe replay; test against local adapter/emulator and clearly identify which AWS semantics require a deployed integration test later.
- Security: role-based and row/resource-based authorization, cross-outlet/depot access denial, malformed JWT/bad credentials, forged headers, presigned URL authorization and object ownership.
- Workflow E2E across all four roles: order → cutoff → plan (served+deferred) → loading (including shortfall) → driver delivery + POD offline → sync/replay → store receipt/issue → notification/read model.
- Performance: load at realistic competition scale, 120 outlets, 60 vehicles and a peak day; record plan duration, API p95 and queue/job throughput. Specify reproducible input sizes, not fictitious results.
- Recovery: no action duplication, no lost commits, idempotent re-run after crash, error paths, rollback/data migration validation.

**Run available commands** and state exactly which tests passed, failed or were blocked. Fix regressions introduced by the migration; do not skip/delete tests, disable type-checking, weaken linting, or mock away business logic merely to report success. If cloud-only integration is unavailable without AWS credentials, document the unverified assumption and supply reproducible validation instructions.

## 13. Step-by-step implementation and progress discipline

Follow this order, completing and validating each slice. The frontend and backend should not be left broken between major completed slices:

1. Audit repository and frontend expectations, establish baseline and write backend audit.
2. Design context boundaries and ownership/compatibility maps; record material decisions as ADRs.
3. Establish common service scaffolding, Docker Compose, shared technical contracts and test fixtures, without creating empty placeholders.
4. Extract Network/Fleet and Orders with DB isolation, migrations and compatible endpoints.
5. Extract Planning; implement constraint validator, async work queue and explainable deferrals.
6. Extract Loading and Delivery; implement POD metadata/storage, offline sync and receipt workflows.
7. Implement outbox/consumer inbox, EventBridge+SQS adapters, notifications and cross-service event handling.
8. Extract or integrate identity/forecasting only where justified; preserve existing auth and optional ML separation.
9. Validate endpoints against frontend, fix missing backend functionality and document any deliberate behavior change.
10. Run all unit/integration/contract/E2E/resilience/performance checks feasible locally. Correct failures; update README, docs, runbooks and final report.

For any potentially destructive database changes: inspect and back up first; implement forward-only/dry-run safe migration steps; do not run irreversible commands blindly. Do not overwrite unrelated uncommitted work or rewrite frontend screens. Reuse correct existing backend code and tests instead of starting from scratch.

## 14. Required final output

After implementing, report:

- Actual final backend tree, services deployed/combined, and why each boundary was chosen.
- Existing endpoints retained/adapted/new, with remaining frontend compatibility gaps.
- Which missing challenge requirements were fully completed vs incomplete, with evidence.
- Database ownership, migrations executed, verification and rollback safety.
- Event types, publishers, queues, consumers, retries/DLQs, outbox/inbox and idempotency mechanisms.
- AWS deployment architecture document and Mermaid diagrams produced, with exact paths.
- Local startup/seed/migration/test commands, test results and environment limitations.
- Known risks, unfinished tasks, cloud-only tests not executable locally and the minimal next actions.

**Begin the actual repository audit now, then carry out the full backend refactoring and implementation to the maximum verified extent. Do not stop at conceptual recommendations.**
