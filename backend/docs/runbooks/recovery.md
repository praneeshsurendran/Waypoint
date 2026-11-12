# Runtime recovery

- Outbox backlog: inspect unpublished count/age and attempts in the owning DB. Restore transport
  access and let publishers retry; never mark rows published manually without delivery evidence.
  Publishing succeeded before a process crash can legitimately produce a duplicate.
- Consumer crash: leave the SQS message unacknowledged. After visibility expiry it replays; the
  inbox protects committed effects. A crash after commit/before DeleteMessage does not repeat them.
- DLQ: quarantine and inspect the event type/version/ID using authorized tools without logging PII.
  Fix the incompatible payload or handler, replay the **same** event ID when effects are intended
  to remain idempotent, and record operator, reason and result. A corrected business action needs
  a new event ID/causation link; do not mutate a processed ID to bypass conflict checks.
- Out-of-order projection: inspect per-aggregate revisions. Older events are ignored. A deliberate
  rebuild should start from an owner snapshot and a known cursor, not delete inbox state blindly.
- Planning timeout/crash: the isolated subprocess exits; its DB transaction rolls back. Retry the
  same job; successful/cancelled/failed jobs are terminal. Pending jobs can be cancelled through
  the API. If a job reaches the DLQ, inspect it before manual replay. Do not publish a second run
  from another worker outside the date lock/version checks.
- Offline conflict: preserve the original device operation, proof and payload. Fetch authoritative
  trip/stop state and explain the conflict. Never turn a rejected arrival into delivery, overwrite
  a completed stop or acknowledge uncommitted work. Reassignment may require dispatcher review.
- Identity outage: protected services return 503 instead of trusting role headers or a stale token
  projection. Restore identity/DB/HTTPS before retrying; public probes remain available.
- DB restore: restore into isolated instances/databases, verify migration heads, PK/count/checksum
  reports and proof-object digests, restore inbox/outbox with business state, then exercise replay
  before reopening ingress. RDS PITR and Multi-AZ failover must be tested in the owner's AWS
  environment; local PostgreSQL tests do not prove those cloud properties.

Deployment acceptance still requires API Gateway stage rewrite, Lambda authorizer, private
ALB/task/RDS reachability, TLS certificate rotation, task-role IAM denial tests, EventBridge rule
fan-out, SQS DLQ/visibility behavior, S3 encryption/URL expiry, task SIGTERM, and backup/PITR drills.
No live AWS resources or cloud acceptance tests were executed by this work.
