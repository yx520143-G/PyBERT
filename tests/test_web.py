"""Web observer semantics, native postconditions and process ownership contracts."""

import json
import time
import threading

import pytest
import yaml

from pybert.web.config import input_hash, new_engine, normalize, snapshot
from pybert.web.tasks import BusyError, Tasks
from pybert.web.worker import run_worker
from pybert.web.data import adapter_sha


def wait_for(task, manager, timeout=30):
    assert manager.tasks[task["task_id"]]["done"].wait(timeout), "worker did not exit"
    return manager.get(task["task_id"])


def terminal_then_delay(task_id, operation, request, directory, cancel, pipe):
    pipe.send({"task_id": task_id, "kind": "terminal", "status": "succeeded", "result": {}, "cancel_observed": False})
    time.sleep(0.8)
    pipe.close()


def missing_terminal(task_id, operation, request, directory, cancel, pipe):
    pipe.close()


def observed_cancel(task_id, operation, request, directory, cancel, pipe):
    cancel.wait(10)
    pipe.send({"task_id": task_id, "kind": "cancel_observed"})
    pipe.send({"task_id": task_id, "kind": "terminal", "status": "cancelled", "cancel_observed": True})
    time.sleep(0.3)
    pipe.close()


def test_native_observer_patch_and_full_load():
    p = new_engine()
    config = snapshot(p)
    original = [row[1] for row in config["rx_taps"]]
    result = normalize({"mode": "patch", "config": config, "patches": [{"field": "rx_n_pre", "value": 6}]})
    p.rx_n_pre = 6
    assert result["config"]["rx_taps"] == snapshot(p)["rx_taps"]
    assert [row[1] for row in result["config"]["rx_taps"]] != original
    loaded = normalize({"mode": "load", "config": result["config"]})
    assert loaded["input_hash"] == result["input_hash"]
    assert loaded["config"]["rx_taps"] == result["config"]["rx_taps"]


@pytest.mark.parametrize("count,expected_pre", [(3, 2), (0, 0)])
def test_tap_count_reduction_uses_native_clamp(count, expected_pre):
    config = snapshot(new_engine())
    assert config["rx_n_taps"] == 15 and config["rx_n_pre"] == 5
    result = normalize({"mode": "patch", "config": config, "patches": [{"field": "rx_n_taps", "value": count}]})
    assert result["config"]["rx_n_pre"] == expected_pre
    assert sum(row[0] for row in result["config"]["rx_taps"]) == count


@pytest.mark.parametrize("count,pre", [(0, 0), (1, 0), (100, 99)])
def test_ffe_dimensions(count, pre):
    config = snapshot(new_engine())
    result = normalize(
        {
            "mode": "patch",
            "config": config,
            "patches": [{"field": "rx_n_taps", "value": count}, {"field": "rx_n_pre", "value": pre}],
        }
    )
    assert len(result["config"]["rx_taps"]) == 100
    assert sum(row[0] for row in result["config"]["rx_taps"]) == count
    assert result["config"]["rx_n_pre"] == pre


@pytest.mark.parametrize(
    "patch",
    [
        {"rx_n_taps": 101},
        {"rx_n_taps": 0, "rx_n_pre": 1},
        {"vod": ""},
        {"rn": float("nan")},
        {"eye_bits": 15000},
        {"rx_eq_sel": "IBIS-AMI"},
        {"ctle_enable": True, "ctle_sel": "File"},
        {"runtime_extensions": {"rlm": 0.9}},
    ],
)
def test_invalid_and_unsupported_inputs(patch):
    with pytest.raises(ValueError):
        normalize({"mode": "load", "config": snapshot(new_engine()) | patch})


def test_inactive_paths_do_not_load(monkeypatch):
    config = snapshot(new_engine()) | {
        "ctle_enable": False,
        "ctle_sel": "File",
        "use_ctle_file": True,
        "ctle_file": "missing.dat",
        "tx_ibis_file": "missing.ibs",
        "rx_dll_file": "missing.dll",
    }
    result = normalize({"mode": "load", "config": config})
    assert result["config"]["tx_ibis_file"] == "missing.ibs"
    assert result["config"]["ctle_sel"] == "File"


def test_yaml_round_trip_and_reject_object():
    a = normalize({"mode": "defaults"})
    b = normalize({"mode": "load", "yaml": a["yaml"]})
    assert a["input_hash"] == b["input_hash"]
    with pytest.raises(yaml.constructor.ConstructorError):
        normalize({"mode": "load", "yaml": "!!python/object/apply:os.system ['bad']"})


def test_dfe_hole_and_input_level_preserved():
    config = snapshot(new_engine())
    config["dfe_tap_tuners"][1][0] = False
    result = normalize({"mode": "load", "config": config})
    assert result["config"]["dfe_tap_tuners"][2][0]
    assert "1 taps" in result["warnings"][0]
    assert any("not consumed" in message for message in result["warnings"])
    assert result["config"]["decision_scaler"] == config["decision_scaler"]


def test_terminal_envelope_does_not_release_slot(tmp_path):
    manager = Tasks(tmp_path, worker=terminal_then_delay)
    task = manager.start("normalize", {})
    time.sleep(0.2)
    with pytest.raises(BusyError):
        manager.start("normalize", {})
    final = wait_for(task, manager)
    assert final["worker_exited"] and final["state"] == "succeeded"
    assert manager.active is None


def test_cancel_requires_observed_and_join(tmp_path):
    manager = Tasks(tmp_path, worker=observed_cancel)
    task = manager.start("normalize", {})
    requested = manager.cancel(task["task_id"])
    assert requested["state"] == "cancel_requested" and not requested["worker_exited"]
    with pytest.raises(BusyError):
        manager.start("normalize", {})
    final = wait_for(task, manager)
    assert final["state"] == "cancelled" and final["cancel_observed"] and final["worker_exited"]


def test_missing_envelope_is_failure_even_if_cancel_requested(tmp_path):
    manager = Tasks(tmp_path, worker=missing_terminal)
    task = manager.start("normalize", {})
    manager.cancel(task["task_id"])
    final = wait_for(task, manager)
    assert final["state"] == "failed" and final["worker_exited"]


def test_normalize_uses_real_spawn(tmp_path):
    manager = Tasks(tmp_path)
    result = manager.normalize({"mode": "defaults"})
    assert result["input_hash"] == input_hash(result["config"])
    assert manager.get(manager.current)["worker_exited"]


def test_adapter_identity_is_independent_of_process_cwd(tmp_path, monkeypatch):
    expected = adapter_sha()
    assert expected != "unavailable"
    monkeypatch.chdir(tmp_path)
    assert adapter_sha() == expected


def test_completed_task_history_is_bounded_and_keeps_successes(tmp_path):
    manager = Tasks(tmp_path)
    manager.runs = ["keep-a", "keep-b"]
    for task_id in ["keep-a", "keep-b", *[f"old-{i}" for i in range(31)]]:
        directory = tmp_path / task_id
        directory.mkdir()
        done = threading.Event()
        done.set()
        manager.tasks[task_id] = {"done": done, "directory": directory, "data": {"task_id": task_id}}
    manager.normalize({"mode": "defaults"})
    assert len(manager.tasks) == 32
    assert manager.get("keep-a")["task_id"] == "keep-a"
    assert manager.get("keep-b")["task_id"] == "keep-b"
    with pytest.raises(KeyError):
        manager.get("old-0")


def test_native_preflight_return_cannot_succeed(tmp_path, monkeypatch):
    import multiprocessing
    from pybert.web import worker

    monkeypatch.setattr(
        worker, "my_run_simulation", lambda p, **kwargs: setattr(p, "status", "ERROR: preflight return")
    )
    manager = multiprocessing.get_context("spawn")
    receive, send = manager.Pipe(duplex=False)
    config = normalize({"mode": "load", "config": snapshot(new_engine())})["config"]
    run_worker(
        "early-return",
        "run",
        {"config": config, "input_hash": input_hash(config)},
        str(tmp_path),
        manager.Event(),
        send,
    )
    terminal = json.loads((tmp_path / "terminal.json").read_text())
    assert terminal["status"] == "failed" and "did not complete" in terminal["error"]
    assert not (tmp_path / "manifest.json").exists()
    receive.close()
