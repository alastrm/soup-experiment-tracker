"""Derive readable measurements from immutable load-test raw JSONL files.

Usage: .venv/Scripts/python scripts/analyze_load.py artifacts/test-output/<run>
Writes analysis.json, explicitly derived data, never substitutes for raw output.
"""
import json
from pathlib import Path
import re
import sys

from load_test import latency, percentile, save


def memory_bytes(value):
    number, unit = re.fullmatch(r"([\d.]+)([A-Za-z]+)", value.strip()).groups()
    return float(number) * {"B": 1, "kB": 1000, "MB": 1000**2, "GB": 1000**3,
                           "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}[unit]


def analyze(path):
    summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    config = summary["config"]
    start, end = config["warmup"], config["warmup"] + config["duration"]
    requests = [json.loads(line) for line in (path / "requests.jsonl").read_text(encoding="utf-8").splitlines()]
    samples = [json.loads(line) for line in (path / "resources.jsonl").read_text(encoding="utf-8").splitlines()]
    services, pg = {}, []
    measurement_samples = [s for s in samples if start <= s["at_s"] < end]
    for sample in measurement_samples:
        if "postgres" in sample:
            pg.append(sample["postgres"])
        if sample["docker"]["exit_code"] != 0:
            continue
        for line in sample["docker"]["stdout"].splitlines():
            stat = json.loads(line)
            services.setdefault(stat["Name"], []).append(stat)
    resource_summary = {}
    for name, stats in services.items():
        cpus = [float(s["CPUPerc"].rstrip("%")) for s in stats]
        memories = [memory_bytes(s["MemUsage"].split("/")[0]) for s in stats]
        resource_summary[name] = {"samples": len(stats), "cpu_percent_mean": sum(cpus) / len(cpus),
                                  "cpu_percent_p95": percentile(cpus, 95), "cpu_percent_max": max(cpus),
                                  "memory_MiB_first": memories[0] / 1024**2, "memory_MiB_last": memories[-1] / 1024**2,
                                  "memory_MiB_max": max(memories) / 1024**2}
    buckets = []
    for left in range(start, end, 10):
        right = min(left + 10, end)
        rows = [r for r in requests if left <= r["finished_s"] < right]
        buckets.append({"from_s": left, "to_s": right,
                        "unique_events_per_s": sum(r["unique_accepted"] for r in rows) / (right - left),
                        "http_requests_per_s": len(rows) / (right - left)})
    mid = (start + end) / 2
    halves = {}
    for label, left, right in (("first_half", start, mid), ("second_half", mid, end)):
        rows = [r for r in requests if left <= r["scheduled_s"] < right and r["kind"] == "primary"]
        halves[label] = latency([r["latency_ms"] for r in rows])
    sse = [json.loads(line) for line in (path / "sse.jsonl").read_text(encoding="utf-8").splitlines()]
    recovery = None
    drop = summary["sse"]["disconnect"]
    if drop and "resumed_s" in drop:
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        run_id = manifest["runs"][0]["run_id"]
        known_high = max([drop["cursor_before"]] + [r["receipt"]["committed_seq"] for r in requests
                         if r["run_id"] == run_id and r["status"] == 200 and r["finished_s"] <= drop["resumed_s"]])
        replay = [e for e in sse if e.get("subscriber") == 0 and "seq" in e
                  and drop["cursor_before"] < e["seq"] <= known_high]
        recovery = {"cursor_before": drop["cursor_before"], "last_acknowledged_seq_before_resume": known_high,
                    "known_missed_events": known_high - drop["cursor_before"], "replayed_events": len(replay),
                    "replay_exact_range": [e["seq"] for e in replay] == list(range(drop["cursor_before"] + 1, known_high + 1)),
                    "seconds_disconnected": drop["resumed_s"] - drop["started_s"],
                    "seconds_to_apply_known_backlog_after_resume": max(e["applied_s"] for e in replay) - drop["resumed_s"] if replay else None}
    audit = json.loads((path / "database-audit.json").read_text(encoding="utf-8"))
    # Older failed generator snapshots did not print this count, but the audit
    # reports an acknowledged_missing object for every nonzero missing count.
    acknowledged_missing = sum(r.get("acknowledged_missing", sum(e.get("acknowledged_missing", 0)
                               for e in r["errors"] if isinstance(e, dict))) for r in audit["runs"])
    result = {"kind": "DERIVED ANALYSIS of raw requests/resources/SSE/SQL audit; not raw test output",
              "source": str(path), "measurement_10_second_buckets": buckets, "primary_latency_halves": halves,
              "resources": resource_summary, "docker_cpu_units": "100 percent = one logical CPU; can exceed 100",
              "docker_memory_units": "Docker stats memory working-set estimate, not total OS/socket buffers",
              "measurement_resource_samples": len(measurement_samples),
              "postgres_observed_max": {key: max(s[key] for s in pg) for key in pg[0]} if pg else {},
              "postgres_monitor_connection_excluded": True,
              "generator_cpu_percent_of_one_core": summary["generator_process_cpu_s"] / summary["elapsed_workload_s"] * 100,
              "acknowledged_but_missing_events": acknowledged_missing,
              "planned_but_not_attempted_events": summary["planned_unique_events"] - summary["unique_events_attempted"],
              "sse_controlled_recovery": recovery}
    save(path / "analysis.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    for argument in sys.argv[1:]:
        analyze(Path(argument))
