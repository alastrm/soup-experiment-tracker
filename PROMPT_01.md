# Prompt 01 — FastAPI + Next.js design review ONLY

Read `AGENTS.md`, `reference/Soup-Full-Stack-Take-Home.pdf`, and ALL current `docs/*.md` before editing anything.

This is Soup's Full-Stack Engineer take-home. Use the selected architecture: **Python 3.12 + FastAPI + Pydantic v2 + async SQLAlchemy/asyncpg + Alembic + PostgreSQL**, **Next.js App Router + TypeScript**, **SSE**, **pytest**, **Playwright**, **Docker Compose**. Soup allows any stack; this is our deliberate choice.

**Do Phase 1 ONLY — challenge and finalize design. Do NOT create implementation code, project scaffolding, migrations, Dockerfiles, Docker Compose, frontend components, API handlers or tests.**

Tasks:
1. Compare the original Soup PDF to `docs/BRIEF.md` and `docs/DESIGN.md`. Report omissions, contradictions and unsupported assumptions; preserve the employer's intended proofs and deliverables.
2. Critically attack the design: per-run committed `seq` under concurrent FastAPI requests/SQLAlchemy transactions; identical vs conflicting retries; canonical batch/event identity; late/out-of-order step semantics; consistent snapshot-to-SSE handoff; `Last-Event-ID` and client cursor advancement; durable replay after process restart; project A/B authorization for read/write/list/SSE; old API key on an already-open stream; slow-reader bounds and partial rollback.
3. Specifically review the **FastAPI ↔ Next.js** boundary: no second API in Next.js, no secrets in `NEXT_PUBLIC_*`, no API keys in URLs, browser-reachable API origin/CORS, private response caching, `fetch` streaming with bearer Authorization instead of native `EventSource`, cancellation and reconnection behavior.
4. Revise `docs/DESIGN.md` minimally while keeping it genuinely one page. Define a compact consistent API contract covering project creation, key rotation, run creation/list/detail, batch metrics, stream subscription and stable error semantics. If full endpoint details won't fit one page, create a concise `docs/API_CONTRACT.md`.
5. Make only necessary updates to `docs/TEST_MATRIX.md`, `docs/STACK_GUIDE.md` or `docs/PLAN.md` when an actual gap is found. Note what still cannot be proven without running software.

At the end provide: (a) changed files, (b) three largest remaining technical risks, (c) assumptions you fixed, (d) evidence needed during implementation, and (e) EXACTLY ONE proposed Phase 2 scope. State explicitly that no code/tests were executed in Phase 1.

No code. No fake test evidence. No claims of proven performance or security. STOP after Phase 1 and wait for the next user instruction.
