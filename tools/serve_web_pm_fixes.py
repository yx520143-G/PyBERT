"""Local #5 PM regressions: native configuration observers only; no main/COM execution."""

from pathlib import Path

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
    root = Path(__file__).resolve().parents[1] / "docs/webui/issue5/evidence/pm-fixes-v6/local/service"
    uvicorn.run(create_app(Tasks(root, worker=observers_only)), host="127.0.0.1", port=8772)
