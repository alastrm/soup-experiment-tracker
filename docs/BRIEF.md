# Employer brief — source-grounded checklist

**Authoritative attachment:** `reference/Soup-Full-Stack-Take-Home.pdf` (1 page). This document is a working paraphrase; the PDF takes precedence.

**Follow-up:** the employer's email supplied by the applicant cancels the live discussion; technical deliverables and48-hour deadline remain. See [FOLLOW_UP.md](FOLLOW_UP.md). The submission must explain itself without an interview. Employment terms are informational. PDF scoring below is historical; no revised scoring was provided.

**Task:** mini experiment tracker. Demonstrate (1) whether the UI matches persisted data, and (2) whether users see only their own project's data.

**Constraints from Soup:** estimated work 5–7 h; deadline 48 h; any stack; service must start using `docker compose up`.

## Features explicitly required
- Projects and API keys.
- Batch metric ingestion at `POST /runs/{id}/metrics` over an unreliable client network.
- Storage, run list, and live-updating run web page (SSE or WebSocket).

## Required proofs and explanations
- **Before code:** one page covering event format and ordering, same-batch retry, catching up after reconnect, and project isolation.
- **Consistency:** automated E2E that exercises UI + API with out-of-order, duplicated and late metrics, interrupted stream and recovery; compare final UI with DB. Preserve output and describe what this test **does not** detect.
- **Isolation:** automated negative tests for cross-project read, write, stream subscription, ID guessing and cache effects. Discuss possible disclosure through logs, errors and timing.
- **Silent failures:** explicitly check dropped replay events, duplicates, slow-client queue overflow, partial writes and old API keys accepted after rotation.
- **Verdict:** SHIP or DON'T SHIP for 50 concurrent runs at 10 events/second each (aggregate 500 events/second); say what to change first. A test-derived verdict, not an assumption.

## Submission
- Repository and Docker Compose setup.
- Tests and raw unedited output (include failures).
- A note of **no more than 2 pages**.
- One paragraph about what surprised the author and what remains concerning.
- Reply to `team@trysoup.dev`.
- Explain AI usage: what was generated/suggested, what was accepted, and what was independently verified, changed or redone.
- Prepare for a **40-minute live technical discussion**, not a memorized script.

## Scoring (from Soup)
- Consistency and isolation: **30%**.
- Silent failures: **20%**.
- Architecture and code quality: **15%**.
- Live discussion: **35%**.

## Not specified by Soup (our design choices, NOT requirements)
- Programming languages, framework, database, schema, authentication UI, API shape beyond the ingest route, specific throughput latency SLO, retention window, deployment topology and plotting library.
- Product-user accounts and roles are not requested; project-scoped API keys are an intentionally narrow auth model for this exercise.
