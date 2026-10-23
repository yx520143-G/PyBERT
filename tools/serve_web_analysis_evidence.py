"""Test-only hydration of two retained full fixtures; product API has no archive import yet."""

import json
import shutil
import sys
import threading
import time
from pathlib import Path

import uvicorn

from pybert.web.server import create_app
from pybert.web.tasks import Tasks


def main():
    source = Path(sys.argv[1]).resolve()
    root = source.parent / f"local/chrome-cache-{time.strftime('%Y%m%d-%H%M%S')}"
    manager = Tasks(root)
    for name in ("F-NRZ-01", "F-PAM4-01"):
        directory = root / name
        directory.mkdir(parents=True,exist_ok=True)
        dataset_source = source / name
        if "--legacy" in sys.argv and name == "F-NRZ-01":
            frozen = json.loads((Path(__file__).resolve().parents[1] / "docs/webui/issue3/fixtures/frozen-manifest.json").read_text(encoding="utf-8"))
            dataset_source = Path(frozen["inputs"][name]["source"])
        for filename in ("manifest.json", "arrays.npz"):
            shutil.copyfile(dataset_source / filename,directory / filename)
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        manifest["run_id"] = name
        manifest["logs"] = [f"Retained {name} raw from #2; #3 immutable helper projection. No new main simulation."]
        (directory / "manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        done = threading.Event()
        done.set()
        manager.tasks[name] = dict(directory=directory,done=done,data=dict(task_id=name,operation="run",state="succeeded",
            phase="retained fixture",cancel_requested=False,cancel_observed=False,worker_exited=True,logs=manifest["logs"]))
        manager.runs.append(name)
    uvicorn.run(create_app(manager),host="127.0.0.1",port=8765)


if __name__ == "__main__":
    main()
