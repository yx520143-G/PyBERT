"""对本机实际服务验证失败/合作取消；旧成功缓存不得被覆盖。"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from pybert.web.config import input_hash

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue2/evidence"


def api(path, body=None):
    request = urllib.request.Request("http://127.0.0.1:8765/api/"+path,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def main():
    mode = sys.argv[1]
    config = json.loads((ROOT / "docs/webui/issue2/fixtures/F-NRZ-01.json").read_text())
    before = api("state")
    assert before["active_task_id"] is None
    config = api("normalize",{"mode": "load","config": config})["config"]
    expected_hash = input_hash(config)
    if mode == "cancel":
        config["nbits"] = 100000
        config = api("normalize",{"mode": "load","config": config})["config"]
        expected_hash = input_hash(config)
    request = {"config": config,"input_hash": "deliberately-wrong-hash" if mode == "failure" else expected_hash,"draft_revision": 0}
    # 完整输入在本次数值任务前保存，取消用例只验生命周期，不做数值资格声明。
    (OUT / f"lifecycle-{mode}-input.json").write_text(json.dumps(request,indent=2),encoding="utf-8")
    task = api("runs",request)
    task_id = task["task_id"]
    phases = []
    conflicts = []
    deadline = time.monotonic()+120
    requested = None
    while True:
        assert time.monotonic()<deadline
        task = api(f"tasks/{task_id}")
        if not phases or phases[-1] != task["phase"]:
            phases.append(task["phase"])
        if mode == "cancel" and task["phase"] == "Running DFE/CDR..." and requested is None:
            requested = api(f"tasks/{task_id}/cancel",{})
            for path,body in (("normalize",{"mode": "load","config": config}),("runs",request)):
                try:
                    api(path,body)
                    conflicts.append(False)
                except urllib.error.HTTPError as err:
                    conflicts.append(err.code==409)
        if task["worker_exited"]:
            break
        time.sleep(.05)
    after = api("state")
    retained = [r["run_id"] for r in before["runs"]] == [r["run_id"] for r in after["runs"]]
    passed = task["state"] == ("failed" if mode=="failure" else "cancelled") and retained and after["active_task_id"] is None
    if mode == "cancel":
        passed = passed and requested is not None and requested["state"]=="cancel_requested" and not requested["worker_exited"] and task["cancel_observed"] and all(conflicts) and len(conflicts)==2
    report = {"mode": mode,"task": task,"requested": requested,"phases": phases,"busy_conflicts": conflicts,
                  "successful_runs_before": [r["run_id"] for r in before["runs"]],
                  "successful_runs_after": [r["run_id"] for r in after["runs"]],"passed": passed}
    (OUT / f"lifecycle-{mode}.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"mode": mode,"passed": passed,"state": task["state"],"task_id": task_id,"phases": phases}))
    assert passed


if __name__ == "__main__":
    main()
