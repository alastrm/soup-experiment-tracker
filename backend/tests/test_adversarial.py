"""Real PostgreSQL faults and real HTTP; never target the demo database."""
import asyncio
import io
import json
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import event, select, text

from app import services
from app.main import create_app
from app.db import Database
from app.models import Batch, Project
from app.schemas import BatchRequest
from app.stream import DurableSSE, StreamSlots
from test_backend import batch, counts, metric, setup_run
from test_stream import live_api, frames_until
from fault_server import serve, DropReceipt, SmallSocketBuffers, resident_bytes


async def test_backend_connection_dies_after_real_metric_insert(client, db):
    _, auth, run = await setup_run(client)
    body = batch(metric(), metric())
    fired = False

    def kill_after_insert(connection, cursor, statement, parameters, context, many):
        nonlocal fired
        if statement.startswith("INSERT INTO metric_events") and not fired:
            fired = True
            pid = connection.connection.dbapi_connection.driver_connection.get_server_pid()
            async def kill(_):
                async with db.engine.connect() as admin:
                    assert await admin.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid":pid})
            connection.connection.dbapi_connection.run_async(kill)

    event.listen(db.engine.sync_engine,"after_cursor_execute",kill_after_insert)
    try:
        result = await client.post(f"/runs/{run}/metrics",headers=auth,json=body)
    finally:
        event.remove(db.engine.sync_engine,"after_cursor_execute",kill_after_insert)
    assert fired and result.status_code == 503
    assert await counts(db,run) == (0,0,0)
    retry = await client.post(f"/runs/{run}/metrics",headers=auth,json=body)
    assert retry.status_code == 200 and await counts(db,run) == (2,1,2)


async def test_postgres_rejects_actual_commit_and_rolls_everything_back(client, db):
    _, auth, run = await setup_run(client)
    async with db.engine.begin() as c:
        await c.execute(text("""CREATE FUNCTION phase4_reject_commit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'private_commit_sentinel' USING ERRCODE='23514'; END $$"""))
        await c.execute(text("""CREATE CONSTRAINT TRIGGER phase4_reject_commit AFTER INSERT ON batches
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION phase4_reject_commit()"""))
    try:
        result = await client.post(f"/runs/{run}/metrics",headers=auth,json=batch(metric(),metric()))
        assert result.status_code == 500 and "sentinel" not in result.text
        assert await counts(db,run) == (0,0,0)
    finally:
        async with db.engine.begin() as c:
            await c.execute(text("DROP TRIGGER phase4_reject_commit ON batches"))
            await c.execute(text("DROP FUNCTION phase4_reject_commit()"))
    assert (await client.post(f"/runs/{run}/metrics",headers=auth,json=batch())).status_code == 200


async def test_cancellation_after_flush_releases_locks_and_rolls_back(client, db):
    _, auth, run = await setup_run(client)
    flushed = asyncio.Event(); body = BatchRequest.model_validate(batch(metric(),metric()))
    async def operation():
        async with db.transaction() as session:
            await services.ingest(session,auth["Authorization"],UUID(run),body)
            flushed.set()
            await session.execute(text("SELECT pg_sleep(30)"))
    task = asyncio.create_task(operation())
    await asyncio.wait_for(flushed.wait(),2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert await counts(db,run) == (0,0,0)
    assert db.engine.pool.checkedout() == 0
    assert (await client.post(f"/runs/{run}/metrics",headers=auth,json=body.model_dump(mode="json"))).status_code == 200


async def test_replay_database_error_closes_stream_then_recovers(live_api, db):
    client, app = live_api
    _, auth, run = await setup_run(client)
    await client.post(f"/runs/{run}/metrics",headers=auth,json=batch())
    async with client.stream("GET",f"/runs/{run}/events",headers=auth) as response:
        lines = response.aiter_lines(); await frames_until(response,lines=lines)
        # ACCESS EXCLUSIVE blocks both replay and watcher; watchdog must fail closed.
        async with db.sessions() as blocker, blocker.begin():
            await blocker.execute(text("LOCK TABLE projects, metric_events IN ACCESS EXCLUSIVE MODE"))
            async with asyncio.timeout(3):
                remaining = [line async for line in lines]
            assert not any(line.startswith("id: ") for line in remaining)
    async with asyncio.timeout(2):
        while app.state.streams.active: await asyncio.sleep(0.01)
    await client.post(f"/runs/{run}/metrics",headers=auth,json=batch(metric(step=2)))
    async with client.stream("GET",f"/runs/{run}/events",headers={**auth,"Last-Event-ID":"1"}) as response:
        frames = await frames_until(response)
    assert [seq for kind,seq,_ in frames if kind=="metric"] == [2]


async def test_revocation_still_works_when_replay_is_blocked(live_api, db):
    client, app = live_api
    _, auth, run = await setup_run(client)
    async with client.stream("GET",f"/runs/{run}/events",headers=auth) as response:
        lines=response.aiter_lines(); await frames_until(response,lines=lines)
        async with db.sessions() as blocker, blocker.begin():
            await blocker.execute(text("LOCK TABLE metric_events IN ACCESS EXCLUSIVE MODE"))
            assert (await client.post("/projects/key/rotate",headers=auth,json={})).status_code == 200
            async with asyncio.timeout(2.5):
                frames=await frames_until(response,"auth_expired",lines=lines)
            assert frames[-1][0] == "auth_expired"
    assert (await client.get(f"/runs/{run}/events",headers=auth)).status_code == 401


async def test_exhausted_pool_fails_stream_closed(client, db):
    _, auth, run = await setup_run(client)
    async with db.transaction() as s: project=await services.authenticate(s,auth["Authorization"])
    slots=StreamSlots(); connections=[]
    try:
        for _ in range(20): connections.append(await db.engine.connect())
        messages=[]
        async def send(message): messages.append(message)
        async def receive(): await asyncio.Event().wait()
        async with asyncio.timeout(3):
            await DurableSSE(db,slots,project,UUID(run),0)({"type":"http"},receive,send)
        assert slots.active==0 and not any(b"id:" in m.get("body",b"") for m in messages)
    finally:
        for c in connections: await c.close()
    assert db.engine.pool.checkedout()==0


async def test_failed_send_is_not_attempted_a_second_time(client, db):
    _, auth, run = await setup_run(client)
    await client.post(f"/runs/{run}/metrics",headers=auth,json=batch())
    async with db.transaction() as s: project=await services.authenticate(s,auth["Authorization"])
    slots=StreamSlots(); response=DurableSSE(db,slots,project,UUID(run),0)
    response.send_timeout=0.05; attempts=0
    async def send(message):
        nonlocal attempts
        if message["type"]=="http.response.body":
            attempts+=1; await asyncio.Event().wait()
    async def receive(): await asyncio.Event().wait()
    await asyncio.wait_for(response({"type":"http"},receive,send),1)
    assert attempts==1, "A timed-out transport must be closed, not re-entered for EOF"
    assert slots.active==0


async def test_error_headers_and_foreign_id_timing_probe(live_api, caplog):
    client, _ = live_api
    _, auth, _ = await setup_run(client,"A")
    other, other_auth, run_b = await setup_run(client,"B")
    await client.post(f"/runs/{run_b}/metrics",headers=other_auth,json=batch())
    timings={"foreign":[],"missing":[]}
    caplog.set_level(logging.WARNING)
    for suffix, method, kwargs in [("","get",{}),("/metrics","post",{"json":batch()}),("/events","get",{})]:
        samples={}
        for label, identity in [("foreign",run_b),("missing",str(uuid4()))]:
            for _ in range(4):
                start=time.perf_counter()
                response=await getattr(client,method)(f"/runs/{identity}{suffix}",headers=auth,**kwargs)
                timings[label].append((time.perf_counter()-start)*1000)
                assert response.status_code==404
                policy={k:response.headers.get(k) for k in ("content-type","cache-control","vary","content-length")}
                samples[label]=(response.content,policy)
        assert samples["foreign"]==samples["missing"]
    assert all(secret not in caplog.text for secret in [other["api_key"],auth["Authorization"][7:]])
    for label,values in timings.items():
        print(f"SECURITY timing probe {label}: n={len(values)}, min_ms={min(values):.3f}, max_ms={max(values):.3f}, mean_ms={sum(values)/len(values):.3f}; no constant-time claim")


async def test_two_api_processes_share_only_postgres_for_ordering(database_url, db):
    processes=[]; clients=[]
    try:
        for _ in range(2):
            with socket.socket() as sock:
                sock.bind(("127.0.0.1",0)); port=sock.getsockname()[1]
            process=subprocess.Popen([sys.executable,"-m","uvicorn","app.main:create_app","--factory",
                "--host","127.0.0.1","--port",str(port),"--no-access-log","--log-level","critical"],
                cwd=Path(__file__).resolve().parents[1],env={**os.environ,"DATABASE_URL":database_url},
                stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            processes.append(process)
            c=httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}",timeout=7);clients.append(c)
            async with asyncio.timeout(10):
                while True:
                    try:
                        if (await c.get("/health")).status_code==200: break
                    except httpx.TransportError: pass
                    await asyncio.sleep(0.05)
        _, auth, run=await setup_run(clients[0])
        shared=metric(step=3,value=42)
        payloads=[batch(shared,metric(step=8-i,value=i)) for i in range(8)]
        responses=await asyncio.gather(*(clients[i%2].post(f"/runs/{run}/metrics",headers=auth,json=b) for i,b in enumerate(payloads)))
        assert all(r.status_code==200 for r in responses)
        assert sum(r.json()["inserted_count"] for r in responses)==9
        async with db.sessions() as s:
            rows=(await s.execute(text("SELECT seq,event_id FROM metric_events WHERE run_id=:id ORDER BY seq"),{"id":UUID(run)})).all()
        assert [r.seq for r in rows]==list(range(1,10)) and len({r.event_id for r in rows})==9
        retry=await clients[1].post(f"/runs/{run}/metrics",headers=auth,json=payloads[0])
        assert retry.json()==responses[0].json()
        print("MULTIPROCESS: two independent Uvicorn processes, concurrent overlapping batches, gapless seq1-9 and original receipt PASS")
    finally:
        for c in clients: await c.aclose()
        for p in processes:
            p.terminate()
            await asyncio.to_thread(p.communicate,timeout=5)


async def test_real_lost_http_receipt_after_commit_then_new_app_retry(db):
    dropping=DropReceipt(create_app(db))
    async with serve(dropping) as (client,_):
        _,auth,run=await setup_run(client)
        body=batch(metric(),metric())
        with pytest.raises(httpx.TransportError):
            await client.post(f"/runs/{run}/metrics",headers=auth,json=body)
    assert dropping.dropped and await counts(db,run)==(2,1,2)
    async with db.sessions() as s:
        original=await s.scalar(select(Batch.receipt).where(Batch.run_id==UUID(run)))
    async with serve(create_app(db)) as (fresh,_):
        retry=await fresh.post(f"/runs/{run}/metrics",headers=auth,json=body)
        assert retry.status_code==200 and retry.json()==original
    assert await counts(db,run)==(2,1,2)


async def test_real_tcp_slow_reader_buffers_deadline_and_complete_replay(db):
    app=create_app(db); observed=SmallSocketBuffers(app)
    async with serve(observed) as (client,port):
        _,auth,run=await setup_run(client)
        for _ in range(4):
            assert (await client.post(f"/runs/{run}/metrics",headers=auth,json=batch(*(metric() for _ in range(250))))).status_code==200
        sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,1024);sock.setblocking(False)
        await asyncio.get_running_loop().sock_connect(sock,("127.0.0.1",port))
        reader,writer=await asyncio.open_connection(sock=sock,limit=1024)
        try:
            writer.write((f"GET /runs/{run}/events HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: {auth['Authorization']}\r\n\r\n").encode())
            await writer.drain();response_headers=await reader.readuntil(b"\r\n\r\n")
            assert response_headers.startswith(b"HTTP/1.1 200") and b"text/event-stream" in response_headers
            # Deliberately never read SSE bytes. Observe real Uvicorn/OS pressure.
            start=time.monotonic(); saw_pressure=False
            baseline=resident_bytes(); peak=baseline
            async with asyncio.timeout(7):
                while app.state.streams.active:
                    size=observed.transport.get_write_buffer_size()
                    observed.maximum=max(observed.maximum,size)
                    peak=max(peak,resident_bytes())
                    saw_pressure |= size>4096
                    await asyncio.sleep(0.02)
            elapsed=time.monotonic()-start
            print(f"TCP diagnostic: elapsed={elapsed:.3f}s, maximum_buffer={observed.maximum}B, polled_pressure={saw_pressure}, slots={app.state.streams.active}")
            saw_pressure |= observed.maximum>4096
            assert saw_pressure, "Test did not actually exercise socket backpressure"
            assert observed.maximum<=8192
            assert peak-baseline < 32*1024*1024
            print(f"SLOW TCP: one unread subscriber, server high-water4096B, max_observed_buffer={observed.maximum}B, cleanup_seconds={elapsed:.3f}, RSS_baseline={baseline}B, RSS_peak={peak}B; fixture1000 events, not a throughput/load test")
        finally:
            writer.close();await writer.wait_closed()
        assert db.engine.pool.checkedout()==0
        # None of those bytes were applied: recover every persisted event from0.
        async with client.stream("GET",f"/runs/{run}/events",headers={**auth,"Last-Event-ID":"0"}) as response:
            frames=await frames_until(response)
        assert [seq for kind,seq,_ in frames if kind=="metric"]==list(range(1,1001))


async def test_real_http_admission_overflow_and_slot_reuse(live_api):
    from contextlib import AsyncExitStack
    client,app=live_api
    _,auth,run=await setup_run(client)
    assert app.state.streams.limit==100
    app.state.streams.limit=2  # Scale threshold, not the exercised HTTP branch.
    async with AsyncExitStack() as stack:
        responses=[]
        for _ in range(2):
            r=await stack.enter_async_context(client.stream("GET",f"/runs/{run}/events",headers=auth))
            lines=r.aiter_lines()
            assert r.status_code==200;await frames_until(r,lines=lines);responses.append((r,lines))
        excess=await client.get(f"/runs/{run}/events",headers=auth)
        assert excess.status_code==503 and excess.headers["retry-after"]=="1"
        await responses[0][0].aclose()
        async with asyncio.timeout(2):
            while app.state.streams.active!=1: await asyncio.sleep(0.01)
        async with client.stream("GET",f"/runs/{run}/events",headers=auth) as response:
            assert response.status_code==200;await frames_until(response)


async def test_postgres_unreachable_is_retryable_not_internal_error(database_url):
    from sqlalchemy.engine import make_url
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0)); port=sock.getsockname()[1]
    unavailable=Database(make_url(database_url).set(host="127.0.0.1",port=port).render_as_string(hide_password=False))
    try:
        async with serve(create_app(unavailable)) as (client,_):
            r=await client.post("/projects",json={"name":"outage"})
            assert r.status_code==503 and r.headers.get("retry-after")=="1"
            assert "127.0.0.1" not in r.text and "password" not in r.text
    finally:
        await unavailable.engine.dispose()


async def test_canonical_identity_ignores_json_object_order_and_spacing(client,db):
    _,auth,run=await setup_run(client)
    body=batch(metric(value=1))
    first=await client.post(f"/runs/{run}/metrics",headers=auth,json=body)
    reformatted=json.dumps(body,sort_keys=True,indent=3).replace('"value": 1','"value": 1.0')
    retry=await client.post(f"/runs/{run}/metrics",headers={**auth,"Content-Type":"application/json"},content=reformatted)
    assert first.status_code==retry.status_code==200 and first.json()==retry.json()
    assert await counts(db,run)==(1,1,1)


async def test_rotation_cannot_target_another_project_in_body_or_query(live_api,db):
    client,_=live_api
    a,auth_a,run_a=await setup_run(client,"A")
    b,auth_b,run_b=await setup_run(client,"B")
    invalid=await client.post("/projects/key/rotate",headers=auth_a,json={"project_id":b["project"]["id"]})
    assert invalid.status_code==422
    rotated=await client.post("/projects/key/rotate?project_id="+b["project"]["id"],headers=auth_a,json={})
    assert rotated.status_code==200
    assert (await client.get(f"/runs/{run_a}",headers=auth_a)).status_code==401
    assert (await client.get(f"/runs/{run_b}",headers=auth_b)).status_code==200
    async with db.sessions() as session:
        assert (await session.get(Project,UUID(b["project"]["id"]))).key_version==1


async def test_cors_denial_and_preflight_do_not_enumerate_runs(live_api):
    client,_=live_api
    _,auth,run=await setup_run(client)
    for identity in (run,str(uuid4())):
        denied=await client.options(f"/runs/{identity}/events",headers={"Origin":"https://untrusted.example",
            "Access-Control-Request-Method":"GET","Access-Control-Request-Headers":"Authorization, Last-Event-ID"})
        assert denied.status_code==400 and "access-control-allow-origin" not in denied.headers
        allowed=await client.options(f"/runs/{identity}/events",headers={"Origin":"http://localhost:3000",
            "Access-Control-Request-Method":"GET","Access-Control-Request-Headers":"Authorization, Last-Event-ID"})
        assert allowed.status_code==200 and allowed.headers["access-control-allow-origin"]=="http://localhost:3000"
        assert allowed.headers["cache-control"]=="no-store"
