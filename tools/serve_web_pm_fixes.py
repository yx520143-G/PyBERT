"""Local #5 PM regressions: native configuration observers only; no main/COM execution."""

from pathlib import Path
import json
import shutil

import uvicorn

from pybert.web.server import create_app
from pybert.web.tasks import Tasks
from pybert.web.worker import run_worker


def observers_only(task_id, operation, request, directory, cancel, pipe):
    if operation == "normalize":
        run_worker(task_id, operation, request, directory, cancel, pipe)
    else:
        pipe.send({"task_id": task_id, "kind": "terminal", "status": "failed",
                   "error": "PM regression service forbids all main/COM execution."})
        pipe.close()


if __name__ == "__main__":
    evidence = Path(__file__).resolve().parents[1] / "docs/webui/issue5/evidence"
    manager = Tasks(evidence / "pm-fixes-v6/local/service-v2", worker=observers_only)
    for run_id in ("c4532a94-3702-44e9-9869-106b3198cf79", "573aed1e-b3b5-4977-8d6b-a482b94fdd2a"):
        source = evidence / "chrome-v2/local/service" / run_id
        target = manager.root / run_id
        target.mkdir(exist_ok=False)
        for name in ("manifest.json", "arrays.npz"):
            shutil.copyfile(source / name, target / name)
        task = json.loads((evidence / "chrome-raw-audit-20261024-110155" / f"task-{run_id}.json").read_text(encoding="utf-8"))
        manager.tasks[run_id] = {"data": task, "directory": target}
        manager.runs.append(run_id)
    uvicorn.run(create_app(manager), host="127.0.0.1", port=8772)
