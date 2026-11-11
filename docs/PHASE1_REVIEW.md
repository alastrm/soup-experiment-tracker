# Phase 1 review - requirements, attacks and limits

**2026-11-10, Asia/Qyzylorda. Static design review only.** Implementation, tests, Compose startup and load measurements: NOT RUN. The architecture is specified, not demonstrated. [DESIGN.md](DESIGN.md) is the one-page architecture; [API_CONTRACT.md](API_CONTRACT.md) holds endpoint/identity/boundary details. This review is not the final <=2-page submission note or a script for the live discussion.

## Employer comparison

The reference PDF and the user's Downloads attachment are byte-identical by SHA-256 (see [evidence](EVIDENCE.md)). The full page was extracted and visually inspected. The PDF is the employer's requirements source; it does not authorize sending email or implementing later phases.

| Employer requirement | BRIEF / original DESIGN assessment | Disposition |
| --- | --- | --- |
| Projects/keys, `POST /runs/{id}/metrics`, storage, run list/live page | BRIEF complete; DESIGN lacked project/run/list/rotation request/response contracts | Seven endpoints now specified; ingestion path retained |
| One page before code: ordering, same-batch retry, catch-up, isolation | Original DESIGN named all four but deferred identity rules and left snapshot consistency abstract | Compact architecture retained; contract fixes normalization, transactions and handoff |
| E2E UI + API, unordered/duplicate/late input, mid-stream disconnect, final DB match, test blind spots | BRIEF complete; DESIGN's requirement for real UI was correct | Current-value UI includes count/cursor; matrix now specifies equal steps, intermediate assertions and independent DB expectations |
| A cannot read/write/subscribe/guess B IDs, including cache; discuss logs/errors/timing | BRIEF complete; DESIGN stated scope but did not specify list, error precedence or key-change cleanup | Scope and generic errors specified; negative evidence still required |
| Lost replay, duplicates, slow-client overflow, partial writes, old rotated key | Named in both; page-level revocation checks alone could stall behind slow sends | Independent watchdog, send deadline, bounded page/admission and failure scenarios specified |
| 50 runs at 10 events/s, SHIP/DON'T SHIP and first change | Both retained measurement; no verdict predeclared | 500 events/s is arithmetic, not measured capacity; define workload/thresholds before the later load run |
| Repository/Compose, raw output including failures, <=2-page note, surprise/concern paragraph, AI disclosure | BRIEF complete; design page need not reproduce submission checklist | Preserved; final note/provenance and actual Compose run remain later deliverables |
| 5-7h work, 48h deadline, any stack, 40-minute discussion | BRIEF faithful | Locked FastAPI/Next.js is applicant choice; no new framework or infrastructure |

**No employer requirement was missing from BRIEF.** The original architecture had omissions/unsupported assumptions rather than an explicit conflict with the PDF. Its unbounded full-history snapshot was a resource risk; it is now a bounded current-value summary. Soup does not require a chart/history UI. All committed raw events remain replayable, and the proof must still check the actual page against persisted facts.

## Adversarial findings and decisions

| Attack / failure | Required design behavior | Evidence still needed |
| --- | --- | --- |
| Two workers read the same run counter; one rolls back | Fresh scoped FOR UPDATE at READ COMMITTED, one session/task; assign only new events; receipt/counter/events in same transaction | Independent sessions/processes; commit/rollback barriers, unique seq and actual row count, not counter alone |
| Auth dependency starts a transaction; service commits too late | Explicit transaction includes auth; commit before returning 2xx; no deferred teardown commit | Instrument flush/commit failures and HTTP result; inspect SQLAlchemy boundaries |
| Identical vs changed batch races, same event across batches | Canonical normalized bytes; ordered batch; check receipt under lock; conflict rolls back all new rows | Concurrent exact/conflicting requests, canonical equivalents and reordered array, mixed old/new/conflicting batch |
| Response disappears after commit | Client cannot infer rollback from transport failure; identical retry resolves stored receipt | Lose response after successful commit, restart API, retry same ID/payload |
| Late step arrives after a high step; equal-step retry/new event | Greatest (step,seq) wins per metric; every distinct event advances count/cursor; retries do neither | UI assertions after each phase, different/equal steps and multiple metrics; compare independently computed DB winners |
| Snapshot metadata and values read different commits | Short read-only REPEATABLE READ; apply summary and H together; no full-history response | Controlled writes between snapshot queries, empty run, 128-name bound, independent DB count |
| Commit after snapshot but before subscription, disconnect mid-frame | Replay `(cursor,H]` from DB; complete applied event advances cursor, never parsed/partial data | Pause snapshot/subscribe; fragmented frames; forced disconnect before/after apply; replay from zero and nonzero |
| Restart destroys in-memory stream state | DB events/identities/counter authoritative; no pruning during demo | Persist DB volume, restart API, recover all missed seq and original receipts; DB crash durability is a separate limit |
| A supplies B's ID/cursor or switches key while callbacks run | Auth-derived scope in every read/write/list/replay/rotation; identical foreign/missing 404; abort/reset client generation | A/B matrix, random and known B UUIDs, warmed caches, stale-generation callbacks, errors/headers/log inspection |
| Rotation races a write or another rotation | Project shared lock for mutations/exclusive for rotation; revalidate key after waiting; project-before-run order | Old-key writer on each side of lock barrier; concurrent rotations; old key fails after rotation commit |
| Revoked stream has backlog or blocked transport | Fixed-tick independent watchdog, fail closed on DB timeout, cancel sends; best-effort terminal frame never delays cancellation | Timestamp rotation/last new send; backlog/idle/stalled reader; query/pool timeout, cleanup and measured buffering |
| Slow reader consumes memory or retains DB connections | One <=250-row page, no queue, 5s actual ASGI-send deadline, <=100 streams/process; close sessions before sends | Real transport backpressure/RSS/pool measurements; overflow admission503; reconnect recovers committed events |
| Next.js becomes an accidental cache/auth proxy | Client fetches FastAPI directly; public origin only, ephemeral key; exact CORS and no-store including errors | Browser network/DOM/storage/bundle/cache inspection, CORS preflight with Last-Event-ID, key switch/unmount |

## Assumptions fixed, not employer mandates

- Event/batch identities are **per run**. JSON field order/formatting is irrelevant; normalized binary64/time identity is explicit; event-array order is significant. Duplicate IDs inside one batch are validation errors. Limits are stated in the contract, not inferred from Pydantic defaults.
- Logical step selects UI values; committed seq selects replay order. No global ordering across runs. Equal steps use committed seq; occurred_at is informational.
- Snapshot is a current-value projection with event count/applied cursor, not all events or a chart. The UI retains <=128 values; raw history/receipts remain in PostgreSQL without retention. Disk usage grows and needs measurement.
- Local project creation is unauthenticated; bearer keys represent project authority, with one active key and no user roles. No public-production bootstrap/security claim. Browser reload needs key entry. Lost rotation response can strand a project; recovery/roles are explicitly outside this minimal demo.
- Revocation is bounded by a **target** under responsive scheduling, not instantaneous revocation of network-buffered bytes. Send timeout must surround ASGI transport; an async generator timeout alone does not solve a blocked send.
- A restored old backup could invalidate client cursors; cursor_ahead is surfaced and requires explicit reset. Process-restart replay assumes intact persistent DB storage. No durability claim for disk destruction, replicas or power loss is established.

## Three largest remaining technical risks

1. **Transactional implementation mistakes.** SQLAlchemy implicit transaction/session state, stale reads after lock waits, cancellation around commit and mixed duplicate conflicts can invalidate the otherwise sound lock protocol. Only PostgreSQL concurrency/fault evidence can substantiate it.
2. **Stream lifecycle under backpressure/revocation.** Cancellation, ASGI buffering, watchdog/pool starvation and React application order span multiple runtimes. The 2s revocation target/5s send deadline and replay completeness are unmeasured; already-sent bytes are not revocable.
3. **Capacity as durable history grows.** Every ingestion locks a run; polling/auth checks consume DB capacity and snapshot winner queries scan growing history unless indexes/plans suffice. Per-stream bounds do not prove safe RSS, disk growth, 500 events/s or side-channel-free multi-tenancy. Local bootstrap and lost-key recovery also limit deployment scope.

## Implementation evidence and blind spots

Execute the [matrix](TEST_MATRIX.md) against real PostgreSQL and Next.js. Preserve exact commands/environment and raw success/failure output. Include injected rollback/ambiguous commit, API restart, forced SSE loss/slow reader, old-key stream termination and A/B/cache probes. Validate page text/steps/winners/count/cursor against independent SQL, with producer quiescence and assertions that failures show stale/re-auth state. Final winners/count cannot alone detect every transient render error: assert intermediate states and stream sequences too. Shared backend/frontend reducer bugs must not define the DB oracle.

Before load testing, record duration, batching, payload size, number of keys/subscribers, hardware/versions, warm-up, acceptable error/lag/resource limits and recovery backlog. Exercise 50 concurrent runs x10 events/s with 50 live pages/streams; include one project with many runs and distinct-project keys. Report actual accepted/committed/applied counts, errors/lag/resources and first bottleneck. No latency SLO is supplied by Soup; applicant thresholds must be declared before measurement. A short local run cannot prove production capacity, all browser behavior, constant-time errors, all log leaks, crash durability or every disconnect schedule. No SHIP verdict yet.

**One proposed Phase 2 scope:** FastAPI foundation with pinned dependencies, PostgreSQL/Alembic and API+DB Compose startup, project/key create/rotate, run create/list, tenant-aware auth and PostgreSQL pytest/httpx evidence. No ingestion, SSE or Next.js implementation in that phase. The complete web+API+DB Compose milestone remains Phase 4. This proposal is not authorization to start.

## Primary references for design reasoning

- PostgreSQL [isolation](https://www.postgresql.org/docs/current/transaction-iso.html) and [row locks](https://www.postgresql.org/docs/current/explicit-locking.html): READ COMMITTED statements can observe different views; row locks serialize conflicting writers, and SERIAL sequences are not rollback counters.
- SQLAlchemy [async sessions](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) and [transaction isolation configuration](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#setting-transaction-isolation-levels-dbapi-autocommit): one AsyncSession/task; set snapshot isolation before transaction SQL.
- FastAPI [CORS](https://fastapi.tiangolo.com/tutorial/cors/) and MDN [SSE framing](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events): explicit origins/header policy and incremental blank-line-delimited events. These docs support protocol choices, not verification of this application.
