# Reproduce verification

Run from the repository root unless a command changes directory. Use a local disposable demo environment: fault tests restart API/PostgreSQL and create test records. Run suites sequentially against one stack. Never point integration tests at valuable databases; fixtures require the database name to end `_test` and truncate its tables. Compose initializes `soup_test` separately from the persistent demo database `soup`.

## Docker-only startup, backend and migrations

```sh
docker compose up --build -d --wait
docker compose ps
docker compose run --rm api pytest -q -s
docker compose exec -T api alembic current
docker compose exec -T api alembic check
```

The API image contains pinned application and pytest/httpx dependencies; Alembic owns the schema. Expected migration revision is0001(head); `alembic check` should find no new upgrade operations. This suite uses real PostgreSQL, ASGI/HTTPX checks and actual Uvicorn/TCP fault fixtures, not SQLite. Successful startup alone does not verify ordering or security.

## Client tests, TypeScript and production build

Host Node.js22.20+ and npm are needed for these commands (Docker uses22.23.4). `package-lock.json` pins the dependency tree.

```sh
cd frontend
npm ci
npm test
npm run typecheck
npm run build
cd ..
```

On Windows use `npm.cmd` if PowerShell execution policy blocks npm.ps1. Next.js build may rewrite its generated `next-env.d.ts` or create ignored `.next`/tsbuildinfo files; do not commit runtime caches.

## Real browser E2E and live HTTP/SQL smoke

Use Python3.12. From Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-e2e.txt -c backend/constraints.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -u -m pytest e2e -q -s
.\.venv\Scripts\python.exe backend/tests/smoke_http.py --restart-api
```

Linux/macOS equivalents:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-e2e.txt -c backend/constraints.txt
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python -u -m pytest e2e -q -s
.venv/bin/python backend/tests/smoke_http.py --restart-api
```

The platform equivalents are documented; the final recorded host execution is Windows/Chromium, not an executed macOS portability claim. Linux backend runs in Docker. E2E drives the actual Next.js page, real API and independent asyncpg SQL comparisons. It creates isolated projects in `soup`, tests real service restarts/outage and restores services in cleanup; it does not truncate demo data. TCP relays alter authentic stream delivery for partial-frame/session-race cases, not response data or the SQL oracle. Browser traces/HAR containing credentials are not recorded. Screenshots show the actual UI.

Default origins/ports: web http://localhost:3000, API http://127.0.0.1:8000, PostgreSQL127.0.0.1:54329. E2E accepts `WEB_BASE_URL`, `API_BASE_URL`, `DATABASE_URL`; backend accepts `TEST_DATABASE_URL`. Pass overrides via environment, never project keys in URLs. When using another Compose project for isolation, export `COMPOSE_PROJECT_NAME` for both startup and fault/smoke commands so their service restarts target that project.

## Preserve actual command output

PowerShell capture pattern (choose a new filename on every attempt):

```powershell
.\.venv\Scripts\python.exe -u -m pytest e2e -q -s 2>&1 | Tee-Object artifacts/test-output/my-browser-run.log
$testExit = $LASTEXITCODE
Add-Content artifacts/test-output/my-browser-run.log "EXIT_CODE=$testExit"
# In a script/CI step: exit $testExit
```

Do not overwrite failures with later successes. `docs/EVIDENCE.md` links raw logs and distinguishes stdout/stderr from derived JSON analyses. Two missing Phase2 compile/config captures are acknowledged there; rerunning commands now cannot recreate historical output.

## Optional load reproduction

No load rerun is required for final functional verification; existing Phase5 captures remain valid because application behavior is unchanged. With the same Python dependencies and Docker CLI:

```powershell
.\.venv\Scripts\python.exe -u scripts/load_test.py --output artifacts/test-output/new-baseline
.\.venv\Scripts\python.exe -u scripts/load_test.py --subscribers 50 --output artifacts/test-output/new-sse
.\.venv\Scripts\python.exe scripts/analyze_load.py artifacts/test-output/new-baseline artifacts/test-output/new-sse
```

Each output directory must be new. Defaults:50 runs,10 unique events/s/run, batch5,10s warm-up +60s measurement,300 identical retries. Unique events/s differs from HTTP requests/s; successful retry receipts retain their original inserted_count and are not counted as new writes. `LOAD_DATABASE_URL` overrides the direct audit connection without putting credentials on the CLI. Config/source/manifest/raw timings/resource samples and derived SQL audits are retained for failed and successful attempts.

## Document artifacts

The runtime application does not need PDF libraries. To rebuild the submission PDFs separately, install `reportlab==4.4.9` and `pypdf==6.21.4` in a documentation environment, then run `python scripts/build_submission_pdfs.py`. The command enforces <=2 pages for the note and1 for the architecture. Inspect rendered pages after content changes; text extraction is not visual verification.
