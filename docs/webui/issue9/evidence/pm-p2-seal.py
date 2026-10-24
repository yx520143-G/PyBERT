"""Read-only final source/download applicability seal; no engine instances."""

import json
import subprocess
import zipfile
from pathlib import Path

from pybert.web.archive import json_bytes, sha256

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent
checks = []


def check(name, passed):
    checks.append({"name": name, "passed": bool(passed)})


for folder in ("metadata-audit-20261024-150741", "chrome-v3"):
    path = OUT / folder
    record = json.loads((path / ("report.json" if folder.startswith("metadata") else "before-execution.json")).read_bytes())
    identities = record.get("source_identity")
    for relative, expected in identities.items():
        captured = (path / "source" / relative).read_bytes()
        check(folder + " actual source hash " + relative, sha256(captured) == expected)
        check(folder + " final product bytes " + relative, captured == (ROOT / "src/pybert" / relative).read_bytes())

audit = json.loads((OUT / "metadata-audit-20261024-150741/report.json").read_bytes())
for row in audit["cases"]:
    source = ROOT / row["source"]
    check(row["run_id"] + " historical manifest retained", sha256(source.read_bytes()) == row["derivation"]["source_manifest_sha256"])
    check(row["run_id"] + " historical raw retained", sha256((source.parent / "arrays.npz").read_bytes()) == row["derivation"]["source_arrays_sha256"])

downloads = ((ROOT / "output/playwright/issue9/PAM4-ERROR.pybert_run", ROOT / "output/playwright/issue9/PAM4-ERROR-v3-legacy.pybert_run"),
             (OUT / "metadata-audit-20261024-150741/local/8/derived.pybert_run", ROOT / "output/playwright/issue9/PAM4-ERROR-v3-schema2-derived.pybert_run"))
for old, new in downloads:
    with zipfile.ZipFile(old) as first, zipfile.ZipFile(new) as last:
        check(new.name + " original raw exact", first.read("arrays.npz") == last.read("arrays.npz"))
        check(new.name + " original source manifest exact", json.loads(first.read("manifest.json"))["source_manifest_utf8"] == json.loads(last.read("manifest.json"))["source_manifest_utf8"])
requests = list((OUT / "chrome-v3/local/service").glob("*/request.json"))
check("Chrome only defaults normalization request", len(requests) == 1 and json.loads(requests[0].read_bytes()) == {"mode": "defaults"})
for filename in ("check-old-v2.log", "check-new.log", "check-reload.log"):
    text = (OUT / "chrome-v3" / filename).read_text(encoding="utf-8")
    result = json.loads(text.split("### Result\n", 1)[1].splitlines()[0])
    check(filename + " no Run posts", result["runPosts"] == 0)
for path in OUT.rglob("*"):
    if path.is_file() and "local" not in path.relative_to(OUT).parts:
        check(str(path.relative_to(OUT)) + " no UTF8 BOM", not path.read_bytes().startswith(b"\xef\xbb\xbf"))
report = {"product_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "main_calls": 0, "COM_calls": 0, "checks": checks, "check_count": len(checks),
          "failed": sum(not row["passed"] for row in checks),
          "metadata_audit_sha256": sha256((OUT / "metadata-audit-20261024-150741/report.json").read_bytes()),
          "source_applicability": "Audit/Chrome captured actual source bytes equal final product. Audit Git HEAD was 1b711cf with the later e812f4a Tasks change already on disk; no new execution claimed."}
(OUT / "pm-p2-seal.json").write_bytes(json_bytes(report))
print(json.dumps({key: report[key] for key in ("product_head", "check_count", "failed", "main_calls", "COM_calls")}))
if report["failed"]:
    raise SystemExit(1)
