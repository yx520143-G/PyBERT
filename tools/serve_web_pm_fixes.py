"""Local #5 PM regressions: native configuration observers only; no main/COM execution."""

from pathlib import Path
import json
import shutil
import time
import uuid

import uvicorn

from pybert.web.server import create_app
from pybert.web.tasks import Tasks
from pybert.web.worker import run_worker


def observers_only(task_id, operation, request, directory, cancel, pipe):
    if operation == "normalize":
        gate = request.get("_fixture_observer_gate")
        if gate:
            pipe.send({"task_id": task_id, "kind": "phase", "phase": "fixture observer gate; main/COM disabled"})
            while not Path(gate).exists() and not cancel.is_set():
                time.sleep(0.05)
        run_worker(task_id, operation, {key: value for key, value in request.items() if key != "_fixture_observer_gate"}, directory, cancel, pipe)
    else:
        pipe.send({"task_id": task_id, "kind": "terminal", "status": "failed",
                   "error": "PM regression service forbids all main/COM execution."})
        pipe.close()


if __name__ == "__main__":
    evidence = Path(__file__).resolve().parents[1] / "docs/webui/issue5/evidence"
    manager = Tasks(evidence / "pm-fixes-v8/local/service", worker=observers_only)
    configs = {}
    for run_id in ("c4532a94-3702-44e9-9869-106b3198cf79", "573aed1e-b3b5-4977-8d6b-a482b94fdd2a"):
        source = evidence / "chrome-v2/local/service" / run_id
        target = manager.root / run_id
        target.mkdir(exist_ok=False)
        for name in ("manifest.json", "arrays.npz"):
            shutil.copyfile(source / name, target / name)
        task = json.loads((evidence / "chrome-raw-audit-20261024-110155" / f"task-{run_id}.json").read_text(encoding="utf-8"))
        manager.tasks[run_id] = {"data": task, "directory": target}
        manager.runs.append(run_id)
        configs[run_id] = json.loads((source / "manifest.json").read_text(encoding="utf-8"))["requested_input"]
    app = create_app(manager)
    gates = {}

    @app.post("/_fixture/hold-observer")
    def hold_observer():
        task_id = str(uuid.uuid4())
        gate = manager.root / f"{task_id}.release"
        gates[task_id] = gate
        return manager.start("normalize", {"mode": "load", "config": configs["573aed1e-b3b5-4977-8d6b-a482b94fdd2a"],
                                           "_fixture_observer_gate": str(gate)}, task_id=task_id)

    app.router.routes.insert(0, app.router.routes.pop())

    @app.post("/_fixture/release-observer")
    def release_observer(request: dict):
        gates[request["task_id"]].touch(exist_ok=False)
        return {"released": request["task_id"], "main_calls": 0, "COM_calls": 0}

    app.router.routes.insert(0, app.router.routes.pop())
    uvicorn.run(app, host="127.0.0.1", port=8772)
