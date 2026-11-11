import asyncio
import json
import re
import subprocess

import httpx
from playwright.async_api import expect

from fault_server import serve
from fault_relay import FrameRelay, route_streams_through
from test_browser import API,WEB,create,connect,event,batch,send,check_sql_and_visible_points,browser_page


async def test_browser_real_tcp_partial_frame_then_complete_replay(browser_page):
    page,_=browser_page
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project,auth,run=await create(client,"Partial frame proof")
        await send(client,run,auth,batch([event(i) for i in range(1,12)]))
        relay=FrameRelay(API,run,cut_seq=11)
        async with serve(relay) as (_,port):
            await route_streams_through(page,port)
            await page.goto(WEB);await connect(page,project["api_key"])
            await page.get_by_role("link",name="Partial frame proof",exact=False).click()
            await asyncio.wait_for(relay.waiting.wait(),15)
            await expect(page.get_by_test_id("applied-cursor")).to_have_text("10")
            await expect(page.get_by_test_id("history-count")).to_have_text("10")
            await expect(page.get_by_test_id("connection-status")).to_have_text("reconnecting")
            assert relay.cursors[1]=="10"
            await send(client,run,auth,batch([event(i) for i in range(12,31)]))
            relay.gate.set()
            await expect(page.get_by_test_id("applied-cursor")).to_have_text("30")
            await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
            await check_sql_and_visible_points(page,run,30)
            print("PARTIAL FRAME: real server frame11 cut over TCP, browser retained10; replay11-30 -> exact SQL/UI points1-30 PASS")


async def test_browser_old_project_frame_cannot_apply_after_key_switch(browser_page):
    page,_=browser_page
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        a,auth_a,run_a=await create(client,"A private run")
        b,auth_b,run_b=await create(client,"B private run")
        await send(client,run_a,auth_a,batch([event(1)]))
        await send(client,run_b,auth_b,batch([event(1,0.77,"onlyB")]))
        relay=FrameRelay(API,run_a,hold_seq=2)
        async with serve(relay) as (_,port):
            await route_streams_through(page,port)
            await page.goto(WEB);await connect(page,a["api_key"])
            await page.get_by_role("link",name="A private run",exact=False).click()
            await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
            await send(client,run_a,auth_a,batch([event(2,123456.789,"onlyA")]))
            await asyncio.wait_for(relay.waiting.wait(),5)
            await page.get_by_role("button",name="Switch project / key").click()
            await connect(page,b["api_key"])
            await expect(page.get_by_role("link",name="B private run",exact=False)).to_be_visible()
            relay.gate.set()
            await page.get_by_role("link",name="B private run",exact=False).click()
            await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
            await expect(page.get_by_test_id("metric-onlyA")).to_have_count(0)
            await expect(page.get_by_test_id("latest-onlyB")).to_have_text("0.77")
            await check_sql_and_visible_points(page,run_b,1)
            assert not await page.evaluate("Object.keys(localStorage).length+Object.keys(sessionStorage).length")
            cookies=json.dumps(await page.context.cookies())
            assert all(secret not in cookies for secret in (a["api_key"],b["api_key"]))
            print("SESSION ISOLATION: buffered real A frame released after switch to B, no A state/points/storage/cookie leak PASS")


async def test_browser_concurrent_unordered_duplicate_events_and_live_rotation(browser_page):
    page,_=browser_page
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project,auth,run=await create(client,"Concurrent proof")
        await page.goto(WEB);await connect(page,project["api_key"])
        await page.get_by_role("link",name="Concurrent proof",exact=False).click()
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        shared=event(4,0.4)
        bodies=[batch([shared,event(step,step/10)]) for step in (9,2,7,1,9,4,0,6)]
        responses=await asyncio.gather(*(client.post(f"/runs/{run}/metrics",json=body,headers=auth) for body in bodies))
        assert all(r.status_code==200 for r in responses)
        await expect(page.get_by_test_id("applied-cursor")).to_have_text("9")
        await check_sql_and_visible_points(page,run,9)
        # Reuse every original receipt from overlapping writes, no UI duplication.
        for body,original in zip(bodies,responses):assert await send(client,run,auth,body)==original.json()
        await check_sql_and_visible_points(page,run,9)
        assert (await client.post("/projects/key/rotate",headers=auth,json={})).status_code==200
        await expect(page.get_by_test_id("connection-status")).to_have_text("error")
        assert (await client.post(f"/runs/{run}/metrics",headers=auth,json=batch([event(100)]))).status_code==401
        await expect(page.get_by_test_id("event-count")).to_have_text("9")
        print("CONCURRENT UI: overlapping duplicate events/out-of-order/equal steps, exact rows/seq/points vs SQL, old-key write denied/live revoked PASS")


async def test_browser_postgres_stop_start_recovery_and_retry(browser_page):
    page,_=browser_page
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project,auth,run=await create(client,"Database outage")
        await send(client,run,auth,batch([event(i) for i in range(1,11)]))
        await page.goto(WEB);await connect(page,project["api_key"])
        await page.get_by_role("link",name="Database outage",exact=False).click()
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        payload=batch([event(i) for i in range(11,21)])
        try:
            result=await asyncio.to_thread(subprocess.run,["docker","compose","stop","-t","1","db"],capture_output=True,text=True)
            assert result.returncode==0
            await expect(page.get_by_test_id("connection-status")).to_have_text("reconnecting")
            response=await client.post(f"/runs/{run}/metrics",headers=auth,json=payload)
            assert response.status_code==503, f"PostgreSQL outage returned {response.status_code}, expected retryable503"
        finally:
            result=await asyncio.to_thread(subprocess.run,["docker","compose","start","db"],capture_output=True,text=True)
            assert result.returncode==0
            async with asyncio.timeout(30):
                while True:
                    try:
                        if (await client.get("/health")).status_code==200:break
                    except httpx.TransportError:pass
                    await asyncio.sleep(0.25)
        await send(client,run,auth,payload)
        await expect(page.get_by_test_id("applied-cursor")).to_have_text("20",timeout=20000)
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        await check_sql_and_visible_points(page,run,20)
        print("DB OUTAGE: actual Compose PostgreSQL stop/start, stream stale, failed ingress503, identical retry -> SQL/UI1-20 PASS")


async def test_runtime_error_privacy_and_actual_docker_logs():
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project,auth,run=await create(client,"Privacy canary")
        invalid=event(1);invalid["value"]=project["api_key"]
        response=await client.post(f"/runs/{run}/metrics",headers=auth,json=batch([invalid]))
        assert response.status_code==422 and response.headers["cache-control"]=="no-store"
        assert bool(project["api_key"] not in response.text), "Validation response echoed credential"
        for path in ("/",f"/runs/{run}"):
            html=(await client.get(WEB+path)).text
            assert bool(project["api_key"] not in html), "Server HTML contained credential"
        result=await asyncio.to_thread(subprocess.run,["docker","compose","logs","--no-color","--since","5m","api","web","db"],capture_output=True,text=True)
        assert result.returncode==0
        logs=result.stdout+result.stderr
        assert not re.search(r"soup_[A-Za-z0-9_-]{43}",logs), "Token-shaped value found in runtime logs (value not printed)"
        print(f"LOG PRIVACY: actual API/web/DB Docker logs inspected ({len(logs.encode())} bytes), token-pattern matches0; invalid-body/SSR key echo absent PASS")
