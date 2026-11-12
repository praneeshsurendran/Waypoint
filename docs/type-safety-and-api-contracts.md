# Type safety and API contracts

The four services' Pydantic schemas and typed response contracts own the HTTP wire format.
Application view models remain in `frontend/src/types`; they represent UI state, offline
records and derived labels, rather than duplicating transport DTOs. SQLAlchemy models own
persistence. The pure allocation domain retains its dataclasses and meaningful strategy port.

## Generation and drift detection

From the repository root, configure the native environment described in `backend/README.md`:

```sh
python backend/scripts/verify/export_contracts.py
cd frontend
npm ci
npm run contracts:install
npm run contracts:generate
npm run contracts:check
npm run typecheck
```

Export does not connect to a database. It imports the four app factories, writes their OpenAPI
schemas and regenerates the ownership inventory. The frozen `legacy-v1.json` remains untouched.
Review schema changes alongside clients; never hand-edit `src/types/generated` or
`src/api/generated`. Generated files intentionally belong in version control so application
builds do not need Python or generation tooling. SHA-256 source fingerprints and byte-for-byte
`contracts:check` detect drift. No CI configuration was introduced.

OpenAPI TypeScript tooling has an isolated, pinned toolchain in `frontend/tools/contracts`
because its TypeScript 5 peer requirement differs from the application's TypeScript 6 compiler.
The generator creates types and AJV standalone validators from the same documents. Standalone generation converts AJV helper snippets into browser-native ESM and rejects any
unsupported CommonJS helper. Validators
are split by service; operational validators load lazily. Production browser code does not
compile schemas or require the generator. The local `time` format accepts Pydantic's time-of-day
representation without requiring a timezone, unlike a timestamp.

## Frontend conventions

- Endpoint helpers select a declared path and method. The response follows that operation;
  callers cannot invent a generic response projection. Requests, enums and query types come
  from generated contracts. Raw transport returns `unknown`.
- `contractRequest` validates JSON input before fetching, then validates the actual successful
  HTTP status and response body before returning its generated type. The one response assertion
  is justified by that validator. Non-JSON success payloads use the separate evidence transport.
- API errors narrow unknown JSON and preserve status, code, message and Retry-After. Invalid
  success bodies become `INVALID_RESPONSE`; malformed JSON becomes `INVALID_JSON`. Client-side
  decoding does not replace backend authentication, authorization or validation.
- A missing property, JSON `null` and UI `undefined` have different meanings. Generated wire
  optionality stays unchanged. `JsonInput` permits an undefined optional object property because
  JSON serialization omits it; explicit null is retained for clearing an assignment/contact.
  View/form types explicitly allow undefined where clearing UI state is part of their contract.
- Strict checking includes `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` across
  application and test code. Empty collections and missing lookups require guards. The test
  `required` helper fails loudly for a missing fixture; it does not skip an assertion.
- Query keys include actor/role/outlet/depot and authentication changes reset queries. Polling
  retries distinguish forbidden requests from transient errors and honor Retry-After. Existing
  APIs, service ports, component props and inferred hook results retain their typed contracts.
- Persisted profile JSON is validated with the generated user-profile validator before use.
  HTTP authentication still verifies every protected request; browser state never authorizes it.
  Authenticated private-evidence cache entries also carry an actor ID; another account must
  obtain fresh backend authorization, and the original local record is retained.

## Backend conventions

`backend/mypy.ini` checks all four service packages and technical packages (149 source files),
with `check_untyped_defs`, `disallow_untyped_defs`, `no_implicit_optional` and unused-ignore
checks. No service directory is excluded to obtain a pass. Run from the repository root:

```sh
.venv/bin/mypy --config-file backend/mypy.ini
.venv/bin/ruff check backend
.venv/bin/ruff format --check backend
```

Public route and application result boundaries have explicit return types. Pydantic
`TypeAdapter` validates ORM/dictionary results into the declared contract; typed dictionaries
are used where existing internal replay callers require dictionary semantics. Domain objects
and ORM records remain separate. FastAPI role dependencies use `Annotated` metadata, rather
than pretending a `Depends` marker is a `None` or user value. Shared read-only `Actor` expresses
what both verified principals and local ORM users provide. Unknown roles are denied.

`JobRepository`, `AllocationStrategy`, `ProofStorage`, `EventPublisher` and `MessageQueue` are
meaningful interchangeable dependencies. SQL jobs and unit-of-work implement explicit session,
transaction and nullable-result signatures. SDK stubs are development dependencies matched to
the runtime AWS SDK; `TYPE_CHECKING` imports do not require them inside production images.

Typed SQLAlchemy `Mapped` fields describe relationships, nullability and local ownership. The
order departure annotation is a query expression, not an undeclared Python attribute or a new
physical column. No schema change was necessary for this audit; all existing Alembic histories
are preserved. Counts aggregate in PostgreSQL; no stored procedure or speculative index was
added. Existing floating-point quantities describe estimated logistics loads, not monetary
amounts. Changing their persisted precision would require a separate data migration.

## Events, validation and tests

The v1 `EventEnvelope` validates supported event names, version, timezone, identity and the
corresponding payload schema. Reference snapshots validate the complete owner DTO, reject
credential fields and reject a network event claiming ownership of users. Additive fields
remain accepted for v1 compatibility. Producers enqueue within their owned transaction;
consumers validate and durably commit before acknowledging. Inbox hashes detect conflicting
replays and projection revisions reject stale updates. EventBridge/SQS remain the transport.

Contracts tests retain the original routes and exercise all four service APIs. Frontend tests
exercise malformed successes, required inputs, actual status matching, omission versus null,
authentication headers, upload boundaries and cancellation. Backend regressions cover
JWT issuer/audience/signature/expiry, password validation without echoing inputs, cross-day
plan edits, equal-timestamp cursor paging and grouped summary queries. Real Redis tests cover
multiple limiter instances, concurrent thresholds, recovery, scoped keys, cache stampedes,
invalidation, expiry and outages, including CORS headers on a 429 response.

## Explicit limits

OpenAPI query types and backend validation enforce query/path constraints; the browser helper
retains URLSearchParams/string query compatibility and does not independently validate every
query parameter. Public endpoint options require JSON bodies when OpenAPI requires them. The lower-level
contract helper also validates missing bodies at runtime for untyped callers. Broader read interfaces
do not all propagate AbortSignal into their transport, although direct HTTP operations support
it and TanStack prevents overlapping fetches for the same active key. There is no invented
refresh-token flow: bearer tokens remain persisted as before, carry an eight-hour configurable
expiry, and are revoked by authoritative account checks/password changes. LocalStorage remains
exposed to scripts in the application's origin; adopting HttpOnly cookie sessions requires a
reviewed browser/server authentication change.

Some dynamic JSON remains in stored audit documents and the integration-envelope container;
it is validated against the selected event schema at ingress. SQLAlchemy mapper metadata and
third-party SDK internals are inherently dynamic. Static annotations do not prove absence of
business defects. Historical browser mismatches and all actual validation results are recorded
in [the audit report](backend-audit-and-optimization.md).
