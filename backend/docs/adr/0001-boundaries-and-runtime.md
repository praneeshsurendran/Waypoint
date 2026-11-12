# ADR 0001 — extract true owners, keep coupled operational transactions

Accepted for this repository migration. The proposed service list is a target domain map,
not evidence of existing independent persistence. Identity, reference ownership and notifications
are independently deployable now. Orders/planning/loading/delivery remain in operations because
working response properties and state transitions cross these records transactionally. Splitting
those today without projections/sagas would break compatibility or create a shared database.
Planning work executes independently against its owner's database and uses its own job queue.

ECS Fargate is the baseline; EKS offers no necessary repository capability to offset its control
plane/operations cost. REST API is selected for direct WAF protection, using VPC Link V2 to an
internal ALB. HTTP API is an alternative only after redesigning the WAF/front-door protection.
Use managed EventBridge fan-out plus independent SQS/DLQs; Kafka/MQ would add operational
requirements without a demonstrated stream retention or broker protocol need. Local Nginx is
path routing only. No Python gateway, Redis, CI/CD or infrastructure provisioning was added.

Tradeoffs: authoritative identity calls improve revocation/resource safety but add an availability
and latency dependency; they have bounded timeouts and fail closed. Reference projections are
eventually consistent. Operational transactions remain local and preserve frontend behavior.
The deterministic optimizer is explainable and feasible, not proven optimal. Browser push and
forecasting model integrations remain optional and are not simulated as working deployments.
