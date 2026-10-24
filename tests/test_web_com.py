"""COM task faults/cancellation without substituting fake values for numerical evidence."""

import json
import logging
import threading
import time
from pathlib import Path

import pytest

from pybert.web.config import input_hash, new_engine, snapshot
from pybert.web.resources import Resources
from pybert.web.tasks import BusyError, Tasks
from pybert.web.worker import run_worker

ROOT = Path(__file__).resolve().parents[1]


class Connection:
    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(message)

    def close(self):
        pass


def inputs(tmp_path):
    store = Resources(tmp_path / "resources")
    thru = store.local(str(ROOT / "PyChOpMarg/chnl_data/example2_THRU.s4p"))
    cfg = store.local(
        str(ROOT / "PyChOpMarg/config/config_com_ieee8023dj_PyChOpMarg_vs_MATLAB.xls")
    )
    return {
        "frozen_resources": [
            store.freeze(thru["resource_id"], "com_thru", "a.s4p"),
            store.freeze(cfg["resource_id"], "com_cfg_file", "c.xls"),
        ],
        "parameter_source": "spreadsheet",
    }


@pytest.mark.parametrize(
    "fault",
    ["sentinel", "nonfinite", "exception", "logged_error", "cancel_after_return"],
)
def test_com_worker_faults_never_publish_numeric_success(tmp_path, monkeypatch, fault):
    import pybert.web.com as module

    cancel = threading.Event()
    connection = Connection()

    def helper(*args, **kwargs):
        if fault == "logged_error":
            logging.getLogger("native-component-test").error("injected native ERROR")
            return 5.0
        cancel.set()
        if fault == "exception":
            raise RuntimeError("native exception while cancellation requested")
        return (
            -999.0
            if fault == "sentinel"
            else float("nan")
            if fault == "nonfinite"
            else 5.0
        )

    monkeypatch.setattr(module, "calc_com", helper)
    run_worker("fault", "com", inputs(tmp_path), str(tmp_path), cancel, connection)
    result = connection.messages[-1]
    assert result["status"] == (
        "cancelled" if fault == "cancel_after_return" else "failed"
    )
    assert not (tmp_path / "com.json").exists()
    if fault == "cancel_after_return":
        assert result["cancel_observed"]
    if fault == "exception":
        assert (
            result["error_type"] == "RuntimeError"
            and "native exception" in result["error"]
        )


def test_real_spawn_com_cancelled_before_validation_exits(tmp_path):
    manager = Tasks(tmp_path)
    resource = manager.resources.add(
        "not-consumed.s4p", b"prevalidation lifecycle test", {"kind": "test-only"}
    )
    task = manager.start(
        "com",
        {
            "thru_resource_id": resource["resource_id"],
            "parameter_source": "IEEE_8023dj defaults",
        },
        cancel_requested=True,
    )
    assert manager.tasks[task["task_id"]]["done"].wait(20)
    final = manager.get(task["task_id"])
    assert (
        final["state"] == "cancelled"
        and final["cancel_requested"]
        and final["cancel_observed"]
        and final["worker_exited"]
    )
    assert (
        final["cancel_requested_at"]
        <= final["cancel_observed_at"]
        <= final["worker_exit_confirmed_at"]
    )
    assert manager.active is None


def late_cancel_core(task_id, operation, request, directory, cancel, pipe):
    if operation == "com":
        return run_worker(task_id, operation, request, directory, cancel, pipe)
    Path(directory, "manifest.json").write_text(
        json.dumps(
            {
                "run_id": task_id,
                "input_hash": "stub",
                "effective_input": {},
                "summary": {},
                "resource_hash": "stub",
                "execution_strategy": {"deferred_com": request["deferred_com"]},
                "method": "lifecycle stub",
            }
        ),
        encoding="utf-8",
    )
    pipe.send(
        {"kind": "terminal", "task_id": task_id, "status": "succeeded", "result": {}}
    )
    time.sleep(0.8)
    pipe.close()


def test_late_core_abort_is_inherited_by_child_after_core_join(tmp_path):
    manager = Tasks(tmp_path, worker=late_cancel_core)
    resource = manager.resources.add(
        "not-consumed.s4p",
        b"lifecycle stub, not numerical evidence",
        {"kind": "test-only"},
    )
    config = snapshot(new_engine()) | {
        "inter_sel": "single",
        "ch_file": "not-consumed.s4p",
        "enable_com": True,
    }
    task = manager.start(
        "run",
        {
            "config": config,
            "input_hash": input_hash(config),
            "resource_bindings": {"ch_file": resource["resource_id"]},
        },
    )
    deadline = time.monotonic() + 20
    while (
        manager.get(task["task_id"])["phase"] != "worker finishing; waiting for exit"
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    assert manager.active == task["task_id"]
    manager.cancel(task["task_id"])
    assert manager.tasks[task["task_id"]]["done"].wait(20)
    with manager.lock:
        child = manager.current
        assert child != task["task_id"]
        original = (manager.directory(task["task_id"]) / "manifest.json").read_bytes()
    with pytest.raises(BusyError):
        manager.start("normalize", {})
    assert manager.tasks[child]["done"].wait(20)
    assert manager.get(task["task_id"])["state"] == "succeeded"
    assert (
        manager.get(child)["state"] == "cancelled"
        and manager.get(child)["cancel_observed"]
    )
    assert (
        manager.directory(task["task_id"]) / "manifest.json"
    ).read_bytes() == original
    assert manager.active is None
