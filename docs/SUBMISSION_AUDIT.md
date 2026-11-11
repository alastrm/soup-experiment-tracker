# Final requirement audit

Sources: original [one-page Soup PDF](../reference/Soup-Full-Stack-Take-Home.pdf), [follow-up supplied by the applicant](FOLLOW_UP.md), current code and executed [evidence](EVIDENCE.md). VERIFIED means the named local experiment/artifact is supported; it never means every schedule, client or deployment is safe. A design assertion alone does not qualify. The follow-up cancels the interview and leaves technical deliverables unchanged.

| Requirement | Classification | Implementation / actual evidence and boundary |
| --- | --- | --- |
| Projects, API keys and persistent storage | VERIFIED | FastAPI project/key services, hashed high-entropy tokens, PostgreSQL/Alembic; backend project/auth tests and real HTTP/SQL smoke |
| Batch POST /runs/{id}/metrics | VERIFIED | Strict Pydantic bounds and canonical identity; real endpoint ingestion and negative validation checks; no ML training needed |
| Run list and live run web page | VERIFIED | Actual Next.js App Router pages; browser demo and SQL/chart comparison, not a mocked frontend |
| One-page design before implementation | VERIFIED | Phase1 design-only record/layout calculation and then accepted implementation phases; docs/DESIGN.md and one-page architecture PDF. No claim that prose alone proves runtime correctness |
| Exact/conflicting batch retries; cross-batch event identity | VERIFIED | test_batch_and_event_idempotency_conflicts_and_order, concurrent exact/conflicting tests; Phase5 repeated300 batches/workload returned original receipts with no extra DB rows |
| Deterministic ordering and late/equal-step values | VERIFIED | PostgreSQL run row lock, atomic gapless counter; two independent API processes; browser/independent SQL point and winner comparison |
| Snapshot/replay handoff and reconnect, including duplicates | VERIFIED | Real TCP snapshot/page-gap tests; actual browser1-10/disconnect/11-30, duplicate10 and snapshot20->80; full recovered points compared with SQL |
| Partial frames and API/DB restart recovery | VERIFIED | Authentic TCP frame11 cut before completion leaves applied10; real API and PostgreSQL service restart browser tests; durable DB history remains authoritative |
| Negative A/B read/write/list/guessed-ID/SSE tests | VERIFIED | Scoped REST/SSE tests deny known foreign/random UUIDs identically; independent unchanged DB checks. UUID knowledge is never authorization |
| Browser state/cache/project switching | VERIFIED | Held A frame released after switch to B cannot alter B UI; no-store headers, empty key storage/cookies and SSR checks. External caches/proxies were not deployed |
| Rotation affects old keys and active streams | VERIFIED | Idle/backlog/blocked-send/blocked-replay watchdog tests, real browser live rotation, concurrent rotation/write revalidation. Already-buffered bytes and hard real-time bounds excluded |
| Partial writes, rollback and uncertain client result | VERIFIED | Kill real PG backend after INSERT, actual deferred COMMIT failure, cancellation rollback, committed response loss followed by identical retry; events/counter/receipt checked independently |
| Literal PostgreSQL COMMIT-ACK packet loss | NOT VERIFIED | Exact PG protocol boundary not injected; definite rollback and committed-but-no-HTTP-receipt cases are covered. No storage/power-loss proof |
| Slow-client bounds/overflow and recovery | PARTIALLY VERIFIED | One constrained unread TCP client,5s send deadline, buffer/RSS observation and complete replay; cap overflow/reuse tested at2, default100 asserted. No100-stalled-client/long-soak aggregate memory proof |
| Logs, generic errors and timing leakage discussion | PARTIALLY VERIFIED | Credential scans, generic matching404s and local timing probes executed; constant time, operator-log metadata and all side channels remain unproven |
| Automated browser/UI/API/DB consistency proof and blind spots | VERIFIED | Real Chromium tests independently compare every retained point/event/count/cursor/winner for selected faults; parser tests are additional, not a substitute. Limits documented below |
| Measured50 runs x10 events/s workload and a verdict | PARTIALLY VERIFIED | Configured500 unique events/s, batch5, warmup10s + measurement60s; measured498.92 baseline/498.17 with50 SSE; all35,000 planned events stored per workload. Scoped SHIP uses self-defined1% tolerance, not Soup's threshold |
| Exact sustained>=500 events/s / production capacity | NOT VERIFIED | Neither measured window achieved500; no long soak, capacity ceiling, WAN/proxy or production headroom proof |
| Reproducible repository-root Compose startup, image builds and migrations | VERIFIED | Phase5 startup/migrations healthy; final clean-clone verification is separately recorded below when executed |
| Tests and raw success/failure output included | PARTIALLY VERIFIED | Existing failed/successful captures retained, exact commands/exit codes indexed. Two Phase2 raw files are missing: phase2-compile.log and phase2-compose-config.log. They are not reconstructed or counted as present |
| Complete English submission note <=2 pages, including architecture/verdict/limits/reflection/AI | VERIFIED | SUBMISSION_NOTE.md and rendered output/pdf/Soup-Submission-Note.pdf:2 physical pages; architecture PDF:1. Page counts and visual inspection cover all pages; final artifacts are explicitly qualified |
| Honest surprise/concern paragraph | VERIFIED | Applicant supplied the generator surprise and long-term slow-SSE concern in chat; note edits that statement without inventing personal test execution |
| Concrete AI disclosure including human checks | VERIFIED | AI_USAGE.md and note distinguish AI architecture/code/tests/debugging/docs from applicant stack/scope decisions and reflection. Independent human code review/test execution is NOT RECORDED |
| Employer follow-up incorporated; no live interview | VERIFIED | Applicant supplied complete email text; cancelled discussion removed from current handoff obligations. Email headers/timezone not independently retrieved |
| Reply within48 hours with accessible repository/artifacts | NOT VERIFIED | No email sent or repository published by Codex. Applicant must verify Gmail timezone/deadline, repository access, URL and attachments, then reply to original thread |

Employment conditions (around4 hours/day, first month unpaid, possible but unguaranteed paid role) are informational, not additional technical features. The original PDF's interview/scoring text is historical; no replacement scoring was supplied.

## Current verdict and remaining risks

**SHIP for the measured local profile with a self-defined1% throughput tolerance.** Exact500 events/s was not achieved; production capacity is unproven. The first confirmed throughput bottleneck was the generator's shared HTTPX pool, corrected without an application change. Server observations show API CPU/pool pressure with50 responsive streams, not a proven saturation point. First production improvement: instrument transaction/pool-wait latency and CPU, then profile existing SSE polling before altering concurrency.

Additional limits: last2,000-event browser chart window/full-history bootstrap cost; unbounded persisted retention; local unauthenticated bootstrap/lost rotation-response recovery;100 slow subscribers and aggregate socket memory; multi-worker quotas; exhaustive async/parser schedules; other browsers; external caches/TLS/WAN; disk/power/replica/backup durability. Sampled memory and generic errors do not prove universal safety. Demo metrics are generated examples, not training results. Existing Phase5 raw captures remain unchanged; no final load rerun is planned.

## Final checkout and artifact verification

NOT RUN at initial preparation. Final commands, actual outcomes and Git state will be appended to EVIDENCE.md and summarized here after execution. The applicant's publish/send actions remain separate; no new development phase is authorized.
