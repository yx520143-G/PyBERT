"""Exact numerical storage and atomic reference publication contracts."""

import io
import json
import pickle
import zipfile

import numpy as np
import pytest
from chaco.api import ArrayPlotData
from fastapi.testclient import TestClient

from pybert.results import PyBertData
from pybert.web.archive import array_identity, load_archive, read_arrays, save_archive
from pybert.web.legacy_results import load_legacy, legacy_report, export_legacy
from pybert.web.records import References, verify_replay_resources
from pybert.web.server import create_app
from pybert.web.tasks import Tasks


def no_engine_terminal(task_id, operation, request, directory, cancel, pipe):
    pipe.send({"task_id": task_id, "kind": "terminal", "status": "failed", "error": "test terminal; no engine called"})
    pipe.close()


@pytest.fixture
def saved(tmp_path):
    directory = tmp_path / "source"
    directory.mkdir()
    arrays = {"t": np.arange(4, dtype="<f8"), "raw": np.array([0., -0., 1.25, -2.], dtype=">f8"),
              "complex": np.array([1+2j, -0.-3j], dtype="complex128"), "mask": np.array([True, False])}
    datasets = {key: dict(dtype=str(a.dtype), shape=list(a.shape), producer="fixture", unit="V", window={"sample_start": 0},
                          clock_basis="nominal", availability="available", axis="t" if key == "raw" else None)
                for key, a in arrays.items()}
    run = {"run_id": "original-run", "status": "succeeded", "raw_schema_version": 4,
           "requested_input": {"decision_scaler": .5}, "effective_input": {"decision_scaler": .5}, "summary": {"final_level_v": .7},
           "datasets": datasets, "window": {}, "plots": {"wave": {"title": "test", "traces": [{"x": "t", "y": "raw", "name": "raw", "xunit": "s", "yunit": "V"}]}},
           "runtime_extensions": {"version": 1, "future": {"retained": True}}}
    (directory / "manifest.json").write_text(json.dumps(run), encoding="utf-8")
    np.savez_compressed(directory / "arrays.npz", **arrays)
    output = tmp_path / "test.pybert_run"
    save_archive(directory, output)
    return directory, output, arrays


def rewrite(content, change):
    source = zipfile.ZipFile(io.BytesIO(content))
    manifest = json.loads(source.read("manifest.json"))
    change(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as target:
        target.writestr("manifest.json", json.dumps(manifest))
        target.writestr("arrays.npz", source.read("arrays.npz"))
    return output.getvalue()


def test_roundtrip_preserves_bytes_dtype_shape_manifest_and_extensions(saved, tmp_path):
    source, archive, arrays = saved
    target = tmp_path / "opened"
    target.mkdir()
    run, size = load_archive(archive.read_bytes(), target)
    assert (source / "arrays.npz").read_bytes() == (target / "arrays.npz").read_bytes()
    assert (source / "manifest.json").read_bytes() == (target / "manifest.json").read_bytes()
    assert size == sum(a.nbytes for a in arrays.values())
    for key, array in read_arrays((target / "arrays.npz").read_bytes()).items():
        assert array_identity(array) == array_identity(arrays[key])
    assert run["requested_input"]["decision_scaler"] == .5 != run["summary"]["final_level_v"]
    assert run["runtime_extensions"]["future"]["retained"]


@pytest.mark.parametrize("damage", [lambda m: m.update(archive_schema=999), lambda m: m.update(required_features=["new"]),
                                        lambda m: m["arrays"]["raw"].update(sha256="bad"),
                                        lambda m: m["run"]["requested_input"].update(decision_scaler=7)])
def test_failed_import_preserves_existing_reference_inventory(saved, tmp_path, damage):
    refs = References(tmp_path / "refs")
    loaded = refs.add(saved[1].read_bytes(), "good.pybert_run")
    before = refs.index()
    with pytest.raises(ValueError):
        refs.add(rewrite(saved[1].read_bytes(), damage), "broken.pybert_run")
    assert refs.index() == before
    assert refs.manifest(loaded["record_id"])["run_id"] == "original-run"


def test_object_array_forbidden_before_load():
    buffer = io.BytesIO()
    np.savez(buffer, unsafe=np.array([None], dtype=object))
    with pytest.raises(ValueError, match="object/pickle"):
        read_arrays(buffer.getvalue())


def test_reference_budget_rejects_without_eviction_and_ids_stay_distinct(saved, tmp_path):
    refs = References(tmp_path / "refs")
    for _ in range(4):
        refs.add(saved[1].read_bytes(), "same.pybert_run")
    before = refs.index()
    assert len({r["record_id"] for r in before}) == 4
    assert {r["run_id"] for r in before} == {"original-run"}
    with pytest.raises(ValueError, match="budget"):
        refs.add(saved[1].read_bytes(), "overflow.pybert_run")
    assert refs.index() == before
    refs.remove(before[0]["record_id"])
    assert len(refs.index()) == 3


def test_missing_or_changed_replay_resources_refused():
    run = {"resources": [{"field": "ch_file", "index": None, "sha256": "original"}]}
    with pytest.raises(ValueError, match="changed/missing"):
        verify_replay_resources(run, [])
    with pytest.raises(ValueError, match="changed/missing"):
        verify_replay_resources(run, [{"field": "ch_file", "index": None, "sha256": "changed"}])
    verify_replay_resources(run, run["resources"])


def native_bytes(value=None):
    result = PyBertData.__new__(PyBertData)
    result.the_data = ArrayPlotData(**{key: np.arange(4.) for key in PyBertData._item_names if key != "tx_out"})
    result.the_data.set_data("tx_out", value)
    result.version, result.date_created = "11.1.0", "original date"
    return pickle.dumps(result)


def test_legacy_trust_missing_none_index_axes_and_no_double_db(tmp_path):
    with pytest.raises(ValueError, match="trusted"):
        load_legacy(native_bytes(), tmp_path)
    run, _ = load_legacy(native_bytes(), tmp_path, trusted=True)
    assert run["legacy"]["absent"]["tx_out"]
    assert run["plots"]["chnl_H"]["traces"][0]["xunit"] == "frequency-bin index"
    assert run["plots"]["chnl_H"]["traces"][0]["yunit"] == "dB"
    with np.load(tmp_path / "arrays.npz", allow_pickle=False) as arrays:
        assert arrays["chnl_H"].tobytes() == np.arange(4.).tobytes()
    report = legacy_report(tmp_path)
    assert not report["available"] and len(report["fields"]) == 22
    with pytest.raises(ValueError, match="tx_out"):
        export_legacy(tmp_path, tmp_path / "bad.pybert_data")
    assert not (tmp_path / "bad.pybert_data").exists()


def test_legacy_export_uses_native_constructor_when_all_23_produced(tmp_path):
    load_legacy(native_bytes(np.arange(4.)), tmp_path, trusted=True)
    export_legacy(tmp_path, tmp_path / "valid.pybert_data")
    result = pickle.loads((tmp_path / "valid.pybert_data").read_bytes())
    assert type(result) is PyBertData and len(result.the_data.arrays) == 23


def test_open_clear_api_no_worker_draft_or_live_run_mutation(saved, tmp_path, monkeypatch):
    manager = Tasks(tmp_path / "tasks")
    monkeypatch.setattr(manager, "start", lambda *args, **kwargs: pytest.fail("opening results ran engine"))
    client = TestClient(create_app(manager))
    content = saved[1].read_bytes()
    response = client.post("/api/references?name=run.pybert_run", content=content)
    assert response.status_code == 201
    record = response.json()
    assert record["run_id"] == "original-run" and record["record_id"].startswith("ref-")
    assert client.get(f"/api/runs/{record['record_id']}/plots/wave").json()["run_id"] == "original-run"
    assert not manager.tasks and not manager.runs
    before = client.get("/api/state").json()
    assert client.post("/api/references?name=broken.pybert_run", content=b"bad").status_code == 422
    assert client.get("/api/state").json() == before
    assert client.post(f"/api/references/{record['record_id']}/remove").status_code == 200
    assert not manager.references.index() and saved[0].exists()


def test_active_subtask_snapshot_and_reopened_reference_never_join_current_task(saved, tmp_path):
    source = saved[0]
    manager = Tasks(tmp_path / "tasks")
    manager.runs = ["original-run"]
    manager.tasks["original-run"] = {"directory": source, "data": {"parent_run_id": None}}
    child = tmp_path / "child"
    child.mkdir()
    (child / "com.json").write_text("unfinished invalid JSON", encoding="utf-8")
    manager.tasks["child-com"] = {"directory": child, "data": {"task_id": "child-com", "parent_run_id": "original-run",
        "operation": "com", "state": "running", "worker_exited": False, "logs": ["original child log"]}}
    client = TestClient(create_app(manager))
    response = client.get("/api/runs/original-run/archive")
    assert response.status_code == 200
    opened = client.post("/api/references?name=saved.pybert_run", content=response.content).json()
    snapshot = opened["saved_subfunctions"]
    linked = snapshot["linked_tasks"]["child-com"]
    assert linked["task"]["state"] == "running"
    assert linked["files"]["com.json"]["availability"] == "waiting_for_exit"
    manager.tasks["child-com"]["data"].update(state="failed", worker_exited=True, logs=["unrelated later log"])
    repeated = client.get(f"/api/runs/{opened['record_id']}/archive")
    manifest = json.loads(zipfile.ZipFile(io.BytesIO(repeated.content)).read("manifest.json"))
    assert manifest["subfunctions"] == snapshot
    assert client.get(f"/api/runs/{opened['record_id']}").json()["saved_subfunctions"] == snapshot


def test_atomic_save_failure_keeps_old_file(saved, monkeypatch, tmp_path):
    from pybert.web import archive

    target = tmp_path / "existing.pybert_run"
    target.write_bytes(b"original file bytes")
    monkeypatch.setattr(archive.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("injected write failure")))
    with pytest.raises(OSError, match="injected"):
        save_archive(saved[0], target)
    assert target.read_bytes() == b"original file bytes"


def test_reference_byte_budget_preserves_inventory(saved, tmp_path, monkeypatch):
    from pybert.web import records

    refs = References(tmp_path / "refs")
    monkeypatch.setattr(records, "MAX_REFERENCE_BYTES", 0)
    with pytest.raises(ValueError, match="byte budget"):
        refs.add(saved[1].read_bytes(), "too-large.pybert_run")
    assert not refs.index()


def test_malformed_known_legacy_container_is_controlled_failure(tmp_path):
    with pytest.raises(ValueError, match="containers"):
        load_legacy(pickle.dumps(PyBertData.__new__(PyBertData)), tmp_path, trusted=True)


def test_replay_guard_survives_removed_reference_without_disabling_resource_check(tmp_path):
    from pybert.web.config import input_hash

    manager = Tasks(tmp_path / "tasks", worker=no_engine_terminal)
    guard = {"version": 1, "source_run_id": "old-run", "resources": [], "resource_hash": input_hash([])}
    task = manager.start("run", {"config": {"inter_sel": "native", "enable_com": False}, "source_record_id": "removed-ref", "replay_guard": guard})
    assert manager.tasks[task["task_id"]]["done"].wait(30)
    assert manager.get(task["task_id"])["error"] == "test terminal; no engine called"
    row = manager.resources.add("changed.s4p", b"explicit changed content", {"kind": "test"})
    guard["resources"] = [{"field": "ch_file", "index": None, "sha256": "original-content"}]
    with pytest.raises(ValueError, match="changed/missing"):
        manager.start("run", {"config": {"inter_sel": "single", "ch_file": "old.s4p", "enable_com": False},
                              "resource_bindings": {"ch_file": row["resource_id"]}, "replay_guard": guard})


def test_unknown_legacy_version_is_preserved_on_native_export(tmp_path):
    result = pickle.loads(native_bytes(np.arange(4.)))
    result.version, result.date_created = "unknown-old-producer", "original date"
    load_legacy(pickle.dumps(result), tmp_path, trusted=True)
    target = tmp_path / "export.pybert_data"
    report = export_legacy(tmp_path, target)
    reopened = pickle.loads(target.read_bytes())
    assert reopened.version == "unknown-old-producer" and reopened.date_created == "original date"
    assert report["native_producer_version"] == "unknown-old-producer"
    second = tmp_path / "second"
    second.mkdir()
    run, _ = load_legacy(target.read_bytes(), second, trusted=True)
    assert run["datasets"]["chnl_H"]["unit"] == "unknown legacy unit"
