# Versioned events and failure policy

Envelope and typed v1 payload contracts live in `packages/contracts/waypoint_contracts/events.py`
and `event_data.py`. Every event has UUID event_id, event_type, version, UTC occurred_at,
aggregate_id, source, correlation_id, data, and optional causation_id/traceparent. No password
hashes are published. Changes and outbox entries commit in the same owner transaction.

| Event | Producer | Effect/consumer |
|---|---|---|
| identity.user_changed | identity-access | operations local principal/contact projection; never authorization authority |
| network.reference_changed | network-fleet | operations full reference projection; identity validation identifiers |
| audit.recorded | identity-access / network-fleet | operations administration audit read model |
| intake.close_requested | scheduler command | operations verifies configured active dispatcher actor and actual Colombo cutoff; idempotent closure |
| order.confirmed | operations | planning visibility in the same owner's local order state; integration event retained |
| orders.closed | operations | immutable closure snapshot; operations consumer creates one closure-keyed planning job if no plan already exists |
| planning.job_requested | operations outbox | dedicated planning SQS queue; isolated optimization worker |
| plan.published | operations | loading/delivery use committed local manifests; identity trip projection and notification consumer |
| order.deferred | operations | durable reason/history/next run; scoped manager notification |
| load.shortfall_reported | operations | dispatcher notification; release blocked pending a later OK/replan decision |
| load.completed | operations | driver readiness and notification |
| delivery.started | operations | trip projection, tracking and notification |
| stop.completed / delivery.failed | operations | trip/stop state, identity trip projection, notifications |
| proof_of_delivery.recorded | operations | separate receipt-ready record and scoped outlet notification |
| receipt.confirmed / receipt.issue_reported | operations | receipt/issue history, audit and notification |
| delivery.delayed | operations | nonterminal driver delay or server-detected window deadline; scoped notification |

Orders, loading and delivery are intentionally co-owned in this phase: they read committed
local state instead of pretending an unnecessary event copy is an independent database.
The source event remains available for downstream consumers and later extraction.

Each independently consuming deployment has its own SQS queue and DLQ. Planning has a separate
job queue/DLQ. Events go through the custom EventBridge bus; jobs are sent directly to their
work queue by the transactional publisher. AWS rules/queue policies are deployment-owner work,
not created here. The local initializer only runs inside LocalStack and creates equivalent
resources there. Provider documentation lists EventBridge rules/SQS targets; pinned LocalStack 3.8.1
interoperability, DLQ redrive/replay and actual queued planning were executed successfully.
The smoke uses disposable queues/rules and leaves application queues intact.

Publishers use bounded AWS SDK retries, pending rows, per-row SKIP LOCKED claims, persisted
attempt counts and loop backoff. A crash after PutEvents but before outbox commit can publish
the same event again. Consumers insert inbox event IDs and apply effects in a local transaction,
then acknowledge. A duplicate payload is ignored; a reused event ID with different data is
rejected. Versioned projections ignore stale arrivals. No exactly-once transport is claimed.

Consumers long-poll 20 seconds with 120-second visibility and renew every 40 seconds. Failure
retries use bounded exponential visibility delays; SQS redrive after five failed receives moves
poison messages to the DLQ. Planning executes in an isolated subprocess with a 90-second wall
limit and 60-second DB statement timeout. A killed worker rolls back its plan/job transaction;
replay safely retries. Only pending jobs can be cancelled. The synchronous 201 auto-plan URL
remains a compatibility path; new clients can use the 202 job endpoints. A synchronous request
cancels an unstarted closure job under the same run lock, avoiding duplicate automatic plans.

Preserve correlation/trace context on HTTP and event hops. Do not log bodies or signed URLs.
Monitor oldest unpublished row, attempt count, queue age, DLQ depth, last successful consumer
commit, planning duration, identity timeouts, API latency/errors and DB pool saturation.
See [recovery](runbooks/recovery.md) for replay/acknowledgement procedures.
