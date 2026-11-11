# AI assistance disclosure (editable provenance log)

Soup permits AI tools but explicitly asks which suggestions were accepted, verified, changed or redone. Keep this record honest; the applicant should personally complete it before submission.

**Current disclosure (Phase6):** Codex wrote/reviewed architecture, backend, frontend, tests, load tooling and documents, and executed the cited automated checks with tools. The applicant selected FastAPI/Next.js, scope/dark UI, accepted phases, supplied the employer's follow-up and personally stated the generator surprise/long-term slow-SSE concern used in the note. Independent human code review/test execution is **NOT RECORDED**; acceptance of a phase is not such verification. Earlier entries below are chronological, not current-status claims. The employer cancelled the live discussion, so the final written disclosure must stand alone.

## Initial context proposal (earlier version)
- Assistance: ChatGPT summarized the one-page Soup PDF and drafted initial rules, architecture, risk tests and an incremental Codex prompt.
- Initially suggested: Java 21 / Spring Boot, React + Vite / TypeScript, PostgreSQL, durable SSE, transactional per-run sequencing and project API keys.
- Outcome: **framework choice replaced at applicant's explicit request**. The original suggestion is preserved here as provenance, not the current design.

## Revised context proposal (current version)
- Assistance: ChatGPT inspected the publicly available developer portfolio and rewrote the Codex context and phase-1 prompt around Python/FastAPI and Next.js.
- Selected framework choice: FastAPI + Next.js (requested by applicant), PostgreSQL, SQLAlchemy async + asyncpg, Alembic, pytest and Playwright.
- Other suggested technical choices: database-backed SSE replay, per-run transactional sequencing, project-token isolation; these are **draft design decisions requiring review and tests**.
- Human acceptance of specific architecture/trade-offs: **NOT YET RECORDED**.
- Independent human code review/verification: **NOT YET RECORDED**.
- Tests executed for this context package: **NONE**. Only markdown documents and a copy of the source PDF were prepared.
- Implementation: **NOT STARTED**.

## Template for later AI-assisted work
- Date / task:
- Tool and prompt summary:
- Suggestions accepted:
- Suggestions rejected or changed (and why):
- Human verification (exact command/output/code inspection):
- Remaining uncertainty:

## Phase 1 - design review and contracts (2026-11-10, resumed after user pause)

- Tool/task: Codex read AGENTS.md, original PDF and current docs, compared employer requirements, challenged transactions/replay/isolation and edited documentation only. PDF extraction/rendering, file hashes, official documentation reads and a document-layout/link inspection were used; no application code or tests were executed.
- Incorporated AI suggestions: canonical batch/event identity and bounds; explicit AsyncSession/lock/commit order; bounded current-value snapshot; contiguous applied-cursor reducer semantics; durable replay, independent revocation watchdog/send deadline; FastAPI-only API ownership, direct browser fetch/CORS/no-store/ephemeral keys; additional negative evidence scenarios. These are design proposals incorporated in docs, **not independently verified implementation facts**.
- Changed/rejected assumptions: unspecified payload identity replaced with versioned normalization; full-history snapshot replaced by <=128 current metric winners; replay-page key checks replaced with independent fixed-tick watchdog; generator-only timeout rejected; final UI equality alone supplemented with intermediate state/sequence checks. No new framework, broker or existing project code used.
- Observed verification: employer PDFs have identical SHA-256; full one-page source visually inspected; DESIGN 440-word layout calculation fits one page at stated settings; local links resolved at inspection. See [EVIDENCE.md](EVIDENCE.md) for actual command/output record and inspection-tool failures. None is a passing application test.
- Human acceptance of specific new limits/trade-offs: **NOT YET RECORDED**. Independent human verification/review: **NOT YET RECORDED**. This entry does not attribute AI work to the applicant or invent their personal surprise/concern paragraph.
- Remaining uncertainty: every software behavior/test matrix row, performance/security claim and SHIP verdict is unverified; local bootstrap/lost-rotation recovery and persistent-history capacity limits are disclosed in the review. Implementation still **NOT STARTED**.

## Phase 2 - backend implementation (2026-11-11)

- User explicitly accepted Phase 1 and authorized expanded Phase 2 including ingestion; no framework change. Codex wrote the FastAPI/services/schemas/SQLAlchemy models, explicit Alembic migration, Compose/Docker setup, dependency pins and focused PostgreSQL tests/live HTTP smoke. No existing personal-project code, Next.js or SSE used.
- Accepted design implemented: auth-derived scope, project/run lock order, atomic receipts/events/counter, canonical event/batch identity, deterministic snapshot winners, ephemeral plaintext token issuance and hashed storage. Docs updated only for run instructions, authorized scope and actual evidence.
- AI mistake found by real tests: a serializer converted ORM timestamps to strings; initial host/container runs failed9 cases. Direct service failure exposed it; changed serializers to JSON-only and corrected error classification. Also fixed non-root pytest-cache permissions and made commit fault injection independent of ORM weak references. Raw failures retained.
- Observed verification: host/container each36 pytest cases passed; live HTTP/API restart/independent SQL smoke passed; migration current/check and Compose health passed. Exact commands/output in EVIDENCE.md; no browser/load/security-completeness claim.
- Independent human code review/verification: **NOT YET RECORDED**. Phase 1 acceptance is recorded by user message; it does not certify Phase 2 code or performance. Remaining UI/SSE/E2E/load/final-submission work is unimplemented and requires further instruction.

## Phase 3 - SSE, dark browser UI and focused proofs (2026-11-11)

- User accepted Phase2 and authorized durable SSE/Next.js App Router/TypeScript/Tailwind with dark visual direction. Codex implemented database replay, independent revocation watcher/send bounds, client parser/applied-cursor state, bounded SVG chart history, persistent session layout and real PostgreSQL/Chromium tests. Supplied MLflow/W&B screenshots informed structure/charts; no product code copied.
- Corrected the summary-only chart assumption: replay initial history from0, retain latest2,000 events explicitly, preserve cursor/points on reconnect. No endpoint/schema change, broker or second backend. Phase2 ingestion/schema/tests preserved.
- Observed failures retained: npm wrong working directory; TypeScript test imports/property typing; HTTPX repeated iterator test misuse; Next alert selector ambiguity; genuine form remount race on project switch. Fixed the UI race with persistent App Router shell/access. Also guarded valid metric names colliding with object prototype properties and validated metric payload before cursor advancement.
- Executed PostgreSQL/TCP tests, client tests/type checks, production Compose build and Chromium/HTTP/independent SQL proofs including1-10/11-30, duplicate replay, actual API restart, snapshot gap and live rotation. See EVIDENCE.md/raw logs for exact counts/outcomes, not inferred passes. Browser screenshots are actual application state. No load test/final report, no invented performance/security proof.
- Independent human code review: NOT RECORDED. Phase2 acceptance does not imply acceptance of Phase3 code. Remaining limits: chart window/initial-history cost, broader transport failure/memory/side-channel/browser/multi-worker evidence and eventual evaluation/delivery work.

- Empty-run usability follow-up: Codex added a clearly labeled, user-triggered demo submission button and a focused Chromium/SQL test (1 passed). Demo metrics are real API-persisted generated samples, not training results or synthetic test evidence; no additional phase/load/report work performed.

## Phase 4 - adversarial verification (2026-11-11)

- User accepted Phase3 and authorized failure/isolation verification, not UI redesign, ML training, load testing or a final report. Codex re-read the full original one-page PDF, checked attachment/reference hashes and compared pending proofs with implementation/matrix.
- Codex authored14 PostgreSQL/TCP/failure tests plus2 additional isolation/CORS cases, test-only TCP helpers/relay, and5 additional Chromium/runtime privacy cases. No new deployed service/dependency/schema or UI change. Faults use actual PostgreSQL termination/deferred commit trigger/locks/outage, actual HTTP response loss, actual TCP backpressure/partial bytes, concurrent independent API processes and independent SQL/UI comparison.
- Confirmed/fixed two production defects: repeated EOF send after transport timeout (extra stalled-send interval/resource retention); native asyncpg socket connection failure returned500 instead of retryable503. Only backend/app/stream.py and db.py changed in production.
- Preserved failed outputs. Corrected test mistakes separately: exact2s timeout raced the watchdog bound, prematurely discarded HTTPX iterators closed admission streams, await inside cookie-check comprehension made an async generator, Linux polling missed brief pressure peaks so send-boundary buffer observations were also used. None is relabeled as a production bug.
- Actual final results: Linux58 passed; Windows56 full suite plus2 newly added cases passed; Chromium9 passed; client5 passed/typecheck0. Human independent review remains NOT RECORDED. These are limited reproducible experiments, not a claim of complete security or production capacity. See EVIDENCE.md for raw commands, failures, measured values and remaining unverified assumptions.

## Phase 5 - measured local load evaluation (2026-11-11)

- User authorized50 runs x10 events/s evaluation, not a final submission note/email. Codex wrote the asyncio/httpx generator and read-only raw-result analyzer, declared gates before execution, and used real authenticated endpoints, PostgreSQL,50 SSE consumers, Docker stats and existing regression suites. No application/UI/schema/dependency/Compose behavior changed.
- AI-generated tooling initially saturated its shared HTTPX connection pool on the Windows generator:288.5 events/s, unsent batches,94.5% of one client CPU core. cProfile showed connection assignment/import discovery overhead. Kept the failed workload/profile; changed only generator clients to one bounded client per run. A short follow-up still failed the throughput gate despite complete storage, and was also preserved. This is a measurement-tool correction, not a server optimization or suppressed application failure.
- Actual full repeats:498.92 events/s baseline and498.17 with50 SSE, each35,000/35,000 unique events stored and audited,300 identical retries, no HTTP errors or timeouts. All50 SSE cursors700; deliberate disconnect resumed400, recovered known missing401-455, then continued to700. Scoped local SHIP uses the explicitly recorded1% tolerance; strict500 completions/s is not claimed. Full backend58, browser9, client5 and TypeScript check passed again.
- Summary/analysis JSON and document tables are explicitly derived from raw captures, not passed off as raw test output. Generator source is frozen per attempt. Independent human execution/review is still NOT RECORDED; no personal surprise/concern paragraph or final submission was invented.

## Phase 6 - final preparation

- User authorized requirement audit, clean-checkout/final tests, a <=2-page English note, test instructions and an unsent email draft. Codex prepared those artifacts and preserved historical failures, including the two explicitly missing Phase2 raw captures. No application feature, UI redesign, new infrastructure or speculative refactor.
- The applicant supplied the follow-up email text cancelling the interview and their own surprise/concern paragraph. The note edits that actual reflection; it does not manufacture personal debugging/test execution. Email headers/timezone were not independently accessed. The draft uses a repository URL placeholder until the applicant publishes it.
- Final automated results/commands belong to EVIDENCE.md; no prospective run is counted as a pass. Note/architecture PDFs use a documentation-only renderer and visually inspected physical page counts. Applicant review, public repository access and actual email delivery remain human actions.
