"""Real rendered chart layout, data and controls; no mocked API/SSE responses."""
from pathlib import Path

import httpx
from playwright.async_api import expect

from test_browser import API, WEB, batch, browser_page, check_sql_and_visible_points, connect, create, event, send


async def test_single_and_multiple_metrics_responsive_layout_and_controls(browser_page):
    page, _ = browser_page
    screenshots = Path("artifacts/screenshots/redesign")
    screenshots.mkdir(parents=True, exist_ok=True)
    await page.set_viewport_size({"width":1536,"height":960})
    async with httpx.AsyncClient(base_url=API, timeout=10) as client:
        project, auth, run = await create(client, "decoder-finetune")
        await send(client, run, auth, batch([event(step, round(1/step,4)) for step in [3,1,2,4,5,6,7,8,9,10]]))
        await page.goto(WEB)
        await connect(page, project["api_key"])
        await expect(page.get_by_role("link", name="decoder-finetune", exact=False)).to_be_visible()
        await page.screenshot(path=str(screenshots/"run-list-1536.png"))
        await page.get_by_role("link", name="decoder-finetune", exact=False).click()
        status = page.get_by_test_id("connection-status")
        await expect(status).to_have_text("connected")
        await check_sql_and_visible_points(page, run, 10)
        grid = await page.locator(".metric-grid").bounding_box()
        panel = await page.get_by_test_id("metric-loss").bounding_box()
        chart = await page.get_by_test_id("chart-loss").bounding_box()
        assert abs(panel["width"]-grid["width"])<2 and panel["width"]>1000
        assert chart["height"]>=350
        assert await status.evaluate("e=>getComputedStyle(e).backgroundColor") == "rgba(0, 0, 0, 0)"
        await page.evaluate("window.scrollTo(0,0)")
        await page.screenshot(path=str(screenshots/"single-metric-1536x960.png"))
        await page.get_by_text("Inspect recovered events",exact=False).click()
        await page.evaluate("window.scrollTo(0,0)")
        await page.screenshot(path=str(screenshots/"single-metric-with-history.png"),full_page=True)
        await page.get_by_text("Inspect recovered events",exact=False).click()

        # Keyboard access and actual Disconnect/replay behavior remain intact.
        button = page.get_by_role("button", name="Disconnect", exact=True)
        await button.focus()
        await expect(button).to_be_focused()
        await page.keyboard.press("Enter")
        await expect(status).to_have_text("disconnected")
        await send(client, run, auth, batch([event(i,round(1/i,4)) for i in range(11,21)]))
        await expect(page.get_by_test_id("event-count")).to_have_text("10")
        await page.get_by_role("button", name="Reconnect", exact=True).click()
        await expect(status).to_have_text("connected")
        await check_sql_and_visible_points(page, run, 20)
        await page.set_viewport_size({"width":390,"height":844})
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert (await page.get_by_test_id("chart-loss").bounding_box())["height"]>=250
        await page.screenshot(path=str(screenshots/"single-metric-mobile.png"), full_page=True)

        await send(client, run, auth, batch([event(i,round(0.5+i/50,4),"accuracy") for i in range(1,21)]))
        await expect(page.get_by_test_id("metric-accuracy")).to_be_visible()
        await check_sql_and_visible_points(page, run, 40)
        assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        boxes = [await page.get_by_test_id("metric-"+m).bounding_box() for m in ("accuracy","loss")]
        assert boxes[1]["y"]>boxes[0]["y"]+boxes[0]["height"]
        await page.screenshot(path=str(screenshots/"multiple-metrics-mobile.png"), full_page=True)

        await page.set_viewport_size({"width":1536,"height":960})
        boxes = [await page.get_by_test_id("metric-"+m).bounding_box() for m in ("accuracy","loss")]
        assert abs(boxes[0]["y"]-boxes[1]["y"])<2
        assert all(b["width"]>450 for b in boxes)
        assert boxes[1]["x"]>boxes[0]["x"]+boxes[0]["width"]
        await page.evaluate("window.scrollTo(0,0)")
        await page.screenshot(path=str(screenshots/"multiple-metrics-1536x960.png"))
        assert (await client.post("/projects/key/rotate",headers=auth,json={})).status_code==200
        await expect(status).to_have_text("error")
        await expect(page.get_by_role("alert").filter(has_text="expired")).to_be_visible()
        print("PRESENTATION PASS: single chart fills content/height400; two desktop columns; mobile stack/no overflow; real SQL/points match; keyboard Disconnect/replay and live rotation states work")
