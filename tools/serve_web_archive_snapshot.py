"""Replay preserved #4 task snapshots for Chrome archive checks; never start a worker."""

import copy
import json
import shutil
from pathlib import Path

import uvicorn

from pybert.web.archive import sha256
from pybert.web.server import create_app
from pybert.web.tasks import BusyError, Tasks


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/evidence/chrome-20261024")
OUTPUT = ROOT / "docs/webui/issue5/evidence/com-snapshot/local/service-v2"
CORE = "c3cadfdc-13e8-4ed9-bee3-b3b11462cd96"
CHILD = "a803f4ca-83f2-4031-a31c-af5213fc71d8"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


class SnapshotTasks(Tasks):
    def start(self, *_args, **_kwargs):
        raise BusyError("Read-only historical snapshot replay: all workers/main/COM disabled.")

    def normalize(self, _request):
        return copy.deepcopy(self.defaults)


if __name__ == "__main__":
    manager = SnapshotTasks(OUTPUT)
    final = read(SOURCE / "final-idle.json")
    transitions = read(SOURCE / "run-child-transitions.json")
    running = next(row["task"] for row in transitions["events"] if row["task"]["task_id"] == CHILD and row["task"]["phase"].startswith("native COM helper"))
    identities = {}
    for task_id in (CORE, CHILD):
        target = OUTPUT / task_id
        target.mkdir(exist_ok=False)
        source = next(path.parent for path in SOURCE.rglob("manifest.json" if task_id == CORE else "com-input.json") if path.parent.name == task_id)
        for name in ("manifest.json", "arrays.npz", "com-input.json", "com.json", "terminal.json", "request.json"):
            if (source / name).exists():
                shutil.copyfile(source / name, target / name)
                identities[str(source / name)] = sha256((source / name).read_bytes())
        manager.tasks[task_id] = {"data": copy.deepcopy(final["tasks"][task_id]), "directory": target}
    defaults_file = ROOT / "docs/webui/issue5/evidence/chrome-v2/local/service/77a50571-905b-4dc0-8a3d-42fcda08d989/terminal.json"
    manager.defaults = read(defaults_file)["result"]
    manager.runs = [CORE]
    manager.current = CHILD
    manager.active = CHILD
    manager.tasks[CHILD]["data"] = copy.deepcopy(running)
    app = create_app(manager)

    @app.post("/_fixture/final")
    def final_snapshot():
        with manager.lock:
            manager.tasks[CHILD]["data"] = copy.deepcopy(final["tasks"][CHILD])
            manager.active = None
        return {"mode": "historical succeeded snapshot", "workers_started": 0, "main_calls": 0, "COM_calls": 0}

    app.router.routes.insert(0, app.router.routes.pop())
    report = {"mode": "historical snapshot replay; no engine", "source_files": identities,
              "snapshots": {"running": running, "final": final["tasks"][CHILD]},
              "transition_source_sha256": sha256((SOURCE / "run-child-transitions.json").read_bytes()),
              "final_source_sha256": sha256((SOURCE / "final-idle.json").read_bytes()),
              "defaults_source_sha256": sha256(defaults_file.read_bytes()), "main_calls": 0, "COM_calls": 0}
    (OUTPUT.parent.parent / "source-report-v2.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    uvicorn.run(app, host="127.0.0.1", port=8771)
