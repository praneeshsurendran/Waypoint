# Database ownership

| Deployment | Authoritative tables | Owned read projections / technical tables |
|---|---|---|
| identity-access | users (password hashes, auth revision, assignments), identity audit_log | network_depots/network_outlets/network_vehicles identifiers; delivery_trips; projection_versions, outbox, inbox |
| network-fleet | depots, outlets, vehicles, calendar_days, vehicle_weekly_fuel, network audit_log | outbox, inbox, projection_versions |
| operations | orders/order_lines, intake_closures, plans/trips/stops/stop_orders, deferrals, load_checks, delivery_events, receipts/issues, vehicle_positions, proof_objects, audit_log, planning_jobs, device_operations/device_cursors | local depots/outlets/vehicles/calendar_days/users copies for legacy FK/response compatibility; outbox/inbox/projection_versions; historical notifications |
| notifications | notifications, notification_reads, notification_delivery_log | inbox; independent technical schema |

Operations' reference/user rows are local projections, not references to another database.
All SQL joins and FKs remain inside one owner's database. No runtime imports another service's
ORM. Bootstrap transfer tooling is an explicit offline administrative exception, not a shared
runtime repository. Original operational FKs and keys are preserved; there is no destructive
split/drop/reseed migration. Existing source password hashes are preserved in identity. Stop
using legacy local authentication after cutover; old copies can only be scrubbed after backup,
identity verification and a separately reviewed compensating migration.

Separate database users are demonstrated in `local/databases.sh`; CONNECT is revoked from
PUBLIC for owner databases. Each migration runs with the owner's credentials, not a shared
superuser. In AWS use separate Secrets Manager secrets and task roles for each principal.
A shared RDS instance is a cost decision, not permission to read other service tables.

Network/fleet owns fuel quotas. The current application does not capture measured fuel
receipts; operations retains the legacy weekly usage snapshot and validates cumulative
planned fuel against it. An accounting integration must feed authoritative usage before
claiming real-world fuel settlement. Plan generations do not deduct fuel a second time on
replanning. Availability changes publish revisioned reference snapshots.

Migrations: legacy operations 0001–0003 preserved; 0004 adds reliability/proof/closure/job
records and availability/trip revision fields; 0005 adds receipt replay identity and query /
single-published-plan indexes; 0006 indexes actor/device/sequence recovery without rewriting
existing evidence. Other services start at frozen `0001_owned_schema`. Unrelated
legacy nullable timestamp columns are intentionally not tightened without a separate backfill.
The unique published-plan migration refuses existing duplicate runs rather than deleting them.

Rollback and backup instructions: [migration runbook](runbooks/migration.md).
