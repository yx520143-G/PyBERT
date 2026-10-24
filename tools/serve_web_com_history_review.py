"""Read-only Chrome review of real saved COM history; rejects calculation requests."""

import copy
import json
from pathlib import Path

import uvicorn

from pybert.web.config import normalize
from pybert.web.server import create_app
from pybert.web.tasks import BusyError

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/webui/issue4/evidence/chrome-20261024"


class SavedHistory:
    def __init__(self):
        snapshot = json.loads(
            (EVIDENCE / "final-idle.json").read_text(encoding="utf-8")
        )
        self.state = snapshot["state"]
        self.tasks = {
            key: {"data": value, "directory": EVIDENCE / key}
            for key, value in snapshot["tasks"].items()
        }
        # Constructor/config normalization only. No worker, main simulation or COM call.
        self.defaults = normalize({"mode": "defaults"})
        self.requests = []

    def index(self):
        return copy.deepcopy(self.state)

    def get(self, task_id):
        return copy.deepcopy(self.tasks[task_id]["data"])

    def directory(self, run_id):
        if not any(row["run_id"] == run_id for row in self.state["runs"]):
            raise KeyError("Saved core unavailable")
        return self.tasks[run_id]["directory"]

    def normalize(self, request):
        if request != {"mode": "defaults"}:
            raise BusyError("Read-only saved review; no input changes or calculations")
        return copy.deepcopy(self.defaults)


def main():
    manager = SavedHistory()
    app = create_app(manager)

    @app.middleware("http")
    async def read_only(request, call_next):
        from fastapi.responses import JSONResponse

        manager.requests.append({"method": request.method, "path": request.url.path})
        if request.url.path == "/_review/audit":
            return JSONResponse(
                {
                    "requests": manager.requests,
                    "main_simulations": 0,
                    "COM_calls": 0,
                    "workers": 0,
                    "current_task": manager.get(manager.state["current_task_id"]),
                    "active_task_id": manager.state["active_task_id"],
                }
            )
        if request.method != "GET" and request.url.path != "/api/normalize":
            return JSONResponse(
                status_code=409,
                content={"detail": "Read-only saved review; calculations disabled"},
            )
        return await call_next(request)

    uvicorn.run(app, host="127.0.0.1", port=8769, access_log=False)


if __name__ == "__main__":
    main()
