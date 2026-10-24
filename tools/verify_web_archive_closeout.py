"""Seal final source applicability and saved Chrome artifacts; no engine calls."""

import json
import subprocess
import zipfile
from pathlib import Path

from pybert.web.archive import json_bytes, sha256


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = root / "docs/webui/issue5/evidence"
    output = evidence / "closeout-v1"
    output.mkdir(exist_ok=False)
    saved = json.loads((evidence / "saved-roundtrip-20261024-104338/report.json").read_text(encoding="utf-8"))
    raw = json.loads((evidence / "chrome-raw-audit-20261024-110155/report.json").read_text(encoding="utf-8"))
    report = {"product_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "main_calls": 0, "COM_calls": 0, "checks": [],
              "actual_source_sha256": {str(path.relative_to(root)): sha256(path.read_bytes()) for path in [*root.glob("src/pybert/web/*.py"), *root.glob("src/pybert/web/static/*"), Path(__file__)] if path.is_file()}}

    def check(label, passed):
        report["checks"].append({"check": label, "passed": bool(passed)})

    check("all Python sources executed in fixed-source saved roundtrip still exact", all(sha256((root / path).read_bytes()) == digest for path, digest in saved["actual_sources"].items()))
    changes = {path: {"observed": digest, "current": sha256((root / path).read_bytes())} for path, digest in raw["actual_source_sha256"].items() if sha256((root / path).read_bytes()) != digest}
    report["changes_after_real_runs"] = changes
    check("real runs remain applicable to all backend/physical sources; only draft/workbench UI subsequently changed", set(changes) == {"src\\pybert\\web\\static\\draft.js", "src\\pybert\\web\\static\\workbench.js"})
    report["real_run_arrays"] = {name: len(row["arrays"]) for name, row in raw["runs"].items()}
    report["real_run_costs"] = raw["costs"]
    source_report = json.loads((evidence / "com-snapshot/source-report-v2.json").read_text(encoding="utf-8"))
    check("all original historical COM/core files unchanged", all(sha256(Path(path).read_bytes()) == digest for path, digest in source_report["source_files"].items()))
    with zipfile.ZipFile(root / "output/playwright/historical-COM-running-v3.pybert_run") as first, zipfile.ZipFile(root / "output/playwright/historical-COM-running-v3-resaved.pybert_run") as second:
        original = json.loads(first.read("manifest.json"))
        resaved = json.loads(second.read("manifest.json"))
        core = Path(next(path for path in source_report["source_files"] if path.endswith("manifest.json")))
        check("Chrome historical parent manifest/NPZ exact original", original["source_manifest_utf8"].encode("utf-8") == core.read_bytes() and first.read("arrays.npz") == (core.parent / "arrays.npz").read_bytes())
        check("Chrome reopen/resave subfunctions snapshot exact despite same-ID success in session", original["subfunctions"] == resaved["subfunctions"] and first.read("arrays.npz") == second.read("arrays.npz") and original["run"] == resaved["run"])
        snapshot = original["subfunctions"]["linked_tasks"]["a803f4ca-83f2-4031-a31c-af5213fc71d8"]
        check("Chrome captured real active task exactly and did not read unexited files", snapshot["task"] == source_report["snapshots"]["running"] and all(row["availability"] == "waiting_for_exit" for row in snapshot["files"].values()))
    report["chrome_results"] = {}
    for name in ("phase10d-restart", "phase11c-com-snapshot", "phase12b-storage", "phase13-selection-before", "phase13-selection-after"):
        path = root / f"output/playwright/{name}.log"
        text = path.read_text(encoding="utf-8")
        value = json.loads(text.split("### Result\n", 1)[1].split("\n", 1)[0])
        report["chrome_results"][name] = {"source_sha256": sha256(path.read_bytes()), "result": value}
        check(name + " completed without main/COM", value["main_calls"] == 0 and value["COM_calls"] == 0)
    report["passed"] = all(row["passed"] for row in report["checks"])
    (output / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({"report": str(output / "report.json"), "passed": report["passed"], "checks": report["checks"], "arrays": report["real_run_arrays"]}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
