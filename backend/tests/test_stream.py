import asyncio
import json
import socket
from uuid import UUID, uuid4

import httpx
import pytest_asyncio
import uvicorn

from app.main import create_app
from app.schemas import MAX_SEQ
from app.stream import DurableSSE
from test_backend import batch, metric, setup_run


@pytest_asyncio.fixture
async def live_api(db):
    app = create_app(db)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.setblocking(False)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="critical", timeout_graceful_shutdown=0.5))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    async with asyncio.timeout(5):
        while not server.started:
            await asyncio.sleep(0.01)
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=5) as client:
        yield client, app
    server.should_exit = True
    await asyncio.wait_for(task, 3)


async def frames_until(response, event_type="caught_up", lines=None):
    event, data, event_id = "", [], None
    frames = []
    async for line in (lines if lines is not None else response.aiter_lines()):
        if line.startswith("event: "):
            event = line[7:]
        elif line.startswith("id: "):
            event_id = int(line[4:])
        elif line.startswith("data: "):
            data.append(line[6:])
        elif not line and data:
            frames.append((event, event_id, json.loads("\n".join(data))))
            if event == event_type:
                return frames
            event, data, event_id = "", [], None
    return frames


async def test_sse_auth_scope_and_cursor_preflight(live_api):
    client, _ = live_api
    _, a, run = await setup_run(client, "A")
    _, b, _ = await setup_run(client, "B")
    assert (await client.get(f"/runs/{run}/events")).status_code == 401
    foreign = await client.get(f"/runs/{run}/events", headers=b)
    missing = await client.get(f"/runs/{uuid4()}/events", headers=b)
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()
    for cursor in ("-1", "01", "bad", str(MAX_SEQ + 1), ""):
        assert (await client.get(f"/runs/{run}/events", headers={**a,"Last-Event-ID":cursor})).status_code == 422
    assert (await client.get(f"/runs/{run}/events", headers={**a,"Last-Event-ID":"1"})).status_code == 409


async def test_exact_1_to_10_disconnect_then_replay_11_to_30(live_api):
    client, app = live_api
    _, auth, run = await setup_run(client)
    body = batch(*(metric(step=i) for i in range(1,11)))
    assert (await client.post(f"/runs/{run}/metrics", headers=auth, json=body)).status_code == 200
    async with client.stream("GET", f"/runs/{run}/events", headers=auth) as response:
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store, no-transform"
        first = await frames_until(response)
    assert [seq for event,seq,_ in first if event=="metric"] == list(range(1,11))
    await client.post(f"/runs/{run}/metrics", headers=auth, json=batch(*(metric(step=i) for i in range(11,31))))
    # Duplicate retry is not a new event or a new stream ID.
    await client.post(f"/runs/{run}/metrics", headers=auth, json=body)
    async with client.stream("GET", f"/runs/{run}/events", headers={**auth,"Last-Event-ID":"10"}) as response:
        second = await frames_until(response)
    assert [seq for event,seq,_ in second if event=="metric"] == list(range(11,31))
    async with asyncio.timeout(2):
        while app.state.streams.active:
            await asyncio.sleep(0.01)
    assert app.state.db.engine.pool.checkedout() == 0


async def test_snapshot_gap_and_replay_across_pages(live_api):
    client, _ = live_api
    _, auth, run = await setup_run(client)
    snapshot = (await client.get(f"/runs/{run}", headers=auth)).json()
    for start in (0,150):
        assert (await client.post(f"/runs/{run}/metrics", headers=auth,
            json=batch(*(metric(step=i) for i in range(start,start+150))))).status_code == 200
    async with client.stream("GET", f"/runs/{run}/events", headers={**auth,"Last-Event-ID":str(snapshot["last_seq"])}) as response:
        frames = await frames_until(response)
    assert [seq for event,seq,_ in frames if event=="metric"] == list(range(1,301))


async def test_rotation_terminates_existing_idle_stream(live_api):
    client, _ = live_api
    _, auth, run = await setup_run(client)
    async with client.stream("GET", f"/runs/{run}/events", headers=auth) as response:
        lines = response.aiter_lines()
        await frames_until(response, lines=lines)
        loop = asyncio.get_running_loop()
        rotation = await client.post("/projects/key/rotate", json={}, headers=auth)
        start = loop.time()
        async with asyncio.timeout(2.5):
            terminal = await frames_until(response,"auth_expired",lines=lines)
        assert terminal[-1][0] == "auth_expired" and loop.time()-start < 2.5
    assert (await client.get(f"/runs/{run}/events", headers=auth)).status_code == 401
    fresh = {"Authorization":"Bearer "+rotation.json()["api_key"]}
    async with client.stream("GET", f"/runs/{run}/events", headers=fresh) as response:
        assert response.status_code == 200
        await frames_until(response)


async def test_transport_send_deadline_and_admission_cleanup(client, db, monkeypatch):
    from app import services
    from app.stream import StreamSlots
    _, auth, run = await setup_run(client)
    await client.post(f"/runs/{run}/metrics",json=batch(),headers=auth)
    async with db.transaction() as session:
        project = await services.authenticate(session,auth["Authorization"])
    slots = StreamSlots()
    response = DurableSSE(db,slots,project,UUID(run),0)
    monkeypatch.setattr(response,"send_timeout",0.05)
    async def send(message):
        if message["type"]=="http.response.body":
            await asyncio.Event().wait()  # Real awaited ASGI-send stall, no queue.
    async def receive():
        await asyncio.Event().wait()
    async with asyncio.timeout(1):
        await response({"type":"http"},receive,send)
    assert slots.active == 0 and db.engine.pool.checkedout() == 0
    slots.active = slots.limit
    messages = []
    async def collect(message): messages.append(message)
    await DurableSSE(db,slots,project,UUID(run),0)({"type":"http"},receive,collect)
    assert messages[0]["status"] == 503 and slots.active == slots.limit


async def test_watchdog_revokes_during_backlog_blocked_send(client, db):
    from app import services
    from app.stream import StreamSlots
    _, auth, run = await setup_run(client)
    await client.post(f"/runs/{run}/metrics",json=batch(*(metric() for _ in range(250))),headers=auth)
    async with db.transaction() as session:
        project = await services.authenticate(session,auth["Authorization"])
    slots = StreamSlots(); blocked = asyncio.Event()
    async def send(message):
        if message["type"]=="http.response.body" and message.get("more_body"):
            blocked.set();await asyncio.Event().wait()
    async def receive(): await asyncio.Event().wait()
    task = asyncio.create_task(DurableSSE(db,slots,project,UUID(run),0)({"type":"http"},receive,send))
    await asyncio.wait_for(blocked.wait(),2)
    await client.post("/projects/key/rotate",json={},headers=auth)
    await asyncio.wait_for(task,2.5)
    assert slots.active == 0 and db.engine.pool.checkedout() == 0
