"""Audit intended Git files without printing potentially sensitive values."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

raw = subprocess.check_output(["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"])
paths = sorted({p.decode("utf-8") for p in raw.split(b"\0") if p})
bad_paths, hits, inventory = [], [], []
patterns = {
    "project_token": re.compile(rb"soup_[A-Za-z0-9_-]{43}"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,}"),
    "aws_access_key": re.compile(rb"AKIA[A-Z0-9]{16}"),
}
for name in paths:
    path = Path(name)
    if not path.is_file():
        bad_paths.append(name)
        continue
    if (any(p in {".git", ".venv", "node_modules", ".next", "__pycache__", ".pytest_cache", "tmp", ".review-checkout", "pgdata"} for p in path.parts)
            or (path.name.startswith(".env") and path.name != ".env.example")
            or path.suffix in {".pyc", ".tsbuildinfo", ".sqlite", ".sqlite3", ".db"}):
        bad_paths.append(name)
    data = path.read_bytes()
    for label, pattern in patterns.items():
        for match in pattern.finditer(data):
            hits.append({"file": name, "line": data[:match.start()].count(b"\n") + 1, "pattern": label})
    inventory.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
print(json.dumps({"files": len(paths), "bytes": sum(x["bytes"] for x in inventory),
                  "excluded_path_violations": bad_paths, "secret_pattern_locations_only": hits,
                  "largest_files": sorted(inventory, key=lambda x: x["bytes"], reverse=True)[:5]}, indent=2))
Path("artifacts/test-output/phase6-intended-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
# Generated inventory hashes are a snapshot, not a self-referential final tree hash.
if bad_paths or hits:
    raise SystemExit(1)
print("INTENDED_FILE_SCAN_PASS; heuristic patterns are not an exhaustive secret audit")
