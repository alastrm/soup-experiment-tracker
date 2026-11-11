# Minimal API contract - Phase 1

Implemented contract, with executed scope and limitations recorded in [the audit](SUBMISSION_AUDIT.md) and [evidence](EVIDENCE.md). Soup specifies the ingestion route; other endpoints/limits below are applicant choices. FastAPI owns every endpoint. Client-supplied project IDs never select authorization scope.

## Wire bounds and identity

- Objects reject extra fields, duplicate JSON keys, null required values and coercion from strings/bools to numbers. Invalid JSON/non-standard NaN/Infinity rejected. Body maximum **262,144 bytes**, enforced while reading even without Content-Length; compressed bodies rejected. Nonempty bodies require `application/json` (optional UTF-8 charset).
- IDs: lowercase hyphenated RFC 4122 UUIDv4; project/run IDs server-generated, batch/event IDs client-generated. Names match `[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}` (1-100 ASCII characters); not unique. Creation body exactly `{name}`; rotation `{}`.
- Event exactly `{event_id,metric,step,value,occurred_at}`. Metric matches `[A-Za-z][A-Za-z0-9_.-]{0,63}`, case-sensitive. Maximum **128 distinct names/run**; admission checked under run lock, whole batch rejected if exceeded. Step is a JSON integer 0..**9,007,199,254,740,991**; fractional syntax/bool/string rejected. Seq/cursor/count share this safe-integer ceiling; new-event overflow => 409.
- Value is a JSON number converted to finite binary64, absolute value <=**1e308**; reject overflow and nonzero underflow to zero. Normalize signed zero to positive zero. Different numeric spellings yielding the same binary64 value are identical; arbitrary-precision decimal identity is not supported.
- Timestamp: valid UTC `YYYY-MM-DDTHH:mm:ss[.1-6 digits]Z`, **2000-01-01T00:00:00Z <= t < 2100-01-01T00:00:00Z**. Validate calendar dates/seconds 00-59. Reject offsets, naive times and >6 fractional digits; output six fractional digits. No wall-clock recency check: offline/late events allowed.
- Batch exactly `{batch_id,events}` with **1-250 events**, distinct event IDs within the array (duplicates =>422, even identical). Invalid batch changes nothing. Events are immutable; no delete/pruning/retention in this demo. Volume destruction is data loss, not process-restart recovery.
- Key: 32 random bytes, unpadded base64url, prefix `soup_`; only unique SHA-256 hash/version stored. High entropy is essential; these are not passwords. HTTPS required outside loopback. No positive authorization cache.

Canonical event bytes: UTF-8 JSON array `[event_id,metric,step,value_hex,utc_time]`, ASCII strings/no whitespace/integer step. `value_hex`: 16 lowercase hex digits of normalized binary64 big-endian bytes; timestamp fixed six fractions. Thus value `1`/`1.0`, timestamp absent/zero fractions, whitespace/object-key order compare equal. Canonical batch: `[1,[event_arrays_in_input_order]]`, same encoding; 1 is frozen canonicalization version. **Reordering the array changes batch identity**, since new seq follows input order. Scope is project + run + batch/event ID. Store canonical batch bytes/digest (SHA-256) and receipt; compare bytes too. Cross-batch events compare normalized fields; retain identity data after restart.

## Endpoints

`Run` = `{id,name,created_at}`; timestamps normalized as above. Names immutable in scope. `EventWithSeq` = event's five fields plus `seq`.

| Method/path | Auth/request | Success (mutations after commit) |
| --- | --- | --- |
| `POST /projects` | Unauthenticated local demo bootstrap; `{name}` | 201 `{project:{id,name,created_at},api_key,key_version:1}` |
| `POST /projects/key/rotate` | Current bearer; `{}`; no project ID | 200 `{api_key,key_version}`; replace hash/increment version atomically |
| `POST /runs` | Bearer; `{name}` | 201 `Run`; initial DB last_seq=0 |
| `GET /runs?limit=50&after=<uuid>` | Bearer; limit 1-100, optional exclusive UUID lower bound | 200 `{runs:Run[],next_after:uuid\|null}`, UUID ascending; fetch limit+1 for continuation |
| `GET /runs/{id}` | Bearer | 200 `{run:Run,last_seq:H,event_count:H,metrics:[EventWithSeq]}`; one winner/metric, ASCII metric order; empty initially |
| `POST /runs/{id}/metrics` | Bearer; batch | 200 stable receipt `{batch_id,accepted:[{event_id,seq}],inserted_count,deduplicated_count,committed_seq}`; accepted in input order, reused seq included |
| `GET /runs/{id}/events` | Bearer; `Accept: text/event-stream`; optional `Last-Event-ID` | 200 SSE after auth/run/cursor checks |

List `after` is only a sort bound, never an existence lookup; a foreign UUID reveals nothing. Pagination is not a historical snapshot: refresh to see new UUIDs before the cursor. No project list. Keys returned once at creation/rotation, never retrievable. Creation/rotation have **no automatic retry guarantee**: lost creation response can duplicate a resource; lost rotation response loses the new plaintext and old key fails. Local demo then needs operator recovery or a new project; no stored plaintext recovery key. Document this handoff limitation.

## Transactions and snapshot

1. Each mutation owns an AsyncSession and explicit READ COMMITTED transaction, **including auth reads** (avoid dependency-triggered implicit transactions). Resolve candidate project from token hash, lock project FOR SHARE, revalidate hash/version **after any wait**, then lock fresh run state with `project_id=authenticated_project AND id=requested_run FOR UPDATE`. Rotation takes project FOR UPDATE and revalidates before replacement. Lock order project then run; shared project locks allow different-run writers. No shared session between concurrent tasks. Reads authorized before rotation may finish; old-key requests newly authorized after rotation fail.
2. Under run lock, check existing batch **before** metric-count/cursor-cap admission: exact retry returns original receipt/committed_seq even after run advances; changed identity =>`batch_conflict`. For a new batch compare all events; any changed duplicate =>`event_conflict`. Allocate contiguous seq only for unseen events in input order; all-dedup batches store receipts without incrementing counter. Unique `(run_id,batch_id)`, `(run_id,event_id)`, `(run_id,seq)` and tenant-consistent foreign keys backstop scoped service queries. No SERIAL cursor/process lock/silent ON CONFLICT acceptance.
3. Events, metric-name admission, counter and receipt commit together. Flush/commit failure aborts session/transaction; return no 2xx before commit completes, including no deferred commit dependency. Lock/statement deadlines **2s/3s**, whole mutation **5s**, including commit. Transient DB/deadlock/timeout =>503; retry identical batch. Lost commit acknowledgement is **unknown outcome**, not proof of rollback; identical retry resolves it.
4. Snapshot uses a short **read-only REPEATABLE READ** transaction configured before first SQL; auth, scoped H and winner query share the view. Greatest `(step,seq)` per metric wins; event time is informational. Append-only gapless storage makes event_count=H. Return <=128 winners; full raw history is replayable from 0. Snapshot is a current-value summary; charts reconstruct history through replay below. E2E independently derives every visible value, step, winning seq, count and cursor from DB.

## Stream, application and resource bounds

- Cursor header: decimal digits, no sign/whitespace/leading zeros except `0`, range 0..safe-integer ceiling. Missing=0, malformed=422, greater than scoped current H=409 `cursor_ahead`. Auth/scoped existence checked before state conflicts. Never reuse cursor across runs/projects; bind it to client run/key generation.
- Metric frame: `event: metric`, `id: <seq>`, `data: <single-line JSON EventWithSeq>`, blank-line delimiter. Header/JSON seq must agree. Replay scoped committed rows `cursor < seq <= H` ascending, pages <=250, indexed `(run_id,seq)`. Each short poll reads H/page in a read-only REPEATABLE READ view; close session before sends, fetch next page only after consumption. No broadcast/client queue or transaction over stream lifetime.
- After sending through poll H send `event: caught_up`, `data: {"cursor":H}`, **no id**; also send on empty initial replay. This never advances the metric cursor. Idle poll **250ms**, comment heartbeat at least every **10s**. Server frame maximum **4,096 UTF-8 bytes**; disable stream compression/proxy buffering.
- Independent watchdog checks the connection's original key hash/version at **fixed monotonic 1s ticks**, query deadline **1s including pool acquisition**; do not sleep 1s after each query. Invalid key marks the stream terminal and cancels metric sends immediately; send best-effort `auth_expired` with `{"code":"unauthorized"}`, no id, only when the serialized send path is free, then close. Auth/DB failure closes fail-closed. Cancel even during replay/backpressure. Target no new metric send >**2s** after rotation under responsive scheduling. Enforce **5s per ASGI send**, around transport send, not merely generator work. Disconnect/`asyncio.CancelledError` cleans reader/watchdog/sessions. Buffered bytes cannot be recalled; network delivery/scheduling are not hard real-time guarantees. Measure transport buffer bounds/timeouts; StreamingResponse alone is insufficient.
- Admit at most **100 active SSE responses per API process**, without a waiting admission queue; excess returns 503 before headers, release slot on every exit. This is resource admission, never a correctness/authorization lock. One bounded DB page/connection, <=4KiB per send; transport backpressure must stop further production. Total RSS/OS buffers remain measurement obligations, not inferred from these limits. Process-local capacity may reveal shared load; no global multi-worker quota is claimed.
- Client: direct `fetch`, bearer header, `cache:'no-store'`, `credentials:'omit'`, AbortController. Incremental UTF-8/SSE parser handles CRLF/LF, comments, split chunks and joined data lines; maximum pending frame **8,192 UTF-8 bytes**. Oversized/malformed/partial-at-EOF frame never applies/advances cursor; EOF reconnects.
- Install snapshot summary/H atomically. One active reader/reducer per generation; apply seq=`cursor+1` atomically with count/winner/reconnect cursor. Ignore seq<=cursor (server event IDs unique/run). Gap/inconsistent id/data => stale/reconnect from last applied, surface protocol failure. Parsing or merely scheduling React state is insufficient: state/cursor must be one committed reducer result. Late lower-step events still advance count/cursor; equal-step higher seq wins. UI retains <=128 current values, a bounded parser and the last **2,000 committed events across metrics** for charts; window limitation is visible.
- Phase 3 chart requirement: winner-only snapshots cannot reconstruct historical chart points. Endpoint/wire contracts are unchanged; on initial load, keep snapshot winners/count at H but replay the stream from0 to populate chart history. This history cursor advances only after each point is applied; replay <=H does not regress snapshot values/count. Reconnect from this last applied cursor without clearing charts or replacing them with a new snapshot. Only an explicit reset/reload rebuilds history. Once caught_up matches applied cursor, status becomes connected. Charts use logical step, greatest seq per equal step; raw event inspection retains every event in the stated window. This replaces the initial summary-only client assumption, not the durable replay protocol.
- Connecting/reconnecting/stale until caught_up equals applied cursor, then live. Abort after **25s** without stream activity. Jittered exponential retries **0.5s..10s**, respect Retry-After up to **30s**, reset on caught_up. Retry transport/EOF/429/5xx; stop on 401/403/auth_expired and require key entry; show other permanent 4xx. Cursor_ahead needs explicit fresh snapshot/reset. Abort streams/requests/retry timers on unmount/run/key change; ignore stale-generation callbacks. Reload requires key re-entry/new snapshot.

## FastAPI / Next.js / caching boundary

- Next.js App Router serves client pages only: no application API handlers/server actions or secret-bearing server components/props. All protected requests go directly to FastAPI.
- Local browser web **http://localhost:3000**, API **http://localhost:8000**. Only public API origin in `NEXT_PUBLIC_API_BASE_URL`, never a token or Docker `api:8000`. Exact configurable CORS origins; methods GET/POST/OPTIONS; allowed headers Authorization/Content-Type/Accept/Last-Event-ID; expose Retry-After; credentials disabled. Preflight unauthenticated, tenant-independent; CORS wraps errors too and is not authorization.
- Every API response including errors/key responses: `Cache-Control: no-store`; streams additionally `no-transform`; `Vary: Origin, Authorization`. No ETag/shared private cache/service-worker caching. Keys only in ephemeral client memory: never URL/cookie/storage/HTML/log/env public token. Clear private state on key change. Do not log auth/request/key-response bodies; scrub validation errors/traces. Access-log run IDs remain a disclosure risk to minimize/redact. Nonlocal bootstrap exposure needs separate protection; this is no-account local setup.

## Stable errors

HTTP envelope exactly `{"error":{"code":"<code>","message":"<message below>"}}`; no input echo, SQL, secrets, stack or foreign IDs. Missing/invalid/revoked bearer all 401 `unauthorized`, `WWW-Authenticate: Bearer`. Foreign/missing run identical 404 `not_found`, body/header policy; authenticate before scoped lookup, scoped existence before cursor/identity conflicts. Transport/JSON/schema errors may precede authentication but consult no tenant state; malformed path UUID is uniformly 422. For valid request shapes, unknown/foreign IDs follow the same authenticated lookup path.

| HTTP | Code | Exact message |
| --- | --- | --- |
| 400 | `invalid_json` (includes duplicate keys) | `Invalid JSON.` |
| 401 | `unauthorized` | `Valid API key required.` |
| 404 | `not_found` | `Resource not found.` |
| 405 | `method_not_allowed` | `Method not allowed.` |
| 413 | `payload_too_large` | `Request body too large.` |
| 415 | `unsupported_media_type` (also encoding) | `Unsupported request format.` |
| 422 | `validation_error` | `Request validation failed.` |
| 409 | `batch_conflict` | `Batch identity conflict.` |
| 409 | `event_conflict` | `Event identity conflict.` |
| 409 | `metric_limit` | `Run metric limit reached.` |
| 409 | `cursor_exhausted` | `Run sequence limit reached.` |
| 409 | `cursor_ahead` | `Cursor exceeds committed sequence.` |
| 503 | `temporarily_unavailable` | `Service temporarily unavailable.` |
| 500 | `internal_error` | `Internal server error.` |

503 includes `Retry-After: 1`; commit outcome may be unknown. Framework errors use the same envelope. Successful CORS preflights/denials are middleware protocol responses without tenant data, not application JSON errors. No role-based 403 here, but client stops on one. After SSE headers, HTTP status cannot change: terminal auth_expired or connection close; client never advances on failure. Generic responses reduce obvious leaks; constant-time behavior, safe aggregate capacity and exhaustive side-channel absence are **not proven**.
