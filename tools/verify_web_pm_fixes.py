"""Audit PM-specific observer-only Chrome results and fixed-source applicability."""

import json
import subprocess
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

from pybert.web.archive import json_bytes, sha256


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    evidence = root / "docs/webui/issue5/evidence"
    output = evidence / "pm-fixes-v6"
    log = root / "output/playwright/pm-fixes-v7.log"
    browser = json.loads(log.read_text(encoding="utf-8").split("### Result\n", 1)[1].split("\n", 1)[0])
    fixture = json.loads((output / "fixture-report.json").read_text(encoding="utf-8"))
    saved = json.loads((evidence / "saved-roundtrip-20261024-114225/report.json").read_text(encoding="utf-8"))
    previous = json.loads((evidence / "closeout-v1/report.json").read_text(encoding="utf-8"))
    report = {"product_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "main_calls": 0, "COM_calls": 0, "checks": [], "tasks": {},
              "browser_log_sha256": sha256(log.read_bytes()),
              "source_sha256": {str(p.relative_to(root)): sha256(p.read_bytes()) for p in [*root.glob("src/pybert/web/*.py"), *root.glob("src/pybert/web/static/*"), Path(__file__)] if p.is_file()}}

    def check(label, passed):
        report["checks"].append({"check": label, "passed": bool(passed)})

    def get(route):
        with urlopen("http://127.0.0.1:8772/api/" + route) as response:
            return json.load(response)

    check("real archive input/runtime/resource/source/guard exact after reset+undo", all(browser["before"]["snapshot"][key] == browser["restored"]["snapshot"][key] for key in ("config", "runtime_extensions", "resource_bindings", "source_record_id", "replay_guard")) and browser["before"]["draft"] == browser["restored"]["draft"])
    error = browser["guard_rejection"]
    check("same-name different B rejected by original A guard", error["status"] == 422 and all(row["sha256"] in error["detail"]["detail"] for row in fixture["resources"].values()))
    check("coherent missing/wrong input_hash rejected atomically in Chrome", len(browser["rejectedFiles"]) == 2 and browser["rejectedFiles"][0]["unchanged"] == browser["rejectedFiles"][1]["unchanged"] and all("input_hash" in row["status"] for row in browser["rejectedFiles"]))
    check("unknown retained original value and blocking restored", browser["retainedBefore"]["retained"] == browser["retainedAfter"]["retained"] and browser["retainedAfter"]["retained"]["future_physical_input"]["value"] == {"gain": 123} and bool(browser["retainedAfter"]["error"]))
    check("invalid JSON undo restores storage availability warning", "仅当前页面保留" in browser["invalid_storage_status"])
    check("raw2/3/4 real saved roundtrips exact with final Python source", saved["passed"] and all(sha256((root / path).read_bytes()) == digest for path, digest in saved["actual_sources"].items()))
    changed = {path: {"previous": digest, "current": sha256((root / path).read_bytes())} for path, digest in previous["actual_source_sha256"].items() if path.startswith("src") and sha256((root / path).read_bytes()) != digest}
    report["changed_since_first_delivery"] = changed
    check("only PM-requested archive/app/workbench product sources changed", set(changed) == {"src\\pybert\\web\\archive.py", "src\\pybert\\web\\static\\app.js", "src\\pybert\\web\\static\\workbench.js"})
    state = get("state")
    report["state"] = state
    seeded = {"c4532a94-3702-44e9-9869-106b3198cf79", "573aed1e-b3b5-4977-8d6b-a482b94fdd2a"}
    for path in (output / "local/service-v2").glob("*/request.json"):
        task = get("tasks/" + path.parent.name)
        report["tasks"][path.parent.name] = {key: task.get(key) for key in ("task_id", "operation", "state", "worker_exited", "created_at", "finished_at")}
    check("all newly created tasks are observer normalization only", bool(report["tasks"]) and all(row["operation"] == "normalize" and row["worker_exited"] for row in report["tasks"].values()))
    check("two original successes and no COM/active task", {row["run_id"] for row in state["runs"]} == seeded and not state["com_tasks"] and state["active_task_id"] is None)
    check("archive/channel A originals unchanged", sha256(Path(fixture["source"]).read_bytes()) == fixture["source_sha256"] and sha256(Path(fixture["resources"]["A"]["path"]).read_bytes()) == fixture["resources"]["A"]["sha256"])
    for run_id in seeded:
        source = evidence / "chrome-v2/local/service" / run_id
        copy = output / "local/service-v2" / run_id
        check(run_id + " original manifest/NPZ unchanged in replay", all((source / name).read_bytes() == (copy / name).read_bytes() for name in ("manifest.json", "arrays.npz")))
    report["task_operations"] = dict(Counter(row["operation"] for row in report["tasks"].values()))
    report["passed"] = all(row["passed"] for row in report["checks"])
    (output / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({"passed": report["passed"], "checks": report["checks"], "operations": report["task_operations"], "main_calls": 0, "COM_calls": 0}))
    if not report["passed"]:
        raise SystemExit(1)
