"""Final checks of real artifacts; use the documentation Python with pypdf."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from pypdf import PdfReader


def squash(text):
    return re.sub(r"\s+", "", text)


for source, pdf, expected in (
    ("docs/SUBMISSION_NOTE.md", "output/pdf/Soup-Submission-Note.pdf", 2),
    ("docs/DESIGN.md", "output/pdf/Soup-Architecture.pdf", 1),
):
    reader = PdfReader(pdf)
    assert len(reader.pages) == expected
    extracted = squash("\n".join(page.extract_text() for page in reader.pages))
    blocks = []
    for block in Path(source).read_text(encoding="utf-8").strip().split("\n\n"):
        if block.strip() == "<!-- PAGEBREAK -->":
            continue
        plain = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", block)
        plain = re.sub(r"^#{1,2} ", "", plain).replace("**", "").replace("`", "")
        blocks.append(plain)
    missing = [block[:60] for block in blocks if squash(block) not in extracted]
    print(pdf, "pages", expected, "source_blocks", len(blocks), "missing_blocks", missing,
          "sha256", hashlib.sha256(Path(pdf).read_bytes()).hexdigest())
    assert not missing

note = Path("docs/SUBMISSION_NOTE.md").read_text(encoding="utf-8")
disclosure = note.split("## AI disclosure\n\n")[1].strip()
assert 70 <= len(disclosure.split()) <= 100
assert disclosure == Path("docs/AI_USAGE.md").read_text(encoding="utf-8").split("\n\n", 1)[1].strip()
for phrase in ("applicant", "no independent human", "human review obligations", "interview", "employment", "unpaid"):
    assert phrase not in (note + disclosure).lower()
print("FIRST_PERSON_AI_DISCLOSURE_WORDS", len(disclosure.split()))

missing_links = []
for path in [Path("README.md"), *Path("docs").glob("*.md")]:
    for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8-sig")):
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", link) or link.startswith("#"):
            continue
        if not (path.parent / link.split("#")[0]).exists():
            missing_links.append((path.name, link))
known = [("EVIDENCE.md", "../artifacts/test-output/phase2-compile.log"),
         ("EVIDENCE.md", "../artifacts/test-output/phase2-compose-config.log")]
print("KNOWN_MISSING_HISTORICAL_LINKS", missing_links)
assert sorted(missing_links) == sorted(known)

changed, checked = [], 0
for entry in subprocess.check_output(["git", "ls-tree", "-r", "-z", "4a59dc4"]).split(b"\0"):
    if not entry:
        continue
    metadata, encoded = entry.split(b"\t", 1)
    name = encoded.decode("utf-8")
    if not re.match(r"artifacts/test-output/phase[1-5]", name):
        continue
    data = Path(name).read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    checked += 1
    if blob != metadata.split()[2].decode():
        changed.append(name)
print("HISTORICAL_CAPTURE_FILES_CHECKED", checked, "BYTE_CHANGES", changed)
assert not changed
old = json.loads(Path("artifacts/test-output/phase5-application-sha256.json").read_text())
product_changes = [p for p, digest in old.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest]
print("PRODUCT_CHANGES_VS_MEASURED_PHASE5", product_changes)
assert not product_changes

for filename in ("phase6-clean-build.log", "phase6-clean-startup.log", "phase6-backend-tests.log",
                 "phase6-npm-ci.log", "phase6-client-tests.log", "phase6-typecheck.log", "phase6-next-build.log",
                 "phase6-browser-e2e.log", "phase6-live-smoke.log", "phase6-migration-current-02.log",
                 "phase6-migration-check.log", "phase6-original-restore.log", "phase6-original-data-preserved.log"):
    text = (Path("artifacts/test-output") / filename).read_text(encoding="utf-8-sig")
    assert text.rstrip().endswith("EXIT_CODE=0"), filename
print("REQUIRED_FINAL_RUN_CAPTURES_PRESENT_WITH_RECORDED_EXIT0")
print("FINAL_ARTIFACT_CHECK_PASS; historical gaps and runtime limits remain explicitly qualified")
