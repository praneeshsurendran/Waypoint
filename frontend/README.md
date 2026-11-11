# WAYPOINT frontend

A responsive operations demo for Waypoint. Includes Dispatcher, Store Manager, Loader, Driver, Entry & Account, Administration, and Recovery. All workspaces share one persistent local dataset. Start with [the frontend architecture guide](docs/ARCHITECTURE.md) for component placement, feature ownership, API boundaries, and tests.

Loader uses depot-scoped API reads, vehicle/trip deep links, structured shortfalls,
revision acknowledgment and reviewed loading photographs. Dispatcher review and
publication now generate every allocated manifest. See
[Loader implementation and backend handoff](docs/ARCHITECTURE.md) for
contracts, local-only persistence and remaining server dependencies.

## Run locally

Use Node.js 20.19+ or a supported newer LTS and npm. Validation for this migration used Node.js 22.23.3.

```powershell
cd C:\Users\abdul\Waypoint\frontend
npm ci
npm run dev
```

On macOS or Linux with nvm, run these commands from `frontend`:

```sh
nvm install
nvm use
npm ci
npm run dev
```

Open the address printed by Vite. To review the production PWA:

```powershell
npm run build
npm run preview -- --port 4173
```

Open `http://127.0.0.1:4173`. Serve `dist` with a static host that rewrites application routes to `index.html`. Use HTTPS for deployed PWA service workers; localhost is supported during development. Never put a Figma personal access token in Vite environment variables or frontend code.

## Verification commands

```powershell
npm run lint
npm run typecheck
npm run check:architecture
npm run test
npm run build
npx playwright install chromium
npm run test:e2e
npm run format:check
```

On this machine the downloaded test browser is inside the project. Use this before browser tests:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = 'C:\Users\abdul\Waypoint\frontend\.playwright'
```

If npm cannot write its default cache, set `$env:npm_config_cache` to the project's `.npm-cache` directory. Both local caches are ignored by Git. The lockfile is included; use `npm ci` for repeatable installs. Generated production files, test reports, and uploaded photographs are not committed.

## Walk through the shared workflow

1. Open `/workspaces` to select a role, and `/demo` for cutoff/offline/sync scenarios. Demo controls are separate from product layouts.
2. Dispatcher: Start allocation, review allocation, publish the plan.
3. Loader: reconcile rear/front quantities, complete safety checks, select a real loading photo, review it and confirm completion.
4. Dispatcher: refresh readiness and dispatch VEH055 Trip 1.
5. Driver: open `/driver/pre-departure`, confirm the cleared load and start. Open navigation, confirm safe parking, capture/review/attach a photo and wait for the Store Manager’s confirmation. If the manager screen or connection is unavailable, choose Manager signs on this device for the signed offline fallback.
6. Captured drafts and submitted offline proof survive reload. `/driver/sync` shows local save, upload, failure and acceptance; pending records resume online, failed uploads require explicit retry, and a route change requires review without replacing the original proof.
7. Store Manager: open Deliveries, review the arrived handoff photo and received quantities, add remarks and sign, then confirm once. The signed handoff records receipt and shortfalls without another order drop-off action.

The featured live handoff is VEH055 Trip 1. `/demo/map` exposes the Leaflet adapter on its own.

## Reset and persistence

Open `/demo`, select **Reset demo**, then confirm the reset. Reset clears this browser's demo changes, photographs, queue, drafts, and audit history and restores seed data. It does not reset other devices or origins.

Dexie stores snapshots, image blobs, and queue entries in IndexedDB. Evidence, its queued action, and the business state change are saved in one transaction. Failed/reviewed records keep their original evidence. An interrupted syncing record becomes retryable on startup. Accepted records remain available in Saved records & sync. Changing browser, hostname, port, or profile uses a different local database.

## Offline and browser limits

- The production PWA caches its application shell, route modules, fonts, and bundled assets after an online visit. Vite's development server is not the offline test target.
- Forms and evidence saves use the local repository even when offline. Sync runs through Saved records & sync or once when the browser reconnects; acceptance is simulated locally.
- Leaflet uses attributed OpenStreetMap tiles online. Saved stops and route lines remain available offline; an offline basemap is not provided.
- Camera capture uses the browser's file input with `capture="environment"`. Mobile browsers may open a camera; desktop and unsupported browsers use file selection. Only JPEG, PNG, and WebP images up to 10 MB are accepted; HEIC requires conversion.
- Browser storage can be cleared or evicted, and private mode/storage restrictions may prevent persistence. This demo does not provide backups or guaranteed retention. Do not treat it as a production evidence store.
- Driver proof requires manager remarks, unloading confirmation and an e-signature. Route start verifies the assigned Loader-confirmed and Dispatcher-released truck; proof navigation unlocks after arrival at an assigned outlet. Route history keeps daily timestamps. Delays & issues handles delays/breakdowns and optional revised ETAs; dispatch decides rescheduling/cancellation. Manager call/SMS links open from a Contact button. GPS is opt-in and saves device coordinates locally. Delivery alerts persist in the store inbox, with optional browser system notifications. Remote location/alerts, real ETA and upload acceptance await the backend. Fresh receiving windows must allow completion by 08:00.
- Workspace switching is not authentication or authorization. No invitations, operational notifications, dispatch messages, or backend API calls are sent. The development map uses external OpenStreetMap tiles.

## Project documentation

- `docs/ARCHITECTURE.md`: source layout, component placement, contracts, services, persistence, and test conventions.
- `docs/MIGRATION_VALIDATION.md`: validation results and known browser-test limitations.

## Driver design continuity

Driver now uses separate native React pages for the Figma journey and recovery states. The obsolete Driver frame renderer was removed. The shared web shell and design tokens are retained. Driver uses the same React Leaflet map as Dispatcher, with saved-stop overlays and functional zoom/recentering. Navigation instructions and upload acknowledgements remain explicitly simulated. Driver components follow atoms, molecules, organisms, templates, pages and hooks, styled with Tailwind. See [the Driver report](docs/ARCHITECTURE.md) for implementation details and intentional differences from the prototype.

## Stack

React, TypeScript, Vite, Tailwind CSS, shadcn/ui with Radix controls, TanStack Query, Dexie, vite-plugin-pwa, Leaflet, Framer Motion, Vitest, and Playwright. DM Sans fonts are bundled locally. Route modules retain their existing lazy-loading boundaries; the production service worker precaches them for offline navigation. Product pages reflow at 760px and 1100px.

## Source organization

Route pages live in `src/app/<feature>`; providers and routing live in `src/app/providers`
and `src/app/router`. Reusable UI lives in `src/components/{atoms,molecules,organisms,templates}`.
The existing features are administration, dispatcher, driver, entry-account, loader,
store-manager, recovery, and demo. Shared navigation metadata lives in `src/constants/workspaces`.

`src/api` owns HTTP transport, endpoint paths, and errors. Shared models, backend DTOs,
and API contracts live in `src/types`. `src/queries`
owns TanStack Query reads, mutations, and synchronization hooks. Business services live in `src/services`; pure business calculations and validation helpers
live in `src/utils`. Local persistence and concrete API implementations live in `src/infrastructure`.
The composition root still selects the HTTP backend when `VITE_API_URL` is configured and
otherwise uses the IndexedDB demo. Authentication session integration lives in `src/infrastructure/auth.ts`.

All tests live under `src/test`: pure unit tests in `unit`, repository and API/workflow
integration tests in `integration`, Playwright specs and helpers in `e2e`, and shared test
data in `fixtures`. Run `npm run test:unit` or `npm run test:integration` separately;
`npm run test` runs both. Playwright discovers only `*.spec.ts` under `src/test/e2e`.
Production modules use the existing `@/` alias; Playwright helpers use relative imports.

See [the architecture guide](docs/ARCHITECTURE.md) for the maintained source layout and
[validation notes](docs/MIGRATION_VALIDATION.md) for verification results.
