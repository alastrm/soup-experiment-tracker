# Sequential implementation plan

**Rule:** the next prompt authorizes exactly one phase. Later phases are a roadmap, not a request to implement everything now. Update status with observed evidence, never assumption.

| Phase | Deliverable | Status |
| --- | --- | --- |
| 1. Design review | Challenge/finalize the 1-page design, freeze minimal endpoint contracts and assumptions | COMPLETE - static review only; software checks NOT RUN |
| 2. Working FastAPI backend | Expanded by user: PostgreSQL/Alembic/Compose, project/key lifecycle, run create/list/detail, ingestion, sequencing/idempotency/isolation, PostgreSQL pytest/httpx evidence | COMPLETE - 36 tests pass on host/container; live HTTP + API restart/SQL smoke passes |
| 3. Durable SSE + Next.js (user-authorized scope) | Authenticated replay/revocation, dark run list/detail/charts, focused PostgreSQL/Chromium proofs | COMPLETE - see Phase 3 evidence; no load/final report |
| 4. Adversarial reliability/security | PostgreSQL/transport faults, mid-frame browser recovery, isolation/log/timing probes; confirmed fixes only | COMPLETE - Linux58; Windows56+2 targeted; browser9; client5. See evidence/remaining limits |
| 5. Evaluation | Measured 50 x10/s load and evidence-based SHIP/DON'T SHIP verdict | COMPLETE - 498.92 events/s baseline; 498.17 with50 SSE; all35,000 aggregate events per workload audited; scoped SHIP with declared1% tolerance. Regression58/9/5 pass; see EVIDENCE |
| 6. Final delivery | <=2-page note, surprise/concern paragraph, AI disclosure and reproducible handoff | IN PROGRESS - note/audit/test instructions prepared; clean-clone/final verification pending |

User prompts override the original roadmap: ingestion in Phase2, SSE/frontend in Phase3, adversarial verification in Phase4, measured evaluation in Phase5 and final submission preparation in Phase6. The employer cancelled the live discussion. No feature expansion, push or email sending; stop after final preparation.

## Time/scope trade-off
Soup suggests 5–7 h of work, so prioritize actual negative tests and transparent evidence above polish. Keep the UI functional but minimal. Avoid implementing "nice-to-have" auth accounts, dashboards, charts or observability infrastructure unless a requirement or test justifies them.

## Definition of done, per phase
- No unexplained change to previously agreed invariants.
- Commands actually executed and outputs recorded, or explicitly NOT RUN.
- Regression risks and the next single concrete task stated.
- A phase cannot be marked complete because code looks plausible.
