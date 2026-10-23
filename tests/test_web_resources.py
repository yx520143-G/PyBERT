"""Resource content, restricted imports, and serial child-task invariants."""

import base64
import copy
import json
import pickle
import time
from pathlib import Path

import pytest

from pybert.configuration import PyBertCfg
from pybert.web.config import input_hash, new_engine, normalize, parse_legacy, snapshot, validate
from pybert.web.resources import Resources, projection
from pybert.web.tasks import BusyError, Tasks


def test_registered_content_survives_external_change_and_preserves_duplicates(tmp_path):
    store = Resources(tmp_path / "resources")
    path = tmp_path / "same.s4p"
    path.write_bytes(b"original nonempty bytes")
    first = store.local(str(path))
    path.write_bytes(b"changed bytes")
    second = store.local(str(path))
    assert first["resource_id"] != second["resource_id"]
    config = snapshot(new_engine()) | {"inter_sel": "multiple", "ch_files": [str(path)] * 3}
    ids = [second["resource_id"], first["resource_id"], second["resource_id"]]
    rows = store.for_run(config, {"ch_files": ids})
    assert [r["resource_id"] for r in rows] == ids
    assert [r["index"] for r in rows] == [0, 1, 2]
    projected = projection(config, rows)
    assert Path(projected["ch_files"][1]).read_bytes() == b"original nonempty bytes"
    assert config["ch_files"] == [str(path)] * 3
    Path(rows[0]["worker_path"]).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash mismatch"):
        store.for_run(config, {"ch_files": ids})


def test_relative_reference_never_uses_cwd(tmp_path, monkeypatch):
    store = Resources(tmp_path / "resources")
    (tmp_path / "channel.s4p").write_bytes(b"some content")
    monkeypatch.chdir(tmp_path)
    config = snapshot(new_engine()) | {"inter_sel": "single", "ch_file": "channel.s4p"}
    with pytest.raises(ValueError, match="unbound"):
        store.for_run(config, {})
    with pytest.raises(ValueError, match="absolute"):
        store.local("channel.s4p")
    bindings = store.bind_base(config, str(tmp_path))
    assert store.for_run(config, bindings)[0]["reference"] == "channel.s4p"


def test_inactive_paths_are_never_given_to_native_observers(monkeypatch):
    import pybert.pybert as native
    monkeypatch.setattr(native, "IBISModel", lambda *a, **k: pytest.fail("inactive IBIS observer executed"))
    cfg = snapshot(new_engine()) | {"tx_ibis_file": "missing.ibs", "rx_ami_file": "missing.ami", "rx_dll_file": "missing.dll",
                                   "ctle_sel": "File", "use_ctle_file": True, "ctle_enable": False, "ctle_file": "missing.csv"}
    result = normalize({"mode": "load", "config": cfg})
    assert result["config"] == cfg
    validate(result["config"], snapshot(new_engine()), execution=True)
    with pytest.raises(ValueError, match="native File"):
        validate(cfg | {"ctle_enable": True}, snapshot(new_engine()), execution=True)


def test_aliases_delta_t_tables_and_runtime_roundtrip():
    defaults = snapshot(new_engine())
    old = {"bit_rate": 5, "mod_type": "pam-4", "delta_t": 2, "use_ch_file": False,
           "tx_use_ibis": False, "rx_use_ibis": False, "ctle_sel": "native", "rx_n_taps": 1, "rx_n_pre": 0,
           "rx_taps": [[True, .7, -1, 1]]}
    runtime = {"version": 1, "values": {"rlm": .91, "rx_use_clocks": True, "ami_opt_trials": 123,
                                        "tx_ami_params": {"Gain": {"value": 2, "enabled": False}}}}
    result = normalize({"mode": "load", "config": old, "runtime_extensions": runtime})
    p = new_engine(); p.bit_rate=5; p.mod_type="PAM-4"
    assert result["config"]["delta_t_ui"] == 2e-12 / p.ui
    assert len(result["config"]["rx_taps"]) == 100
    assert result["config"]["rx_taps"][0][1] == .7
    assert result["import_report"]["defaulted_fields"]
    saved = normalize({"mode": "load", "yaml": result["yaml"]})
    assert saved["runtime_extensions"] == runtime
    assert saved["input_identity_hash"] == result["input_identity_hash"]
    assert saved["config"]["decision_scaler"] == defaults["decision_scaler"]
    with pytest.raises(ValueError, match="Conflicting"):
        normalize({"mode": "load", "config": old | {"inter_sel": "single"}})


def test_restricted_legacy_pickle_and_unknown_yaml(tmp_path):
    cfg = PyBertCfg.__new__(PyBertCfg)
    cfg.__dict__.update(bit_rate=10., tx_taps=[(True, .1, -1, 1)])
    value = parse_legacy(pickle.dumps(cfg))
    assert value["tx_taps"][0] == (True, .1, -1, 1)
    result = normalize({"mode": "load", "legacy_base64": base64.b64encode(pickle.dumps(cfg)).decode()})
    assert result["config"]["tx_taps"][0][1] == .1
    with pytest.raises(ValueError, match="安全转换"):
        parse_legacy(pickle.dumps(Path("do-not-construct")))
    with pytest.raises(Exception):
        normalize({"mode": "load", "yaml": "!!python/object/apply:os.system ['echo must-not-run']"})


def serial_stub(task_id, operation, request, directory, cancel, pipe):
    """Lifecycle-only worker: no numerical engine and no physics claims."""
    path = Path(directory)
    if operation == "run":
        (path / "manifest.json").write_text(json.dumps({"run_id": task_id, "input_hash": "core", "effective_input": {},
            "summary": {}, "resource_hash": "resource", "deferred": request["deferred_com"]}), encoding="utf-8")
    else:
        assert request["parent_run_id"]
        cancel.wait(.4)
    pipe.send({"task_id": task_id, "kind": "terminal", "status": "succeeded", "result": {}})
    time.sleep(.2)  # A terminal envelope is intentionally earlier than actual exit.
    pipe.close()


def test_core_then_com_joins_and_preserves_parent_manifest(tmp_path):
    manager = Tasks(tmp_path, worker=serial_stub)
    row = manager.resources.add("a.s4p", b"not a numerical fixture", {"kind": "test stub"})
    config = snapshot(new_engine()) | {"inter_sel": "single", "ch_file": "a.s4p", "enable_com": True}
    core = manager.start("run", {"config": config, "input_hash": input_hash(config), "resource_bindings": {"ch_file": row["resource_id"]}})
    assert manager.tasks[core["task_id"]]["done"].wait(20)
    # Holding the same lock waits for the atomic parent->child slot handoff.
    with manager.lock:
        assert manager.get(core["task_id"])["worker_exited"]
        child = manager.current
        assert child != core["task_id"] and manager.active == child
    before = (manager.directory(core["task_id"]) / "manifest.json").read_bytes()
    with pytest.raises(BusyError):
        manager.start("normalize", {})
    assert manager.tasks[child]["done"].wait(20)
    assert manager.get(child)["worker_exited"]
    assert (manager.directory(core["task_id"]) / "manifest.json").read_bytes() == before
    assert manager.active is None
