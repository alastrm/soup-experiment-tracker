# Soup experiment tracker

Mini experiment tracker: FastAPI/Pydantic v2, async SQLAlchemy/asyncpg, Alembic, PostgreSQL and Next.js App Router/TypeScript/Tailwind. The dark run list/detail UI displays persisted metrics with authenticated, recoverable SSE.

Start with the [two-page submission note](output/pdf/Soup-Submission-Note.pdf), [requirement audit and limitations](docs/SUBMISSION_AUDIT.md), [one-page architecture](output/pdf/Soup-Architecture.pdf), [test instructions](docs/TESTING.md) and [AI disclosure](docs/AI_USAGE.md). The employer's [follow-up](docs/FOLLOW_UP.md) cancels the live discussion; technical deliverables remain unchanged.

## Run

Prerequisites: Git and Docker Engine/Desktop with Linux containers and Docker Compose v2, free local ports3000/8000/54329, and network access to pull images/packages on the first build. Host Python/Node are only needed for optional host tests. From the cloned repository root:

```sh
docker compose up
```

Open **http://localhost:3000**. Enter a project API key (or create one in the access form), create/select a run, then ingest metrics via FastAPI. API: `http://localhost:8000`; health: `http://localhost:8000/health`. Startup waits for PostgreSQL and applies Alembic migrations. Data persists in the Compose volume. Local-only ports: web3000, API8000, PostgreSQL54329. Override using `.env.example`; never place project API keys in `.env`. `NEXT_PUBLIC_API_BASE_URL` is a public browser-reachable URL only; changing the web origin also requires updating API CORS_ORIGINS in Compose.

For a detached rebuild/health wait use `docker compose up --build -d --wait`; inspect with `docker compose ps` and stop with `docker compose stop`. `docker compose down -v` destroys the database volume; it is not a restart/recovery command.

## Browser demo - about two minutes

1. Open http://localhost:3000 and enter an optional project label.
2. Click **Create project & key**. Copy the displayed one-time key somewhere safe for this local demo, then click **Connect project** (the key field is already filled). Do not include the key in screenshots, issue reports or logs.
3. Enter a **New run name**, click **Create run**, then open its run link.
4. Wait for **connected**, then click **Send demo metrics** on the empty run. Expect40 committed events and live demo.loss/demo.accuracy charts without refreshing.
5. **Disconnect** pauses the fetch stream; **Reconnect** replays after the applied cursor. Reloading clears the in-memory key: enter the saved key again to see persisted data. **Switch project / key** clears the private session.

These are explicitly generated demo samples stored through the real API, not training output. There is no pre-shared project credential or hidden seed data. The browser's network requests go directly to FastAPI with a bearer header; Next.js contains no second business API.

## API example

Create a project using `POST /projects`, JSON `{"name":"demo"}`. Its response returns the only plaintext copy of its key. Use `Authorization: Bearer <key>` for:

- `POST /runs` with `{"name":"experiment"}`.
- `GET /runs` (optional `limit`/`after`) and `GET /runs/{id}` (consistent snapshot/count/cursor).
- `POST /runs/{id}/metrics` with the batch below. Identical retries return the original receipt; changed contents return 409 without writes. Event IDs also deduplicate across batches.
- `POST /projects/key/rotate` with `{}`. Old key stops working; keep the new key from that response. Lost rotation response has no automatic recovery in this local demo.

```json
{
  "batch_id": "be8315a0-8dcc-44f1-85ba-35797778d5e3",
  "events": [{
    "event_id": "080110ba-9577-4d8b-8552-6474b88895ae",
    "metric": "loss", "step": 1, "value": 0.5,
    "occurred_at": "2026-01-01T00:00:00Z"
  }]
}
```

Generate fresh UUIDv4 IDs for new data; retain them for retries. [API_CONTRACT.md](docs/API_CONTRACT.md) specifies exact bounds, identity and errors. Snapshot winners use greatest `(step,seq)`; seq is commit order, not logical step. Tenant scope derives only from the bearer key. Bootstrap is local and unauthenticated; this is not production account management.

Runnable PowerShell example, from the repository root with services running. It creates an isolated project/run, keeps its key in memory and prints only the receipt/snapshot. Use the browser workflow above for the interactive demo; this separate project's API key is not printed or persisted.

```powershell
$apiBase = 'http://localhost:8000'
$demoProject = Invoke-RestMethod -Method Post -Uri "$apiBase/projects" -ContentType 'application/json' -Body '{"name":"API demo"}'
$demoAuth = @{ Authorization = "Bearer $($demoProject.api_key)" }
$demoRun = Invoke-RestMethod -Method Post -Uri "$apiBase/runs" -Headers $demoAuth -ContentType 'application/json' -Body '{"name":"Example run"}'
$demoBatch = @{
    batch_id = [guid]::NewGuid().ToString()
    events = @(@{
        event_id = [guid]::NewGuid().ToString()
        metric = 'loss'; step = 1; value = 0.5
        occurred_at = '2026-01-01T00:00:00Z'
    })
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri "$apiBase/runs/$($demoRun.id)/metrics" -Headers $demoAuth -ContentType 'application/json' -Body $demoBatch
# Identical retry: same receipt, no extra events.
Invoke-RestMethod -Method Post -Uri "$apiBase/runs/$($demoRun.id)/metrics" -Headers $demoAuth -ContentType 'application/json' -Body $demoBatch
Invoke-RestMethod -Uri "$apiBase/runs/$($demoRun.id)" -Headers $demoAuth
Remove-Variable demoProject,demoAuth
```

## Verify

Run suites sequentially: browser fault tests intentionally restart API/PostgreSQL. Full prerequisites, Linux/macOS/Windows instructions, failure boundaries and raw-output capture are in [TESTING.md](docs/TESTING.md). Production build: `npm run build` from frontend after `npm ci`.

```sh
docker compose run --rm api pytest -q
docker compose exec -T api alembic current
docker compose exec -T api alembic check
```

Tests migrate and truncate the separate `soup_test` database initialized by Compose. Fixtures refuse database names not ending `_test`; do not point them at valuable data or run competing suites against one test database. No SQLite fallback.

Optional host workflow (Windows PowerShell, Python 3.12):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt -c backend/constraints.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe backend/tests/smoke_http.py --restart-api
```

Live smoke sends real HTTP requests, restarts the API, retries a batch and checks PostgreSQL independently. It creates demo records, keeps keys only in memory and prints no tokens. It expects default local ports/credentials; override `API_BASE_URL` and `DATABASE_URL` as needed. Pytest accepts `TEST_DATABASE_URL`.

For direct API startup, set `DATABASE_URL` then, from `backend` in the installed environment, run `alembic upgrade head` and `uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log`.

Browser verification (Windows host, full Compose stack running):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-e2e.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest e2e -q -s
```

Client parser/reducer tests and type checks: from `frontend`, run `npm ci`, `npm test`, `npm run typecheck`. Browser E2E creates isolated demo projects in the main demo DB and restarts API during a recovery scenario; run suites sequentially. It does not truncate demo data. Screenshots live in `artifacts/screenshots/`.

Authenticated streaming uses browser `fetch`/ReadableStream, never native EventSource. Initial replay reconstructs charts (last2,000 committed events); reconnect keeps points and sends last applied cursor. Latest values include all history. Keys are ephemeral, cleared on switch/reload, never persisted or sent to Next.js. All business endpoints remain FastAPI-only.

Measured local load test (same host dependencies, full Compose stack running; creates isolated projects and retains their data):

```powershell
.\.venv\Scripts\python.exe -u scripts/load_test.py --output artifacts/test-output/my-baseline
.\.venv\Scripts\python.exe -u scripts/load_test.py --subscribers 50 --output artifacts/test-output/my-sse
.\.venv\Scripts\python.exe scripts/analyze_load.py artifacts/test-output/my-baseline artifacts/test-output/my-sse
```

Output directories must be new. Defaults:50 runs x10 unique metric events/s, batch5,10s warmup +60s measurement, controlled exact retries. Authenticated HTTP and optional SSE use real endpoints; asyncpg audits every event/receipt/sequence and compares API snapshots independently. `LOAD_DATABASE_URL` overrides the loopback PostgreSQL connection (pass credentials through the environment, never CLI). Run benchmarks and fault suites sequentially. `summary.json` and `analysis.json` are derived measurements; `requests.jsonl`, `resources.jsonl`, `sse.jsonl` and console captures preserve observations. Each attempt freezes generator source/config; failed attempts remain intact.

## Measured verdict and evidence

**SHIP for the tested local profile under a self-defined1% tolerance.** The fixed60s windows achieved **498.92 events/s without SSE** and **498.17 with50 SSE subscribers**. Exact500 events/s was not achieved; Soup did not specify the tolerance. Each workload stored all35,000 planned events without HTTP failures or lost acknowledged events. This is not proof of production capacity, prolonged slow-client safety or an indefinite throughput floor.

Successful and failed captures remain under [artifacts/test-output](artifacts/test-output/); `summary.json`/`analysis.json` are derived, not raw test output. Two historical Phase2 files (`phase2-compile.log`, `phase2-compose-config.log`) are absent, explicitly unverified and not reconstructed. [EVIDENCE.md](docs/EVIDENCE.md) records commands/exit codes, failures, scoped results and limitations; [TEST_MATRIX.md](docs/TEST_MATRIX.md) maps scenarios. No expensive load rerun is needed to reproduce the final functional verification.

The [email reply draft](docs/EMAIL_DRAFT.md) is unsent and contains an explicit repository URL placeholder. Publication and sending are the applicant's final actions. The [original assignment](reference/Soup-Full-Stack-Take-Home.pdf) and [follow-up](docs/FOLLOW_UP.md) are included.
