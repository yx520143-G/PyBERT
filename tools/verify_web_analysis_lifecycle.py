"""Actual service failure/cancel-before-simulation; keep both retained successful results."""

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def api(path, body=None, binary=False):
    request = urllib.request.Request("http://127.0.0.1:8765/api/"+path,
        data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request) as response:
        value = response.read()
    return value if binary else json.loads(value)


def retained():
    state = api("state")
    return dict(active=state["active_task_id"], runs={r["run_id"]:dict(
        raw_sha256=hashlib.sha256(api(f"runs/{r['run_id']}/raw",binary=True)).hexdigest(),
        manifest=api(f"runs/{r['run_id']}")) for r in state["runs"]})


def main():
    mode = sys.argv[1]
    assert mode in ("failure","cancel")
    before = retained()
    assert before["active"] is None and len(before["runs"]) == 2
    frozen = json.loads((ROOT / "docs/webui/issue3/fixtures/frozen-manifest.json").read_text(encoding="utf-8"))
    item = frozen["inputs"]["F-NRZ-01"]
    request = dict(config=item["config"], input_hash=item["input_hash"] if mode == "cancel" else "deliberately-wrong-hash")
    dest = ROOT / f"docs/webui/issue3/evidence/lifecycle-{mode}-{time.strftime('%Y%m%d-%H%M%S')}"
    dest.mkdir()
    (dest / "frozen-request.json").write_text(json.dumps(request,indent=2),encoding="utf-8")
    task = api("runs",request)
    snapshots, conflicts = [task], []
    requested = None
    if mode == "cancel":
        requested = api(f"tasks/{task['task_id']}/cancel",{})
        snapshots.append(requested)
        for endpoint, body in (("normalize",dict(mode="load",config=item["config"])),("runs",request)):
            try:
                api(endpoint,body)
                conflicts.append(False)
            except urllib.error.HTTPError as err:
                conflicts.append(err.code == 409)
    deadline = time.monotonic()+60
    while not task["worker_exited"]:
        assert time.monotonic() < deadline
        task = api(f"tasks/{task['task_id']}")
        if task != snapshots[-1]:
            snapshots.append(task)
        time.sleep(.05)
    after = retained()
    passed = task["state"] == ("failed" if mode == "failure" else "cancelled") and before["runs"] == after["runs"] and after["active"] is None
    if mode == "cancel":
        passed = passed and requested["cancel_requested"] and not requested["worker_exited"] and task["cancel_observed"] and all(conflicts)
        # The request is observed before native simulation, so this adds no numerical control run.
        passed = passed and not any("Running" in s["phase"] or s["phase"] == "running" for s in snapshots)
    report = dict(mode=mode,passed=passed,task=task,snapshots=snapshots,conflicts=conflicts,
                  successful_ids=list(before["runs"]),retained_raw_hashes={k:v["raw_sha256"] for k,v in after["runs"].items()},
                  both_manifests_and_raw_unchanged=before["runs"] == after["runs"],
                  scope="Actual spawn/HTTP/exit lifecycle; cancel requested before native simulation, not a new numerical fixture")
    (dest / "report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(dest,task["task_id"],task["state"],passed,flush=True)
    assert passed


if __name__ == "__main__":
    main()
