"""Live HTTP + independent PostgreSQL smoke; run from repository root.

No tokens are printed or persisted. Optional API restart proves durable receipts.
"""
import argparse
import asyncio
import json
import os
import subprocess
import time
from uuid import UUID, uuid4

import asyncpg
import httpx


async def main(restart_api: bool):
    base = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    dsn = os.getenv("DATABASE_URL", "postgresql://soup:soup_local_only@127.0.0.1:54329/soup")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    async with httpx.AsyncClient(base_url=base, timeout=10) as client:
        assert (await client.get("/health")).status_code == 200
        response_a = await client.post("/projects", json={"name": "Phase2 smoke A"})
        response_b = await client.post("/projects", json={"name": "Phase2 smoke B"})
        assert response_a.status_code == response_b.status_code == 201
        a, b = response_a.json(), response_b.json()
        auth_a = {"Authorization": "Bearer " + a["api_key"]}
        auth_b = {"Authorization": "Bearer " + b["api_key"]}
        created = await client.post("/runs", json={"name": "live HTTP smoke"}, headers=auth_a)
        assert created.status_code == 201
        run_id = created.json()["id"]
        payload = {"batch_id": str(uuid4()), "events": [
            {"event_id": str(uuid4()), "metric": "loss", "step": step, "value": value,
             "occurred_at": "2026-01-01T00:00:00Z"} for step, value in [(5, 50), (1, 10), (5, 55)]
        ]}
        first = await client.post(f"/runs/{run_id}/metrics", json=payload, headers=auth_a)
        assert first.status_code == 200
        if restart_api:
            subprocess.run(["docker", "compose", "restart", "api"], check=True)
            deadline = time.monotonic() + 30
            while True:
                try:
                    if (await client.get("/health")).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("API did not become healthy after restart")
                await asyncio.sleep(0.25)
        duplicate = await client.post(f"/runs/{run_id}/metrics", json=payload, headers=auth_a)
        assert duplicate.status_code == 200 and duplicate.json() == first.json()
        assert (await client.get(f"/runs/{run_id}", headers=auth_b)).status_code == 404
        assert (await client.post(f"/runs/{run_id}/metrics", json=payload, headers=auth_b)).status_code == 404
        assert (await client.get("/runs", headers=auth_b)).json()["runs"] == []
        rotated = await client.post("/projects/key/rotate", json={}, headers=auth_a)
        assert rotated.status_code == 200
        assert (await client.get(f"/runs/{run_id}", headers=auth_a)).status_code == 401
        new_auth = {"Authorization": "Bearer " + rotated.json()["api_key"]}
        snapshot_response = await client.get(f"/runs/{run_id}", headers=new_auth)
        assert snapshot_response.status_code == 200
        snapshot = snapshot_response.json()

    connection = await asyncpg.connect(dsn)
    try:
        row = await connection.fetchrow(
            "SELECT count(*) AS events, min(seq) AS first, max(seq) AS last "
            "FROM metric_events WHERE project_id=$1 AND run_id=$2",
            UUID(a["project"]["id"]), UUID(run_id))
        winner = await connection.fetchrow(
            "SELECT step,value,seq FROM metric_events WHERE project_id=$1 AND run_id=$2 "
            "ORDER BY step DESC,seq DESC LIMIT 1", UUID(a["project"]["id"]), UUID(run_id))
        receipt_count = await connection.fetchval("SELECT count(*) FROM batches WHERE run_id=$1", UUID(run_id))
        counter = await connection.fetchval("SELECT last_seq FROM runs WHERE id=$1", UUID(run_id))
        revision = await connection.fetchval("SELECT version_num FROM alembic_version")
        assert dict(row) == {"events": 3, "first": 1, "last": 3}
        assert counter == receipt_count + 2 == snapshot["last_seq"] == snapshot["event_count"] == 3
        assert {key: snapshot["metrics"][0][key] for key in winner.keys()} == dict(winner)
        print(json.dumps({"live_http": "PASS", "api_restarted": restart_api, "migration": revision,
                          "persisted_events": row["events"], "persisted_receipts": receipt_count,
                          "identical_retry": "PASS", "cross_project_read_write_list": "PASS",
                          "key_rotation": "PASS", "snapshot_matches_independent_sql": "PASS"}))
    finally:
        await connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart-api", action="store_true")
    asyncio.run(main(parser.parse_args().restart_api))
