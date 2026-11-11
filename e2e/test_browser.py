"""Real Chromium + Next.js + FastAPI + independent SQL, no mocked responses."""
import asyncio
import json
import math
import os
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright, expect

API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
WEB = os.getenv("WEB_BASE_URL", "http://localhost:3000")
DSN = os.getenv("DATABASE_URL", "postgresql://soup:soup_local_only@127.0.0.1:54329/soup").replace("postgresql+asyncpg://","postgresql://")
ARTIFACTS = Path(os.getenv("SCREENSHOT_DIR", "artifacts/screenshots"))


def event(step, value=None, metric="loss"):
    return {"event_id":str(uuid4()),"metric":metric,"step":step,"value":value if value is not None else round(1/(step+1),4),"occurred_at":"2026-01-01T00:00:00Z"}


def batch(events): return {"batch_id":str(uuid4()),"events":events}


@pytest_asyncio.fixture
async def browser_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width":1440,"height":1050}, color_scheme="dark")
        page = await context.new_page()
        page.set_default_timeout(15000)
        yield page, context
        await context.close()
        await browser.close()


async def create(client, name):
    response = await client.post("/projects",json={"name":"E2E project"})
    assert response.status_code == 201
    project = response.json()
    auth = {"Authorization":"Bearer "+project["api_key"]}
    response = await client.post("/runs",json={"name":name},headers=auth)
    assert response.status_code == 201
    return project, auth, response.json()["id"]


async def connect(page, key):
    await page.get_by_label("Project API key",exact=True).fill(key)
    await page.get_by_role("button",name="Connect project",exact=False).click()


async def test_empty_run_demo_button_populates_real_metrics(browser_page):
    page, _ = browser_page
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project, auth, run = await create(client,"Empty run preview")
        await page.goto(WEB);await connect(page,project["api_key"])
        await page.get_by_role("link",name="Empty run preview",exact=False).click()
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        await page.get_by_role("button",name="Send demo metrics",exact=True).click()
        await expect(page.get_by_test_id("event-count")).to_have_text("40")
        await check_sql_and_visible_points(page,run,40)
        await expect(page.get_by_test_id("chart-demo.loss").locator("circle")).to_have_count(20)
        await expect(page.get_by_test_id("chart-demo.accuracy").locator("circle")).to_have_count(20)
        assert (await client.get(f"/runs/{run}",headers=auth)).json()["event_count"] == 40
        print("EMPTY RUN demo button:40 real persisted events,2 live charts, independent SQL/UI agreement PASS")


async def send(client, run, auth, payload):
    response = await client.post(f"/runs/{run}/metrics",json=payload,headers=auth)
    assert response.status_code == 200
    return response.json()


async def check_sql_and_visible_points(page, run, expected_count):
    connection = await asyncpg.connect(DSN)
    try:
        rows = await connection.fetch("SELECT metric,step,value,seq FROM metric_events WHERE run_id=$1 ORDER BY seq",UUID(run))
    finally:
        await connection.close()
    assert len(rows) == expected_count
    assert [r["seq"] for r in rows] == list(range(1,expected_count+1))
    await expect(page.get_by_test_id("event-count")).to_have_text(str(expected_count))
    await expect(page.get_by_test_id("applied-cursor")).to_have_text(str(expected_count))
    await expect(page.get_by_test_id("history-count")).to_have_text(str(expected_count))
    for metric in sorted({r["metric"] for r in rows}):
        oracle = {}
        for row in rows:
            if row["metric"]==metric:
                oracle[row["step"]] = row
        points = sorted(oracle.values(),key=lambda r:r["step"])
        circles = page.get_by_test_id("chart-"+metric).locator("circle")
        await expect(circles).to_have_count(len(points))
        visible = await circles.evaluate_all("nodes=>nodes.map(n=>({seq:Number(n.dataset.seq),step:Number(n.dataset.step),value:Number(n.dataset.value)}))")
        assert visible == [{k:r[k] for k in ("seq","step","value")} for r in points]
    await page.get_by_text("Inspect recovered events",exact=False).click()
    await expect(page.get_by_test_id("history-row")).to_have_count(expected_count)
    visible_seqs = await page.get_by_test_id("history-row").locator("td:first-child").all_text_contents()
    assert [int(s) for s in visible_seqs] == list(range(1,expected_count+1))
    await page.get_by_text("Inspect recovered events",exact=False).click()


async def test_browser_exact_recovery_duplicates_late_events_rotation_and_switch(browser_page):
    page, _ = browser_page
    cursors = []
    page.on("request",lambda request: cursors.append(request.headers.get("last-event-id")) if request.url.endswith("/events") else None)
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project, auth, run = await create(client,"Recovery proof 1-30")
        first = batch([event(i) for i in range(1,11)])
        await send(client,run,auth,first)
        await page.goto(WEB)
        await connect(page,project["api_key"])
        await page.get_by_role("link",name="Recovery proof 1-30",exact=False).click()
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        await check_sql_and_visible_points(page,run,10)
        await page.get_by_role("button",name="Disconnect",exact=True).click()
        await expect(page.get_by_test_id("connection-status")).to_have_text("disconnected")
        await expect(page.get_by_test_id("history-count")).to_have_text("10")
        missed = batch([event(i) for i in range(11,31)])
        receipt = await send(client,run,auth,missed)
        assert await send(client,run,auth,missed) == receipt
        # Force one legitimate repeated event from the actual endpoint. Browser
        # requests its applied cursor10; interceptor asks server for9 once.
        repeated = False
        async def repeat_one(route):
            nonlocal repeated
            headers = dict(route.request.headers)
            if not repeated and headers.get("last-event-id")=="10":
                repeated = True;headers["last-event-id"]="9"
            await route.continue_(headers=headers)
        await page.route("**/events",repeat_one)
        await page.get_by_role("button",name="Reconnect",exact=True).click()
        await expect(page.get_by_test_id("event-count")).to_have_text("30")
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        assert "10" in cursors and repeated
        await check_sql_and_visible_points(page,run,30)
        await page.unroute("**/events",repeat_one)
        await send(client,run,auth,batch([event(3,-0.2),event(30,0.02),event(1,0.9,"accuracy")]))
        await expect(page.get_by_test_id("event-count")).to_have_text("33")
        await check_sql_and_visible_points(page,run,33)
        await expect(page.get_by_test_id("latest-loss")).to_have_text("0.02")
        assert await page.evaluate("Object.keys(localStorage).length+Object.keys(sessionStorage).length") == 0
        async with httpx.AsyncClient() as public:
            html = (await public.get(WEB+f"/runs/{run}")).text
        assert project["api_key"] not in html
        rotated = await client.post("/projects/key/rotate",headers=auth,json={})
        assert rotated.status_code == 200
        await expect(page.get_by_test_id("connection-status")).to_have_text("error")
        await expect(page.get_by_role("alert").filter(has_text="expired")).to_be_visible()
        other, other_auth, other_run = await create(client,"Project B only")
        await page.get_by_role("button",name="Switch project / key").click()
        await connect(page,other["api_key"])
        await page.goto(WEB)  # reload must clear ephemeral access and data
        await expect(page.get_by_label("Project API key",exact=True)).to_be_visible()
        await connect(page,other["api_key"])
        await expect(page.get_by_role("link",name="Project B only",exact=False)).to_be_visible()
        await expect(page.get_by_role("link",name="Recovery proof 1-30",exact=False)).to_have_count(0)
        assert (await client.get(f"/runs/{run}/events",headers=other_auth)).status_code == 404
        print("BROWSER proof: applied1-10, disconnected, stored11-30, resumed cursor10 (forced duplicate10), applied exact1-30; late/equal-step SQL/UI agreement; live rotation and session isolation PASS")


async def test_browser_api_restart_replays_every_missed_event(browser_page):
    page, _ = browser_page
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project, auth, run = await create(client,"Restart recovery")
        await send(client,run,auth,batch([event(i) for i in range(1,11)]))
        gate = asyncio.Event(); gate.set(); blocked = asyncio.Event(); cursors=[]
        async def hold_reconnect(route):
            cursor=route.request.headers.get("last-event-id");cursors.append(cursor)
            if not gate.is_set():blocked.set()
            await gate.wait();await route.continue_()
        await page.route("**/events",hold_reconnect)
        await page.goto(WEB);await connect(page,project["api_key"])
        await page.get_by_role("link",name="Restart recovery",exact=False).click()
        await expect(page.get_by_test_id("applied-cursor")).to_have_text("10")
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        gate.clear()
        result=await asyncio.to_thread(subprocess.run,["docker","compose","restart","-t","1","api"],capture_output=True,text=True)
        assert result.returncode == 0
        async with asyncio.timeout(30):
            while True:
                try:
                    if (await client.get("/health")).status_code==200:break
                except httpx.TransportError:pass
                await asyncio.sleep(0.25)
        await asyncio.wait_for(blocked.wait(),15)
        await expect(page.get_by_test_id("connection-status")).to_have_text("reconnecting")
        await send(client,run,auth,batch([event(i) for i in range(11,31)]))
        gate.set()
        await expect(page.get_by_test_id("applied-cursor")).to_have_text("30")
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        assert "10" in cursors
        await check_sql_and_visible_points(page,run,30)
        print("BROWSER API restart: persistent cursor10 -> gated real reconnect -> committed11-30 -> exact SQL/UI/point sequences1-30 PASS")


async def test_browser_snapshot_gap_and_dark_responsive_layout(browser_page):
    page, _ = browser_page
    async with httpx.AsyncClient(base_url=API,timeout=10) as client:
        project, auth, run = await create(client,"transformer-baseline")
        await send(client,run,auth,batch([event(i,round(math.exp(-i/20)+0.08,4)) for i in range(1,21)]))
        gate = asyncio.Event(); waiting=asyncio.Event()
        async def hold_initial(route):waiting.set();await gate.wait();await route.continue_()
        await page.route("**/events",hold_initial)
        await page.goto(WEB);await connect(page,project["api_key"])
        ARTIFACTS.mkdir(parents=True,exist_ok=True)
        await page.screenshot(path=str(ARTIFACTS/"phase3-run-list.png"),full_page=True)
        await page.get_by_role("link",name="transformer-baseline",exact=False).click()
        await asyncio.wait_for(waiting.wait(),10)
        # Snapshot is20; commit another60 metric events before opening stream.
        await send(client,run,auth,batch([event(i,round(math.exp(-i/20)+0.08,4)) for i in range(21,41)]+
                                       [event(i,round(0.55+0.4*(1-math.exp(-i/16)),4),"accuracy") for i in range(1,41)]))
        gate.set()
        await expect(page.get_by_test_id("connection-status")).to_have_text("connected")
        await check_sql_and_visible_points(page,run,80)
        await page.screenshot(path=str(ARTIFACTS/"phase3-run-detail.png"),full_page=True)
        await page.set_viewport_size({"width":390,"height":844})
        assert await page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        await page.screenshot(path=str(ARTIFACTS/"phase3-mobile.png"),full_page=True)
        print("BROWSER snapshot gap: snapshot20, committed21-80 before subscription, all80 recovered; dark desktop/mobile layout PASS")
