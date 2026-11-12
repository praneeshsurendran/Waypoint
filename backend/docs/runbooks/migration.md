# Data migration and rollback

1. Inventory the original database revision, table/PK counts, original upload volume and valid
   user/password hashes. Stop destructive `seed.reset` use. Freeze writes for the final copy;
   dry-run reads alone do not establish a cutover synchronization protocol.
2. Take a custom-format pg_dump backup using environment/service-file credentials, restrict its
   filesystem permissions and validate `pg_restore --list`. Restore into a separate isolated DB
   and compare table counts/IDs before treating the backup as recoverable. Back up the upload
   volume separately; a DB dump does not contain photographs.
3. Create isolated identity/network/operations/notification databases and users. Apply each owner's
   Alembic history **once from a migration job**. To retain existing operations data, upgrade its
   existing 0001–0003 lineage through 0004/0005/0006; do not recreate it. A duplicate-published-plan
   preflight failure requires a reviewed business decision before retrying; no rows are deleted.
4. Configure LEGACY_DATABASE_URL, IDENTITY_DATABASE_URL and NETWORK_DATABASE_URL, then run
   `python backend/scripts/migrate/transfer.py` for the default dry-run. It compares shared columns
   by primary key, refuses conflicting target records, reports counts/checksums and never overwrites
   or deletes a source row. Review output without exposing connection strings or hashes.
5. After backup/restore verification, run the same script with `--apply --backup-file /secure/legacy.dump`.
   Targets are copied in local transactions, and sequences are advanced past copied integer IDs.
   It bootstraps identity reference/trip projections. Re-run to prove idempotency. Cross-owner
   copying is administrative tooling, not a runtime data-access permission. Verify every owner
   report and the source order/plan/delivery/receipt counts and keys before changing routes.
6. Run `python backend/scripts/migrate/proof_inventory.py --legacy-upload-dir /secure/original-uploads`
   as a dry-run. Resolve missing files, invalid types, conflicting owners and ambiguous paths.
   With --apply it records immutable private metadata and copies to S3 if configured, preserving
   original files and URL keys. For local storage, point UPLOAD_DIR at the retained/copied volume.
   Keep evidence writes quiesced while verifying SHA-256 and ownership. Retain unreferenced files
   for review; never delete them as part of cutover.
7. Start publishers/consumers, verify lag is zero, check identity authorization with all roles,
   switch exact ingress paths to their owners, and run the four-role walkthrough. The ops task must
   have SERVICE_MODE=operations, IDENTITY_URL configured, and no public static uploads. Production
   additionally disables demo clock/seeding and requires verified DB/identity TLS and private S3.
8. Keep the source backup and routing manifest through the rollback window. Before new-owner
   writes, rollback can restore old routing and retained volumes. After such writes, reconcile/replay
   the new owner audit/outbox back into a tested recovery target before routing back. Do not simply
   point at the stale legacy DB. Password hashes must be verified in identity before retiring legacy
   auth; optional legacy hash scrubbing is a separately reviewed follow-up, not a destructive default.

Local validation performed during this migration uses synthetic data only: four non-superuser
owner roles, migrations applied twice, dry-run/apply/rerun transfer, original ID/password preservation,
unchanged source counts and rejected cross-database access. See testing.md for actual output.
