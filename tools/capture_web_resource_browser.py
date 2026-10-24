"""Read-only snapshots of the real browser service, preserving first raw results."""

import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.request import urlopen


def fetch(path):
    with urlopen("http://127.0.0.1:8767/api/" + path) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    parser.add_argument("--task", action="append", default=[])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    directory = root / "docs/webui/issue4/evidence/chrome-20261024"
    directory.mkdir(exist_ok=True)
    state_bytes = fetch("state")
    state = json.loads(state_bytes)
    target = directory / (args.label + ".json")
    if target.exists():
        raise FileExistsError(target)
    tasks = {}
    ids = {state[k] for k in ("active_task_id", "current_task_id") if state[k]}
    ids.update(row["run_id"] for row in state["runs"])
    ids.update(row["task_id"] for row in state["com_tasks"])
    ids.update(args.task)
    for task_id in ids:
        tasks[task_id] = json.loads(fetch("tasks/" + task_id))
        task = tasks[task_id]
        resources = task.get("resource_inputs", [])
        if task["worker_exited"] and resources:
            service_root = Path(resources[0]["worker_path"]).parent.parent
            source = service_root / task_id
            saved = directory / task_id
            saved.mkdir(exist_ok=True)
            for name in ("request.json", "com-input.json", "com.json"):
                if (source / name).is_file() and not (saved / name).exists():
                    (saved / name).write_bytes((source / name).read_bytes())
    for row in state["runs"]:
        run_id = row["run_id"]
        run = directory / run_id
        run.mkdir(exist_ok=True)
        for name, endpoint in (("manifest.json", ""), ("arrays.npz", "/raw")):
            path = run / name
            if not path.exists():
                path.write_bytes(fetch("runs/" + run_id + endpoint))
        latest = fetch("runs/" + run_id)
        assert latest == (run / "manifest.json").read_bytes(), (
            "Published core manifest changed"
        )
    target.write_text(
        json.dumps(
            {"captured_at": time.time(), "state": state, "tasks": tasks}, indent=2
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "file": str(target),
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                "active": state["active_task_id"],
                "runs": [r["run_id"] for r in state["runs"]],
                "com": [(r["task_id"], r["state"]) for r in state["com_tasks"]],
            }
        )
    )


if __name__ == "__main__":
    main()
