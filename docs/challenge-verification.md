# Full-project challenge verification — 17 November 2026

This audit uses the repository's `Challenge Booklet.md`, working implementation and authorized
local Datathon assets. Application behavior and submission deliverables are assessed separately.
No AWS resources, provisioning, infrastructure-as-code, CI/CD or publication were performed.

## Findings and implemented corrections

- The existing four owner APIs and seven workers are retained. Intelligence is a fifth, stateless
  service: no database ownership was moved to models, and operations keeps transactional order,
  loading, delivery and receipt invariants. Existing migrations and tests remain.
- Local seeding previously used independent `SYN` references. With the private workspace present,
  seeding now imports the actual 120 outlets / 60 vehicles / two depots and calendar. Idempotent
  insertion preserves existing rows, accounts and history. Synthetic fixtures remain available for
  isolated tests. Outlet coordinates are approximate district geocoding; source CSVs lack GPS.
- The Datathon directory is copied into backend-owned source/private assets. No runtime imports
  or mounts depend on the removable original folder. Notebook checkpoints and experiment caches
  are unnecessary. [Setup and reproducibility](../backend/intelligence/README.md) are explicit.
- The supplied workspace lacked final Task 1 artifacts. A reproducible chronological compact
  candidate now provides handling/late predictions. Task 2A uses the existing saved ensemble;
  Task 2B preserves and independently validates the selected whole-order allocation and optimizer.
- Operations forecast history previously omitted Task 1 test order records. It now deduplicates
  the combined requested demand, including deferred/not-run orders, by calendar ISO week.
  Learned forecasts replace the baseline only when the inference service is configured. Model
  failures return an explicit unavailable response; no fake model scores are substituted.
- Live prediction requests contain planned data only, with finite constrained transport types,
  bounded batch size, verified identity/role/depot scope and artifact hashes. Operations forwards
  authentication and tracing through a bounded pooled HTTP client. The Dispatcher allocation
  screen requests predictions and its demand view consumes learned forecasts.
- Own-contact editing is restored with offline queuing. Assignment/role requests are durably
  audited and cannot modify authorization. The admin audit view displays the request text.
- Fixed a newly created outlet redirecting away before query refresh, loading clearance being
  bypassed in the departure-screen guard, a fleet details drawer that could not stay closed,
  missing driver route geometry, and first-visit offline service-worker control. Dispatcher
  delivery status now comes from delivery records, rather than treating loading completion as
  proof of delivery.
- Browser assertions were reconciled with the enforced quantity/weight rules, responsive
  navigation and actual replacement actions. Coverage remains: no tests were deleted or skipped.
  Scheduled account suspension is explicitly unsupported by the identity API; the HTTP adapter
  now rejects that option instead of silently suspending immediately. It is not a booklet requirement.
- A fixed 09:00 local demo clock makes fresh-install intake reproducible. It is used only in demo
  mode; production always uses wall-clock time and rejects demo mode. Examples now match Compose.

## Requirements and evidence

| Booklet requirement | Implementation / local evidence | Remaining boundary |
|---|---|---|
| Responsive four-role order-to-receipt workflow | Browser role screens plus real HTTP order, queued planning, loading, release, signed proof, duplicate replay, receipt and notifications | Real-device/network and live-host acceptance remain deployment work |
| Shared reference data and realistic seeded day | Private CSV reference bootstrap, representative orders and fixed local intake; [numbered walkthrough](judge-walkthrough.md) | Existing databases are not destructively replaced; new references are inserted alongside existing rows |
| Capacity, temperature, access, windows, depot, two trips, fuel | Preserved pure planner, publication validation, concurrency and lifecycle tests | Approximate geocoding is not turn-by-turn routing |
| Shortfalls, excess demand and deferrals | Loader missing/damaged revision flows, release gates, reasons/priority checks, S1 adversarial tests | No invented monetary penalty rates |
| Offline driver proof and manager receipt | Browser IndexedDB/PWA tests, signed-manifest binding, exact operation replay and HTTP evidence authorization | Offline basemap tiles are not promised |
| Task 1 labels and valid predictions | Chronological fitting/evaluation, planned-only API tests, 5,014 template-aligned rows | Compact candidate differs from missing source boosted artifacts; scores are reported honestly |
| Task 2A ten-week requested-demand forecast | Saved ensemble, future-outcome leakage test, 60 template rows, Fresh chilled subset, recomputed backtest | Historical supplied horizon; refresh data/evaluate drift before later production dates |
| Task 2B whole-order allocation | Selected CSV, bounded CP-SAT policy, independent exact feasibility validator, all 85 decisions | Time-capped objectives have recorded bounds; no unsupported global-optimality claim |
| Models, notebook, preprocessing, architecture and prioritization policy | Saved private models; executable source notebook and privately executed copy; [preprocessing/model diagram](datathon-integration.md); generated private one-page policy and trip calculations | Team naming, original authorship disclosures and permitted submission packaging require team review |
| Root Compose/env example, setup, architecture, data model, AI disclosure | Existing monorepo documentation updated; owner migration histories retained; current walkthrough added | Private assets must be restored separately on a fresh checkout |
| Public URL, seeded public credentials and videos | Not published by this task | Human videos, deployment and competition submission remain outstanding |
| Designathon source design fidelity | Current responsive screens exercised | Original final design/prototype submission and human rationale were not independently verified |

## Validation scope

Native backend tests use real disposable PostgreSQL and Redis. Cross-service tests use isolated
owner databases with in-process identity transport; the Docker HTTP smoke additionally verifies
actual network boundaries, SQS workers and private S3 evidence through LocalStack. The browser
feature suite uses the local demonstration adapter; separate real-browser role logins and
inference UI checks validate the configured backend. These are different forms of evidence,
not a claim that all demo browser tests use live services.

Final counts, command outcomes, resource measurements and warnings are recorded in
[the machine-readable validation report](validation-2026-11-17.json). Earlier reports are retained
as dated historical evidence. All local assets and temporary validation projects are isolated
from existing application volumes; no volume reset or history rewrite was used.

## Production and confidentiality limits

The AWS account was created on/after July 15, 2025. [The AWS reconciliation](aws-architecture.md)
uses current account-plan rules and distinguishes a credit-funded small deployment from the
larger availability reference. Local validation cannot certify a public production deployment,
free ongoing hosting, backup restoration, resource budgets, TLS/DNS, IAM or real AWS behavior.
Those remain deployment-owner acceptance work. Supplied dated calendar/road features must be
updated before enabling unsupported live dates. No live AWS resources were created.

The copied data, artifacts, executed notebook and exports are gitignored and excluded from
images. **Pre-existing `data/` files are already tracked in this repository**; this work did not
remove functionality or rewrite Git history. Review organizer authorization and repository/history
exposure before any publication. `.gitignore` does not retract previously committed datasets.
The booklet restricts data and derivative sharing, so generated artifacts were not uploaded.

## Unified intelligence workspace follow-up

Offline tooling is now `backend/intelligence`; its private datasets/models/exports are
`backend/private/intelligence`. The independently deployable API remains
`backend/services/intelligence`. Docker mounts, seed defaults, notebooks, commands and links
use these paths. `WAYPOINT_INTELLIGENCE_WORKSPACE` is the current configuration variable;
the previous workspace variable and directory remain supported as fallbacks for existing
configurations. No models were discarded or silently retrained during the move.

Pytest's default test paths now include both intelligence test suites. The follow-up reruns
all backend tests using bare `pytest -c backend/pytest.ini`, verifies the source notebook and
all three template exports, and exercises the renamed training command in an isolated
workspace so deployed artifacts are preserved.
