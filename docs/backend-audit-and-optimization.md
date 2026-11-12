# Full-stack audit and optimization

Audit baseline: commit `bbb93e9` (2026-11-12). The worktree was clean when this audit began.
This is a new audit of the implemented four-service migration, not a claim that the earlier
migration already satisfied every hardening/type-safety requirement. Findings below are initial
observations; executed validation and closure evidence will be recorded as implementation proceeds.

| Area | Initial status / severity | Evidence and correction | Verification |
|---|---|---|---|
| Rate limiting | Missing; high | No distributed limiter or reverse-proxy quotas. Add atomic Redis token buckets for clients and verified users; distinguish login/read/write/planning/bulk; bounded outage policy and trusted-proxy handling. | Real Redis threshold/concurrency/recovery/isolation tests; HTTP 429 and Retry-After checks. |
| Caching | Partial; medium | Frontend reference promises never expire; no shared reference cache; identity creates a new HTTP client per request. Add measured reference cache-aside with scoped keys, TTL, commit invalidation and stampede protection; pool identity connections without caching authorization. | Query counts/latency before and after; hit/miss/expiry/invalidation/concurrency/outage tests. |
| Polling | Partial; medium | Query refresh configuration is fragmented; driver interval retries at a fixed 30s; request cancellation and Retry-After are not consistently exposed. Retain polling, add central intervals/backoff/jitter, actor-scoped keys and cancellation. | Fake-timer/offline/reconnect/overlap tests and role workflows. |
| Message queues | Implemented, review required | EventBridge/SQS, transactional outbox/inbox, per-consumer queues/DLQs and planning workers exist. Envelope data still uses broad dictionaries; inspect retry/ack failure paths and strengthen typed contracts. | Consumer contracts, crash/retry/reordering tests and real LocalStack smoke. |
| Database optimization | Partial; medium | Owner DBs and migrations exist; notifications perform one read-receipt query per row; dashboard summaries load entire tables into Python. Measure queries/plans, replace N+1 and use set-based aggregates where equivalent. | PostgreSQL EXPLAIN, query counts, unchanged response tests and realistic-scale measurements. |
| Authentication | Partial; high | JWT verifies signature/expiry/revision, but lacks issuer/audience checks. Shared Principal accepts arbitrary roles and inactive values. Add versioned issuer/audience validation with explicit migration policy and default-deny principals. | Forged/expired/wrong-issuer/wrong-audience/reset/rotation tests. |
| Authorization | Implemented, review required; high | Existing role/resource guards cover delivery/loading/receipt/evidence. Audit dispatcher depot scope, notification scope fallback, reference/contact disclosure and every write. | Cross-user/outlet/depot tests, unknown-role denial, actual HTTP flows. |
| Dead code cleanup | Partial; low | Legacy compatibility endpoints and migrations are intentional; inspect actual imports, dynamic routes and consumers before removing unused dependencies/helpers. | Architecture/import checks, full tests and unchanged route inventory. |
| Security | Partial; high | Runtime headers/errors differ by service; no application throttling; upload/storage checks exist. Run Bandit, dependency audits and regression tests; never expose SQL or validation input values in errors/logs. | Scanners plus targeted security tests, not scanner-only assurances. |
| Performance | Partial; medium | Previous synthetic results exist but are not this audit's before/after measurements. Measure current DB/API/cache/identity/polling behavior; avoid inventing improvements. | Reproducible workload, p95, query counts and queue timings. |
| Code quality | Partial; medium | Pure planning domain is enforced; many application functions still use legacy HTTP errors and loosely typed dictionaries. Strengthen boundary contracts and meaningful ports without creating empty layers. | Ruff, architecture checks, type checks and behavior tests. |
| Frontend type safety | Partial; high | TypeScript strict is enabled, but noUncheckedIndexedAccess/exactOptionalPropertyTypes are absent. API wrappers accept caller-selected generic responses and unchecked JSON casts. Generate API types/validators and fix actionable strictness issues. | TypeScript, ESLint, runtime-invalid response tests and generated-contract drift checks. |
| Backend type safety | Partial; high | Mypy checks only 22 domain/port/contract modules. Many routers, application functions and workers lack return annotations; some new endpoints have empty OpenAPI response schemas. Expand enforced scope, annotate boundaries and publish concrete schemas. | Mypy on expanded source scope; Pydantic/OpenAPI tests; no blanket ignores/exclusions. |
| API contract consistency | Partial; high | Frozen compatibility tests preserve 59 original operations, but runtime decoding and generated TypeScript are missing. Treat current Pydantic/OpenAPI as authority and preserve wire behavior while making shapes explicit. | Type generation, runtime validators, nullable/optional/enum/error contracts and full workflows. |
| Event schema consistency | Partial; medium | v1 payload models exist, but reference records use dict[str, Any] and several payloads omit meaningful optional fields. Tighten producer/consumer schemas without dropping additive v1 data. | Valid/invalid/versioned event tests and projection integration. |
| Local execution | Implemented, extend | Docker stack includes four APIs, PostgreSQL, seven workers, Nginx and LocalStack. Redis is absent. Add private Redis/health/dependencies without production provisioning. | Fresh/repeated migrations, complete Compose startup, Redis checks and four-role HTTP/browser workflows. |

The earlier full browser run had 50 passed / 49 failed, matching untouched HEAD. This task
will assess those failures rather than delete/disable tests. The frontend must not be redesigned
to satisfy stale copy assertions. Corrections to tests must retain their original behavioral
coverage and be justified against current UI/business requirements.

No CI/CD, IaC, production AWS resource or Kafka migration is authorized by this task.

## Implemented corrections

The initial findings above are retained as the baseline. Changes now implemented:

| Finding / affected paths | Correction and evidence | Status |
|---|---|---|
| Missing distributed quotas; `backend/packages/runtime`, all API factories, `backend/local/nginx.conf` | Atomic Redis TIME-based token buckets, separate client/verified-user scopes, login/read/write/planning/bulk budgets, 429/Retry-After, proxy spoof protection, finite local read fallback and fail-closed sensitive writes. Redis tests cover concurrency across two instances, isolation and recovery. CORS wraps the limiter so browsers can read rejections. | Fixed |
| Unbounded reference promises; `frontend/src/infrastructure/adapters/http/reference.ts` | Actor-scoped, expiring 30-second promise caches coalesce requests and clear on authentication changes. Existing mutation invalidation remains. | Fixed |
| Repeated reference SQL; network reference router/outbox and runtime cache | Schema-validated cache-aside, actor/role/assignment/filter keys, owner-commit generation invalidation, bounded distributed stampede lock, malformed-entry eviction and database fallback. Cache hit/miss/expiry/corruption/invalidation/outage tests pass. Security decisions are not cached. | Fixed |
| Fragmented refresh and HTTP failures; frontend queries/client | Configurable visible-screen polling, no background polling, actor-scoped query keys, transient retry backoff/jitter, reconnect refresh and Retry-After handling. Mutations still require explicit retry; offline replay preserves captured identity/payload. | Improved; cancellation limits below |
| Per-request identity connections; shared security package | One bounded HTTPX pool per process, short connection/read timeouts, no redirects and lifespan cleanup. Identity authorization remains authoritative on every protected request. Upstream 429 stays a 429. | Fixed |
| Missing issuer/audience and permissive principals; identity security/shared security | Require and verify issuer/audience/expiry/signature; keep previous-key rotation and password-revision revocation. Valid roles and active principals are enforced. Legacy tokens need re-login. Invalid UTF-8 byte-length passwords return 422 without echoed input. Browser-generated temporary passwords now use crypto randomness. | Fixed |
| Inconsistent errors and evidence retrieval; runtime handlers, operations handler, frontend assets/useEvidence | Safe 409/503/500 mapping, validation-input redaction, private/no-store and nosniff headers, protected evidence fetched with API-origin credentials rather than an unauthenticated image URL, and actor ownership on IndexedDB proof-cache reads. Raw SQL/exception payloads are not returned or logged. | Fixed |
| Notification N+1 and read-receipt race; notification router | One outer-join query includes actor read receipts; inserts use ON CONFLICT DO NOTHING. Loader, outlet, vehicle and assigned dispatcher depot scopes default-deny unsupported roles. | Fixed |
| Dashboard full-row hydration; operations admin use cases | Three grouped SQL counts preserve daily-summary fields. Real 10,000-order PostgreSQL measurement and plans are described below. Existing date/status indexes suffice; no speculative index or procedure added. | Fixed |
| Cross-day manual plan edits; operations plans use case | Reject orders outside the plan's date and eligible context before detaching any assignment. Regression asserts rejected edits leave the order unchanged. | Fixed |
| Timestamp-only audit synchronization; operations admin poll | Optional monotonic ID cursor, ascending bounded drain and next_cursor preserve simultaneous timestamps; legacy since remains supported. Limit rejects zero/negative values. Device sync already has actor/device cursor recovery. | Fixed |
| Caller-selected generic API types and unchecked external JSON | Backend OpenAPI generates TypeScript and standalone validators. Endpoint responses validate status and JSON before exposing the generated type; stored user profiles validate too. Existing routes are retained. | Fixed; options limits documented separately |
| Narrow Python scope and missing annotations | Mypy expanded from 22 to 149 files across all services/packages, including disallow_untyped_defs. Explicit route/application/worker/DI/storage/repository signatures, Actor/queue/publisher protocols and typed SQL jobs. | Fixed within enforced source scope |
| Weak reference-event records | Validate owner DTO snapshots, supported v1 payloads, record revision, absence of password hashes and event/entity ownership. Outbox/inbox, at-least-once retry and projection version checks remain intact. | Improved; extensible JSON container retained |
| Duplicate class-name helpers/dependency | Consolidated the seven primitive imports into the existing clsx/tailwind-merge utility and removed the duplicate package. Kept compatibility endpoints, dynamic routes, migrations, legacy demo functionality and tests. | Fixed |
| Dependency advisories | Nonbreaking upgrades plus validated glob/minimatch overrides remove all moderate/high/critical frontend findings. Runtime Python audit reports none. Four low build-chain findings remain below. | Residual low risk recorded |

## Measured database result

`backend/scripts/verify/database_performance.py` uses an explicitly disposable `_test` database,
creates 10,000 synthetic orders in a rolled-back transaction, compares counts, and captures
EXPLAIN ANALYZE/BUFFERS JSON for both statements. Five samples under the same connection:

| Measure | Existing ORM row hydration | Grouped SQL counts |
|---|---:|---:|
| Median query + Python processing | 276.086 ms | 2.922 ms |
| Peak traced Python allocation | 20,700,259 bytes | 57,086 bytes |
| Rows transferred | 10,000 | 3 |

Counts were identical: 3,334 confirmed, 3,333 delivered, 3,333 deferred. The original plan used
a bitmap heap scan; the grouped plan aggregates in PostgreSQL with the existing indexes.
This measures a synthetic local workload and Python materialization, not a production SLA.
Notification list now performs one joined receipt query rather than one query per notice.
Reference-cache tests prove the loader executes once for a hit and once across a 24-call
concurrent stampede. Operational state is read directly; no broad dashboard cache was added.

## Security and operational decisions

Redis is private to Compose, bounded to 128 MB, AOF-enabled and uses noeviction so cached
reference data cannot evict limiter state. Production requires authenticated TLS Redis.
Cache failure falls back to PostgreSQL; failed commit invalidation can leave only reference
information stale for its bounded TTL. Login/mutations fail with 503 during Redis outages;
reads have a bounded process-local limiter. Trusted proxy CIDRs are explicit, and the local
Docker trust range is not production configuration.

JWT refresh tokens and a cookie session protocol were not invented. Existing bearer behavior
is preserved with issuer/audience enforcement, expiry, rotation and authoritative account
revocation. Browser token storage remains a documented XSS-sensitive boundary. No auth result
is cached. Private S3 upload authorization, MIME/size/magic-byte checks and safe object keys
remain; DTO password validation closes an otherwise unhandled hashing error.

Existing EventBridge/SQS fan-out, per-consumer DLQs, visibility renewal, outbox publication,
inbox hashing and committed-before-ack processing remain. Ordering uses entity revisions and
device sequences rather than assuming SQS standard queues provide global order. Operations
continues to own the order/planning/loading/delivery transaction boundary. A saga is not
justified for those locally atomic writes. No Kafka, custom gateway, cross-service database
writes, stored procedures, CI, IaC or live AWS resources were introduced.

The AWS reference remains a proposed deployment: use its EventBridge/SQS/private-S3 services
and service-owned databases, add a private authenticated TLS Redis deployment, and supply
workload identities, ingress trust, secrets, capacity and monitoring through the separately
owned deployment work. The local Compose credentials/endpoints are synthetic development
configuration. Existing ownership/recovery runbooks and architecture diagrams remain valid.

## Validation ledger

Results here describe executed checks, with final rerun details appended below. Logs and raw
plans/screenshots remain under `/private/tmp/waypoint-audit-*` for this local session.

- Baseline: 91 backend tests passed, one dataset skip; 128 frontend tests passed; production
  build passed. Initial broad mypy audit found 182 errors in 36 files.
- Implemented backend suite: 104 passed, one dataset skip after contract/type/security changes;
  the subsequently added CORS regression is verified separately and in the final rerun.
- Frontend unit/integration: 135 passed, including seven new contract/validation cases.
- Python mypy: 149 source files, including disallow_untyped_defs; no errors.
- Frontend: strict TypeScript, ESLint and production build pass. Largest emitted application
  entry is approximately 304 KB; lazy operations validators approximately 395 KB; no 500 KB
  chunk warning. Validators add about 2.8 MB total precache with the existing route chunks.
- Bandit: no medium/high findings; low findings are reviewed demo/test-password literals,
  deterministic synthetic random values and controlled subprocess imports/invocation.
- pip-audit: no known vulnerabilities in the pinned runtime set. npm audit: zero moderate,
  high or critical; four low dependency-chain entries (one deepmerge advisory) remain in Workbox/PWA build
  tooling. `npm audit --omit=dev` reports **zero production dependency findings**. The available automatic fix downgrades major tools; it was not forced. Trusted
  repository build inputs limit exposure, but these advisories remain open.
- Real Docker workflow passed: all five roles, asynchronous planning, duplicate replay,
  protected evidence and notifications. One observed queue completion was 2.302 seconds;
  this is an end-to-end synthetic sample, not saturated throughput.
- A full browser run improved from the recorded baseline 50/99 to 76/99 after fixing obsolete
  navigation setup. A final complete rerun follows. No tests were removed, skipped or replaced
  with mocks to obtain these results.

## Remaining constraints

The historical browser suite includes editable weight/volume controls, old profile/navigation
copy, removal of the mobile navigation and a scheduled-suspension option that current screens
do not provide. Reintroducing editable quantities or redesigning screens would conflict with
preserving current behavior and the cases-based challenge constraints. Those assertions are
retained and their failures remain visible. A transient lazy-module fetch failure was also
captured in one all-routes run; final reruns distinguish it from deterministic UI mismatches.

Public endpoint options require the JSON bodies declared mandatory by OpenAPI. Runtime JSON
request validation also detects missing bodies for untyped callers. Query/path validation remains authoritative on
the backend, with generated browser query types and compatibility URLSearchParams accepted.
Some broad read ports do not propagate AbortSignal all the way to fetch. See
[type-safety-and-api-contracts.md](type-safety-and-api-contracts.md) for the precise boundaries.
The optional operations audit cursor is available to clients; existing operational screens
continue refreshing their authoritative projections. No unsupported claim of WebSocket/SSE
or full incremental synchronization is made.

The original forecast test required a `/data` mount despite the authorized dataset existing in
this workspace. It now accepts `WAYPOINT_DATA_ROOT`, `/data`, or the repository dataset; the
final run exercises its existing 60-row assertion without skipping. This does not establish
challenge-wide optimization accuracy or production load capacity.
The full acceptance criterion of a completely green historical browser suite is therefore not
claimed unless the final recorded run actually satisfies it.

## Final executed results (2026-11-13 local time)

| Check | Actual result |
|---|---|
| Full backend suite, including real dataset and Redis | **107 passed, 0 skipped**; one upstream Starlette/httpx TestClient deprecation warning |
| Frontend unit/integration | **136 passed** in 17 files |
| Mypy | **149 source files passed**, disallow_untyped_defs enabled |
| TypeScript | Passed with strict, noUncheckedIndexedAccess and exactOptionalPropertyTypes |
| Ruff / format / compileall | Passed |
| ESLint / frontend architecture | Passed; 323 production modules |
| Architecture rule tests | 6 passed |
| Contract drift | Four owners, **79 HTTP operations**, generated files match |
| Production build | Passed; no chunk-size warning |
| Docker startup/rebuild | Four APIs, seven workers, Redis, PostgreSQL, LocalStack, ingress and frontend started |
| Docker browser, real backend | Five role logins passed; **0 uncaught browser errors, 0 API errors** |
| Docker end-to-end HTTP | Passed: planner job, deliveries, receipts, duplicate replay, private proof authorization and notifications; final observed job completion 3.177 seconds |
| Migration repeat | All four owner upgrades passed twice; operations head 0006_device_history_index; other owner heads 0001_owned_schema |
| LocalStack | Fan-out, DLQ redrive/replay and private-object roundtrip passed |
| Real Nginx edge limiter | 300 concurrent local requests: 153 allowed, 147 returned 429; Retry-After and local-origin CORS assertions passed |
| Historical demo Playwright | **78 passed / 21 failed**, all 99 executed; recorded baseline 50 / 49 |

The last complete demo browser run used the corrected ESM validator generator. The subsequent
actor-cache regression passed in the unit/integration suite and strict compilation; it changes
only the authenticated HTTP adapter, while the historical suite runs the demo adapter. The
Docker development server also exercises the native validator imports: an initial `require is
not defined` startup defect was detected there, fixed in generation, and all five real role
logins then passed. The generator rejects unsupported CommonJS helpers instead of emitting a
browser startup failure. Nginx's local rate-limit error handler exposes Retry-After only to
loopback frontend origins; ordinary API CORS continues using each service's configured list.

The proof-cache regression keeps another actor's evidence inaccessible while preserving the
original owner's local record. Password/principal tests additionally reject missing activity,
inactive accounts and unknown roles. Tests and migration histories remain present.

The 21 retained browser failures are listed below. Several share a stale selector or UI
expectation; the list is an actual result, not a waiver or a completely green E2E claim.

- `src/test/e2e/features/administration.spec.ts:174:3 › administration › suspending a driver on route is blocked until the trip is handled`
- `src/test/e2e/features/driver-refinements.spec.ts:193:1 › offline route moves to the next outlet and proof navigation follows its arrival`
- `src/test/e2e/features/driver.spec.ts:19:3 › Driver happy path retains signed proof and records the manager receipt at 390px`
- `src/test/e2e/features/driver.spec.ts:19:3 › Driver happy path retains signed proof and records the manager receipt at 1440px`
- `src/test/e2e/features/driver.spec.ts:144:1 › actual browser offline mode preserves proof through refresh and resumes on reconnect`
- `src/test/e2e/features/driver.spec.ts:166:1 › Driver layouts keep controls accessible at 360–1440px and protect unsynced drafts on sign-out`
- `src/test/e2e/features/driver.spec.ts:225:1 › Driver shares the Dispatcher Leaflet map, fits saved stops and recenters after zoom`
- `src/test/e2e/features/driver.spec.ts:269:1 › Driver guards departure, unknown stops and proof steps, and resumes a saved draft`
- `src/test/e2e/features/driver.spec.ts:335:1 › completing both stops ends the trip and does not offer the last stop as the next delivery`
- `src/test/e2e/features/driver.spec.ts:390:1 › changing reviewed handoff details invalidates the signature and persists the replacement`
- `src/test/e2e/features/store-manager.spec.ts:24:3 › store manager › places two separate orders: create, review, confirm`
- `src/test/e2e/features/store-manager.spec.ts:55:3 › store manager › weight and volume follow the cases until they are edited`
- `src/test/e2e/features/store-manager.spec.ts:135:3 › store manager › after the cutoff the order is kept as a draft for the next run`
- `src/test/e2e/features/store-manager.spec.ts:339:3 › store manager › the store has its own notifications, profile and preferences`
- `src/test/e2e/features/store-manager.spec.ts:425:3 › store manager › a Style outlet places one weekly order inside its mall window`
- `src/test/e2e/features/store-manager.spec.ts:520:3 › store manager › the last order can be repeated`
- `src/test/e2e/features/store-manager.spec.ts:533:3 › store manager › the profile lets the manager edit their contact details`
- `src/test/e2e/features/store-manager.spec.ts:557:3 › store manager › outlet and role changes are requested, not edited`
- `src/test/e2e/features/store-manager.spec.ts:569:3 › store manager › contact details edited offline are sent later`
- `src/test/e2e/features/store-manager.spec.ts:583:3 › store manager › a Tech outlet can have several orders and change one of them`
- `src/test/e2e/navigation/routes.spec.ts:107:1 › the root opens the welcome page and leads to sign-in and workspaces`

Final static/build checks were repeated after the proof-cache fix: TypeScript, ESLint,
Prettier, contract drift, architecture rules and production build pass. `pip check` reports
no broken requirements. The final largest lazy operations-validator chunk remains below
500 KB. The standalone validator imports work in the Docker Vite development server as
well as the production build; this was verified through actual browsers, not only Node tests.

A bounded three-sample Docker queue benchmark also passed: planner completion times
**2.052, 2.049, 2.049 seconds**, with 33.742 seconds for the complete sequential workflows.
The observed 5.33 completed jobs/minute includes HTTP/authentication/workflow overhead and
rate-limit waits; it is explicitly not saturated queue capacity. The verification helper
now honors Retry-After on rejected requests, preserving real login limits during repeated
samples instead of disabling throttling to get a passing benchmark.

Validation cleanup completed: only the `waypoint-audit-validation` Docker project and the
`/private/tmp/waypoint-refactor-pg` native test server were stopped. Named volumes, databases,
backups, raw logs and browser traces were preserved. Other Docker projects were not stopped.
Immediately before cleanup, all four API containers, PostgreSQL, Redis and LocalStack were
healthy, all seven workers were running, and all four migration jobs plus seeding had exited 0.
