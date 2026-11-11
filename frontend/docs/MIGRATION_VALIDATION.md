# Migration validation

Validated with Node.js 22.23.3 on 12 November 2026. The default shell provided Node.js
20.12.1, which is below the package's minimum version and could not start the current
Vite/Vitest toolchain. The installed Node 22 runtime was used without changing dependencies.

## Baseline

- Strict TypeScript compilation passed.
- The production build passed, including PWA generation, with an existing large-chunk warning.
- ESLint reported 31 errors: old dependency-boundary violations, empty catch blocks,
  conditional breadcrumb hooks, a synchronous auth effect update, and unused assignments.
- Vitest reported 109 passing tests and one failing assertion in OperationsService's automatic
  synchronization test. The assertion expected every seeded stop to be delivered after only
  two stops had submitted proof.

## Completed checks

| Check                                                               | Result                                                                                                     |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `npm run typecheck`                                                 | Passed with strict settings; includes relocated browser tests                                              |
| `npm run lint`                                                      | Passed, including the new dependency boundaries                                                            |
| `npm run check:architecture`                                        | Passed for 302 production modules; no unresolved local imports, layer violations, or static runtime cycles |
| `npm run test:unit`                                                 | 49 tests passed in 10 files                                                                                |
| `npm run test:integration`                                          | 69 tests passed in 5 files                                                                                 |
| `npm run test`                                                      | 118 tests passed in 15 files                                                                               |
| `npm run build -- --outDir /private/tmp/waypoint-frontend-complete` | Passed; TypeScript, Vite, and PWA generation completed                                                     |
| `npm run format:check`                                              | Passed                                                                                                     |
| `git diff --check`                                                  | Passed                                                                                                     |

Builds were written outside the repository to preserve the existing `dist` output.
The existing large-chunk warning remains; it was not hidden by changing thresholds.
Public assets and the dependency lockfile are unchanged. Global CSS moved to
`design-system/theme.css`; its formatting was normalized without changing style rules.
An AST comparison confirmed that 19 domain, application, local-adapter, and persistence
implementations retain the same code after excluding imports and comments.

The existing synchronization test now explicitly checks that STOP001 and STOP008 become
delivered and that all unrelated stops remain unchanged. No production synchronization
rules were changed to satisfy that assertion. All 110 existing tests remain, with eight
additional mocked HTTP contract tests covering authentication/session persistence,
authorization headers, credentials/cancellation, multipart uploads, empty responses,
backend error envelopes, endpoint paths, and payload forwarding.

## Browser verification

Playwright discovers the same 99 tests in seven files after relocation. The configured
Chromium revision was not installed; a temporary validation configuration used the existing
Chromium headless binary (revision 1248). The repository Playwright configuration retains
its original browser selection, 120-second timeout, and single worker.

The sandbox initially blocked binding a local preview port; browser checks were subsequently
run with permission to serve only local temporary builds. Validation configs, screenshots,
traces, and browser results were kept in `/private/tmp`, outside the source tree.

A run using the normal 120-second timeout recorded 20 passes, five failures, and one
interruption before stopping repeated driver failures. It left 73 tests unexecuted in that
particular run. A separate 52-test loader/store/navigation diagnostic run used a 30-second
timeout and recorded 26 passes and 26 failures. These runs overlap and their totals must
not be added. The shorter diagnostic route timeouts were subsequently resolved by running
the route suite with the repository's original timeout.

The dedicated navigation suite passed every-route rendering at 390, 834, and 1440 pixels,
plus the breadcrumb home/back test. It recorded four passes and one failure: the existing
sign-in test expects `Incorrect email or password` for blank credentials, while the current
application correctly displays `Please enter your username and password.`

Baseline comparisons reproduced the administration suspension failure, the initial driver
navigation and manager-handoff failures, the loader publication failure, and the store
order-edit/after-cutoff failures. They involve older UI expectations such as an unavailable
radio option, an old navigation link, `Plan published`, and editable weight/volume inputs.
The original application already derives Fresh weights and volumes from case counts.
Existing browser specs were retained, with only relocation/import/fixture typing changes.
The complete browser suite is not green, and the remaining driver scenarios were not all
executed; this report does not claim full E2E success.

The diagnostic store suite passed 25 scenarios, including offline order sending, offline
receipt synchronization, receiving windows, delivery issue handling, order pagination,
multiple brand-specific operations, and map vehicle details.

The complete 36-scenario store suite was also run against the original build with the
same 30-second diagnostic timeout. All 36 pass/fail outcomes matched: both builds recorded
25 passes and the same 11 failures. The sign-in assertion also failed on the original build,
for a combined baseline comparison of 37 scenarios with 25 passes and 12 failures.
Timeout results are counted as failures in that comparison. No store outcome regressions
were detected in this comparison.

## Visual and functional comparison

Nine full-page screenshots of original and completed builds were pixel-identical:

| Screen                 | Width |
| ---------------------- | ----- |
| Welcome                | 390   |
| Administration team    | 1440  |
| Store overview         | 390   |
| Driver home            | 390   |
| Loader queue           | 1440  |
| Dispatcher order queue | 1440  |
| Store create orders    | 390   |
| Dispatcher analytics   | 1440  |
| Dispatcher release     | 1440  |

Each screen also had matching headings, no browser page errors, and no horizontal overflow.
These are representative comparisons, not an assertion about every possible UI state.

A separate comparison followed the supported Fresh order flow in both builds: increment
chilled case counts, reload the saved form, review two orders, confirm, and return to the
overview. Visible results matched exactly at every step and neither build raised page errors.

## Remaining limitations

- The pre-existing E2E specification mismatches need a separate test-maintenance pass.
  No UI, business rules, or backend contracts were changed to satisfy outdated expectations.
- A real backend was not configured for this migration. HTTP/auth contracts were exercised
  with mocked fetch responses, and existing local/offline workflows were exercised in Chromium.
- Existing HTTP adapter behavior, including device-local preferences, proof persistence,
  compatibility fallbacks, and unimplemented backend operations, is preserved.
- Type-only dependencies and lazy route edges are deliberately excluded from synchronous
  runtime cycle detection; TypeScript and the resolved layer checks still validate their imports.

## Interface/service flattening and cleanup

Contracts moved from `src/application/ports` to `src/interface`, and business services
moved from `src/application/services` to `src/services`. Imports, boundary checks, and
pure-service test paths were updated, and the empty former hierarchy was removed.

The complete TypeScript import graph was audited from `main.tsx`, all tests, and environment
declarations. The unused AuthContext, loadSummary, and store contact helpers had no callers
and were deleted. Obsolete API factories, duplicate reference endpoints, unused DTOs, and
the unused session refresh helper were also removed. Generated source-tree/migration-map
snapshots were replaced by the maintained architecture guide. Build/test output directories
and the stale TypeScript build cache were cleared. All tests, required assets, environment
files, and installed dependency directories were retained.

The unused `@fontsource/dm-sans` and `dexie-react-hooks` package declarations were removed;
fonts continue to load from `public/fonts`, and IndexedDB subscriptions use Dexie's `liveQuery`.

Cleanup verification: strict TypeScript, ESLint, formatting, production Vite/PWA build,
and resolved dependency/cycle checks pass. All 118 unit/integration tests still pass in
15 files. The complete source/test import audit reports no unreferenced TypeScript files.
The existing E2E limitations documented above were not changed or masked by deleting tests.

## Shared types and business utilities

The former domain folder was removed. Its interfaces and type aliases now live in
`src/types`; its required runtime functions and supporting constants now live in `src/utils`.
The API/repository/outbox contracts from `src/interface` and the backend DTOs from
`src/api/types` were consolidated into `src/types`, with API-specific declarations under
`src/types/api`. Shared Session and BusinessClock interfaces were separated from their hooks.

All imports, inline type imports, architecture rules, and documentation were updated.
Business-rule tests moved from `src/test/unit/domain` to `src/test/unit/utils`. No tests or
business implementations were removed. Boundary checks keep shared declarations independent
of runtime implementations and keep utilities independent of HTTP, storage, and React hooks.

Final verification after consolidation: all 118 unit/integration tests pass, together with
strict TypeScript, ESLint, formatting, the production build, and dependency/cycle checks.
All 12 moved business utility implementations match their original code after excluding
imports, type declarations, and comments. Every file under `src/types` contains declarations
only; none contains runtime functions or values.

## Frontend structure review

- Consolidated shared store forms, draft edits, receipt validation, list filters, lateness, notifications, demo states, administration capabilities, and outbox delivery results under `types`. Local props and inferred hook result aliases remain with their implementations.
- Replaced `utils/utils.ts` with focused `utils/cn.ts` and `utils/formatTime.ts`; updated the component generator alias.
- Moved authentication integration from the single-file `lib` folder into `infrastructure/auth.ts` and removed the empty folder.
- Grouped the persisted outbox subscription with store-manager queries; standardized administration query module names.
- Extended resolved dependency checks to inline type imports, declaration-only types, schema/mapper independence, page transport boundaries, and atom dependencies. Fixed runtime-cycle classification for default imports combined with named type imports.
- Added six isolated architecture-checker regression tests. All six pass, along with all 118 unit/integration tests, TypeScript, ESLint, Prettier, the architecture check (313 production modules), and the production/PWA build.
- The entry/test-rooted import audit found no unreachable production modules; no empty source folders or stale references to the moved paths remain.
- Build output: `/private/tmp/waypoint-frontend-structure-review`. The existing large-chunk warning remains. Browser E2E tests were not rerun for this structural follow-up; the earlier browser limitations still apply.

## Bundle loading improvement

The production bundle audit traced the oversized entry chunk to the eagerly imported
workspace template and its shared dialogs, menus, and animation dependencies, alongside
React and the storage/workflow runtime. The workspace template and not-found view are
now lazy imports using the existing route Suspense fallback. React/React DOM/scheduler
form a separate cacheable runtime chunk; feature libraries retain automatic splitting.

Using final emitted JavaScript files (decimal kB), the entry shrank from 739.57 kB to
273.77 kB. Its full static import closure shrank from 884.21 kB to 626.95 kB (29.1%).
Gzip at Node's default level across that closure shrank from 280.27 kB to 197.79 kB
(29.4%). These startup totals exclude the selected page's dynamic imports and PWA
background precaching. Workbox still precaches the complete application for offline
use; this change improves eager execution/loading rather than reducing offline cache
coverage. React's separate chunk is 218.84 kB, and all emitted chunks are below the
unchanged 500 kB warning threshold.

The production/PWA build, all 118 unit/integration tests, six architecture regression
tests, ESLint, and architecture checks passed. The build emits no bundle-size warning.

An installed Chromium production-preview smoke check passed 219 route/viewport
combinations at widths 390, 834, and 1440 with no page errors or failed local JS/CSS
responses. It explicitly verified that login does not request the workspace template
and workspace routes do load it. External network requests and service workers were
blocked for this smoke check to isolate application chunk loading.
