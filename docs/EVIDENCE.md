# Execution evidence — append-only verification log

No implementation or tests have been run as part of this starter context package. **All test cases: NOT RUN.** A static review of the employer PDF is not an integration test.

For each real command, append an entry; never rewrite or remove a failure when retrying:

## TEMPLATE — replace only when an actual run occurs
- Timestamp (with zone): NOT RUN
- Phase / test ID: NOT RUN
- Environment (OS, Python, FastAPI, Node, Next.js, Docker, DB versions): NOT RECORDED
- Exact command: NOT RUN
- Exit code: NOT RUN
- Raw output file: NOT CREATED
- Result / observed counts: NOT MEASURED
- Interpretation / uncovered weakness: PENDING

## Raw output location (future)
Use `artifacts/test-output/` for unedited logs, or another clearly identified reproducible file. Do not create fabricated logs.

## Phase 1 - static review, including pause/resume

- Date context: review started 2026-11-10, Asia/Qyzylorda; user paused for battery and subsequently resumed. No application code or tests were executed in Phase 1. Python/PowerShell/Poppler were used only for document extraction, layout measurement and file inspection; Markdown was edited with apply_patch.
- Environment: Windows, PowerShell; bundled document-tooling Python **3.12.14** (observed in the layout log); system `python` resolved to a Python310 path. Application FastAPI/Next.js/PostgreSQL/Docker versions: **NOT SELECTED OR RUN**. No package installation or version pinning in this phase.
- Read AGENTS.md, the full one-page reference PDF and all current docs before editing. Reference/Downloads PDFs have the same SHA-256: `EFA2DDB310A11AEB89482128FFF4AA6C54D35E9B165A46C1FAAFE9FC2DB6E0B7`. Text extraction and source-page PNG inspection succeeded after the encoding retry below.
- Primary documentation consulted: PostgreSQL isolation/locks, SQLAlchemy sessions/isolation configuration, FastAPI CORS, MDN SSE framing and Starlette responses. An initial fetch of `https://www.starlette.io/responses/` returned502; `https://starlette.dev/responses/` later loaded. These are reference reads, not application evidence.
- Changes are documentation and one genuine document-inspection log. No code, migration, Dockerfile, Compose setup, UI, API handler or test was created. `docker compose up`, pytest, httpx integration runs, Playwright and load/security checks: **NOT RUN**. SHIP/DON'T SHIP verdict: **NOT ASSESSED**.

### Commands actually run and observed outcomes

The shell commands below were run from `C:\AGp\SoupTask`. Earlier full command outputs were retained in chat tool history, **not initially captured as raw files**; no later reconstruction is claimed to be a complete raw capture. Document reads/searches were also run using `Get-Content` for each docs Markdown file (including the handoff/contract), `rg --files docs reference`, `rg --files`, and `Get-Content README.md`; they succeeded. Tool metadata discovery and apply_patch are tool calls, not software tests.

```powershell
git status --short
Get-Command python,pdftotext,pdftoppm -ErrorAction SilentlyContinue | Select-Object Name,Source
Get-FileHash 'reference\Soup-Full-Stack-Take-Home.pdf','C:\Users\madi\Downloads\Soup-Task-06-Full-Stack-Engineer(1).pdf' | Format-List Path,Hash
```

Observed Git output (verbatim):

```text
fatal: not a git repository (or any of the parent directories): .git
```

The combined shell call continued after Git failed, so its reported final exit code0 is **not a successful Git check**; the standalone Git exit code was not captured. No Git diff/change-baseline verification is available. File inventory shows only original context files, Markdown changes and the inspection log.

```powershell
& 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe' -c "from pypdf import PdfReader; p=PdfReader('reference/Soup-Full-Stack-Take-Home.pdf'); print('PAGES', len(p.pages)); [print('\nPAGE',i+1,'\n',page.extract_text()) for i,page in enumerate(p.pages)]"
```

This first extraction failed to print the PDF text using cp1251. Original error output (verbatim):

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\dependencies\python\Lib\encodings\cp1251.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode character '\u2264' in position 1610: character maps to <undefined>
PAGES 1

PAGE 1
```

This was an inspection-tool encoding failure, not a failed application test. The surrounding shell call later ran Get-FileHash and reported0; Python's standalone exit code was not separately recorded. Retry:

```powershell
& 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe' -X utf8 -c "from pypdf import PdfReader; p=PdfReader('reference/Soup-Full-Stack-Take-Home.pdf'); [print('PAGE',i+1,'\n',page.extract_text()) for i,page in enumerate(p.pages)]"
$reviewDir = Join-Path $env:TEMP 'soup-phase1-review'
New-Item -ItemType Directory -Force -Path $reviewDir | Out-Null
pdftoppm -scale-to 1800 -singlefile -png 'C:\AGp\SoupTask\reference\Soup-Full-Stack-Take-Home.pdf' (Join-Path $reviewDir 'employer')
Get-ChildItem -LiteralPath $reviewDir | Select-Object FullName,Length | Format-List
```

Observed: full PDF text printed; rendered source PNG at `C:\Users\madi\AppData\Local\Temp\soup-phase1-review\employer.png` (323084 bytes), visually inspected. Shell calls reported0. No authored PDF or screenshot of test results.

The first apply_patch request attempted Delete/Add for the same DESIGN path and failed before mutation. Tool output (verbatim):

```text
Script error:
apply_patch verification failed: invalid patch: multiple operations target C:\AGp\SoupTask\docs\DESIGN.md
```

Retried with Update for DESIGN and Add for API_CONTRACT; tool succeeded. This was an editing-tool failure, not an application test. Failures remain recorded here and in the original chat.

### One-page / links / file inventory inspection

Exact command run (document utility only):

```powershell
New-Item -ItemType Directory -Force -Path artifacts/test-output | Out-Null
& 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe' -X utf8 -c 'import sys,re,html; from pathlib import Path; from reportlab.platypus import Paragraph; from reportlab.lib.styles import ParagraphStyle; from reportlab.lib.pagesizes import A4; from reportlab.lib.units import mm; t=Path("docs/DESIGN.md").read_text(encoding="utf-8"); ps=t.strip().split("\n\n"); plain=lambda s: re.sub(r"\[([^]]+)\]\([^)]+\)",r"\1",s).replace("**","").replace("`","").lstrip("# "); body=ParagraphStyle("body",fontName="Helvetica",fontSize=11,leading=13.5); title=ParagraphStyle("title",fontName="Helvetica-Bold",fontSize=14,leading=17); width=A4[0]-36*mm; available=A4[1]-36*mm; height=sum(Paragraph(html.escape(plain(p)),title if i==0 else body).wrap(width,10000)[1] for i,p in enumerate(ps))+8*(len(ps)-1); print("DOCUMENT INSPECTION ONLY - NO APPLICATION OR TEST EXECUTION"); print("Tooling Python:",sys.version.split()[0]); print("DESIGN words:",len(t.split())); print("A4, 18mm margins, Helvetica 11pt/13.5pt; heading 14pt/17pt; paragraph gap 8pt"); print("Required height pt:",height,"Available height pt:",round(available,2),"Fits one page:",height<=available); links=[(str(p),target) for p in Path("docs").glob("*.md") for target in re.findall(r"\]\(([^)]+)\)",p.read_text(encoding="utf-8")) if not re.match(r"^[a-zA-Z]+:",target) and not (p.parent/target.split("#")[0]).exists()]; print("Missing local Markdown link targets:",links); print("Project files:"); print("\n".join(str(p) for p in sorted(Path(".").rglob("*")) if p.is_file()))' 2>&1 | Tee-Object -FilePath artifacts/test-output/phase1-document-inspection.log
```

- Reported shell exit code: **0**. Raw output: [phase1-document-inspection.log](../artifacts/test-output/phase1-document-inspection.log), captured by Tee-Object during the actual command, not synthesized later.
- Observed DESIGN: **440 words**, typeset paragraph height **599.5pt** within **739.84pt** available on A4/18mm margins, Helvetica11pt/13.5pt leading. This is a layout calculation with inline Markdown removed, not a rendered final submission PDF and not a software test.
- Missing local Markdown link targets at inspection: **[]**. Inventory contained only context/docs/source PDF; the log was being created during the pipeline and did not appear in its own initial inventory. Final reads/inventory are static inspection, not runtime verification.
- Interpretation: compact architecture fits a readable one-page layout; endpoint details live separately. This does not prove transactional correctness, tenant security, parser behavior, stream bounds or load capacity. All matrix entries remain **NOT RUN**.

Final static inspection after documentation/provenance edits (actual output appended to the same log):

```powershell
& 'C:\Program Files\WindowsApps\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\dependencies\python\python.exe' -X utf8 -c 'import re; from pathlib import Path; docs=sorted(Path("docs").glob("*.md")); missing=[(str(p),target) for p in docs for target in re.findall(r"\]\(([^)]+)\)",p.read_text(encoding="utf-8")) if not re.match(r"^[a-zA-Z]+:",target) and not (p.parent/target.split("#")[0]).exists()]; rows=[line for line in Path("docs/TEST_MATRIX.md").read_text(encoding="utf-8").splitlines() if re.match(r"\| [CIFVSP][0-9]+ \|",line)]; print("FINAL STATIC DOCUMENT INSPECTION - NOT SOFTWARE TESTS"); print("Markdown documents:",len(docs)); print("Missing local link targets:",missing); print("Planned matrix rows:",len(rows)); print("All matrix rows NOT RUN:",all(line.endswith("NOT RUN |") for line in rows)); print("File inventory:"); print("\n".join(str(p) for p in sorted(Path(".").rglob("*")) if p.is_file()))' 2>&1 | Tee-Object -FilePath artifacts/test-output/phase1-document-inspection.log -Append
Get-Content docs/EVIDENCE.md -Tail 15
Get-Content docs/PLAN.md
```

Reported shell exit0; observed 10 docs Markdown files, missing link targets [], 23 planned matrix rows all NOT RUN. Inventory contained 15 files: original instructions/prompt/README/source PDF, 10 docs and the actual inspection log. Final edited docs were also read using Get-Content (review/design/stack/plan and contract/matrix/provenance/log); no application artifact appeared. This entry records the completed inspection; app/test execution remains NONE.

## Phase 2 - working backend, 2026-11-11 (Asia/Qyzylorda)

The user accepted Phase 1 and explicitly expanded Phase 2 to include run detail and ingestion. This overrides the old foundation-only boundary. No Next.js or SSE was implemented. Historical Phase 1 statements above describe that phase, not current software status.

Environment: Windows host Python3.12.10; Docker Desktop4.55.0 / Engine29.1.3, Linux containers. Runtime Python3.12.16, PostgreSQL17.11, FastAPI0.162.4, Pydantic2.14.3, SQLAlchemy2.0.57, asyncpg0.32.0, Alembic1.20.1, Uvicorn0.54.0, pytest9.2.0, pytest-asyncio1.4.1.post1, httpx0.28.1. [Observed versions](../artifacts/test-output/phase2-runtime-versions.log); complete dependency pins in backend/constraints.txt. Direct versions were checked against PyPI metadata; image patches were checked against Docker Hub tags and actually pulled/built.

### Exact functional commands and results

Working directory `C:\AGp\SoupTask`. Output pipes used `2>&1 | Tee-Object <log>`; important commands captured `$LASTEXITCODE` immediately, appended `EXIT_CODE=<value>` and exited with that value. Logs below contain raw output; failures were not replaced by later successes.

| Command (before output pipe) | Observed outcome | Raw output |
| --- | --- | --- |
| `docker version` | Initially failed: Docker Desktop Linux engine pipe missing; started Docker Desktop hidden, subsequent version check succeeded | Initial failure in chat; [running daemon](../artifacts/test-output/phase2-docker-version.log) |
| `py -3.12 -m venv .venv` | Success; dedicated environment created | Tool history |
| `.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt` | Success; required pinned packages installed | [pip](../artifacts/test-output/phase2-pip-install.log) |
| `.\.venv\Scripts\python.exe -m compileall -q backend/app backend/alembic backend/tests` | Initial files compiled without output; this alone is not a behavioral test | [compile](../artifacts/test-output/phase2-compile.log) |
| `.\.venv\Scripts\python.exe -m pip freeze` | Captured with `Set-Content -Encoding utf8 backend/constraints.txt`; transitive constraints applied during Linux build | backend/constraints.txt |
| `docker compose config --quietка` | Success | [config](../artifacts/test-output/phase2-compose-config.log) |
| `docker compose up -d db` | PostgreSQL image pulled, volume initialized, separate soup/soup_test DBs created | [DB startup](../artifacts/test-output/phase2-db-start.log) |
| `docker compose up --build -d --wait` | First build exit0; migrations and health worked, ingestion still had the bug below. After correction/rebuild, exit0 and both services healthy | [first](../artifacts/test-output/phase2-compose-build-01.log), [corrected](../artifacts/test-output/phase2-compose-build-02.log) |
| `.\.venv\Scripts\python.exe -m pytest -q` | Exit1: **9 failed,21 passed in77.95s** | [host first run](../artifacts/test-output/phase2-pytest-host-01.log) |
| `.\.venv\Scripts\python.exe -u -c "import faulthandler; faulthandler.dump_traceback_later(15); import pytest; raise SystemExit(pytest.main(['--collect-only','-q']))"` | Collected30 cases; no test execution | [collection diagnostic](../artifacts/test-output/phase2-pytest-collection-diagnostic.log) |
| `.\.venv\Scripts\python.exe -u -m pytest backend/tests/test_backend.py::test_project_rotation_auth_and_run_listing -vv -s -o faulthandler_timeout=15` | Exit0:1 passed in5.24s | [auth diagnostic](../artifacts/test-output/phase2-pytest-host-diagnostic.log) |
| `docker compose run --rm api pytest -q` | Exit1: **9 failed,21 passed,2 warnings in2.36s** | [container first run](../artifacts/test-output/phase2-pytest-container-01.log) |
| `.\.venv\Scripts\python.exe -u -m pytest backend/tests/test_backend.py::test_service_commit_is_durable -q` | Exit1:1 failed; direct service trace identified datetime serialization bug | [service diagnostic](../artifacts/test-output/phase2-service-diagnostic.log) |
| `.\.venv\Scripts\python.exe -u -m pytest -q` | After correction: exit0, **31 passed in5.12s** | [host corrected](../artifacts/test-output/phase2-pytest-host-02.log) |
| `.\.venv\Scripts\python.exe -u -m pytest -q` | After additional lock-race/timeout/boundary cases: exit0, **36 passed in8.32s** | [host final](../artifacts/test-output/phase2-pytest-host-03.log) |
| `docker compose run --rm api pytest -q` | Corrected/rebuilt image: exit0, **36 passed in5.10s**, no warnings | [container final](../artifacts/test-output/phase2-pytest-container-02.log) |
| `docker compose exec -T api alembic current` | `0001 (head)` | [migration checks](../artifacts/test-output/phase2-migrations.log) |
| `docker compose exec -T api alembic check` | Exit0: `No new upgrade operations detected.` | [migration checks](../artifacts/test-output/phase2-migrations.log) |
| `.\.venv\Scripts\python.exe backend/tests/smoke_http.py --restart-api` | Exit0: real HTTP, API restart, identical retry, A/B read/write/list isolation, rotation and snapshot vs independent SQL all passed;3 persisted events/1 receipt | [live HTTP](../artifacts/test-output/phase2-live-http.log) |
| `docker compose ps` | API+DB healthy, bound only to127.0.0.1:8000/54329 | [final service state](../artifacts/test-output/phase2-services-final.log) |

The pytest fixture invokes `[sys.executable, '-m', 'alembic', '-c', 'alembic.ini', 'upgrade', 'head']` in backend with DATABASE_URL set to the explicitly guarded `_test` database. Compose startup runs `alembic upgrade head` before `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log`. No create_all, SQLite, mock DB or hidden migrations.

Diagnostics actually run: `py -0p`, `Get-Command python,py,docker,psql,uv`, process inspection and Start-Process for Docker Desktop; `Test-NetConnection -ComputerName 127.0.0.1 -Port 54329 -InformationLevel Quiet` returnedTrue. Host fixture now uses127.0.0.1, avoiding localhost's IPv6-first resolution. The first host run's buffered output appeared idle; Stop-Process was attempted for its two known Python PIDs, but its complete normal exit1/summary was recovered. It was not recorded as a timeout or passing run.

`docker compose exec -T db psql -U soup -d soup_test -c "SELECT pid, state, wait_event_type, wait_event, left(query, 90) AS query FROM pg_stat_activity WHERE datname='soup_test';"` inspected waiting activity. `docker compose logs --no-color --tail 100 db` was captured in [DB diagnostic](../artifacts/test-output/phase2-db-diagnostic.log). `docker compose logs --no-color api` captured [API startup/restart](../artifacts/test-output/phase2-api-startup.log). Package/image metadata queries are captured in phase2-package-versions.log, phase2-image-versions.log and phase2-python-image.log; they are discovery, not test evidence.

### Failures, fixes and scope of proof

- Initial ingestion failures were real: Pydantic's timestamp field_serializer applied to Python model_dump too, so asyncpg received strings instead of datetime objects. Restricted serializers to `when_used='json'`. The service test then passed; host/container suites verified ingestion. Unexpected DB programming errors now return sanitized500; only recognized transient SQL states/connection invalidation/timeouts return503.
- The first container test run also had2 pytest-cache permission warnings (non-root user, root-owned source directory). Set container pytest cache to `/tmp/soup-pytest-cache`; corrected run had no warnings.
- Strengthened the commit-failure injection: before_commit raises regardless of ORM weak-reference lifetime; after_flush observes pending Batch. Tests demonstrate events/counter/receipt rollback and successful retry. No passing failure-handling claim is based on a mocked commit response.
- Two documentation-only patch attempts failed before mutation: duplicate Delete/Add target for README, then wrong README heading context. Corrected using a literal README write and separate valid patches. Tool failures remain in chat history; application source was unaffected.
- Tests cover real PostgreSQL independent sessions, concurrent exact/conflicting batch/event retries, canonical equality/reordering, deterministic late/equal-step winners, byte/event/metric/value/time bounds, tenant read/write/list errors, key hashes/rotation and observed lock waits. Lock-timeout test obtains actual PostgreSQL lock contention and observes503/Retry-After with no partial writes. Rotation race tests wait for pg_blocking_pids rather than an arbitrary timing sleep.
- Snapshot test commits a writer between run and winner reads; read-only REPEATABLE READ returns consistent old state. Durable receipt test uses a fresh app/engine; live smoke additionally restarts the actual API process before retry and compares SQL facts without using application reducers. The live smoke creates demo records but prints/persists no keys.
- **Not proven:** SSE replay/revocation/slow readers, browser UI/state/cache/storage, multi-worker/process concurrency, timing/log side-channel absence, host crash/storage-loss durability, sustained500 events/s capacity. No Playwright/load test or SHIP verdict. These runs complete only the expanded Phase 2 backend scope. Services remain running for inspection.

### Phase 2 file changes / repository state

Created application/configuration files:

- `backend/app/__init__.py`, `db.py`, `errors.py`, `main.py`, `models.py`, `schemas.py`, `services.py`.
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial.py`.
- `backend/tests/conftest.py`, `backend/tests/test_backend.py`, `backend/tests/smoke_http.py`.
- `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/constraints.txt`, `backend/Dockerfile`, `backend/.dockerignore`, `backend/db-init.sql`, `backend/pytest.ini`.
- Root `compose.yaml`, `pytest.ini`, `.env.example`, `.gitignore`.

Modified `AGENTS.md`, `README.md`, `docs/PLAN.md`, `docs/TEST_MATRIX.md`, `docs/AI_USAGE.md`, and this evidence log. Added actual `artifacts/test-output/phase2-*.log` captures, preserving all earlier Phase 1 output. No DESIGN/API_CONTRACT changes in Phase 2. Local `.venv`, Python bytecode and pytest caches are ignored/generated development files, not deliverables.

The folder was not initially a Git repository. Executed `git init -b main` (exit0), then `git status --short --untracked-files=all`: [init output](../artifacts/test-output/phase2-git-init.log), [file inventory](../artifacts/test-output/phase2-files.log). No commit or remote publication performed. All pre-existing context files also appear untracked in that inventory; it is not a before/after diff. The list above identifies the actual Phase 2 edits.

## Phase 3 - durable SSE and dark Next.js application, 2026-11-11 (Asia/Qyzylorda)

Implemented only the user-authorized Phase 3 scope. Original Phase 2 application/tests preserved. PostgreSQL remains authoritative; no broker or in-memory event notification dependency. No load test, SHIP verdict or final submission report performed.

### Commands actually executed / raw results

All commands start in repository root unless noted. Main runs pipe `2>&1 | Tee-Object <log>`, capture `$LASTEXITCODE`, append `EXIT_CODE=<value>` and return it. Earlier combined discovery/type-check commands sometimes ended with another successful command: their overall shell0 does **not** mean the preceding npm/type check succeeded.

| Command | Actual outcome / raw log |
| --- | --- |
| `npm.cmd install --prefix frontend` | Failed ENOENT looking for root package.json; [raw failure](../artifacts/test-output/phase3-npm-install.log). Retried from frontend below |
| `npm.cmd install` (cwd frontend) | Succeeded; generated package-lock.json; [install](../artifacts/test-output/phase3-npm-install-02.log) |
| `.\.venv\Scripts\python.exe -m pip install playwright==1.65.0` | Succeeded; [install](../artifacts/test-output/phase3-playwright-install.log) |
| `.\.venv\Scripts\python.exe -m playwright install chromium` | Succeeded; [Chromium install](../artifacts/test-output/phase3-chromium-install.log) |
| `.\.venv\Scripts\python.exe -u -m pytest -q` | First:41 passed/1 failed (HTTPX test iterator misuse), [first](../artifacts/test-output/phase3-pytest-01.log). Corrected: **42 passed in16.24s, exit0**, [host](../artifacts/test-output/phase3-pytest-02.log) |
| `docker compose run --rm api pytest -q` | **42 passed in9.84s, exit0**, including original36; [container](../artifacts/test-output/phase3-pytest-container.log) |
| `npm.cmd run typecheck` (cwd frontend) | Initial TS5097: test .ts imports needed allowImportingTsExtensions; later TS2339 in new test's dot-constructor access. Fixed config and bracket access; final **exit0**, [final type check](../artifacts/test-output/phase3-typecheck-final-02.log). Failures retained in phase3-typecheck-01.log and phase3-typecheck-03.log |
| `npm.cmd test` (cwd frontend) | Initial3, then4, final **5 passed/0 failed, exit0**; [final client tests](../artifacts/test-output/phase3-client-tests-final-02.log) |
| `npm.cmd run build` (cwd frontend) | Production build succeeded; [host build](../artifacts/test-output/phase3-next-build-01.log) |
| `docker compose up --build -d --wait` | All builds succeeded; final includes corrected persistent layout, production TypeScript/build, web/API/DB healthy; [final build](../artifacts/test-output/phase3-compose-final-02.log). Earlier build logs retained |
| `.\.venv\Scripts\python.exe -u -m pytest e2e -q -s` | First:1 failed/2 passed (ambiguous Next.js alert selector), [first](../artifacts/test-output/phase3-browser-01.log); corrected run3 passed, [second](../artifacts/test-output/phase3-browser-02.log). Later final run exposed genuine switch/navigation form remount race, [failure](../artifacts/test-output/phase3-browser-final.log). Moved Shell/access into persistent App Router layout; [corrected final](../artifacts/test-output/phase3-browser-final-02.log) records actual final result |
| `docker compose ps` | Web/API/DB healthy on loopback3000/8000/54329; [state](../artifacts/test-output/phase3-services-final.log) |

Discovery also executed `node --version`, `npm.cmd --version`, `npm.cmd view <package> version` (next/react/tailwindcss/typescript/@tailwindcss/postcss/@types/react/@types/node), pip index versions playwright and Docker Hub tags query for Node22. Dependencies pinned: Next16.4.6, React/DOM19.3.1, Tailwind/PostCSS4.3.5, TypeScript7.0.2, Playwright1.65.0; Chromium158.0.8127.18. Host Node22.20.0; container Node22.23.4. Existing Python/PostgreSQL pins unchanged. npm's reported zero advisories is not a security proof.

### What the executed proofs establish

- SSE tests use actual Uvicorn TCP responses and PostgreSQL. Receive seq1-10, close response, commit11-30, retry an earlier batch, reconnect with Last-Event-ID10: exactly11-30 replay. Gap test takes snapshot0, commits300 before subscribing, and receives every1-300 across bounded250-row pages. Invalid cursor/auth/foreign run are rejected before stream headers.
- Watchdog checks the captured key hash/version on fixed1s ticks with1s DB/pool deadline, independent of sender/backlog. Actual TCP idle-stream rotation reaches terminal auth_expired within the test's2.5s bound; old key401/new key works. Controlled ASGI blocked-send tests prove cancellation during250-event backlog and timeout/slot/session cleanup. Admission rejects capacity overflow503 without waiting. **These do not measure every OS/proxy buffer or RSS under sustained slow clients.**
- Browser tests drive real Chromium/Next.js, ingest through actual FastAPI and compare SVG circle seq/step/value attributes, rendered history table, count and applied cursor against independent asyncpg queries. No mocked response body or shared application reducer defines that SQL oracle.
- Exact browser scenario: persisted1-10 displayed; click Disconnect (real fetch abort), commit11-30, duplicate identical batch, reconnect. Browser requests cursor10; an interceptor changes it to9 once to force the real server to repeat event10. UI ignores the duplicate and renders exactly1-30. Late lower-step and equal-step events update deterministic winners; independent SQL checks all33 events/points. Thus a correct final latest value alone cannot conceal missing intermediate events in this proof.
- API restart scenario uses actual `docker compose restart -t 1 api`, preserves browser state/cursor10, gates the next real SSE request, commits11-30 through the restarted API, then releases it. Browser recovers exact1-30 without refresh. Snapshot-gap browser scenario holds initial subscription after snapshot20, commits21-80, then opens stream: all80 raw events and chart points recovered. Route interception controls timing/one duplicate cursor only; storage and HTTP responses remain real.
- Browser verifies live key rotation enters error/re-auth state, project switch clears private content, reload requires key entry, local/sessionStorage remain empty, and server-rendered run HTML contains no key. The navigation race found in the later run was fixed by keeping the shell/access form in persistent root layout; failed run retained. No browser traces/HAR containing bearer headers recorded. A phase3 log token-pattern scan reported0 matches; this is limited evidence, not proof about every logging surface.
- Actual browser screenshots inspected at desktop1440px and mobile390px: [run list](../artifacts/screenshots/phase3-run-list.png), [run detail](../artifacts/screenshots/phase3-run-detail.png), [mobile](../artifacts/screenshots/phase3-mobile.png). Checked dark theme, chart/axis legibility, no horizontal mobile overflow; corrected tall step badge/mobile axis size. These are application screenshots, not synthetic passing-test screenshots.

### Contract clarification / remaining limits

New requested charts expose a concrete gap in the summary-only UI plan: snapshot winners cannot reconstruct intermediate points. Kept all endpoint/schema contracts. Initial client installs summary/H, then replays from0 into an explicit last2,000-event chart window. Snapshot winners/count never regress during historical replay. Reconnect preserves that window and sends last applied stream cursor, not a fresh snapshot cursor. Persistent DB history remains complete; equal-step chart points use highest seq. The visible window is deliberate retention, not silent reconnection loss; initial replay cost grows with DB history.

No new migrations or ingestion rewrite. Resource limits are per process (100 streams, page250, frame4KiB, send5s); buffers already sent cannot be recalled. Remaining evidence includes real OS/proxy slow-reader memory bounds, more partial-frame/DB-outage/cancellation schedules, exhaustive log/cache/timing leak review, other browsers/multi-worker cases and eventual sustained-load measurement. Phase3 does not claim production security/performance or finish the final submission.

Created `backend/app/stream.py`, `backend/tests/test_stream.py`, complete `frontend/` source/build/dependency lock/tests, `e2e/test_browser.py`, `requirements-e2e.txt`, phase3 raw logs/screenshots. Modified backend main/errors/Dockerfile only for stream route/policy/shutdown; modified Compose, .gitignore, .env.example, README, AGENTS and relevant plan/contract/evidence/provenance/matrix notes. No Phase2 schema/service/model/test_backend changes.

### Final observed Phase 3 state

- After the persistent-layout fix, `pytest e2e -q -s` passed3 in12.28s ([corrected run](../artifacts/test-output/phase3-browser-final-02.log)). After capping jittered reconnect delay at10s and preserving Retry-After up to30s, rebuilt with `docker compose up --build -d --wait`: exit0 ([verified image/build](../artifacts/test-output/phase3-compose-verified.log)). Production build includes TypeScript checks.
- Final command `.\.venv\Scripts\python.exe -u -m pytest e2e -q -s`: **3 passed in12.11s, exit0** ([verified browser run](../artifacts/test-output/phase3-browser-verified.log)). Both app corrections are in this tested image. No further application changes after that run. Backend42/container42 and client5 results above remain applicable; no backend/lib changes since their passing runs.
- `docker compose ps` after the final restart scenario showed all3 services healthy ([verified services](../artifacts/test-output/phase3-services-verified.log)). Services left running. Final screenshots overwritten only by actual successful browser captures and visually inspected.
- Static scan of32 phase3 log files found **0 token-shaped values** (`soup_[A-Za-z0-9_-]{43}`); [scan output](../artifacts/test-output/phase3-log-secret-scan-final.log). This does not inspect every infrastructure/browser log or establish absence of timing leaks.
- `git status --short --untracked-files=all` saved [file inventory](../artifacts/test-output/phase3-file-inventory.log); repository still has no initial commit, so old context also appears untracked. Newly authored frontend files are package.json/lock, tsconfig, next-env, next.config, postcss.config, Dockerfile/.dockerignore, src/app/layout/page/globals and runs/[id]/page, components/session/run-list/run-detail/chart, lib/api/live and tests/live.test. Node modules/build caches are ignored.
- One documentation patch failed expected-line validation before mutation; corrected without changing application behavior. All actual test/install/type-check/browser failures remain in their original logs; none relabeled as passing.

### Phase 3 usability follow-up - empty run preview

User opened a new empty run and requested a usable preview. Added an explicit **Send demo metrics** button to frontend/src/components/run-detail.tsx:40 generated events, named demo.loss/demo.accuracy, sent using the existing authenticated FastAPI endpoint. No automatic/fabricated chart data, DB bypass or persisted API key. Ambiguous submission retry retains the same batch/payload while the page is mounted; navigation cancels its request.

Added e2e/test_browser.py::test_empty_run_demo_button_populates_real_metrics. Actual commands:

- `docker compose up --build -d --wait`: exit0, production build/type-check and all3 services healthy; [raw output](../artifacts/test-output/phase3-demo-build.log).
- `.\.venv\Scripts\python.exe -u -m pytest e2e/test_browser.py::test_empty_run_demo_button_populates_real_metrics -q -s`: **1 passed in6.41s, exit0**; [raw output](../artifacts/test-output/phase3-demo-browser.log). Browser clicked the button on an empty run;40 persisted events,20 SVG points per metric and independent SQL/UI equality verified.

This follow-up ran the new focused browser case, not a repeat of every prior suite. Existing limitations remain; app was rebuilt so already-open browser tabs require reload/key re-entry to load this new UI. No secret recovery or storage was added.

## Phase 4 - adversarial reliability/security, 2026-11-11 (Asia/Qyzylorda)

User accepted Phase3 and explicitly authorized failure verification/confirmed fixes only. Re-read the entire original one-page PDF. Downloads attachment and reference remain byte-identical SHA256 `EFA2DDB310A11AEB89482128FFF4AA6C54D35E9B165A46C1FAAFE9FC2DB6E0B7`. The PDF requires consistency/isolation/failure proofs, not real ML training. Demo data remains intentional. No UI, schema, framework, deployed infrastructure, dependency or API contract change; no load test/final submission report/SHIP verdict.

### Actual commands, results and preserved failures

Repository-root PowerShell unless stated. Each principal test/build command pipes `2>&1 | Tee-Object <log>`, captures `$LASTEXITCODE`, appends `EXIT_CODE=<value>` and exits accordingly. Raw files are captured command output, not generated test-result summaries. Existing logs are retained untouched.

| Command | Actual result / raw output |
| --- | --- |
| `.\.venv\Scripts\python.exe -u -m pytest backend/tests/test_adversarial.py -q -s` | First **2 failed/7 passed**: confirmed repeated failed send, plus too-tight test deadline at watchdog2s boundary; [first run](../artifacts/test-output/phase4-adversarial-01.log). Later **1 failed/11 passed**: admission test had discarded its iterator/closed streams; [second](../artifacts/test-output/phase4-adversarial-02.log) |
| `.\.venv\Scripts\python.exe -u -m pytest backend/tests/test_adversarial.py::test_real_tcp_slow_reader_buffers_deadline_and_complete_replay -q -s` | **1 failed**, real unread TCP response retained slot beyond7s before fix; [slow-reader failure](../artifacts/test-output/phase4-slow-tcp-01.log) |
| `.\.venv\Scripts\python.exe -u -m pytest backend/tests/test_adversarial.py::test_postgres_unreachable_is_retryable_not_internal_error -q -s` | **1 failed**, actual connection refusal returned500 instead of503; [DB failure](../artifacts/test-output/phase4-db-unavailable-01.log) |
| `.\.venv\Scripts\python.exe -u -m pytest -q -s` | Corrected run **55 passed in42.53s** [first full host](../artifacts/test-output/phase4-backend-01.log); after RSS/canonical cases, **56 passed in44.45s, exit0**, [final full host](../artifacts/test-output/phase4-backend-final.log) |
| `.\.venv\Scripts\python.exe -u -m pytest backend/tests/test_adversarial.py::test_rotation_cannot_target_another_project_in_body_or_query backend/tests/test_adversarial.py::test_cors_denial_and_preflight_do_not_enumerate_runs -q -s` | **2 passed in2.01s, exit0**, added after full56 run; [extra isolation cases](../artifacts/test-output/phase4-isolation-extra.log) |
| `docker compose up --build -d --wait` | Exit0, fixed backend deployed, web/API/DB healthy; [initial build](../artifacts/test-output/phase4-compose-01.log), [final full-stack build](../artifacts/test-output/phase4-compose-final.log) |
| `docker compose run --rm api pytest -q -s` | First **1 failed/55 passed**, coarse poll missed Linux pressure spike; [original Linux failure](../artifacts/test-output/phase4-container-final.log). Final **58 passed in27.39s, exit0**, [verified Linux suite](../artifacts/test-output/phase4-container-verified.log) |
| `docker compose build api` then `docker compose run --rm api pytest tests/test_adversarial.py::test_real_tcp_slow_reader_buffers_deadline_and_complete_replay -q -s` | Rebuilt test image, diagnostic **1 passed in6.76s**; [build](../artifacts/test-output/phase4-test-image-build.log), [Linux send-boundary observation](../artifacts/test-output/phase4-slow-linux-diagnostic.log) |
| `.\.venv\Scripts\python.exe -u -m pytest e2e -q -s` | First **1 failed/7 passed** (await in cookie-check generator made an async generator, test error), [first browser](../artifacts/test-output/phase4-browser-01.log). Corrected **9 passed in34.32s, exit0**, [final browser](../artifacts/test-output/phase4-browser-final.log) |
| `npm.cmd run typecheck` (cwd frontend) | Exit0; [type check](../artifacts/test-output/phase4-typecheck.log) |
| `npm.cmd test` (cwd frontend) | **5 passed/0 failed, exit0**; [client tests](../artifacts/test-output/phase4-client-tests.log) |
| `docker compose ps` | All3 healthy after PostgreSQL/API restart scenarios; [final services](../artifacts/test-output/phase4-services-final.log) |
| `docker compose exec -T api alembic check` | Exit0, `No new upgrade operations detected.`; [schema](../artifacts/test-output/phase4-schema-check.log) |
| `docker compose exec -T db psql -U soup -d soup_test -c "SELECT count(*) AS leftover_fault_functions FROM pg_proc WHERE proname LIKE 'phase4_%';"` | **0** leftover fault functions; [cleanup](../artifacts/test-output/phase4-fault-cleanup.log) |
| `git status --short --untracked-files=all` | [File inventory](../artifacts/test-output/phase4-file-inventory.log). Existing repo has no initial commit; old context is also untracked, so this is not a before/after diff |

Versions unchanged from Phase3: PostgreSQL17.11/Python3.12.16 in Docker, Windows Python3.12.10, Chromium158.0.8127.18/Playwright1.65.0. No new dependency installed. Primary docs checked for pg_terminate_backend and SQLAlchemy connection hooks; initial Uvicorn docs fetch502 was not treated as evidence of runtime behavior. Source inspection/PDF extraction/hash comparisons were read-only tooling; full outputs remain in chat.

### Confirmed production bugs and minimal fixes

1. `backend/app/stream.py`: producer send timed out, then cleanup attempted another send for EOF, waiting another timeout and retaining admission resources. ASGI regression observed two send attempts; real unread TCP regression exceeded7s with a5s deadline. Capture completed producer failure/blocked-send/disconnect state; do not re-enter failed transport. Incomplete HTTP EOF intentionally closes transport and client recovers from its applied cursor. Existing normal terminal auth-expired/healthy close preserved.
2. `backend/app/db.py`: asyncpg initial connection establishment can raise native OSError, outside SQLAlchemy DBAPIError; API then returned500. Translate socket failures inside the DB transaction boundary to generic503/Retry-After1. Actual refused connection and actual Compose PostgreSQL stop/start both verify the correction. No raw address/credential echo; no broader error-handler refactor.

Test fixes are separate: watchdog deadline assertion increased from exact2s to3s (1s tick+1s query is not a hard real-time guarantee); keep HTTPX line iterator alive when holding admission slots; await cookies before synchronous all(); combine send-boundary transport observation with polling for short Linux peaks. The Linux correction still **requires actual buffer pressure**, rather than skipping/weakening the negative test. UI did not require a correction.

### Failure experiments actually executed

| Required failure | Real fault / negative observation |
| --- | --- |
| Partial batch writes | After real metric INSERT, separate PG connection calls pg_terminate_backend on that exact application backend; original request503 and rows/receipt/counter all0, then retry succeeds |
| Commit-time rollback | Test-only deferred constraint trigger raises on actual PostgreSQL COMMIT after flush; HTTP500 generic body, no persisted event/receipt/counter; trigger/function removed in finally |
| Cancellation | Cancel task after successful real ingest flush while PostgreSQL pg_sleep is active; transaction/lock/session cleanup, unchanged DB, identical retry succeeds. This is explicit server-task cancellation, not a claim client socket loss necessarily rolls back |
| Unknown client outcome after commit | Test-only TCP wrapper aborts actual response transport after committed metrics endpoint reaches200 start; client sees TransportError while DB contains2 rows/1 receipt. Fresh ASGI app returns the stored original receipt, no extra writes. Literal PG COMMIT-ACK packet loss is not injected |
| Replay/authorization DB failure | ACCESS EXCLUSIVE locks block replay/watcher queries; connection closes fail-closed, sessions/slots released, subsequent cursor1 replays exactly2. Separately block only metric replay and rotate key: independent watcher terminates subscription. Exhaust all20 DB pool connections: watcher times out and stream closes without metrics |
| PostgreSQL service outage | Browser test uses actual `docker compose stop -t 1 db`, with `docker compose start db` in finally and health wait. UI reconnects, failed ingest503, repeat same batch after recovery yields exact1-20 SQL/UI/events |
| Slow subscriber and admission overflow | Real Uvicorn TCP; reader stops consuming after headers. Constrain server write high-water4096B/socket buffers and client receive1024B to force pressure with1000 fixture events. Record OS resident memory via native Windows API or /proc/self/statm. Slot/DB sessions clean up, replay0 recovers every1-1000. Real HTTP admission overflow/slot reuse scales cap to2; actual default100 asserted |
| Partial frame / disconnect | Ephemeral TCP relay reads authentic upstream SSE; cuts frame11's JSON before its delimiter. Chromium applies only1-10, reports reconnecting, requests cursor10, then receives full11-30 and matches independent SQL/actual SVG points/history table |
| Late frame after tenant switch | Hold real A event2 in test relay, switch key/session to B, release pending frame. B remains at its own seq1/metric onlyB; no A card/state/cookie/storage content. Foreign REST/SSE UUIDs fail identically |
| Concurrent ordering/duplicates | Two independent Uvicorn processes share only PG, concurrent overlapping batches yield gapless1-9/original receipt; separate browser test injects unordered/equal-step/shared-event concurrent requests and compares every point/winner/count/cursor to independent SQL |
| Rotation and guessed identifiers | Existing idle/backlog/blocked-send tests retained; additional blocked-replay watcher and concurrent browser/write cases. Body project_id cannot rotate B; query project_id is ignored for scope, A rotates and B key/version remains unchanged. Valid/invalid CORS preflight has no run-existence branch |
| Error/log/timing privacy | Generic foreign/missing404 bodies and content/private headers identical across read/write/SSE;24 sequential local timing samples reported without equivalence claim. Actual API/web/DB Docker logs inspected, no token-shaped values; malformed body containing ephemeral token not echoed; SSR/cookies/storage checked |

TCP relays/Uvicorn wrappers are **test fixtures only**, not added Compose infrastructure or replacement application responses. They forward real PostgreSQL-backed endpoint frames and alter delivery timing/termination. No mocked response data supplies the SQL oracle. Original42 backend,4 browser and5 client cases remain included.

### Observed resource values - scope and limits

- Windows experiment: maximum transport buffer4224B, cleanup5.047s, sampled RSS baseline101945344B/peak102576128B. Linux verified suite: maximum4240B, cleanup5.011s, RSS baseline96399360B/peak96399360B. Sampling every20ms can miss allocation peaks; the 32MiB delta assertion is conservative single-test headroom, not a production capacity SLO.
- In the Linux failed diagnostic, coarse polling alone missed brief pressure. Send-boundary observation recorded4240B>4096B, so the corrected test measures actual backpressure on both runtimes. Buffers were deliberately reduced; production default socket/proxy settings and100 simultaneous clients are **not measured**. This is one-subscriber failure testing, not load/throughput evaluation.
- Already-buffered network bytes cannot be revoked. Admission is per API process/response; no global cross-worker connection quota or DoS resistance claimed. Long run history still grows in PostgreSQL; browser intentionally retains only the stated2,000-event window.
- Raw PostgreSQL protocol/TLS COMMIT acknowledgement cut, power loss, disk destruction, replicas, external CDN/proxy caches, other browsers and all asynchronous schedules are **not reproduced**. For raw commit-ACK loss, the current deterministic probes cover the observable rollback and committed-but-no-HTTP-receipt cases instead; a PG-aware wire fault point would be needed for that exact packet boundary.
- Timing probes establish same error contract, not constant time or absence of existence/load side channels. Operator-accessible PG logs may contain SQL/identifiers/metric metadata; credentials absent from checked captures does not prove every logging surface safe. Local unauthenticated project bootstrap/key-recovery limitations remain unchanged.

### PDF deliverable audit / next boundary

Projects/keys, batch ingestion, persistence, run list/live page and automated consistency/isolation/silent-failure evidence now exist. The original requirement to preserve failures is met by the unchanged failed logs above. The final deliverable still needs a measured50 runs x10 events/s SHIP/DON'T SHIP verdict and first change; <=2-page note; author's surprise/concern paragraph; completed human AI-use review; coherent repository/submission. Those are **not produced or claimed in Phase4**. No email sent and no live-discussion script written.

Changed production files only `backend/app/db.py` and `backend/app/stream.py`. Created `backend/tests/test_adversarial.py`, `backend/tests/fault_server.py`, `e2e/test_adversarial_browser.py`, `e2e/fault_relay.py`; updated root pytest helper search path and AGENTS/PLAN/TEST_MATRIX/AI_USAGE/EVIDENCE. UI/demo behavior, API shapes, migrations, services/models, original tests, dependencies and Compose services unchanged. New phase4 raw captures under artifacts/test-output. All temporary SQL fault objects cleaned; PostgreSQL and all3 application services left healthy.

Recommended **one** next phase: Phase5 controlled50x10 events/s evaluation with predefined workload/error/lag/resource thresholds and evidence-based verdict. Not executed or authorized automatically.

Final runtime log capture executed `docker compose logs --no-color --since 5m api web db` using subprocess with stdout/stderr combined. Exit0 and token-pattern matches0; original combined output saved unmodified as [phase4-runtime-docker.log](../artifacts/test-output/phase4-runtime-docker.log), capture/audit output in [phase4-runtime-log-audit.log](../artifacts/test-output/phase4-runtime-log-audit.log). Credential guard prevents persisting a token-shaped value if one is found; none was found. Earlier runtime log inspection in Chromium suite remains a separate observed test, not this later capture.

## Phase 5 - measured load, 2026-11-11 (Asia/Qyzylorda)

**Verdict: SHIP for the tested local workload, using the declared1% rate tolerance.** This is a time-bounded take-home verdict, not production readiness or a strict guarantee of >=500 completions/s. Actual fixed-window rates were498.92 and498.17 events/s; neither is rounded up to500. Both full corrected workloads accepted every planned event, passed the latency/correctness gates and preserved exact replay. No application optimization, UI redesign, schema, API contract, dependency or Compose configuration change was needed. Final submission note/email is not part of this phase.

### Environment and method

- Windows11 build26200 host; Intel Core i5-13450HX,10 physical/16 logical cores; physical RAM16,873,545,728B. Host CIM captures: [CPU](../artifacts/test-output/phase5-host-cpu.json), [RAM](../artifacts/test-output/phase5-host-memory.json). Laptop/background desktop activity was not controlled; no dedicated-host claim.
- Docker Desktop4.55.0, Engine29.1.3, Compose2.40.3, Linux/amd64 WSL2 kernel6.6.87.2. Engine reports16 logical CPUs,8,172,797,952B (7.612GiB) memory. API/web/db have no individual CPU/memory quotas; they share this VM/host. Existing named PG volume retained earlier demo/test campaign history; it was not reset for favorable cold/empty-table results. No network/disk bandwidth limit imposed or measured independently.
- PostgreSQL17.11, max_connections100, shared_buffers128MB. Python3.12.16/one Uvicorn worker in API; application pool10 +10 overflow (20 maximum), acquisition timeout2s. Windows generator Python3.12.10, httpx0.28.1, asyncpg0.32.0. Next.js production image remains running/health-checked, not a50-browser rendering load. Per-attempt `environment.json` preserves exact Docker information, image IDs, service state, limits, command and PG version/settings without bearer tokens/DSNs.
- [Generator](../scripts/load_test.py):50 runs in one newly created project,50 producer tasks with one bounded HTTP client each. Batch5 fresh events every0.5s/run, staggered across the interval:500 unique events/s,100 primary HTTP requests/s. Two metric names/run; deterministic input order and known values/steps; generated UUIDv4 identities. All ingestion uses bearer-authenticated real FastAPI endpoints. No DB writes by the generator. Payload manifest is frozen before load; keys remain in memory and are never captured.
- Each principal workload has10s warm-up +60s sustained measurement (35,000 unique events including5,000 warm-up;700 events/run). Setup/audit excluded. Exactly one identical retry every20th measurement batch/run:300 controlled retries, an additional1,500 event delivery attempts, not fresh events. Fresh and retried responses must match the original receipt. Every producer waits for its response; a delay of an entire batch interval skips/records the batch as a failure instead of creating an unbounded catch-up queue.
- Gates written to each `config.json` **before** sending: fixed-window throughput>=99% of configured rate, all planned events acknowledged, zero HTTP/pacing/protocol failures, primary request p95<500ms (batch interval), p99<1s, exact SQL/receipt/snapshot audit, complete SSE application when enabled. These latency/tolerance thresholds are applicant benchmark choices, not Soup requirements. Strict500/s is not inferred from passing the99% gate.
- Rate = unique events first acknowledged during the fixed monotonic window `[10s,70s)` /60, including any warm-up response crossing its start and excluding drain after its end. Request rate counts HTTP completions separately, including retries. Latencies use measurement-scheduled request cohorts, monotonic time and interpolated percentiles; all-request and primary-only statistics are separately retained. Windows timers occasionally wake a few ms early; recorded schedule lateness can be negative. Raw timestamps, actual completions and all failures remain available.
- Resources: repeated real `docker stats --no-stream --format '{{json .}}'` and independent `pg_stat_activity` queries (~3s actual sample spacing). Docker CPU100%=one logical CPU and can exceed100%; memory is Docker's working-set estimate, not all OS/socket memory. PG counts exclude the monitor connection. Sampling can miss peaks and does not directly measure application pool checkout wait. Generator CPU is process CPU time divided by whole workload elapsed time; subprocess CPU excluded.
- `requests.jsonl`, `resources.jsonl`, `sse.jsonl` preserve observations. `manifest.json` records planned identities/payloads. `database-audit.json`, `summary.json`, `analysis.json` are explicitly **derived** checks/measurements, not raw console output. Each directory freezes `load_test.py` used for that attempt. Existing failures were neither edited nor replaced.

### Actual commands, exit codes and preserved failures

Repository-root PowerShell unless stated. Command capture wrapper actually used: `2>&1 | Tee-Object <log>; $loadExit = $LASTEXITCODE; Add-Content <log> "PROCESS_EXIT_CODE=$loadExit"; exit $loadExit` (test/build wrappers use equivalent named variables/EXIT_CODE). Result JSON is emitted by executed tools, not fabricated as pytest output.

| Exact principal command | Result / raw capture |
| --- | --- |
| `docker compose up --build -d --wait` | Exit0; all3 healthy, [build/start](../artifacts/test-output/phase5-compose.log). Initial read-only daemon check failed because Docker Desktop was stopped; started it with `Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden`, then built. Failed info's zero/empty fields were not used as hardware measurements |
| `.\.venv\Scripts\python.exe -u scripts/load_test.py --runs 2 --warmup 1 --duration 3 --retry-every 2 --subscribers 2 --disconnect-seconds 1 --output artifacts/test-output/phase5-calibration-01` | Exit0,80 events/2 SSE clients, [calibration output](../artifacts/test-output/phase5-calibration-01.log). Generator check only, not target evidence |
| `.\.venv\Scripts\python.exe -u scripts/load_test.py --output artifacts/test-output/phase5-baseline-01` | **Exit1**,288.5 events/s,20,665/35,000 planned events attempted/accepted,14,335 never attempted because of recorded pacing misses; zero HTTP failures. [Original failure](../artifacts/test-output/phase5-baseline-01.log), [full failed summary](../artifacts/test-output/phase5-baseline-01/summary.json). SQL confirmed no acknowledged event missing: failed offered workload, not14,335 lost commits |
| `.\.venv\Scripts\python.exe -u -m cProfile -o artifacts/test-output/phase5-generator-profile.pstats scripts/load_test.py --warmup 2 --duration 5 --output artifacts/test-output/phase5-generator-profile` | Diagnostic workload **logical EXIT_CODE1**, cProfile wrapper process exit0 (retained as observed);139 events/s under profiling overhead. [Raw diagnostic](../artifacts/test-output/phase5-generator-profile.log), [binary profile](../artifacts/test-output/phase5-generator-profile.pstats) |
| `.\.venv\Scripts\python.exe -c "import pstats; pstats.Stats('artifacts/test-output/phase5-generator-profile.pstats').sort_stats('tottime').print_stats(22)"` | Exit0, [actual profiler output](../artifacts/test-output/phase5-generator-profile-analysis.log). Connection-pool assignment cumulative3.978s; repeated import discovery/stat overhead visible. Instrumented times are diagnostic, not target capacity |
| `.\.venv\Scripts\python.exe -u scripts/load_test.py --warmup 2 --duration 5 --retry-every 5 --output artifacts/test-output/phase5-client-pool-check` | **Exit1**, after generator-only client-pool fix:all3,500 events stored,489/s fixed5s window fails495/s gate; [preserved short-run failure](../artifacts/test-output/phase5-client-pool-check.log). Did not relax gates to pass it |
| `.\.venv\Scripts\python.exe -u scripts/load_test.py --output artifacts/test-output/phase5-baseline-02` | Exit0, [raw successful baseline](../artifacts/test-output/phase5-baseline-02.log), [full summary](../artifacts/test-output/phase5-baseline-02/summary.json), [SQL audit](../artifacts/test-output/phase5-baseline-02/database-audit.json) |
| `.\.venv\Scripts\python.exe -u scripts/load_test.py --subscribers 50 --output artifacts/test-output/phase5-sse-01` | Exit0, [raw combined workload](../artifacts/test-output/phase5-sse-01.log), [full summary](../artifacts/test-output/phase5-sse-01/summary.json), [SQL audit](../artifacts/test-output/phase5-sse-01/database-audit.json) |
| `.\.venv\Scripts\python.exe -u scripts/analyze_load.py artifacts/test-output/phase5-baseline-01 artifacts/test-output/phase5-baseline-02` | Exit0, [derived baseline analysis output](../artifacts/test-output/phase5-baseline-analysis.log); analysis is labeled as derived from raw files |
| `.\.venv\Scripts\python.exe -u scripts/analyze_load.py artifacts/test-output/phase5-sse-01` | Exit0, [derived SSE analysis output](../artifacts/test-output/phase5-sse-analysis.log) |
| `docker compose run --rm api pytest -q -s` | **58 passed in27.19s, exit0**, [backend regression](../artifacts/test-output/phase5-regression-backend.log) |
| `.\.venv\Scripts\python.exe -u -m pytest e2e -q -s` | **9 passed in38.23s, exit0**, [real Chromium regression](../artifacts/test-output/phase5-regression-browser.log); partial frames, actual DB/API restarts, duplicates/out-of-order/late events, live rotation/isolation/UI-vs-SQL retained |
| `npm.cmd test` (cwd frontend) | **5 passed/0 failed, exit0**, [client regression](../artifacts/test-output/phase5-regression-client.log) |
| `npm.cmd run typecheck` (cwd frontend) | Exit0, [type check](../artifacts/test-output/phase5-regression-typecheck.log) |
| `.\.venv\Scripts\python.exe -u artifacts/test-output/phase5-post-regression-sql.py` | Exit0, [actual SQL/source](../artifacts/test-output/phase5-post-regression-sql.py), [all100 run rows after API/DB restarts](../artifacts/test-output/phase5-post-regression-sql.log);70,000 events/14,000 receipts unchanged |
| `docker compose ps`; `docker compose exec -T api alembic check` | Both exit0; [healthy services](../artifacts/test-output/phase5-services-final.log), [no schema drift](../artifacts/test-output/phase5-schema-check.log) |
| `docker compose logs --no-color --since 20m api web db` (subprocess capture and credential guard) | Exit0,7,355B saved unchanged as [actual service output](../artifacts/test-output/phase5-runtime-docker.log); token-pattern matches0. [Audit](../artifacts/test-output/phase5-log-and-source-audit.log) also confirms19 phase5 console captures clean and application file hashes unchanged |

Original assignment re-read through bundled pypdf: [extracted full page](../artifacts/test-output/phase5-original-assignment.log), exit0 with Python `-X utf8`; earlier read-only print without UTF-8 failed on the <= symbol under Windows cp1251 (tool transcript, not a test). Attachment/reference SHA256 remains `EFA2DDB310A11AEB89482128FFF4AA6C54D35E9B165A46C1FAAFE9FC2DB6E0B7`. Source/file reads, host CIM and hash inspection commands were read-only; no unexecuted application checks are reported as passes.

### Measured outcomes (not target estimates)

| Measurement | Baseline,0 SSE | Combined,50 SSE |
| --- | ---: | ---: |
| Warm-up / fixed measurement | 10s /60s | 10s /60s |
| Whole workload incl drain (excludes setup/audit) | 70.291s | 70.620s |
| Planned / attempted / accepted unique events | 35,000 /35,000 /35,000 | 35,000 /35,000 /35,000 |
| Event delivery attempts incl retries | 36,500 | 36,500 |
| HTTP requests, all200 | 7,300 | 7,300 |
| Controlled exact retries | 300 | 300 |
| Rejected event deliveries / HTTP failures / timeouts | 0 /0 /0 | 0 /0 /0 |
| Unique event completions inside fixed60s | 29,935 | 29,890 |
| **Actual unique events/s** | **498.917** | **498.167** |
| HTTP completions/s incl retries | 104.433 | 103.900 |
| Primary request p50 /p95 /p99 | 40.62 /206.30 /282.97ms | 109.47 /309.63 /438.63ms |
| All measurement request p50 /p95 /p99 | 41.72 /237.56 /293.14ms | 114.52 /319.31 /446.02ms |
| Last primary response relative to workload start | 70.184s | 70.481s |
| Generator CPU, whole workload, percent of1 core | 63.00% | 71.27% |

Each measurement-scheduled cohort contains all30,000 expected unique events, including final responses outside the fixed window. The actual fixed-window deficits are reported; receipt drain and timer/pacing variation are visible in timestamps, not silently excluded. Six10s bucket rates: baseline492.5/499/498.5/500.5/499.5/503.5; SSE493/501/499.5/498.5/497.5/499.5. This supports the declared approximate500/s local profile; it does **not** establish500+ in every interval or indefinite capacity. No pacing omissions in either corrected full run.

Independent asyncpg queries checked **every stored field/identity/input order**, unique events, contiguous sequences, counters, project scope, receipt-to-row mapping/original HTTP receipts and API snapshots against independently selected greatest(step,seq) winners. Per workload:50 runs, each700 events/seq1-700/last_seq700 and140 receipts; aggregate35,000 events/7,000 receipts. All50 snapshots match DB; no missing acknowledged events, unexpected duplicates or extra retry receipts. API and DB restart regressions ran afterward; an additional direct SQL probe verified both load projects still intact.

SSE used50 real HTTP streaming consumers, authenticated headers and independent contiguous application checks; all received700 events, no duplicate/gap/protocol errors. Subscriber0 deliberately closed with applied cursor400 at40.430s, paused5.034s, then sent `Last-Event-ID: 400`. By resume the API had acknowledged through455; exact401-455 (55 known missed events) were applied within0.096s of resume, then live updates continued to700. Full raw application records remain in `sse.jsonl`; this is not an inferred visual/chart update. Browser correctness is separately covered by9 actual Chromium regressions, not50 parallel browsers.

### Resources, first observed bottleneck and limits

19 measurement samples per full run; below are observed means/maxima, not unsampled absolute peaks. CPU units are percent of one logical CPU; memory maxima are MiB from Docker stats.

| Service | Baseline CPU mean /max; memory max | With50 SSE CPU mean /max; memory max |
| --- | --- | --- |
| API | 63.38% /93.57%;101.70MiB | 103.63% /120.20%;115.00MiB |
| PostgreSQL | 17.38% /28.77%;119.80MiB | 34.28% /39.26%;174.10MiB |
| Next.js | 3.40% /10.60%;83.10MiB | 4.54% /8.60%;98.58MiB |

PG observed max connections10->20, active1->6, idle-in-transaction4->17; sampled lock waiters0 in both. Idle-in-transaction samples during short multi-statement transactions are not evidence of a leaked stream-long transaction. Combined connections reached the configured API pool ceiling; no HTTP timeout/rejection or stream failure occurred, but pool wait was not directly instrumented, so absence of waiting is **not proven**. Memory growth over70s is insufficient to establish a leak or a long-term bound; PG buffers/cache and retained data were not reset.

**First confirmed bottleneck was the measurement client.** Initial shared HTTPX pool reached94.47% of one generator CPU, missed2,867 planned batches and offered only288.5 events/s; API averaged41.75% CPU, PG11.44%, connections<=10. cProfile identified repeated connection assignment/import discovery. One bounded client/run raised offered throughput without changing the server. The short489/s failure and the initial/profile failures remain part of the evidence.

For the unchanged application the highest observed resource cost is API work with SSE: CPU mean63.38->103.63%, primary p95 206->310ms, PG connections10->20. Combined second-half primary p99 rose from303 to515ms compared with its first half. These are measured pressure/latency signals, **not proof of the exact server saturation point or sole root cause**. No higher-rate capacity sweep or server profile was performed. **First change before production:** instrument API transaction/pool-acquisition latency and CPU, then profile the existing SSE polling/revalidation work before changing worker count, pool size or polling cost. Adding a broker or blindly increasing connections is not supported by this experiment.

Unverified at load: long soak, substantial old-history bootstrap,50 real browser renderers,100 slow subscribers/aggregate socket memory, multi-worker/global quotas, WAN/TLS/external proxy behavior, noisy neighbors, disk/power faults, replicas/backup recovery and capacity beyond500 offered events/s. Phase4's security/commit-ACK/timing limitations remain. Local unauthenticated project bootstrap/key recovery still needs a production access policy. The scoped verdict does not certify these properties.

Changed files: new `scripts/load_test.py` and `scripts/analyze_load.py`; minimal run instructions/status/provenance in README, AGENTS, PLAN, TEST_MATRIX, AI_USAGE and this evidence; actual captures/source snapshots/probe under artifacts/test-output. Product files remain byte-identical to their measured hashes. **One recommended next phase: Phase6 final submission packaging and the <=2-page note, author surprise/concern and AI review, reproducible repository handoff.** Not started; no email sent.

Final artifact check confirmed both successful attempts' frozen generator bytes equal current source and every recorded gate passed, then **failed** on two pre-existing Phase2 document links: `phase2-compile.log` and `phase2-compose-config.log` are absent. [Original failed check](../artifacts/test-output/phase5-artifact-check.log) is preserved, exit1. Those historical raw captures cannot be reconstructed; their old table entries (including the malformed `--quietка` command spelling) are not treated as independently verifiable evidence here. Phase5 build/schema/regression/load captures are present. Follow-up validates current Phase5 links while explicitly retaining these known historical gaps, rather than manufacturing replacement logs.

[Actual follow-up output](../artifacts/test-output/phase5-artifact-check-followup.log): exit0, all current links/captures/source snapshots valid; the two historical gaps remain explicitly unverified.
