"""Seal busy undo / legacy-capability evidence without running numerical engines."""

import json
import subprocess
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

from pybert.web.archive import json_bytes, sha256


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    evidence = root / "docs/webui/issue5/evidence"
    output = evidence / "pm-fixes-v8"
    log = root / "output/playwright/pm-fixes-v8.log"
    browser = json.loads(log.read_text(encoding="utf-8").split("### Result\n", 1)[1].split("\n", 1)[0])
    previous = json.loads((evidence / "pm-fixes-v6/report.json").read_text(encoding="utf-8"))
    report = {"product_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "main_calls": 0, "COM_calls": 0, "checks": [], "browser_log_sha256": sha256(log.read_bytes()),
              "source_sha256": {str(p.relative_to(root)): sha256(p.read_bytes()) for p in [*root.glob("src/pybert/web/*.py"), *root.glob("src/pybert/web/static/*"), Path(__file__)] if p.is_file()}}

    def check(label, passed):
        report["checks"].append({"check": label, "passed": bool(passed)})

    def get(route):
        with urlopen("http://127.0.0.1:8772/api/" + route) as response:
            return json.load(response)

    before, after, request = browser["before"], browser["after"], browser["patchRequest"]
    check("busy state has original base A and pending different reference B", before["native"]["config"]["ch_file"] == "example2_THRU.s4p" and before["draft"]["ch_file"] == "channel-B.s4p")
    check("busy undo preserves draft and actual resource event binding", before["draft"] == after["draft"] and before["bindings"] == after["bindings"] and before["selected"] == after["selected"])
    check("native base/runtime/source/guard preserved", all(before["native"][key] == after["native"][key] for key in ("config", "runtime_extensions", "source_record_id", "replay_guard")))
    keys = [row["field"] for row in request["patches"]]
    check("original native base and ordered observer patches applied after release", request["mode"] == "patch" and request["config"] == before["native"]["config"] and request["resource_bindings"] == before["bindings"] and keys.index("ch_file") < keys.index("rx_n_taps") < keys.index("rx_n_pre"))
    normalized = browser["normalized"]["config"]
    check("native observer result B/9/2", (normalized["ch_file"], normalized["rx_n_taps"], normalized["rx_n_pre"]) == ("channel-B.s4p", 9, 2))
    check("original replay guard still rejects Run after busy undo", browser["guard"]["status"] == 422 and "Saved run resource content changed/missing" in browser["guard"]["detail"]["detail"])
    check("legacy full archive disabled while subset entry stays enabled", browser["legacy"]["saveDisabled"] and browser["legacy"]["nativeEnabled"] and "物理轴" in browser["legacy"]["title"] and "archive不可用" in browser["legacy"]["stale"])
    sidecar = root / "output/playwright/pm-v8-legacy-sidecar.json"
    check("legacy report/dialog/downloaded sidecar agree on capability", browser["report"]["full_archive_available"] is False and "无法保存完整Web archive" in browser["guidance"] and json.loads(sidecar.read_text(encoding="utf-8")) == browser["report"])
    report["sidecar_sha256"] = sha256(sidecar.read_bytes())
    changed = {path: {"previous": digest, "current": sha256((root / path).read_bytes())} for path, digest in previous["source_sha256"].items() if path.startswith("src") and sha256((root / path).read_bytes()) != digest}
    report["changed_since_9484_product"] = changed
    check("only requested storage/UI product boundaries changed", set(changed) == {"src\\pybert\\web\\archive.py", "src\\pybert\\web\\legacy_results.py", "src\\pybert\\web\\static\\workbench.js", "src\\pybert\\web\\static\\results.js", "src\\pybert\\web\\static\\index.html"})
    report["tasks"] = {}
    for path in (output / "local/service").glob("*/request.json"):
        task = get("tasks/" + path.parent.name)
        report["tasks"][path.parent.name] = {key: task.get(key) for key in ("task_id", "operation", "phase", "state", "worker_exited", "created_at", "finished_at")}
    report["task_operations"] = dict(Counter(row["operation"] for row in report["tasks"].values()))
    check("all new workers are exited normalize observers", bool(report["tasks"]) and all(row["operation"] == "normalize" and row["worker_exited"] for row in report["tasks"].values()))
    report["held_task"] = get("tasks/" + browser["held"]["task_id"])
    check("held real observer exited successfully", report["held_task"]["state"] == "succeeded" and report["held_task"]["worker_exited"])
    state = get("state")
    report["state"] = state
    check("two old successes remain; no COM/active task", len(state["runs"]) == 2 and not state["com_tasks"] and state["active_task_id"] is None)
    for row in state["runs"]:
        source = evidence / "chrome-v2/local/service" / row["run_id"]
        copy = output / "local/service" / row["run_id"]
        check(row["run_id"] + " original manifest/NPZ preserved", all((source / name).read_bytes() == (copy / name).read_bytes() for name in ("manifest.json", "arrays.npz")))
    report["passed"] = all(row["passed"] for row in report["checks"])
    (output / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({"passed": report["passed"], "checks": report["checks"], "operations": report["task_operations"], "main_calls": 0, "COM_calls": 0}))
    if not report["passed"]:
        raise SystemExit(1)
