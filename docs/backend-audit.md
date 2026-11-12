# Backend audit — before migration

Repository baseline: `5f16690` on `main`. User-provided `waypoint_codex_backend_prompt.md` and `waypoint_aws_architecture.md` are retained unchanged. No backend files have been moved at this audit checkpoint.

## Evidence and current state

`api/app/main.py` mounts eleven router modules and publicly serves `/uploads`. FastAPI 0.115.5, SQLAlchemy 2.0.36, Alembic 1.14.0, Pydantic 2.10.2, bcrypt and HS256 JWT are already used. There is no refresh-token flow to preserve. `api/requirements.txt` permits unbounded psycopg whereas pyproject pins it; the setuptools legacy backend name is invalid. No SQS/EventBridge/S3 adapter, transactional outbox/inbox, optimization worker, job ledger, or tracing middleware exists. CSV seeding is invoked from startup and Compose; current `seed/reset.py` is explicitly destructive and must never be used for migration.

Working code to retain: order sizing/entry/edit/cancel, repeat-deferral priority, deterministic greedy allocation, manual moves/validation/publication, reverse-stop loading manifests, flags/release, driver start/events/POD paths, store receipt/issues, reference and people administration, calendar/fuel reads, and a historical rolling demand estimator. Forecasting is not a trained Datathon model and will stay optional/co-deployed. All original tests will be retained.

Missing/incorrect behavior and priority:

1. P0: driver stop events/sync do not verify vehicle ownership or that order_id belongs to the stop; current-trip without vehicle may disclose another driver's work; loaders can access arbitrary trip IDs; latest GPS returns all vehicles; uploads accept unbounded arbitrary files and are public.
2. P0: terminal replay dedup is globally keyed but payload conflicts are accepted; ARRIVED has no durable dedup; invalid state transitions are swallowed. Sync may leak internal exception strings.
3. P0: client-specified delivery_date can bypass closed intake; brand may mismatch outlet; sequential reference generation races. Clock always uses a 2024 demo date even in production.
4. P1: window violations are warnings; fuel checks are per-trip rather than cumulative; unknown references and missing/duplicated orders are not rejected comprehensively. Vehicle availability is absent. S1 time formula exists but is mixed into generic policy.
5. P1: plan creation/publication has no date lock, expected-version guard or one-published-plan constraint; optimizer runs synchronously. Loading flags do not prevent unresolved shortages leaving the depot.
6. P1: no closure snapshot, durable event delivery, poison handling, notification consumer, secure object metadata or migration verification/rollback tooling. Existing cross-owner joins must be broken with projections before separately deploying each operational capability.

## Route inventory and compatibility map

Bodies are named Pydantic DTOs; full fields are in `api/app/schemas`. Query/default parameters and exact response aliases will also be frozen as an OpenAPI contract after dependencies are installed. Frontend `src/api/endpoints`, `src/infrastructure/adapters/http`, query hooks and role route modules were compared; their URL base is `/api/v1`. Existing list responses must stay arrays (add optional offset/limit rather than envelope changes). Existing `POST /plans/auto-plan` must stay synchronous 201 for current clients; introduce a separate 202 job API and a worker using the same use case.

| Method | Path | Body/query/path arguments | Response | Auth/role | Frontend consumers | Status/evidence | Business owner |
|---|---|---|---|---|---|---|---|
| POST | `/api/v1/admin/clock` | `body: ClockAdvanceRequest` | `dict (see handler)` | authenticated; router guard applies | dispatcher monitoring/clock/fuel; legacy clients | implemented: `api/app/api/routers/admin.py:31` | operations administration |
| GET | `/api/v1/admin/clock` | `none` | `dict (see handler)` | authenticated; router guard applies | dispatcher monitoring/clock/fuel; legacy clients | implemented: `api/app/api/routers/admin.py:45` | operations administration |
| GET | `/api/v1/admin/events/poll` | `since: Optional[dt.datetime], limit: int` | `dict (see handler)` | authenticated; router guard applies | dispatcher monitoring/clock/fuel; legacy clients | implemented: `api/app/api/routers/admin.py:57` | operations administration |
| GET | `/api/v1/admin/capacity/forecast` | `date: Optional[dt.date]` | `dict (see handler)` | authenticated; router guard applies | dispatcher monitoring/clock/fuel; legacy clients | implemented: `api/app/api/routers/admin.py:88` | operations administration |
| GET | `/api/v1/admin/analytics/daily` | `date: Optional[dt.date]` | `dict (see handler)` | authenticated; router guard applies | dispatcher monitoring/clock/fuel; legacy clients | implemented: `api/app/api/routers/admin.py:219` | operations administration |
| GET | `/api/v1/admin/analytics/fuel` | `iso_year: Optional[int], iso_week: Optional[int]` | `dict (see handler)` | authenticated; router guard applies | dispatcher monitoring/clock/fuel; legacy clients | implemented: `api/app/api/routers/admin.py:284` | operations administration |
| GET | `/api/v1/analytics/demand-forecast` | `none` | `dict (see handler)` | authenticated; router guard applies | dispatcher analytics | implemented: `api/app/api/routers/analytics.py:16` | operations analytics |
| POST | `/api/v1/auth/login` | `body: LoginRequest` | `TokenResponse` | public | entry/account; session | implemented: `api/app/api/routers/auth.py:17` | identity-access |
| GET | `/api/v1/auth/me` | `none` | `UserProfile` | authenticated; router guard applies | entry/account; session | implemented: `api/app/api/routers/auth.py:34` | identity-access |
| PATCH | `/api/v1/auth/me` | `body: ContactUpdate` | `UserProfile` | authenticated; router guard applies | entry/account; session | implemented: `api/app/api/routers/auth.py:39` | identity-access |
| POST | `/api/v1/deferrals` | `body: DeferralCreate` | `DeferralOut` | authenticated; router guard applies | dispatcher deferrals | implemented: `api/app/api/routers/deferrals.py:29` | deferrals |
| GET | `/api/v1/deferrals` | `date: Optional[dt.date]` | `list[DeferralOut]` | authenticated; router guard applies | dispatcher deferrals | implemented: `api/app/api/routers/deferrals.py:116` | deferrals |
| GET | `/api/v1/deferrals/outlets/{outlet_id}/history` | `outlet_id: str` | `list[DeferralHistoryOut]` | authenticated; router guard applies | dispatcher deferrals | implemented: `api/app/api/routers/deferrals.py:131` | deferrals |
| GET | `/api/v1/driver/trips/current` | `none` | `Optional[TripOut]` | authenticated; router guard applies | driver route/proof/sync/location | implemented: `api/app/api/routers/driver.py:32` | driver |
| POST | `/api/v1/driver/trips/start` | `none` | `dict (see handler)` | authenticated; router guard applies | driver route/proof/sync/location | implemented: `api/app/api/routers/driver.py:64` | driver |
| POST | `/api/v1/driver/stops/{stop_id}/events` | `stop_id: int, body: DeliveryEventIn` | `dict (see handler)` | authenticated; router guard applies | driver route/proof/sync/location | implemented: `api/app/api/routers/driver.py:163` | driver |
| POST | `/api/v1/driver/sync` | `body: SyncBatch` | `list[DeliveryEventResult]` | authenticated; router guard applies | driver route/proof/sync/location | implemented: `api/app/api/routers/driver.py:209` | driver |
| POST | `/api/v1/driver/uploads` | `file: UploadFile, stop_id: Optional[str]` | `dict (see handler)` | authenticated; router guard applies | driver route/proof/sync/location | implemented: `api/app/api/routers/driver.py:269` | driver |
| POST | `/api/v1/driver/positions` | `body: PositionIn` | `dict (see handler)` | authenticated; router guard applies | driver route/proof/sync/location | implemented: `api/app/api/routers/driver.py:290` | driver |
| GET | `/api/v1/driver/positions/latest` | `none` | `list[PositionOut]` | authenticated; router guard applies | driver route/proof/sync/location | implemented: `api/app/api/routers/driver.py:317` | driver |
| GET | `/health` | `none` | `dict (see handler)` | public | health probes | implemented: `api/app/api/routers/health.py:13` | technical |
| GET | `/health/db` | `none` | `dict (see handler)` | authenticated; router guard applies | health probes | implemented: `api/app/api/routers/health.py:18` | technical |
| GET | `/api/v1/loading/trips` | `date: Optional[dt.date], depot: Optional[str]` | `list[TripOut]` | authenticated; router guard applies | loader queue/loading/proof; driver readiness | implemented: `api/app/api/routers/loading.py:26` | loading |
| GET | `/api/v1/loading/trips/{trip_id}` | `trip_id: int` | `TripOut` | authenticated; router guard applies | loader queue/loading/proof; driver readiness | implemented: `api/app/api/routers/loading.py:60` | loading |
| POST | `/api/v1/loading/trips/{trip_id}/flags` | `trip_id: int, body: LoadFlagIn` | `dict (see handler)` | authenticated; router guard applies | loader queue/loading/proof; driver readiness | implemented: `api/app/api/routers/loading.py:70` | loading |
| POST | `/api/v1/loading/trips/{trip_id}/start` | `trip_id: int` | `dict (see handler)` | authenticated; router guard applies | loader queue/loading/proof; driver readiness | implemented: `api/app/api/routers/loading.py:96` | loading |
| POST | `/api/v1/loading/trips/{trip_id}/release` | `trip_id: int` | `dict (see handler)` | authenticated; router guard applies | loader queue/loading/proof; driver readiness | implemented: `api/app/api/routers/loading.py:110` | loading |
| POST | `/api/v1/orders` | `body: OrderCreate` | `OrderOut` | "STORE_MANAGER", "DISPATCHER" | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:155` | orders |
| GET | `/api/v1/orders/stops` | `outlet_id: Optional[str], date: Optional[dt.date]` | `list[StopOut]` | authenticated; router guard applies | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:255` | orders |
| GET | `/api/v1/orders/intake-status` | `none` | `dict (see handler)` | authenticated; router guard applies | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:309` | orders |
| POST | `/api/v1/orders/close` | `date: Optional[dt.date]` | `dict (see handler)` | "DISPATCHER" | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:328` | orders |
| GET | `/api/v1/orders` | `date: Optional[dt.date], status_filter: Optional[str], outlet_id: Optional[str]` | `list[OrderOut]` | authenticated; router guard applies | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:354` | orders |
| GET | `/api/v1/orders/{order_id}` | `order_id: int` | `OrderOut` | authenticated; router guard applies | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:385` | orders |
| PATCH | `/api/v1/orders/{order_id}` | `order_id: int, body: OrderUpdate` | `OrderOut` | "STORE_MANAGER", "DISPATCHER" | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:408` | orders |
| POST | `/api/v1/orders/{order_id}/cancel` | `order_id: int` | `OrderOut` | "STORE_MANAGER", "DISPATCHER" | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:469` | orders |
| POST | `/api/v1/orders/{order_id}/confirm` | `order_id: int` | `dict (see handler)` | "DISPATCHER" | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:516` | orders |
| POST | `/api/v1/orders/{order_id}/receipt` | `order_id: int, body: ReceiptCreate` | `dict (see handler)` | "STORE_MANAGER" | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:539` | orders |
| POST | `/api/v1/orders/{order_id}/issues` | `order_id: int, body: IssueCreate` | `dict (see handler)` | "STORE_MANAGER" | store-manager orders/receipts; dispatcher queue; HTTP snapshot | implemented: `api/app/api/routers/orders.py:604` | orders |
| GET | `/api/v1/admin/users` | `none` | `list[AdminUserOut]` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:98` | identity/network administration |
| POST | `/api/v1/admin/users` | `body: AdminUserCreate` | `AdminUserOut` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:104` | identity/network administration |
| PATCH | `/api/v1/admin/users/{user_id}` | `user_id: int, body: AdminUserUpdate` | `AdminUserOut` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:135` | identity/network administration |
| POST | `/api/v1/admin/users/{user_id}/reassign-trip` | `user_id: int, body: TripReassign` | `dict (see handler)` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:169` | identity/network administration |
| POST | `/api/v1/admin/users/{user_id}/reset-password` | `user_id: int, body: PasswordReset` | `dict (see handler)` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:190` | identity/network administration |
| POST | `/api/v1/admin/outlets` | `body: OutletCreate` | `OutletOut` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:213` | identity/network administration |
| POST | `/api/v1/admin/vehicles` | `body: VehicleCreate` | `VehicleOut` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:250` | identity/network administration |
| GET | `/api/v1/admin/audit` | `limit: int` | `list[AuditOut]` | authenticated; router guard applies | administration users/outlets/vehicles/audit | implemented: `api/app/api/routers/people.py:289` | identity/network administration |
| GET | `/api/v1/plans` | `date: Optional[dt.date], status_filter: Optional[str]` | `list[PlanOut]` | authenticated; router guard applies | dispatcher planning/review/release | implemented: `api/app/api/routers/plans.py:41` | plans |
| GET | `/api/v1/plans/{plan_id}` | `plan_id: int` | `PlanOut` | authenticated; router guard applies | dispatcher planning/review/release | implemented: `api/app/api/routers/plans.py:57` | plans |
| POST | `/api/v1/plans/auto-plan` | `date: Optional[dt.date]` | `PlanOut` | authenticated; router guard applies | dispatcher planning/review/release | implemented: `api/app/api/routers/plans.py:64` | plans |
| POST | `/api/v1/plans/{plan_id}/validate` | `plan_id: int` | `dict (see handler)` | authenticated; router guard applies | dispatcher planning/review/release | implemented: `api/app/api/routers/plans.py:164` | plans |
| PATCH | `/api/v1/plans/{plan_id}` | `plan_id: int, body: dict[str, Any]` | `dict (see handler)` | authenticated; router guard applies | dispatcher planning/review/release | implemented: `api/app/api/routers/plans.py:264` | plans |
| POST | `/api/v1/plans/{plan_id}/publish` | `plan_id: int` | `dict (see handler)` | authenticated; router guard applies | dispatcher planning/review/release | implemented: `api/app/api/routers/plans.py:361` | plans |
| GET | `/api/v1/reference/depots` | `none` | `list[DepotOut]` | authenticated; router guard applies | HTTP snapshots, administration, fleet, account | implemented: `api/app/api/routers/reference.py:19` | network-fleet |
| GET | `/api/v1/reference/outlets` | `depot: Optional[str], brand: Optional[str], district: Optional[str]` | `list[OutletOut]` | authenticated; router guard applies | HTTP snapshots, administration, fleet, account | implemented: `api/app/api/routers/reference.py:24` | network-fleet |
| GET | `/api/v1/reference/outlets/{outlet_id}` | `outlet_id: str` | `OutletOut` | authenticated; router guard applies | HTTP snapshots, administration, fleet, account | implemented: `api/app/api/routers/reference.py:42` | network-fleet |
| GET | `/api/v1/reference/store-managers` | `none` | `dict (see handler)` | "DISPATCHER", "DRIVER", "LOADER" | HTTP snapshots, administration, fleet, account | implemented: `api/app/api/routers/reference.py:51` | network-fleet |
| GET | `/api/v1/reference/vehicles` | `depot: Optional[str], type: Optional[str], refrigerated: Optional[bool]` | `list[VehicleOut]` | authenticated; router guard applies | HTTP snapshots, administration, fleet, account | implemented: `api/app/api/routers/reference.py:65` | network-fleet |
| GET | `/api/v1/reference/vehicles/{vehicle_id}` | `vehicle_id: str` | `VehicleOut` | authenticated; router guard applies | HTTP snapshots, administration, fleet, account | implemented: `api/app/api/routers/reference.py:83` | network-fleet |
| GET | `/api/v1/reference/calendar` | `from_: Optional[dt.date], to: Optional[dt.date], operating_only: bool` | `list[CalendarDayOut]` | authenticated; router guard applies | HTTP snapshots, administration, fleet, account | implemented: `api/app/api/routers/reference.py:92` | network-fleet |

## Database ownership and coupling

- `api/app/models/audit.py`: tables audit_log; FK targets users.id.
- `api/app/models/deferral.py`: tables deferrals; FK targets plans.id, orders.id.
- `api/app/models/delivery.py`: tables delivery_events; FK targets stops.id, orders.id, users.id.
- `api/app/models/issue.py`: tables issues; FK targets orders.id, stops.id, users.id.
- `api/app/models/loading.py`: tables load_checks; FK targets trips.id, orders.id, users.id.
- `api/app/models/notification.py`: tables notifications; FK targets users.id.
- `api/app/models/order.py`: tables orders, order_lines; FK targets outlets.outlet_id, users.id, orders.id.
- `api/app/models/plan.py`: tables plans, trips, stops, stop_orders; FK targets users.id, plans.id, vehicles.vehicle_id, trips.id, outlets.outlet_id, stops.id, orders.id.
- `api/app/models/position.py`: tables vehicle_positions; FK targets vehicles.vehicle_id, users.id.
- `api/app/models/receipt.py`: tables receipts; FK targets orders.id, users.id.
- `api/app/models/reference.py`: tables depots, outlets, vehicles, calendar_days, vehicle_weekly_fuel; FK targets depots.code, depots.code, vehicles.vehicle_id.
- `api/app/models/user.py`: tables users; FK targets outlets.outlet_id, vehicles.vehicle_id, depots.code.

Three migrations: initial tables; GPS positions; ADMIN role/phone/outlet name/vehicle registration. Every model uses one `Base`, one connection string and cross-context relationships. Order response properties traverse trips/plans/events/receipts/deferrals, so splitting orders, dispatch, loading and delivery immediately would change response consistency and require substantial read projections.

## Proposed incremental deployment boundaries

Identity and network/fleet are real ownership boundaries, but their current administration commands depend on active trip/assignment validation. Extract them only with authoritative authorization and event-fed projections. Keep order/dispatch/loading/delivery workflows together initially in an **operations** service to preserve their local transaction and frontend response contracts. Split notification consumption into an independent database/worker immediately; split expensive planning execution into its own worker/job queue while keeping the operations transaction owner. No service may import another service's ORM or access its database; local projections have explicit ownership/versioning. This is an incremental migration, not a claim that co-deployed modules already have independent databases.

## Baseline validation/environment

- Docker CLI exists; `docker info` fails because the daemon socket is unavailable. No containers or live AWS resources were created.
- Host default Python is 3.15; Python 3.13 is available. Isolated test environment is `/private/tmp/waypoint-backend-venv`; dependency installation and tests are being established before file moves.
- Local PostgreSQL 15 tools are available. Sandbox initdb shared memory was denied; an isolated cluster was initialized with approved execution at `/private/tmp/waypoint-refactor-pg`, port 55439. It will contain only disposable validation databases.
- Actual pytest/lint/migration baseline results will be appended before migration.

## Migration/data safety and rollback

Never drop/reset the source database or rewrite keys. Preserve the legacy Alembic lineage. Add tables/columns/indexes forward-only. Back up with pg_dump, inventory row counts/PK checksums and FK integrity, dry-run owner transfers, then copy under a quiesced write window and verify exact IDs/counts/checksums. Keep the source unchanged and retain a routing rollback path. Once new-owner writes begin, rollback requires replay/reconciliation, not restoring a stale snapshot. Test fixtures must require explicitly disposable database names before create/drop. Dataset files are not copied into images; Compose uses independently generated synthetic seed data.

Baseline command before moves: `/private/tmp/waypoint-backend-venv/bin/python -m pytest api/tests -q` failed with `No module named pytest`. Dependency download was interrupted resolving files.pythonhosted.org; retry is in progress. An exact pre-change copy of `api/` is retained at `/private/tmp/waypoint-backend-baseline` so the real baseline can still run once dependencies are available. No database-backed tests are claimed passed at this checkpoint.

Completed unchanged baseline after dependency recovery: 60 passed, 1 skipped (dataset unavailable), 3 deprecation warnings, in 25.00 s against PostgreSQL 15. Baseline Ruff: 63 errors (unused imports, forward-reference type names, late imports and comparisons). Original files and raw outputs remain in `/private/tmp/waypoint-backend-baseline*`. The migration retains every test and assertion. Security fixture corrections explicitly assign test drivers to their trip, set the authoritative outlet brand for Style/Tech tests, and provide an image magic header instead of arbitrary JPEG text.

Final implementation, Docker execution, migration/restore evidence and limitations are recorded in [backend/docs/testing.md](../backend/docs/testing.md). The daemon limitation above describes only the initial audit checkpoint.
