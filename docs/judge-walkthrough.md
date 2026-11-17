# Local judge walkthrough

Use the root Compose stack and its five seeded logins (`manager`, `dispatcher`, `loader`,
`driver`, `admin`); the password is `DEMO_PASSWORD` in `.env` or `backend/.env`. Shared references
and trained artifacts must first exist in the private backend workspace; they are already copied
on the current machine. A fresh checkout needs the authorized private restore described in
[Datathon setup](../backend/intelligence/README.md). No account or data is reset on restart.

```sh
cp .env.example .env
docker compose up --build
```

Open http://localhost:5173. The local server uses the supplied 2026-02-16 delivery day and a
09:00 demonstration clock so orders and planning remain reproducible after 16:00 wall time.
This clock applies only to demo mode. Production uses real Asia/Colombo time and must disable demo mode.
The seed imports the shared 120-outlet/60-vehicle references and representative whole orders.
Coordinates are approximate district geocodes because the source references do not supply GPS.

1. Sign in as **manager**. In Orders, review the existing OUT001 orders, create or replace the
   dry/chilled order and confirm quantities and receiving windows. Fresh weight/volume derives
   from cases; separate dry and chilled records remain separate. Optional: toggle browser offline,
   create a change, reconnect and verify it leaves the pending queue exactly once.
2. Sign in as **dispatcher** in another browser profile. Open Orders, close intake, then propose
   allocations in Planning. Inspect assignments, hard constraint feedback and deferred orders.
   Review deferral reasons and publication checks, then publish. Depot, temperature, van access,
   weight, volume, windows, two trips and weekly fuel remain hard constraints.
3. In Planning, request **Estimate saved plan** for handling/late-risk predictions. Open the Analytics
   screen's demand forecast for learned weekly demand and its dated backtest. An unavailable
   model is reported explicitly and never bypasses publication checks.
4. Sign in as **loader** on a phone-sized browser. Select the published vehicle assigned to the
   seeded driver. Enter loaded counts, complete safety checks and attach a real JPEG/PNG/WebP
   loading photo. Report a missing/damaged quantity before completion to demonstrate shortfall
   revision, then resolve it with the dispatcher and recheck the revised manifest.
5. As **dispatcher**, inspect the completed load and release it. Release requires current-revision
   loading completion and proof. Never edit a database row to bypass this step.
6. As **driver**, open Home, complete Before-you-leave, start the route and select the first assigned
   outlet. Confirm arrival/parking. Capture proof, review quantities and obtain manager sign-off,
   either in the manager's Deliveries screen or on the driver's device. Include required remarks
   and an actual drawn signature.
7. Disconnect the driver's browser after opening the route online. Submit proof locally and refresh:
   retained evidence remains pending. Reconnect and verify one accepted event, evidence and updated
   order/stop status. A stale manifest requires review/re-signing; interrupted uploads require Retry.
   The online smoke checks also replay the same operation ID and verify deduplication.
8. As **manager**, open Deliveries, inspect retained driver evidence, confirm the received quantities
   or report the exact discrepancy. Check Alerts/Notifications. As dispatcher inspect resulting
   delivery status; as admin inspect the durable audit trail.
9. In Profile, edit contact details and test offline persistence. Role/outlet changes are requests:
   submit one, then review **Assignment change requested** in the admin audit log. Users cannot
   self-promote or reassign their outlet.

For a repeatable automated cross-service walkthrough on a running **local** stack:

```sh
API_BASE_URL=http://localhost:8000 DEMO_PASSWORD=local-role-password-change-me \
  .venv/bin/python backend/scripts/verify/http_workflow.py
API_BASE_URL=http://localhost:8000 DEMO_PASSWORD=local-role-password-change-me \
  .venv/bin/python backend/scripts/verify/intelligence.py
```

Use the actual local password and plan ID (`VERIFY_PLAN_ID`) when changed. The HTTP workflow
creates a separate operating day's order/plan, preserves existing seed/history, and exercises
loading, release, driver proof, duplicate replay, receipt and notifications. Do not run these
write checks against a live production deployment.
