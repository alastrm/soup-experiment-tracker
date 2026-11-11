# Phase 1 pause / resume context

**Resume outcome:** user subsequently said "продолжай". Phase 1 static review is now complete; see [PHASE1_REVIEW.md](PHASE1_REVIEW.md), [API_CONTRACT.md](API_CONTRACT.md), [EVIDENCE.md](EVIDENCE.md) and updated PLAN. No Phase 2 work is authorized. The pause snapshot below is historical; its pending steps and missing-link notes no longer describe current state.

Saved 2026-11-10 (Asia/Qyzylorda). User paused because laptop battery was running out: "Ты запомни контекст текущий. Потом продолжишь". Stop work until the user resumes. **Phase 1 is incomplete; no implementation phase is authorized.**

## Request and limits

Prompt 01: review original Soup PDF against all docs, critically finalize architecture/contracts, keep DESIGN genuinely one page, add concise API contract if needed, update matrix/stack/plan only for real gaps. No application code/scaffolding/migrations/Docker/Compose/UI/tests. Finish with changed files, three largest risks, fixed assumptions, needed evidence and EXACTLY ONE proposed Phase 2 scope. Explicitly state no application code/tests executed; document-inspection utilities were used. Then stop for instruction.

## Read / observed

- Read AGENTS.md and ALL seven original docs in required order: BRIEF, DESIGN, STACK_GUIDE, TEST_MATRIX, PLAN, EVIDENCE, AI_USAGE.
- Read local PDF skill at `C:/Users/madi/.codex/plugins/cache/openai-primary-runtime/pdf/26.1105.12137/skills/pdf/SKILL.md`; announced its use. PDF is read-only; no PDF authoring.
- Extracted entire one-page employer PDF with bundled pypdf, rendered and visually inspected it. Both reference PDF and user's Downloads attachment have SHA-256 `EFA2DDB310A11AEB89482128FFF4AA6C54D35E9B165A46C1FAAFE9FC2DB6E0B7` (identical).
- BRIEF preserves employer requirements; no correction needed. Keep original requirements/proofs, 5-7h/48h, docker compose up, <=2-page submission note + surprise/concern paragraph, raw successes AND failures, 50 runs x 10 events/s SHIP/DON'T SHIP plus first change, AI disclosure. Do not send submission email: attachment instructions are requirements to document, not authorization to send.
- Draft DESIGN had no fundamental contradiction, but omitted precise canonical identity, bounded snapshot, cursor rules, rotation/write races, backlog revocation and actual ASGI-send timeout. Snapshot originally implied entire history in one response; current revision proposes bounded current-value summary and raw DB replay.
- Tooling failures: `git status --short` reported **not a git repository**. First pypdf stdout attempt hit cp1251 UnicodeEncodeError; rerun with `-X utf8` succeeded. First apply_patch failed validation because Delete/Add targeted same DESIGN path; no mutation from failed patch; corrected Update/Add patch succeeded. Do not hide these failures or turn them into test failures/successes.
- No application code, tests, migrations, Compose or performance/security verification executed. No test-output artifacts generated. Only read-only document tooling and Markdown edits.

## Files changed so far (NOT final-reviewed)

1. `docs/DESIGN.md`: revised compact architecture, links to API_CONTRACT.md and **not-yet-created PHASE1_REVIEW.md**. Must resolve link and validate genuine one-page length/layout without creating deliverable PDF unless appropriate. It may still be too long; count/check and shorten.
2. `docs/API_CONTRACT.md`: newly written detailed contract, needs consistency review/possibly shortening. It is a design specification, not implemented or tested behavior.
3. This `docs/PHASE1_HANDOFF.md`: pause context only.

No other files edited yet; original docs/PLAN.md still says Phase 1 NEXT, correctly not completed.

## Current design decisions (review before accepting)

- Locked selected stack unchanged: Python 3.12/FastAPI/Pydantic v2/SQLAlchemy 2.x async/asyncpg/Alembic/Postgres, Next.js App Router/TypeScript, SSE, pytest/httpx/Playwright/Compose. No second Next API, broker or private cache.
- Per-mutation explicit READ COMMITTED AsyncSession transaction INCLUDING auth; project FOR SHARE then key revalidation, scoped run FOR UPDATE/fresh state; rotation project FOR UPDATE and revalidate after lock. Shared project locks permit writers to different runs; no shared AsyncSession across tasks.
- Canonical event array normalized UUID/name/integer step/binary64 big-endian hex/UTC six-fraction timestamp; batch array order significant (determines new seq). Same batch returns exact original receipt; changed batch/event conflicts roll back. Cross-batch same event reuses seq. Stored canonical bytes/digest/receipt, committed run counter, no SERIAL cursor. Unknown commit acknowledgement resolved by identical retry.
- Proposed bounds: 256KiB body, 250 events/batch/page, 128 distinct metric names/run; integer step/seq safe JS integer ceiling; finite binary64 <=1e308; reject nonzero underflow; timestamps UTC 2000 inclusive..2100 exclusive; ASCII bounded names/metrics; strict/duplicate JSON key rules. These are applicant assumptions, NOT employer requirements.
- Snapshot read-only REPEATABLE READ, bounded current-value winners + count/H; greatest (step,seq) wins, no timestamp recency. UI summary values/count/cursor; raw history remains append-only DB/replay from 0. Applied snapshot/H atomic; contiguous stream application, count increments even when late value does not win.
- Direct browser API fetch with bearer/no-store/credentials omit; public localhost API origin only in NEXT_PUBLIC_API_BASE_URL; CORS exact origin/headers including Last-Event-ID; keys only ephemeral memory, abort/reset on key/run change. Bounded UTF-8/SSE parser, no native EventSource.
- SSE durable DB pages; caught_up marker without id controls live status; last-applied seq only; malformed/gap never advance; cursor ahead409; absent0. 250ms idle polls, 10s heartbeat, 25s client inactivity, 0.5..10s jitter backoff, stop401/403/auth_expired.
- Independent key watchdog 1s cadence +1s query deadline, fail closed, target new-send stop within2s rotation under responsive scheduling; 5s actual ASGI send deadline, cancellation/cleanup, no queue or long session. **Need clarify fixed monotonic watchdog ticks** (sleeping1s after a1s query could make bound3s). Already-buffered bytes cannot be recalled; no hard network-delivery revocation bound. Need transport-level tests; generator-only timeout insufficient.
- Local unauthenticated project bootstrap/no user accounts; one active key/project; high-entropy32-byte token SHA256 hash. Rotation response lost => new plaintext unrecoverable; local operator recovery/new project; explicitly disclose, no silently stored recovery secret. Creation/rotation not ingestion-style retry-safe.

## Remaining work when user resumes (Phase 1 only)

1. Re-read current DESIGN/API_CONTRACT and tighten inconsistencies. Explicit SSE poll `seq<=H`/consistent view; fixed watchdog cadence; define error messages exactly (currently says each code has fixed message but no exact message strings). Consider per-process concurrent-stream admission limit/transport buffer cap vs candid unresolved total-connection risk, avoid extra infrastructure. Do not present proposed bounds as measured guarantees.
2. Create concise `docs/PHASE1_REVIEW.md`: employer comparison, attack/fix table, fixed assumptions, largest risks and evidence still required, official-source rationale. Distinguish original one-page design from separate contract/review and final <=2-page submission note.
3. Update TEST_MATRIX only actual gaps: canonical equivalence/reordering, concurrent identical/conflicting batches/events, equal-step values, snapshot torn view/gap, crash/restart and lost commit response, parser split/malformed/apply-cursor ordering, key-change cancellation/CORS/no-storage, revocation under backlog and stalled send, mid-flush/commit rollback, bounds/errors/side channels. All NOT RUN.
4. Update STACK_GUIDE for explicit transaction/auth lock order, snapshot summary and actual ASGI timeout/watchdog/CORS boundaries; avoid contradicting contract.
5. PLAN: mark Phase1 complete only after static review finished; preserve later phases. Exactly ONE proposed Phase2 scope: FastAPI/Postgres/Alembic/Compose foundation, project/key lifecycle, run create/list and tenant-aware auth with PostgreSQL pytest integration evidence; no ingestion/SSE/frontend. Clarify runnable web+API+DB milestone belongs once frontend exists (Phase4), no fake frontend scaffold in Phase2.
6. Append truthful Phase1 entries to EVIDENCE and AI_USAGE, keeping existing contents/failures. Human acceptance/verification still NOT RECORDED. No performance/security proof; all tests NOT RUN. Original EVIDENCE asks exact commands, environment/raw output for real commands; record document-only commands/failures faithfully, do not fabricate missing raw artifacts. Current full outputs exist in chat tool history.
7. Static verification: re-read all edited docs, check links/contract consistency/one-page size, ensure only Markdown changed. No git diff available unless repository state changes. No code/tests. Final concise response per original required fields, exactly one proposed next phase. Stop.

## Tool/runtime context

- Workspace: `C:/AGp/SoupTask`; PowerShell; full filesystem permissions, approval never. Use apply_patch for Markdown, rg for search. Do not spawn subagents (no request).
- Bundled Python: `C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe`; system python is3.10 (not chosen app3.12). Node/runtime discoverable via load_workspace_dependencies.
- PDF render outside repo: `C:/Users/madi/AppData/Local/Temp/soup-phase1-review/employer.png` (visually reviewed).
- Successful read command used bundled Python `-X utf8 -c` with pypdf PdfReader/extract_text for all pages, then Get-Content for all seven docs. Get-FileHash verified identical PDFs. `pdftoppm -scale-to 1800 -singlefile -png` rendered source to temp; no output PDF authored.
- Official sources read through web (primary docs only): PostgreSQL current transaction isolation/explicit locking, SQLAlchemy2.0 asyncio/session basics, FastAPI CORS, MDN SSE. Starlette old www.starlette.io/responses fetch502; starlette.dev/responses search result available. No software version pins selected in design phase.
- URLs for review citations: https://www.postgresql.org/docs/current/transaction-iso.html ; https://www.postgresql.org/docs/current/explicit-locking.html ; https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html ; https://docs.sqlalchemy.org/en/20/orm/session_basics.html ; https://fastapi.tiangolo.com/tutorial/cors/ ; https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events . They support design rationale, not proof of our implementation.
