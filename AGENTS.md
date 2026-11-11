# Codex repository instructions — Soup take-home

Read this file at the start of each Codex task. This evaluation is about **consistency, multi-tenant isolation, and evidence of failure handling**, not feature count. The proposed implementation uses **FastAPI + Next.js** because that is the applicant's selected stack; Soup allows any stack.

## Sources of truth (read in this order)
1. `reference/Soup-Full-Stack-Take-Home.pdf` — original employer requirements; do not silently weaken or omit any requirement.
2. `docs/BRIEF.md` — source-grounded checklist (PDF takes precedence).
3. `docs/DESIGN.md` — proposed **one-page** architecture, not yet validated.
4. `docs/STACK_GUIDE.md` — Python / FastAPI / Next.js implementation boundaries.
5. `docs/TEST_MATRIX.md` — required evidence; planned tests are not passing tests.
6. `docs/PLAN.md` — phased tasks; only the phase authorized by the current prompt is permitted.
7. `docs/EVIDENCE.md` and `docs/AI_USAGE.md` — truthful verification and AI provenance.

## Scope and working mode
- **Implement exactly the phase requested by the current prompt, then STOP.** No implementation of later phases in anticipation.
- Design before code: explain ordering, retries, snapshot/replay, tenant scope, failures and any assumptions before implementation.
- Before edits, state briefly what files and behavior you plan to change. At completion state: changed files, commands actually run, observed results including failures, remaining risks and ONE suggested next phase.
- Favor a small, demonstrably correct solution over scaffolding, premature abstractions, polished dashboards and extra infrastructure.
- **Locked architecture choice:** Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.x async (asyncpg) + Alembic; PostgreSQL; Next.js App Router + React + TypeScript; SSE via FastAPI; pytest + httpx and Playwright; Docker Compose. Use compatible maintained pinned releases; do not add a framework or change the stack without explicit permission.
- The employer is stack-agnostic; the stack above is a user decision, not an employer mandate. Do not introduce Spring Boot, Java, React/Vite frontend, Django, Next.js API backend, Redis, Kafka, Celery or microservices unless the user requests a change or verified need justifies it.
- Code and evidence must be understandable without an interview: the employer's follow-up cancelled the 40-minute live discussion. Do not copy an existing personal project; make the take-home independently reproducible.

## Non-negotiable invariants
1. **Isolation:** every project-scoped read, write, list, stream, replay, key rotation or cache lookup derives `project_id` from the validated bearer API key, never from untrusted request data. Every run lookup must be filtered by the authenticated project. A guessed UUID is never authorization.
2. **Idempotency:** retrying an identical `batch_id` + payload returns the original receipt and causes no new writes; reusing the same batch ID with changed contents fails. Unique client `event_id` also deduplicates identical events across different batches, while conflicting payloads fail.
3. **Atomicity:** metric inserts, per-run sequence updates and deduplication/receipt records must commit together or roll back. A 2xx response must not precede successful commit. Do not rely on a Python process lock for correctness.
4. **Ordering:** network arrival time != metric step. Maintain a committed monotonic per-run `seq` for replay, assigned under a PostgreSQL row lock; do not depend on nontransactional `SERIAL`/`BIGSERIAL` sequences for a gapless per-run cursor. Document deterministic UI value selection for late and equal-step events.
5. **Replay:** a client must be able to recover every committed event after its last *applied* cursor, including the snapshot-to-subscription gap. DB persistence is authoritative; an in-memory SSE broadcast alone is insufficient.
6. **UI correctness:** compare the **actual browser UI**, backend API and database via automated E2E after duplicated, out-of-order, late and missed-stream events. Do not assume API tests alone prove the UI.
7. **SSE security:** authenticate before streaming, filter every replay query by project, and ensure rotated/revoked keys do not authorize indefinite existing streams. No API key in URL, logs or browser persistent storage.
8. **Bounded memory:** don't create unbounded per-client event queues. Use bounded DB read pages and define timeout/disconnection behavior for slow clients; replay handles their reconnect.
9. **Truthful verification:** never invent test runs, exit codes, performance figures, screenshots, logs or screenshots of passing tests. Keep failures and raw output intact; mark unrun checks NOT RUN.
10. **Side channels:** do not expose another project's existence via error body, headers or obvious ID enumeration; review logs, timing and caching. Be candid about limits.

## FastAPI backend rules
- Use FastAPI strictly for all application API endpoints and SSE streams; do not split business logic between Next.js server handlers and FastAPI.
- Use Pydantic v2 request/response schemas with explicit bounds; reject NaN/Infinity, malformed IDs, oversized batches, invalid timestamps and invalid metric names. Specify exact bounds in API contract and test them.
- Keep HTTP routes thin; place domain logic in explicit service functions and persistence in SQLAlchemy models/queries. Prefer parameterized queries and clear transactions using `AsyncSession`.
- PostgreSQL is required for correctness/integration tests: SQLite cannot substantiate PostgreSQL row-lock and transaction properties. Use Alembic for schema changes; do not use `create_all` as a hidden substitute for migrations in the deliverable.
- FastAPI `StreamingResponse` may use an async generator; do not keep a transaction or `AsyncSession` open over the lifetime of the SSE connection. Open short-lived sessions for replay polls and key-revocation checks.
- Store a keyed/strong hash of high-entropy API tokens, show plaintext only once at project creation or key rotation, revoke old tokens transactionally, and avoid writing raw secrets to `.env` in version control.
- Prefer DB-backed incremental SSE polling over a broker for this scope; measure performance rather than claim it. Explicitly handle `asyncio.CancelledError`/disconnect and bounded pages.

## Next.js frontend rules
- Use Next.js **App Router** with TypeScript; build only the run list, run detail/live metrics view and minimal project/key setup required by the exercise.
- Client-side authenticated requests go **directly to FastAPI** with `Authorization: Bearer …` and `cache: 'no-store'`; configure exact allowed CORS origin(s). Do not accidentally use Docker hostname `api` as a browser URL; distinguish server-internal and browser-reachable API addresses.
- Do not place project API keys in `NEXT_PUBLIC_*`, URLs, cookies, browser localStorage, server component HTML, logs or Next.js static data cache. The demo can keep a user-entered API key in ephemeral client memory; explain reload limitations.
- Native `EventSource` cannot provide a bearer Authorization header: use `fetch()` + `ReadableStream` to parse FastAPI SSE safely, or another explicitly justified safe approach. Send `Last-Event-ID` on reconnect and advance it **only after an event has been applied**.
- Keep client event application idempotent. Abort subscriptions on unmount/key change; back off and retry transient failures, but stop/re-authenticate on 401/403. Display an explicit reconnecting/stale state; do not silently present stale data as live.
- Do not introduce Next.js server actions/API route handlers as a second backend, or use a charting/state-management library unless it materially improves the required UI.

## Testing and delivery
- Backend: pytest + httpx for API behavior; PostgreSQL-backed integration tests for transaction, concurrency and tenant isolation. Do not replace these with SQLite-only tests.
- E2E: Playwright drives the **real Next.js page**, sends metrics through actual FastAPI and independently checks persisted PostgreSQL state. Include forced SSE disconnect/reconnect and failure assertions.
- Preserve raw outputs for failures and successes under `artifacts/test-output/`, with exact commands and environment in `docs/EVIDENCE.md`. Do not fabricate outputs.
- `docker compose up` must start a usable web + API + PostgreSQL stack when implementation reaches runnable state; actually execute it before claiming it works.
- Include original requirements, <=2-page note, one-paragraph surprise/concern, explicit SHIP or DON'T SHIP for 50 runs × 10 events/s based on evidence, and AI disclosure. Do not predeclare SHIP.

## Current authorized phase
**Phase 6: final requirement audit, clean-checkout/startup/regression verification, <=2-page English submission note, honest AI disclosure and an unsent email draft. No new features, UI redesign, infrastructure or speculative refactoring. Local commits use short messages; no push/publication/email sending. Stop after final submission preparation.**
