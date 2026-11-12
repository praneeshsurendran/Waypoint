# Browser validation and existing failures

All 99 existing demo Playwright cases were executed without editing their assertions. The
installed Chromium binary was selected through a temporary config; four workers, a 10-second
action timeout and a 30-second navigation timeout bounded missing-selector waits. Expectation
and overall test timeouts were retained. Raw traces/screenshots are retained under `/private/tmp/waypoint-playwright-bounded-results`.

An untouched `HEAD` frontend was exported into `/private/tmp/waypoint-frontend-baseline`,
built independently with demo mode, and served on a separate local port. The same complete
suite and browser settings ran against it.

| Run | Passed | Failed |
|---|---:|---:|
| Migrated build, initial full run | 49 | 50 |
| Final migrated build, complete rerun | 50 | 49 |
| Untouched HEAD baseline | 50 | 49 |

The final complete rerun has **exactly the same 49 failing cases as untouched HEAD**.
The initial additional failure was the 1440px all-routes case; it passed when rerun alone
(54 seconds) and in the final full suite. No failing test was deleted,
skipped or rewritten to report success. These failures block claiming a green historical browser
suite; the actual migrated HTTP role checks and backend workflow are separate passing checks.

Common existing mismatches include the expected `Open turn-by-turn demo` link, `Plan published`
heading, suspension radio option, old quantity fields/copy and profile/preferences navigation.
The three representative failures were also reproduced separately on untouched HEAD. This
backend change does not edit frontend screens or those E2E specs. The comparison inventory follows.

## Failures shared with untouched HEAD

- `src/test/e2e/features/administration.spec.ts:174:3 › administration › suspending a driver on route is blocked until the trip is handled`
- `src/test/e2e/features/driver-refinements.spec.ts:121:1 › breakdown records an updated late ETA and persists daily history while leaving delivery open`
- `src/test/e2e/features/driver-refinements.spec.ts:154:1 › Store Manager retains pending signed evidence and can log out while Driver uploads are pending`
- `src/test/e2e/features/driver-refinements.spec.ts:16:1 › Driver navigation follows arrival and proof stages on a small mobile screen`
- `src/test/e2e/features/driver-refinements.spec.ts:178:1 › manager contacts open on demand and remain usable without internet`
- `src/test/e2e/features/driver-refinements.spec.ts:192:1 › offline route moves to the next outlet and proof navigation follows its arrival`
- `src/test/e2e/features/driver-refinements.spec.ts:75:1 › manager confirms quantities, remarks and signature in their workspace without another receipt action`
- `src/test/e2e/features/driver.spec.ts:126:1 › cannot-deliver evidence sync does not complete the delivery and allows retry`
- `src/test/e2e/features/driver.spec.ts:143:1 › actual browser offline mode preserves proof through refresh and resumes on reconnect`
- `src/test/e2e/features/driver.spec.ts:165:1 › Driver layouts keep controls accessible at 360–1440px and protect unsynced drafts on sign-out`
- `src/test/e2e/features/driver.spec.ts:18:3 › Driver happy path retains signed proof and records the manager receipt at 1440px`
- `src/test/e2e/features/driver.spec.ts:18:3 › Driver happy path retains signed proof and records the manager receipt at 390px`
- `src/test/e2e/features/driver.spec.ts:224:1 › Driver shares the Dispatcher Leaflet map, fits saved stops and recenters after zoom`
- `src/test/e2e/features/driver.spec.ts:268:1 › Driver guards departure, unknown stops and proof steps, and resumes a saved draft`
- `src/test/e2e/features/driver.spec.ts:306:1 › delay notes survive reload without cancelling the stop or losing its photo draft`
- `src/test/e2e/features/driver.spec.ts:334:1 › completing both stops ends the trip and does not offer the last stop as the next delivery`
- `src/test/e2e/features/driver.spec.ts:359:1 › an accepted attempt remains viewable in history after a successful delivery retry`
- `src/test/e2e/features/driver.spec.ts:389:1 › changing reviewed handoff details invalidates the signature and persists the replacement`
- `src/test/e2e/features/driver.spec.ts:417:1 › GPS is opt-in, survives navigation, stops explicitly and retains its last offline fix`
- `src/test/e2e/features/driver.spec.ts:465:1 › denied GPS permission keeps the saved route usable`
- `src/test/e2e/features/driver.spec.ts:485:1 › store manager sees persistent outlet alerts, acknowledges them and views retained signed proof`
- `src/test/e2e/features/driver.spec.ts:48:1 › offline proof stays pending, interrupted upload is retained, and explicit retry accepts it`
- `src/test/e2e/features/driver.spec.ts:523:1 › denying system notifications keeps the persistent store inbox available`
- `src/test/e2e/features/driver.spec.ts:545:1 › a revised order quantity requires replacement manager sign-off and preserves the original proof`
- `src/test/e2e/features/driver.spec.ts:604:1 › an on-time arrival remains on time when signed proof is submitted after the delivery window`
- `src/test/e2e/features/driver.spec.ts:75:1 › route revision review preserves the original proof and resumes acknowledgement`
- `src/test/e2e/features/driver.spec.ts:99:1 › camera recovery and retake require manager sign-off for partial acceptance`
- `src/test/e2e/features/loader.spec.ts:128:5 › Damaged report and revision review at 1440px`
- `src/test/e2e/features/loader.spec.ts:128:5 › Damaged report and revision review at 390px`
- `src/test/e2e/features/loader.spec.ts:128:5 › Damaged report and revision review at 834px`
- `src/test/e2e/features/loader.spec.ts:128:5 › Missing report and revision review at 1440px`
- `src/test/e2e/features/loader.spec.ts:128:5 › Missing report and revision review at 390px`
- `src/test/e2e/features/loader.spec.ts:128:5 › Missing report and revision review at 834px`
- `src/test/e2e/features/loader.spec.ts:181:1 › selected loads, unavailable routes and legacy URLs`
- `src/test/e2e/features/loader.spec.ts:200:1 › photo validation, replacement and local saving while offline`
- `src/test/e2e/features/loader.spec.ts:85:3 › Loader published-to-release flow at 1440px`
- `src/test/e2e/features/loader.spec.ts:85:3 › Loader published-to-release flow at 390px`
- `src/test/e2e/features/loader.spec.ts:85:3 › Loader published-to-release flow at 834px`
- `src/test/e2e/features/store-manager.spec.ts:135:3 › store manager › after the cutoff the order is kept as a draft for the next run`
- `src/test/e2e/features/store-manager.spec.ts:24:3 › store manager › places two separate orders: create, review, confirm`
- `src/test/e2e/features/store-manager.spec.ts:339:3 › store manager › the store has its own notifications, profile and preferences`
- `src/test/e2e/features/store-manager.spec.ts:425:3 › store manager › a Style outlet places one weekly order inside its mall window`
- `src/test/e2e/features/store-manager.spec.ts:520:3 › store manager › the last order can be repeated`
- `src/test/e2e/features/store-manager.spec.ts:533:3 › store manager › the profile lets the manager edit their contact details`
- `src/test/e2e/features/store-manager.spec.ts:557:3 › store manager › outlet and role changes are requested, not edited`
- `src/test/e2e/features/store-manager.spec.ts:55:3 › store manager › weight and volume follow the cases until they are edited`
- `src/test/e2e/features/store-manager.spec.ts:569:3 › store manager › contact details edited offline are sent later`
- `src/test/e2e/features/store-manager.spec.ts:583:3 › store manager › a Tech outlet can have several orders and change one of them`
- `src/test/e2e/navigation/routes.spec.ts:107:1 › the root opens the welcome page and leads to sign-in and workspaces`

## Subsequent full-stack audit (2026-11-13)

The baseline above is preserved as historical evidence. The later audit corrected the
obsolete driver-navigation setup, loader publication navigation and ambiguous loader link
selection, preserving the original behavioral assertions. The latest complete suite result
is **78 passed / 21 failed** of all 99 cases. No case was deleted or skipped. Source test
fixtures now also use explicit required-value guards under strict array-index checks.

The exact remaining inventory and separate passing real-backend Docker/browser checks are
in [the full-stack audit](../../docs/backend-audit-and-optimization.md). Existing quantity,
profile/navigation, map-style and suspension-option mismatches remain visible; the frontend
was not redesigned to satisfy stale tests. The full historical browser acceptance criterion
is not yet met. Raw final traces remain under `/private/tmp/waypoint-playwright-bounded-results`.
