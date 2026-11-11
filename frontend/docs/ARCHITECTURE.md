# Frontend architecture

Waypoint keeps the existing React, TypeScript, Vite, React Router, TanStack Query,
Dexie, Tailwind/Radix, Leaflet, Framer Motion, and PWA implementations. This migration
changes module ownership and import boundaries while retaining the operational workflows.
No dependencies were added and no backend contracts or route URLs were changed.

## Feature ownership and routing

- `app/administration`: team, invitations, roles, assignments, outlets, vehicles, audit.
- `app/dispatcher`: order queue, allocation, deferrals, review, release, fleet, analytics.
- `app/driver`: route, departure, navigation, arrival, evidence, handoff, issues, history, sync.
- `app/store-manager`: orders, drafts, delivery tracking, receipts, issues, notifications, settings.
- `app/loader`: shift queue, loading workspace, loading proof.
- `app/entry-account`: public entry, login, workspace chooser, shared profile and preferences.
- `app/recovery`: saved evidence review and synchronization recovery.
- `app/demo`: existing development scenario and map pages.

Each operational feature keeps its route definition in `<feature>-routes.ts`.
`app/router/registry.ts` aggregates these definitions; `AppRouter.tsx` retains the existing
BrowserRouter, redirects, role and sign-in guards, Suspense boundaries, error fallback,
and lazy imports. Multi-page chunks remain grouped where they were grouped previously.

`constants/workspaces` owns route-free navigation, search, identity, and shell settings.
Components and session hooks consume this metadata without importing lazy page registries.
The router supplies breadcrumb route titles through `RouteMetadataContext`.
Templates receive dynamic page content through children and do not declare routes.
The workspace template and not-found view load lazily through the existing Suspense
boundary, so public entry pages do not load workspace menus, dialogs, and their
animation dependencies. Vite gives React, React DOM, and the scheduler their own
`react-runtime` chunk for caching; other dependencies retain automatic splitting.
The default bundle-size warning threshold remains enabled.

## Atomic component placement

- Atoms: Radix primitives, inputs, buttons, icons, badges, themed administration/store controls,
  driver button, and entry wordmark. They do not fetch data or import higher categories.
- Molecules: fields, metrics, notices, search, modal composition, breadcrumbs, navigation items,
  themed form controls, pagination, signature input, photo picker/preview, and progress indicators.
- Organisms: maps, order tables, planning navigation, delivery alerts, proof and signature details,
  handoff/issue forms, driver route and sync sections, entry footer and motion sections.
- Templates: workspace shell, driver screen/stop arrangements, administration page and store page.

Feature-specific UI remains under the relevant atomic category and feature subdirectory.
The former mixed AdminKit, StoreKit, and EntryChrome modules are split by responsibility.
Third-party primitives retain their existing composition and accessibility behavior.
Existing markup, classes, assets, and stylesheet rules are preserved. `styles.css`
imports `design-system/theme.css`, which contains the original global styling and tokens;
feature styles live in `design-system/features` and retain their existing loading boundaries.

## Data and dependency direction

`types` contains shared business models, API and repository contracts, backend DTOs,
driver proof/signature structures, route history records, sessions, business clocks, and
navigation contracts. `types/api` groups the API interfaces and backend response shapes.
Type modules contain declarations only and do not import implementations from services,
utilities, hooks, transport, or storage.

`utils` contains the required calendar, capacity, delivery-window, route-history,
proof/signature validation, fleet/outlet, and photo-digest functions. These retain their
existing behavior and have no React, HTTP, or storage dependencies.

`services` coordinates workflows using the models and contracts in `types` and the pure
functions in `utils`. OperationsService receives the existing remote-session decision
from the composition root instead of importing browser authentication storage.

`api/client` owns JSON request configuration, bearer headers, multipart handling, response
errors, and uploaded-image retrieval. `api/endpoints` groups existing backend URLs by
orders, plans, loading, driver, administration, analytics, reference, auth, and deferrals.
Typed response projections remain at adapter call sites where roles use different backend
views. `types/api` owns DTOs; `mappers/operations.ts` owns pure DTO-to-model conversion.
The existing transport options, cancellation, credentials, payloads, and error fallbacks remain.
No refresh-token flow was added; the existing application has none.

`infrastructure/adapters/http` implements the API interfaces, coordinating transport,
DTO mapping, and device-only persistence. `adapters/local` retains the IndexedDB demo API.
`infrastructure/storage` owns IndexedDB, authentication/session persistence, order-form drafts,
and the store outbox. Demo seed/reference data stays in `infrastructure/demo`.
`infrastructure/auth.ts` coordinates login/session integration, separately from endpoint transport.

`app/providers/AppProviders.tsx` wires the existing QueryClient, service and API contexts,
repository, gateway, liveQuery invalidation, identity cache reset, and reconnect behavior.
Authentication continues through the existing session integration and route guards; the unused, unmounted AuthProvider has been removed. `createApis.ts` selects HTTP or local implementations.

`queries` owns server reads, mutation coordination, proof queries, device setting reads,
and outbox synchronization, grouped by the real operational features. Query keys retain
their exact existing values; `queries/keys/queryKeys.ts` owns the shared snapshot prefix.
This preserves invalidation after writes and IndexedDB updates, retries, stale time,
network modes, polling, and explicit retry behavior. Components call these hooks.

`queries/store-manager/useOutbox.ts` subscribes to persisted outbox data. Administration query modules use the `useOutlets`, `useVehicles`, and `useTeamQueries` filenames.

`hooks` owns browser behavior and local React state, including connectivity, media queries,
blob URLs, sessions, paging, form drafts, signatures, and form interaction.
`schemas` contains existing validation functions without adding a schema library.
`types/store-manager` and `types/administration` own shared feature contracts, including form values, validation results, and workflow records. Local component props and inferred hook return types stay beside their implementations to avoid reverse dependencies.
`utils/cn.ts` owns class-name composition and `utils/formatTime.ts` owns time formatting.
`types` centralizes shared declarations; `utils` contains pure business and formatting/search helpers;
`constants` contains immutable presentation configuration. New folders are created only
when there is code that belongs in them.

## Tests and checks

`test/unit/utils` contains the relocated business-rule tests. Other unit suites cover pure services, mappers/schemas, and routing contracts.
`test/integration` contains fake-IndexedDB adapter/storage/workflow tests and mocked HTTP tests.
`test/e2e` contains Playwright auth, navigation, and feature suites plus shared browser helpers.
`test/fixtures` contains the shared sign-off fixture and Goods.png.
No tests were deleted. Existing tests were relocated and their imports updated.

Vitest discovers only `test/{unit,integration}/**/*.test.{ts,tsx}` and excludes browser tests.
Playwright discovers only `test/e2e/**/*.spec.ts`. The existing strict TypeScript configuration
also checks relocated browser tests. The browser GPS fixture has a typed Window declaration.
Coverage includes production source and excludes tests and environment declarations.

Run:

```sh
npm run typecheck
npm run lint
npm run check:architecture
npm run test:architecture
npm run test
npm run test:unit
npm run test:integration
npm run build
npm run test:e2e
```

ESLint enforces type/service/utility independence, Atomic Design dependency direction,
page/transport separation, and API/React separation. `tools/check-architecture.mjs`
resolves local static and dynamic imports, enforces dependency direction after path resolution, and detects synchronous runtime dependency cycles.
The checker also resolves inline type imports, requires declaration-only type modules, and enforces UI/transport boundaries after resolving aliases and relative paths. Its fixture tests cover both rejected dependencies and valid type-only cycles.
Type-only edges and deliberately lazy route chunks are excluded from runtime cycle detection.
It complements TypeScript and ESLint rather than replacing them.

The maintained source layout is:

```text
src/
├── api/                  # HTTP clients and endpoints
├── app/                  # Feature pages, routing, and global providers
├── components/           # Atoms, molecules, organisms, and templates
├── constants/            # Navigation and shared immutable values
├── design-system/        # Theme and existing feature styles
├── hooks/                # Shared browser and form behavior
├── infrastructure/       # HTTP/local adapters, persistence, and demo data
├── mappers/              # DTO and view-model transformations
├── queries/              # Feature query/mutation/synchronization hooks
├── schemas/              # Input validation
├── services/             # Business workflows and outbox operations
├── test/                 # Unit, integration, E2E tests, and fixtures
├── types/                # Shared models, DTOs, and all shared contracts
│   └── api/              # Feature API interfaces and backend DTOs
├── utils/                # Pure business functions and shared helpers
├── main.tsx
├── styles.css
└── vite-env.d.ts
```

Types stay independent of concrete services and storage. Services depend on shared
models, contracts, and pure utility functions; global providers select and inject implementations. Tests for pure
services live in `test/unit/services`, and repository-backed workflows remain in
`test/integration/workflows`.

The obsolete `application`, `domain`, `interface`, and `interfaces` folders have been removed. An import-graph audit rooted at the
application entry point and every test verifies that all retained TypeScript source files
are used. The unused auth provider, load summary, contact helper, duplicate API factory,
reference API object, unused DTOs, and a redundant driver-action re-export were removed. All public assets and test fixtures
have consumers and are retained. Generated build/test outputs can be recreated with the
existing scripts; dependency directories and local environment files are retained.

See [MIGRATION_VALIDATION.md](MIGRATION_VALIDATION.md) for results and remaining limitations.
