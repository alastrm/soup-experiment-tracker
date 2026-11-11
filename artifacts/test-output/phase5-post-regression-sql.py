"""Executed SQL probe after regression restarted both API and PostgreSQL."""
import asyncio
import json
import os
from pathlib import Path
from uuid import UUID

import asyncpg

SQL = """
SELECT r.id, r.last_seq, count(e.event_id)::int AS event_count,
       count(DISTINCT e.event_id)::int AS distinct_events,
       count(DISTINCT e.seq)::int AS distinct_sequences,
       min(e.seq) AS first_seq, max(e.seq) AS last_event_seq,
       (SELECT count(*) FROM batches b WHERE b.run_id=r.id)::int AS receipt_count
FROM runs r LEFT JOIN metric_events e ON e.run_id=r.id AND e.project_id=r.project_id
WHERE r.project_id=$1 GROUP BY r.id ORDER BY r.id
"""


async def main():
    connection = await asyncpg.connect(os.getenv("LOAD_DATABASE_URL", "postgresql://soup:soup_local_only@127.0.0.1:54329/soup"))
    print("SQL:", SQL)
    for name in ("phase5-baseline-02", "phase5-sse-01"):
        manifest = json.loads((Path("artifacts/test-output") / name / "manifest.json").read_text())
        rows = [dict(r) for r in await connection.fetch(SQL, UUID(manifest["project_id"]))]
        print(json.dumps({"campaign": name, "rows": rows}, default=str))
        assert {str(r["id"]) for r in rows} == {r["run_id"] for r in manifest["runs"]}
        assert len(rows) == 50
        assert all(r["last_seq"] == r["event_count"] == r["distinct_events"] == r["distinct_sequences"] == r["last_event_seq"] == 700
                   and r["first_seq"] == 1 and r["receipt_count"] == 140 for r in rows)
        print(name, "PASS: 50 runs, 35000 rows, 7000 receipts, exact1-700 each after API/DB restarts")
    await connection.close()


asyncio.run(main())
