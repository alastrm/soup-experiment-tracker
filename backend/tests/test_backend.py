import asyncio
import copy
import hashlib
import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event as sa_event, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.models import Batch, MetricEvent, Project, Run
from app.schemas import BatchRequest, MAX_BODY, MAX_SEQ


def metric(*, step=1, value=1.0, name="loss", event_id=None):
    return {"event_id": event_id or str(uuid4()), "metric": name, "step": step,
            "value": value, "occurred_at": "2026-01-01T00:00:00Z"}


def batch(*events, batch_id=None):
    return {"batch_id": batch_id or str(uuid4()), "events": list(events or [metric()])}


async def setup_run(client, name="test"):
    response = await client.post("/projects", json={"name": name})
    assert response.status_code == 201, response.text
    project = response.json()
    auth = {"Authorization": "Bearer " + project["api_key"]}
    response = await client.post("/runs", json={"name": "run"}, headers=auth)
    assert response.status_code == 201, response.text
    return project, auth, response.json()["id"]


async def counts(db, run_id):
    async with db.sessions() as session:
        scope = UUID(run_id)
        return (
            await session.scalar(select(func.count()).select_from(MetricEvent).where(MetricEvent.run_id == scope)),
            await session.scalar(select(func.count()).select_from(Batch).where(Batch.run_id == scope)),
            await session.scalar(select(Run.last_seq).where(Run.id == scope)),
        )


async def test_service_commit_is_durable(db):
    async with db.transaction() as session:
        project = await services.create_project(session, "direct")
    authorization = "Bearer " + project.api_key
    async with db.transaction() as session:
        run = await services.create_run(session, authorization, "run")
    async with db.transaction() as session:
        receipt = await services.ingest(session, authorization, run.id, BatchRequest.model_validate(batch()))
    assert receipt.inserted_count == 1
    assert await counts(db, str(run.id)) == (1, 1, 1)


async def test_project_rotation_auth_and_run_listing(client, db):
    project, auth, run_id = await setup_run(client)
    async with db.sessions() as session:
        saved = await session.get(Project, UUID(project["project"]["id"]))
        assert saved.key_hash == hashlib.sha256(project["api_key"].encode()).digest()
        assert project["api_key"].encode() not in saved.key_hash
    detail = (await client.get(f"/runs/{run_id}", headers=auth)).json()
    assert detail["metrics"] == [] and detail["last_seq"] == detail["event_count"] == 0
    for _ in range(2):
        assert (await client.post("/runs", json={"name": "another"}, headers=auth)).status_code == 201
    first = (await client.get("/runs?limit=2", headers=auth)).json()
    second = (await client.get("/runs?limit=2&after=" + first["next_after"], headers=auth)).json()
    ids = [r["id"] for r in first["runs"] + second["runs"]]
    assert ids == sorted(ids) and len(set(ids)) == 3 and second["next_after"] is None
    rotation = await client.post("/projects/key/rotate", json={}, headers=auth)
    assert rotation.status_code == 200 and rotation.json()["key_version"] == 2
    assert (await client.get("/runs", headers=auth)).status_code == 401
    assert (await client.post("/runs", json={"name": "bad"}, headers=auth)).status_code == 401
    assert (await client.post("/projects/key/rotate", json={}, headers=auth)).status_code == 401
    fresh = {"Authorization": "Bearer " + rotation.json()["api_key"]}
    assert (await client.get(f"/runs/{run_id}", headers=fresh)).status_code == 200


async def test_strict_project_isolation(client, db):
    _, auth_a, run_a = await setup_run(client, "A")
    _, auth_b, run_b = await setup_run(client, "B")
    body = batch()
    assert (await client.post(f"/runs/{run_b}/metrics", json=body, headers=auth_b)).status_code == 200
    for path, method, kwargs in [("/runs/", "get", {}), ("/runs/", "post", {"json": body})]:
        suffix = "/metrics" if method == "post" else ""
        foreign = await getattr(client, method)(path + run_b + suffix, headers=auth_a, **kwargs)
        missing = await getattr(client, method)(path + str(uuid4()) + suffix, headers=auth_a, **kwargs)
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json() == {"error": {"code": "not_found", "message": "Resource not found."}}
        assert foreign.headers["cache-control"] == missing.headers["cache-control"] == "no-store"
    listed = (await client.get("/runs", headers=auth_a)).json()
    assert [r["id"] for r in listed["runs"]] == [run_a]
    assert run_b not in (await client.get("/runs?after=" + run_b, headers=auth_a)).text
    # Same IDs are permitted in a different run/project, never a global cache hit.
    result_a = await client.post(f"/runs/{run_a}/metrics", json=body, headers=auth_a)
    assert result_a.json()["inserted_count"] == 1
    assert await counts(db, run_b) == (1, 1, 1)
    for headers in ({}, {"Authorization": "Bearer invalid"}):
        denied = await client.get(f"/runs/{run_b}", headers=headers)
        assert denied.status_code == 401 and denied.headers["www-authenticate"] == "Bearer"


async def test_batch_and_event_idempotency_conflicts_and_order(client, db):
    _, auth, run = await setup_run(client)
    original = batch(metric(step=5, value=50), metric(step=2, value=20))
    url = f"/runs/{run}/metrics"
    receipt = await client.post(url, json=original, headers=auth)
    assert receipt.status_code == 200, receipt.text
    assert [e["seq"] for e in receipt.json()["accepted"]] == [1, 2]
    canonical_equivalent = copy.deepcopy(original)
    canonical_equivalent["events"][0]["value"] = 50.0
    canonical_equivalent["events"][0]["occurred_at"] = "2026-01-01T00:00:00.000000Z"
    assert (await client.post(url, json=canonical_equivalent, headers=auth)).json() == receipt.json()
    changed = copy.deepcopy(original)
    changed["events"].reverse()
    assert (await client.post(url, json=changed, headers=auth)).json()["error"]["code"] == "batch_conflict"
    reused = await client.post(url, json=batch(*original["events"]), headers=auth)
    assert reused.json()["inserted_count"] == 0 and reused.json()["deduplicated_count"] == 2
    conflicting = copy.deepcopy(original["events"][0])
    conflicting["value"] = 999
    assert (await client.post(url, json=batch(metric(), conflicting), headers=auth)).json()["error"]["code"] == "event_conflict"
    assert await counts(db, run) == (2, 2, 2)
    late_equal = batch(metric(step=1, value=10), metric(step=5, value=55), metric(step=0, name="accuracy"))
    assert (await client.post(url, json=late_equal, headers=auth)).status_code == 200
    snapshot = (await client.get(f"/runs/{run}", headers=auth)).json()
    assert snapshot["last_seq"] == snapshot["event_count"] == 5
    assert [e["metric"] for e in snapshot["metrics"]] == ["accuracy", "loss"]
    assert snapshot["metrics"][1]["value"] == 55 and snapshot["metrics"][1]["seq"] == 4
    # Original retry still returns its old committed_seq, not the current run's.
    assert (await client.post(url, json=original, headers=auth)).json() == receipt.json()


async def test_concurrent_batches_and_event_retries(client, db):
    _, auth, run = await setup_run(client)
    url = f"/runs/{run}/metrics"
    original = batch(metric(), metric())
    results = await asyncio.gather(*(client.post(url, json=original, headers=auth) for _ in range(8)))
    assert all(r.status_code == 200 for r in results)
    assert all(r.json() == results[0].json() for r in results)
    assert await counts(db, run) == (2, 1, 2)
    shared = metric(step=3)
    results = await asyncio.gather(*(client.post(url, json=batch(shared, metric(step=i)), headers=auth) for i in range(8)))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    assert sum(r.json()["inserted_count"] for r in results) == 9
    async with db.sessions() as session:
        seqs = (await session.scalars(select(MetricEvent.seq).where(MetricEvent.run_id == UUID(run)).order_by(MetricEvent.seq))).all()
        assert list(seqs) == list(range(1, 12))
    assert await counts(db, run) == (11, 9, 11)


async def test_concurrent_conflicting_batch_and_event(client, db):
    _, auth, run = await setup_run(client)
    url = f"/runs/{run}/metrics"
    one = batch()
    two = copy.deepcopy(one)
    two["events"][0]["value"] = 2
    results = await asyncio.gather(*(client.post(url, json=b, headers=auth) for b in (one, two)))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert await counts(db, run) == (1, 1, 1)
    shared = str(uuid4())
    results = await asyncio.gather(*(client.post(url, json=batch(metric(event_id=shared, value=v)), headers=auth) for v in (4, 5)))
    assert sorted(r.status_code for r in results) == [200, 409]
    assert await counts(db, run) == (2, 2, 2)


@pytest.mark.parametrize("failure_stage", ["after_flush", "before_commit"])
async def test_failure_rolls_back_events_counter_and_receipt(client, db, failure_stage):
    _, auth, run = await setup_run(client)
    body = batch(metric(), metric())

    def fail(session, *args):
        if failure_stage == "before_commit" or any(isinstance(obj, Batch) for obj in session.new):
            raise RuntimeError("injected persistence failure")

    # after_flush observes inserted rows, changed counter and receipt in the same tx.
    target = AsyncSession.sync_session_class
    sa_event.listen(target, failure_stage, fail)
    try:
        response = await client.post(f"/runs/{run}/metrics", json=body, headers=auth)
    finally:
        sa_event.remove(target, failure_stage, fail)
    assert response.status_code == 500
    assert "injected" not in response.text
    assert await counts(db, run) == (0, 0, 0)
    assert (await client.post(f"/runs/{run}/metrics", json=body, headers=auth)).json()["committed_seq"] == 2


async def test_lost_receipt_survives_new_application_instance(client, db):
    from httpx import ASGITransport, AsyncClient
    from app.db import Database
    from app.main import create_app
    _, auth, run = await setup_run(client)
    body = batch()
    original = await client.post(f"/runs/{run}/metrics", json=body, headers=auth)
    # Simulate a lost response/new process state using an independent engine/app.
    other = Database(str(db.engine.url.render_as_string(hide_password=False)))
    try:
        async with AsyncClient(transport=ASGITransport(app=create_app(other)), base_url="http://new") as fresh:
            replay = await fresh.post(f"/runs/{run}/metrics", json=body, headers=auth)
        assert replay.json() == original.json() and await counts(db, run) == (1, 1, 1)
    finally:
        await other.engine.dispose()


async def test_snapshot_is_consistent_when_write_commits_between_queries(client, db, monkeypatch):
    _, auth, run = await setup_run(client)
    await client.post(f"/runs/{run}/metrics", json=batch(metric(value=1)), headers=auth)
    saved_scoped_run = services.scoped_run

    async def write_after_run_read(session, project_id, run_id, *, lock=False):
        result = await saved_scoped_run(session, project_id, run_id, lock=lock)
        if not lock:
            async with db.transaction() as writer:
                await services.ingest(writer, auth["Authorization"], run_id,
                                      BatchRequest.model_validate(batch(metric(step=10, value=10))))
        return result

    monkeypatch.setattr(services, "scoped_run", write_after_run_read)
    snapshot = (await client.get(f"/runs/{run}", headers=auth)).json()
    assert snapshot["last_seq"] == snapshot["event_count"] == 1
    assert snapshot["metrics"][0]["value"] == 1
    assert await counts(db, run) == (2, 2, 2)


async def test_metric_cap_and_retry_at_cursor_cap(client, db):
    _, auth, run = await setup_run(client)
    url = f"/runs/{run}/metrics"
    body = batch(*(metric(name=f"metric_{i}") for i in range(128)))
    receipt = await client.post(url, json=body, headers=auth)
    assert receipt.status_code == 200
    rejected = await client.post(url, json=batch(metric(name="one_more")), headers=auth)
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "metric_limit"
    assert await counts(db, run) == (128, 1, 128)
    async with db.engine.begin() as connection:
        await connection.execute(text("UPDATE runs SET last_seq=:seq WHERE id=:id"), {"seq": MAX_SEQ, "id": UUID(run)})
    assert (await client.post(url, json=body, headers=auth)).json() == receipt.json()
    response = await client.post(url, json=batch(metric(name="metric_0")), headers=auth)
    assert response.json()["error"]["code"] == "cursor_exhausted"


@pytest.mark.parametrize("field,value", [
    ("step", -1), ("step", True), ("step", "1"), ("step", 1.0), ("step", MAX_SEQ + 1),
    ("value", True), ("value", "1"), ("value", None),
    ("metric", "bad name"), ("metric", "a" * 65), ("metric", "1invalid"),
    ("event_id", "not-a-uuid"), ("event_id", "00000000-0000-0000-0000-000000000000"),
    ("occurred_at", "2026-02-30T00:00:00Z"), ("occurred_at", "2026-01-01T00:00:00+00:00"),
    ("occurred_at", "1999-12-31T23:59:59Z"), ("occurred_at", "2100-01-01T00:00:00Z"),
    ("occurred_at", "2026-01-01T00:00:00.0000001Z"), ("project_id", str(uuid4())),
])
async def test_invalid_event_is_atomic(client, db, field, value):
    _, auth, run = await setup_run(client)
    invalid = metric()
    invalid[field] = value
    response = await client.post(f"/runs/{run}/metrics", json=batch(metric(), invalid), headers=auth)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["message"] == "Request validation failed."
    assert await counts(db, run) == (0, 0, 0)


async def test_wire_limits_nonfinite_duplicate_keys_and_cors(client, db):
    _, auth, run = await setup_run(client)
    url = f"/runs/{run}/metrics"
    for events in ([], [metric()] * 2, [metric() for _ in range(251)]):
        assert (await client.post(url, json={"batch_id": str(uuid4()), "events": events}, headers=auth)).status_code == 422
    headers = {**auth, "Content-Type": "application/json"}
    for raw, status in [('NaN', 400), ('Infinity', 400), ('1e309', 422), ('1e-9999', 422)]:
        encoded = json.dumps(batch()).replace('1.0', raw)
        assert (await client.post(url, content=encoded, headers=headers)).status_code == status
    assert (await client.post("/projects", content='{"name":"a","name":"b"}', headers=headers)).status_code == 400
    assert (await client.post(url, content=b" " * (MAX_BODY + 1), headers=headers)).status_code == 413

    async def chunked():
        yield b" " * MAX_BODY
        yield b" "

    assert (await client.post(url, content=chunked(), headers=headers)).status_code == 413
    assert (await client.post(url, content="{}", headers=auth)).status_code == 415
    assert (await client.post(url, content="{}", headers={**headers, "Content-Encoding": "gzip"})).status_code == 415
    preflight = await client.options(url, headers={"Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Authorization, Last-Event-ID, Content-Type"})
    assert preflight.status_code == 200 and preflight.headers["access-control-allow-origin"] == "http://localhost:3000"
    error = await client.get("/runs", headers={"Origin": "http://localhost:3000"})
    assert error.status_code == 401 and error.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert error.headers["cache-control"] == "no-store"
    assert await counts(db, run) == (0, 0, 0)


async def wait_for_database_blocker(db, blocker_pid):
    """Wait for an observed PostgreSQL lock wait, not an arbitrary race sleep."""
    async with asyncio.timeout(1.5):
        while True:
            async with db.sessions() as observer:
                blocked = await observer.scalar(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                    "WHERE :blocker = ANY(pg_blocking_pids(pid)))"), {"blocker": blocker_pid})
            if blocked:
                return
            await asyncio.sleep(0.01)


async def test_rotation_revalidates_old_key_after_lock_wait(client, db):
    _, auth, run = await setup_run(client)
    pending = None
    try:
        async with db.transaction() as rotator:
            project = await services.authenticate(rotator, auth["Authorization"], lock="update")
            token, project.key_hash = services.new_key()
            project.key_version += 1
            await rotator.flush()
            pid = await rotator.scalar(text("SELECT pg_backend_pid()"))
            # Reader can find the old hash before rotation commits, then blocks.
            pending = asyncio.create_task(client.post(f"/runs/{run}/metrics", json=batch(), headers=auth))
            await wait_for_database_blocker(db, pid)
        denied = await pending
        assert denied.status_code == 401
        assert await counts(db, run) == (0, 0, 0)
        assert (await client.get(f"/runs/{run}", headers={"Authorization": "Bearer " + token})).status_code == 200
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)


async def test_inflight_write_commits_before_rotation(client, db):
    _, auth, run = await setup_run(client)
    pending = None
    try:
        async with db.transaction() as writer:
            await services.ingest(writer, auth["Authorization"], UUID(run), BatchRequest.model_validate(batch()))
            pid = await writer.scalar(text("SELECT pg_backend_pid()"))
            pending = asyncio.create_task(client.post("/projects/key/rotate", json={}, headers=auth))
            await wait_for_database_blocker(db, pid)
        rotation = await pending
        assert rotation.status_code == 200
        assert await counts(db, run) == (1, 1, 1)
        assert (await client.post(f"/runs/{run}/metrics", json=batch(), headers=auth)).status_code == 401
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)


async def test_lock_timeout_is_retryable_and_atomic(client, db):
    _, auth, run = await setup_run(client)
    body = batch(metric(), metric())
    async with db.sessions() as locker, locker.begin():
        await locker.scalar(select(Run).where(Run.id == UUID(run)).with_for_update())
        response = await client.post(f"/runs/{run}/metrics", json=body, headers=auth)
        assert response.status_code == 503 and response.headers["retry-after"] == "1"
    assert await counts(db, run) == (0, 0, 0)
    assert (await client.post(f"/runs/{run}/metrics", json=body, headers=auth)).json()["committed_seq"] == 2


async def test_concurrent_rotations_only_one_old_key_succeeds(client):
    _, auth, run = await setup_run(client)
    responses = await asyncio.gather(*(client.post("/projects/key/rotate", json={}, headers=auth) for _ in range(2)))
    assert sorted(r.status_code for r in responses) == [200, 401]
    rotated = next(r.json() for r in responses if r.status_code == 200)
    assert rotated["key_version"] == 2
    assert (await client.get(f"/runs/{run}", headers={"Authorization": "Bearer " + rotated["api_key"]})).status_code == 200


async def test_valid_boundaries_and_signed_zero_identity(client, db):
    _, auth, run = await setup_run(client)
    events = [metric(step=i) for i in range(250)]
    events[0].update(metric="a" * 64, step=MAX_SEQ, value=1e308, occurred_at="2000-01-01T00:00:00Z")
    events[1].update(value=-1e308, occurred_at="2099-12-31T23:59:59.999999Z")
    events[2]["value"] = -0.0
    body = batch(*events)
    response = await client.post(f"/runs/{run}/metrics", json=body, headers=auth)
    assert response.status_code == 200 and response.json()["inserted_count"] == 250
    body["events"][2]["value"] = 0
    assert (await client.post(f"/runs/{run}/metrics", json=body, headers=auth)).json() == response.json()
    assert await counts(db, run) == (250, 1, 250)
    # Exact byte limit accepted (JSON whitespace is legitimate); +1 tested above.
    encoded = b'{"name":"' + b"a" * 100 + b'"}'
    encoded += b" " * (MAX_BODY - len(encoded))
    assert (await client.post("/projects", content=encoded, headers={"Content-Type": "application/json"})).status_code == 201
