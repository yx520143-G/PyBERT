"""Bounded normalize-only Chrome supplement; numerical entry points are forbidden."""

import functools
import json
import shutil
import time
from pathlib import Path
from unittest.mock import patch

import uvicorn

from pyibisami.ami.model import AMIModel
from pybert.web.data import source_identity
from pybert.web.server import create_app
from pybert.web.tasks import Tasks
from pybert.web.worker import run_worker

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue10/evidence/p2-supplement"


def checked_worker(task_id, operation, request, directory, cancel, pipe, *, loads):
    assert operation == "normalize"
    original = AMIModel.__init__
    attempts = []

    def load(self, path, *args, **kwargs):
        with loads.get_lock():
            if loads.value >= 12:
                raise ValueError("P2 frozen library-load attempt budget exhausted")
            loads.value += 1
        attempts.append(str(path))
        (Path(directory) / "library-load-attempts.json").write_text(json.dumps(attempts), encoding="utf-8")
        return original(self, path, *args, **kwargs)

    def forbidden(*args, **kwargs):
        (Path(directory) / "forbidden-entry.json").write_text("unexpected numerical entry blocked", encoding="utf-8")
        raise AssertionError("P2 supplement forbids numerical execution")

    with patch.object(AMIModel, "__init__", load), patch.object(AMIModel, "initialize", forbidden), \
         patch.object(AMIModel, "getWave", forbidden), patch("pybert.web.worker.my_run_simulation", forbidden):
        run_worker(task_id, operation, request, directory, cancel, pipe)


class ChecksOnly(Tasks):
    def start(self, operation, request, **kwargs):
        if operation != "normalize":
            raise ValueError("P2 supplement permits normalization only; Main/coopt/COM budgets are zero")
        return super().start(operation, request, **kwargs)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    for name in source_identity():
        target = OUT / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / name, target)
    fixture = ROOT / "docs/webui/issue10/fixtures/v4-final/A-NRZ-Native-GetWave.json"
    shutil.copyfile(fixture, OUT / "frozen-input.json")
    shutil.copyfile(__file__, OUT / "serve_web_ami_p2.py")
    (OUT / "before.json").write_text(json.dumps({"frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "Main": 0, "coopt": 0, "AMI_Init": 0, "AMI_GetWave": 0, "COM": 0,
        "max_library_load_attempts": 12, "source": source_identity(),
        "allowed_changes": "clocks true/false; Tx modal Native controls preserve Rx; no Run/Tune",
        "fixture": "v4-final NRZ Native/GetWave; original content identities, parameters and resources unchanged"}, indent=2), encoding="utf-8")
    manager = ChecksOnly(ROOT / ".pybert-web/issue10-p2-service")
    loads = manager.context.Value("i", 0)
    manager.worker = functools.partial(checked_worker, loads=loads)
    manager._remove_directory = lambda directory: None  # retain all task originals for this harness
    try:
        uvicorn.run(create_app(manager), host="127.0.0.1", port=8785)
    finally:
        (OUT / "library-load-total.json").write_text(json.dumps({"attempts": loads.value}), encoding="utf-8")
