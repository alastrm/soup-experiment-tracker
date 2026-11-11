"""Measured HTTP/SSE workload; run from repo root with .venv Python.

Default: 50 runs, 10 unique events/s/run, batches of 5, 10s warm-up + 60s
measurement. No application internals imported. SQL audit uses asyncpg directly.
Credentials stay in memory; output deliberately excludes headers and DSNs.
Use LOAD_DATABASE_URL to override the loopback Compose database connection.
Each invocation creates a new output directory and leaves its DB rows intact.
"""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from uuid import UUID, uuid4

import asyncpg
import httpx


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def percentile(values, percent):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * percent / 100
    low = math.floor(index)
    return values[low] + (values[math.ceil(index)] - values[low]) * (index - low)


def latency(values):
    return {f"p{p}_ms": percentile(values, p) for p in (50, 95, 99)}


async def command(*args):
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate()
    return {"command": list(args), "exit_code": proc.returncode,
            "stdout": out.decode("utf-8", "replace"), "stderr": err.decode("utf-8", "replace")}


def event_equal(left, right):
    # API uses six fractional digits; PG returns datetime. Compare instants.
    def stamp(value):
        return value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (str(left["event_id"]) == str(right["event_id"])
            and left["metric"] == right["metric"] and left["step"] == right["step"]
            and left["value"] == right["value"] and stamp(left["occurred_at"]) == stamp(right["occurred_at"]))


class Workload:
    def __init__(self, args, output):
        self.a, self.out = args, output
        self.interval = args.batch_size / args.rate
        self.ticks = round((args.warmup + args.duration) / self.interval)
        self.records, self.samples, self.protocol_errors = [], [], []
        self.runs, self.batches = [], []
        self.receipts, self.sent = {}, set()
        self.cursor = [0] * args.subscribers
        self.sse_seen = [set() for _ in self.cursor]
        self.sse_errors, self.sse_connections, self.disconnect = [], [], None
        self.sse_ready = [asyncio.Event() for _ in self.cursor]
        self.stop = asyncio.Event()
        self.epoch = 0.0
        self.request_file = (output / "requests.jsonl").open("w", encoding="utf-8")
        self.resource_file = (output / "resources.jsonl").open("w", encoding="utf-8")
        self.sse_file = (output / "sse.jsonl").open("w", encoding="utf-8")

    def now(self):
        return time.perf_counter() - self.epoch

    def log_sse(self, record):
        self.sse_file.write(json.dumps(record) + "\n")
        self.sse_file.flush()

    async def setup(self, client):
        response = await client.post("/projects", json={"name": f"Load {self.out.name[-16:]}"})
        response.raise_for_status()
        body = response.json()
        self.project = body["project"]["id"]
        self.headers = {"Authorization": "Bearer " + body["api_key"]}
        for i in range(self.a.runs):
            response = await client.post("/runs", headers=self.headers, json={"name": f"Load run {i:02d}"})
            response.raise_for_status()
            self.runs.append(response.json()["id"])
        stamp = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        for i, run in enumerate(self.runs):
            batches = []
            for tick in range(self.ticks):
                events = []
                for offset in range(self.a.batch_size):
                    number = tick * self.a.batch_size + offset
                    events.append({"event_id": str(uuid4()), "metric": "load.loss" if number % 2 == 0 else "load.accuracy",
                                   "step": number // 2, "value": (i + 1) / (number + 1), "occurred_at": stamp})
                batches.append({"batch_id": str(uuid4()), "events": events})
            self.batches.append(batches)
        save(self.out / "manifest.json", {"project_id": self.project, "runs": [
            {"run_id": run, "batches": batches} for run, batches in zip(self.runs, self.batches)]})

    async def send(self, client, run, batch, scheduled, kind):
        started = self.now()
        record = {"run_id": run, "batch_id": batch["batch_id"], "kind": kind,
                  "scheduled_s": scheduled, "started_s": started,
                  "phase": "warmup" if scheduled < self.a.warmup else "measurement",
                  "event_count": len(batch["events"]), "status": None, "error": None,
                  "unique_accepted": 0}
        self.sent.add(batch["batch_id"])
        try:
            response = await client.post(f"/runs/{run}/metrics", headers=self.headers, json=batch)
            record["status"] = response.status_code
            if response.status_code == 200:
                receipt = response.json()
                record["receipt"] = receipt
                previous = self.receipts.get(batch["batch_id"])
                if previous is not None and previous != receipt:
                    self.protocol_errors.append({"batch_id": batch["batch_id"], "error": "retry receipt changed"})
                if previous is None:
                    record["unique_accepted"] = len(batch["events"])
                    self.receipts[batch["batch_id"]] = receipt
                expected_ids = [e["event_id"] for e in batch["events"]]
                if ([e["event_id"] for e in receipt["accepted"]] != expected_ids
                        or receipt["inserted_count"] != len(expected_ids) or receipt["deduplicated_count"] != 0):
                    self.protocol_errors.append({"batch_id": batch["batch_id"], "error": "unexpected fresh receipt"})
            else:
                record["error"] = f"http_{response.status_code}"
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            record["error"] = type(exc).__name__  # Never log potentially credential-bearing exception text.
        record["finished_s"] = self.now()
        record["latency_ms"] = (record["finished_s"] - started) * 1000
        self.records.append(record)
        self.request_file.write(json.dumps(record) + "\n")
        self.request_file.flush()
        return record["error"] is None

    async def producer(self, client, i):
        for tick, batch in enumerate(self.batches[i]):
            scheduled = tick * self.interval + i / self.a.runs * self.interval
            await asyncio.sleep(max(0, scheduled - self.now()))
            if self.now() - scheduled >= self.interval:
                self.protocol_errors.append({"run_id": self.runs[i], "tick": tick, "error": "pacing missed batch"})
                continue  # Bounded: no unbounded queue or hidden burst to make up an overloaded generator.
            ok = await self.send(client, self.runs[i], batch, scheduled, "primary")
            if not ok:
                await self.send(client, self.runs[i], batch, scheduled, "recovery_retry")
            elif scheduled >= self.a.warmup and (tick - round(self.a.warmup / self.interval) + 1) % self.a.retry_every == 0:
                await self.send(client, self.runs[i], batch, scheduled, "controlled_retry")

    async def subscriber(self, client, i):
        expected = {e["event_id"]: e for b in self.batches[i] for e in b["events"]}
        dropped = False
        while not self.stop.is_set():
            headers = {**self.headers, "Accept": "text/event-stream", "Last-Event-ID": str(self.cursor[i])}
            try:
                async with client.stream("GET", f"/runs/{self.runs[i]}/events", headers=headers) as response:
                    if response.status_code != 200:
                        self.sse_errors.append({"subscriber": i, "status": response.status_code})
                        await asyncio.sleep(0.5)
                        continue
                    self.sse_connections.append({"subscriber": i, "cursor": self.cursor[i], "at_s": self.now()})
                    self.sse_ready[i].set()
                    fields = {}
                    async for line in response.aiter_lines():
                        if self.stop.is_set():
                            break
                        if self.epoch and i == 0 and not dropped and self.now() >= self.a.warmup + self.a.duration / 2:
                            dropped = True
                            self.disconnect = {"cursor_before": self.cursor[i], "started_s": self.now()}
                            break
                        if line.startswith(":"):
                            continue
                        if line:
                            key, _, value = line.partition(":")
                            fields[key] = value.lstrip(" ")
                            continue
                        if fields.get("event") == "metric":
                            event = json.loads(fields["data"])
                            seq = int(fields["id"])
                            valid = (seq == event["seq"] and seq == self.cursor[i] + 1
                                     and event["event_id"] not in self.sse_seen[i]
                                     and event["event_id"] in expected and event_equal(event, expected[event["event_id"]]))
                            if not valid:
                                self.sse_errors.append({"subscriber": i, "seq": seq, "cursor": self.cursor[i], "error": "identity/gap/duplicate"})
                                raise ValueError("Invalid stream event")
                            self.sse_seen[i].add(event["event_id"])
                            self.cursor[i] = seq  # Only after identity and contiguous application.
                            self.log_sse({"subscriber": i, "seq": seq, "event_id": event["event_id"], "applied_s": self.now()})
                        elif fields.get("event") == "auth_expired":
                            self.sse_errors.append({"subscriber": i, "error": "unexpected revocation"})
                        fields = {}
                if i == 0 and dropped and self.disconnect and "resumed_s" not in self.disconnect:
                    await asyncio.sleep(self.a.disconnect_seconds)
                    self.disconnect["resumed_s"] = self.now()
                    self.disconnect["cursor_sent"] = self.cursor[i]
                    self.log_sse({"disconnect": self.disconnect})
                elif not self.stop.is_set():
                    self.sse_errors.append({"subscriber": i, "error": "unexpected EOF"})
                    await asyncio.sleep(0.2)
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                self.sse_errors.append({"subscriber": i, "error": type(exc).__name__})
                await asyncio.sleep(0.5)

    async def monitor(self, connection, containers):
        while not self.stop.is_set():
            sample = {"at_s": self.now()}
            try:
                sample["postgres"] = dict(await connection.fetchrow("""
                    SELECT count(*)::int AS connections,
                           count(*) FILTER(WHERE state='active')::int AS active,
                           count(*) FILTER(WHERE wait_event_type='Lock')::int AS lock_waiters,
                           count(*) FILTER(WHERE state='idle in transaction')::int AS idle_in_transaction
                    FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()
                """))
            except (asyncpg.PostgresError, OSError) as exc:
                sample["postgres_error"] = type(exc).__name__
            sample["docker"] = await command("docker", "stats", "--no-stream", "--format", "{{json .}}", *containers)
            self.samples.append(sample)
            self.resource_file.write(json.dumps(sample) + "\n")
            self.resource_file.flush()
            try:
                await asyncio.wait_for(self.stop.wait(), timeout=1)
            except TimeoutError:
                pass  # docker stats takes ~1s; record actual timestamps, not an assumed sampling interval.

    async def audit(self, connection, client):
        all_errors, rows = [], []
        total_events = total_batches = 0
        for run, batches in zip(self.runs, self.batches):
            actual = await connection.fetch("SELECT * FROM metric_events WHERE run_id=$1 ORDER BY seq", UUID(run))
            receipts = await connection.fetch("SELECT batch_id,receipt FROM batches WHERE run_id=$1", UUID(run))
            high = await connection.fetchval("SELECT last_seq FROM runs WHERE id=$1 AND project_id=$2", UUID(run), UUID(self.project))
            planned = {e["event_id"]: e for batch in batches for e in batch["events"]}
            acknowledged = {e["event_id"] for batch in batches if batch["batch_id"] in self.receipts for e in batch["events"]}
            actual_ids = {str(e["event_id"]) for e in actual}
            errors = []
            if actual_ids != set(planned):
                errors.append({"planned_missing": len(set(planned) - actual_ids), "unexpected": len(actual_ids - set(planned))})
            if not acknowledged.issubset(actual_ids):
                errors.append({"acknowledged_missing": len(acknowledged - actual_ids)})
            if high != len(actual) or [e["seq"] for e in actual] != list(range(1, len(actual) + 1)):
                errors.append("non-contiguous sequence or counter mismatch")
            if len(actual_ids) != len(actual) or any(str(e["project_id"]) != self.project or str(e["event_id"]) not in planned
                                                     or not event_equal(e, planned[str(e["event_id"])]) for e in actual):
                errors.append("duplicate, tenant or payload mismatch")
            expected_order = [e["event_id"] for batch in batches if batch["batch_id"] in self.sent for e in batch["events"]]
            if [str(e["event_id"]) for e in actual] != expected_order:
                errors.append("input-to-sequence order mismatch")
            db_receipts = {str(r["batch_id"]): json.loads(r["receipt"]) for r in receipts}
            if set(db_receipts) != {b["batch_id"] for b in batches}:
                errors.append("receipt identities/count differ from planned batches")
            by_event = {str(e["event_id"]): e["seq"] for e in actual}
            for batch in batches:
                receipt = db_receipts.get(batch["batch_id"])
                if not receipt:
                    continue
                expected = [{"event_id": e["event_id"], "seq": by_event.get(e["event_id"])} for e in batch["events"]]
                if (receipt["accepted"] != expected or receipt["inserted_count"] != len(expected)
                        or receipt["deduplicated_count"] != 0 or receipt["committed_seq"] != expected[-1]["seq"]
                        or receipt != self.receipts.get(batch["batch_id"])):
                    errors.append({"batch_id": batch["batch_id"], "error": "receipt does not match events/HTTP"})
            response = await client.get(f"/runs/{run}", headers=self.headers)
            if response.status_code != 200:
                errors.append({"snapshot_status": response.status_code})
            else:
                snapshot = response.json()
                winners = {}
                for event in actual:
                    current = winners.get(event["metric"])
                    if current is None or (event["step"], event["seq"]) > (current["step"], current["seq"]):
                        winners[event["metric"]] = event
                if (snapshot["last_seq"] != high or snapshot["event_count"] != len(actual)
                        or len(snapshot["metrics"]) != len(winners)
                        or any(e["metric"] not in winners or e["seq"] != winners[e["metric"]]["seq"]
                               or not event_equal(e, winners[e["metric"]]) for e in snapshot["metrics"])):
                    errors.append("API snapshot differs from independently selected PG winners")
            row = {"run_id": run, "expected_events": len(planned), "stored_events": len(actual),
                   "acknowledged_events": len(acknowledged), "last_seq": high, "receipts": len(receipts), "errors": errors}
            rows.append(row)
            total_events += len(actual)
            total_batches += len(receipts)
            all_errors.extend({"run_id": run, "error": error} for error in errors)
        result = {"passed": not all_errors, "stored_events": total_events, "stored_receipts": total_batches,
                  "runs": rows, "errors": all_errors}
        save(self.out / "database-audit.json", result)
        return result

    def summary(self, audit, elapsed, cpu_seconds):
        end = self.a.warmup + self.a.duration
        window = [r for r in self.records if self.a.warmup <= r["finished_s"] < end]
        cohort = [r for r in self.records if r["phase"] == "measurement"]
        primary = [r for r in cohort if r["kind"] == "primary"]
        failures = [r for r in self.records if r["error"]]
        controlled = [r for r in cohort if r["kind"] == "controlled_retry"]
        unique = sum(r["unique_accepted"] for r in window)
        expected = self.a.runs * self.a.rate * (self.a.warmup + self.a.duration)
        sse_ok = not self.sse_errors and all(c == self.ticks * self.a.batch_size for c in self.cursor)
        if self.a.subscribers and self.disconnect:
            self.disconnect["final_cursor"] = self.cursor[0]
            self.disconnect["replayed_after_drop"] = self.cursor[0] - self.disconnect["cursor_before"]
        result = {"config": vars(self.a), "elapsed_workload_s": elapsed, "generator_process_cpu_s": cpu_seconds,
                  "planned_unique_events": expected, "attempted_event_deliveries": sum(r["event_count"] for r in self.records),
                  "unique_events_attempted": len(self.sent) * self.a.batch_size,
                  "unique_events_accepted": sum(r["unique_accepted"] for r in self.records),
                  "failed_request_event_deliveries": sum(r["event_count"] for r in failures),
                  "http_rejected_event_deliveries": sum(r["event_count"] for r in failures if r["status"] is not None),
                  "timeouts": sum("Timeout" in (r["error"] or "") for r in failures),
                  "http_status_counts": dict(Counter(str(r["status"]) for r in self.records)),
                  "http_failure_count": len(failures), "measurement_window_s": self.a.duration,
                  "measurement_window_unique_events": unique, "measurement_window_events_per_s": unique / self.a.duration,
                  "measurement_window_http_requests_per_s": len(window) / self.a.duration,
                  "measurement_primary_cohort_events": sum(r["unique_accepted"] for r in primary),
                  "measurement_primary_cohort_latency": latency([r["latency_ms"] for r in primary]),
                  "measurement_all_request_latency": latency([r["latency_ms"] for r in cohort]),
                  "controlled_retry_requests": len(controlled), "controlled_retry_latency": latency([r["latency_ms"] for r in controlled]),
                  "primary_schedule_lateness": latency([(r["started_s"] - r["scheduled_s"]) * 1000 for r in primary]),
                  "last_primary_completion_s": max(r["finished_s"] for r in self.records if r["kind"] == "primary"),
                  "protocol_errors": self.protocol_errors, "database_audit_passed": audit["passed"],
                  "sse": {"subscribers": self.a.subscribers, "passed": sse_ok, "cursors": self.cursor,
                          "errors": self.sse_errors, "connections": self.sse_connections, "disconnect": self.disconnect},
                  "resource_samples": len(self.samples)}
        # Predeclared local benchmark gates, not employer or production SLOs.
        result["gates"] = {"all_planned_events_acknowledged": result["unique_events_accepted"] == expected,
                           "no_http_failures": not failures, "no_pacing_or_receipt_errors": not self.protocol_errors,
                           "throughput_at_least_99_percent_target": unique / self.a.duration >= self.a.runs * self.a.rate * .99,
                           "primary_p95_below_batch_interval": result["measurement_primary_cohort_latency"]["p95_ms"] < self.interval * 1000,
                           "primary_p99_below_1s": result["measurement_primary_cohort_latency"]["p99_ms"] < 1000,
                           "postgres_audit": audit["passed"], "sse_replay": sse_ok}
        result["passed"] = all(result["gates"].values())
        return result

    async def run(self):
        dsn = os.getenv("LOAD_DATABASE_URL", "postgresql://soup:soup_local_only@127.0.0.1:54329/soup")
        connection = await asyncpg.connect(dsn, server_settings={"application_name": "soup-load-monitor"})
        limits = httpx.Limits(max_connections=150, max_keepalive_connections=100)
        async with httpx.AsyncClient(base_url=self.a.api, timeout=10, limits=limits, trust_env=False) as client, \
                httpx.AsyncClient(base_url=self.a.api, timeout=httpx.Timeout(10, read=30), limits=limits, trust_env=False) as stream_client:
            await self.setup(client)
            environment = {"utc": datetime.now(timezone.utc).isoformat(), "python": sys.version, "platform": platform.platform(),
                           "httpx": httpx.__version__, "asyncpg": asyncpg.__version__, "command": sys.argv,
                           "postgres": dict(await connection.fetchrow("SELECT version(), current_setting('max_connections') AS max_connections, current_setting('shared_buffers') AS shared_buffers"))}
            environment["docker_info"] = await command("docker", "info", "--format", "{{json .}}")
            environment["compose_ps"] = await command("docker", "compose", "ps", "--format", "json")
            container_result = await command("docker", "compose", "ps", "-q")
            containers = container_result["stdout"].split()
            environment["container_limits"] = await command("docker", "inspect", "--format", "{{.Name}} image={{.Image}} memory={{.HostConfig.Memory}} nano_cpus={{.HostConfig.NanoCpus}} cpu_quota={{.HostConfig.CpuQuota}}", *containers)
            save(self.out / "environment.json", environment)
            # Origin intentionally in future until subscribers are ready. No ingestion before readiness.
            self.epoch = time.perf_counter() + 3600
            subscribers = [asyncio.create_task(self.subscriber(stream_client, i)) for i in range(self.a.subscribers)]
            if subscribers:
                await asyncio.wait_for(asyncio.gather(*(e.wait() for e in self.sse_ready)), timeout=15)
            self.epoch = time.perf_counter() + 0.25
            cpu = time.process_time()
            monitor = asyncio.create_task(self.monitor(connection, containers))
            producers = [asyncio.create_task(self.producer(client, i)) for i in range(self.a.runs)]
            print(f"START project={self.project} runs={self.a.runs} rate={self.a.rate} batch={self.a.batch_size} warmup={self.a.warmup}s measurement={self.a.duration}s SSE={self.a.subscribers}", flush=True)
            while not all(p.done() for p in producers):
                await asyncio.sleep(5)
                print(f"PROGRESS t={self.now():.2f}s requests={len(self.records)} unique_accepted={sum(r['unique_accepted'] for r in self.records)} errors={sum(bool(r['error']) for r in self.records)}", flush=True)
            await asyncio.gather(*producers)
            await asyncio.sleep(max(0, self.a.warmup + self.a.duration - self.now()))
            elapsed, cpu_seconds = self.now(), time.process_time() - cpu
            expected_cursor = self.ticks * self.a.batch_size
            deadline = time.perf_counter() + 15
            while any(c != expected_cursor for c in self.cursor) and time.perf_counter() < deadline:
                await asyncio.sleep(.1)
            self.stop.set()
            for task in subscribers:
                task.cancel()
            await asyncio.gather(*subscribers, return_exceptions=True)
            await monitor
            audit = await self.audit(connection, client)
            result = self.summary(audit, elapsed, cpu_seconds)
            save(self.out / "summary.json", result)
            print(json.dumps(result, indent=2), flush=True)
        await connection.close()
        return 0 if result["passed"] else 1


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--rate", type=int, default=10, help="unique metric events per second per run")
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--retry-every", type=int, default=20, help="one controlled exact retry every N measurement batches")
    parser.add_argument("--subscribers", type=int, default=0)
    parser.add_argument("--disconnect-seconds", type=float, default=5)
    parser.add_argument("--output", required=True, help="new directory, never overwritten")
    args = parser.parse_args()
    if (not 1 <= args.runs <= 100 or not 1 <= args.batch_size <= 250 or args.rate <= 0
            or args.warmup < 1 or args.duration < 1 or args.retry_every < 1
            or not 0 <= args.subscribers <= args.runs or args.disconnect_seconds <= 0):
        parser.error("invalid workload bounds")
    interval = args.batch_size / args.rate
    if any(abs(seconds / interval - round(seconds / interval)) > 1e-8 for seconds in (args.warmup, args.duration)):
        parser.error("warmup/duration must be exact multiples of batch interval")
    return args


if __name__ == "__main__":
    args = arguments()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    save(output / "config.json", {**vars(args), "gates_declared_before_run": {
        "throughput_tolerance_percent": 1, "primary_p95_ms": args.batch_size / args.rate * 1000,
        "primary_p99_ms": 1000, "all_planned_events_required": True, "zero_http_failures_required": True,
        "exact_sql_and_receipt_audit_required": True, "all_sse_events_required_when_enabled": True}})
    # Freeze the exact generator used with each successful OR failed attempt.
    (output / "load_test.py").write_bytes(Path(__file__).read_bytes())
    try:
        exit_code = asyncio.run(Workload(args, output).run())
    except Exception as exc:
        # Exception messages/tracebacks from network tools can contain credentials.
        save(output / "failure.json", {"error_type": type(exc).__name__, "stage": "generator failed; raw partial files retained"})
        print(f"GENERATOR_FAILED {type(exc).__name__}; see partial files in {output}", flush=True)
        exit_code = 2
    print(f"EXIT_CODE={exit_code}", flush=True)
    sys.exit(exit_code)
