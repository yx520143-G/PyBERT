"""Optimizer constraints, exact Native handler fields, archive integrity, and real checkpoints."""

import copy
import io
import json
import multiprocessing
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from pybert.gui.handler import MyHandler
from pybert.web.config import input_hash, load_config, new_engine, normalize, snapshot
from pybert.web.optimization import CancelBridge, OptimizationCancelled, optimizer_action, prepare, preflight
from pybert.threads.optimization import OptThread, _report_progress

ROOT = Path(__file__).resolve().parents[1]


def fixture(name="O-NRZ-grid"):
    return json.loads((ROOT / f"docs/webui/issue8/fixtures/v1/{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["O-NRZ-grid", "O-PAM4-MMSE", "O-PAM4-MMSE-RLM080"])
def test_plan_matches_frozen_order(name):
    plan = preflight(prepare(fixture(name)))
    frozen = json.loads((ROOT / "docs/webui/issue8/fixtures/v1/manifest.json").read_text(encoding="utf-8"))["cases"][name]
    assert plan["outer_order"] == frozen["outer_order"]
    assert plan["rx_inner_order"] == (frozen["rx_inner_order"] or [])


@pytest.mark.parametrize("field,value,error", [("step_mag_tune", 0, "step"), ("min_mag_tune", 2, "min"),
    ("rx_n_taps", 0, "at least"), ("rx_bw_tune", -1, "positive"), ("max_mag_tune", 1000, "budget")])
def test_invalid_optimizer_fields(field, value, error):
    p = prepare(fixture())
    setattr(p, field, value)
    with pytest.raises(ValueError, match=error):
        preflight(p)


def test_dfe_gap_and_ffe_identity_rejected():
    p = prepare(fixture())
    p.dfe_tap_tuners[0].enabled = False
    with pytest.raises(ValueError, match="continuous prefix"):
        preflight(p)
    p.dfe_tap_tuners[0].enabled = True
    p.ffe_tap_tuners[9].enabled = True
    with pytest.raises(ValueError, match="mapping"):
        preflight(p)


def test_mmse_observation_storage_refused_before_computation():
    p = prepare(fixture("O-PAM4-MMSE"))
    p.bit_rate, p.nspui, p.nbits = 200, 64, 1024
    p.eye_bits = 512
    p.min_mag_tune, p.max_mag_tune, p.step_mag_tune = 0., 127., 1.
    with pytest.raises(ValueError, match="storage budget"):
        preflight(p)


def test_observation_collection_retains_only_within_budget(monkeypatch):
    import pybert.web.optimization as module

    monkeypatch.setattr(module, "MAX_ARRAY_BYTES", 64)
    collector = module.NativeObservations(8)
    collector.update(candidates=[], mmse_calls=[], mmse_context={"t_s": np.zeros(1)})
    collector["candidates"].append({"pulse": np.zeros(2)})  # pulse plus exported axis
    assert collector.used == 48
    with pytest.raises(ValueError, match="storage budget"):
        collector["mmse_calls"].append({"tx_H": np.zeros(2, dtype=complex)})
    assert collector.used == 48 and not collector["mmse_calls"]


def test_archive_open_cannot_consume_active_optimization_reservation(tmp_path, monkeypatch):
    from pybert.web.tasks import Tasks, BusyError
    import pybert.web.tasks as module

    tasks = Tasks(tmp_path)
    tasks.active = "working"
    tasks.tasks["working"] = {"data": {"operation": "optimization"}}
    monkeypatch.setattr(module, "load_optimization", lambda *_: pytest.fail("Must refuse before reading archive"))
    with pytest.raises(BusyError, match="reservation"):
        tasks.open_optimization(b"unused")
    assert not tasks.optimization_references


def test_native_reset_exact_and_does_not_reset_ranges():
    request = fixture()
    p, q = prepare(request), prepare(request)
    before = snapshot(p)
    runtime, _ = optimizer_action(p, request["runtime_extensions"], "reset_eq")
    MyHandler().do_reset_eq(SimpleNamespace(object=q))
    assert snapshot(p) == snapshot(q)
    for key in ("tx_tap_tuners", "ffe_tap_tuners"):
        assert [r[2:] for r in snapshot(p)[key]] == [r[2:] for r in before[key]]
    assert runtime["values"]["optimizer_values"] == {"tx": [t.value for t in q.tx_tap_tuners], "ffe": [t.value for t in q.ffe_tap_tuners]}
    roundtrip = normalize({"mode": "load", "config": snapshot(p), "runtime_extensions": runtime})
    restored = normalize({"mode": "load", "yaml": roundtrip["yaml"]})
    assert restored["runtime_extensions"] == runtime


def test_use_eq_only_native_handler_fields_and_no_dfe_values():
    request = fixture()
    current = copy.deepcopy(request["config"])
    current["tx_taps"][2][2:] = [-.9, .9]
    current["rn"] = .02
    p, q = new_engine(), new_engine()
    load_config(p, current)
    load_config(q, current)
    candidate = {"status": "succeeded", "opt_id": "opt-test", "selected_candidate_id": "candidate-0",
        "requested_input": request["config"], "input_hash": request["input_hash"], "input_identity_hash": request["input_identity_hash"],
        "runtime_extensions": request["runtime_extensions"], "resource_bindings": {}, "current_config": current,
        "selected_values": {"tx": [0, 0, -.1, 0, 0, 0], "ffe": [0, 1, -.03], "ctle_db": 1.}}
    frozen = prepare(request)
    for i, (tap, source) in enumerate(zip(q.tx_tap_tuners, frozen.tx_tap_tuners)):
        tap.enabled, tap.value = source.enabled, candidate["selected_values"]["tx"][i]
    for i, (tap, source) in enumerate(zip(q.ffe_tap_tuners, frozen.ffe_tap_tuners)):
        tap.enabled, tap.value = source.enabled, candidate["selected_values"]["ffe"][i] if i < 3 else source.value
    q.peak_mag_tune = 1.
    q.peak_freq_tune, q.rx_bw_tune, q.ctle_enable_tune = frozen.peak_freq_tune, frozen.rx_bw_tune, frozen.ctle_enable_tune
    MyHandler().do_use_eq(SimpleNamespace(object=q))
    expected = snapshot(q)
    runtime, report = optimizer_action(p, request["runtime_extensions"], "use_eq", candidate)
    actual = snapshot(p)
    targets = {"tx_taps", "rx_taps", "peak_freq", "peak_mag", "rx_bw", "ctle_enable"}
    assert {k: actual[k] for k in targets} == {k: expected[k] for k in targets}
    assert all(actual[k] == current[k] for k in set(actual)-targets)
    assert actual["dfe_tap_tuners"] == current["dfe_tap_tuners"]
    assert report["after"] == {k: actual[k] for k in targets}
    assert report["DFE_weights_applied"] is False
    assert runtime["values"]["eq_application"]["after_input_hash"] == input_hash(actual)


@pytest.mark.parametrize("count,pre", [(1, 0), (3, 0), (3, 2)])
def test_use_eq_rejects_changed_rx_topology_before_applying(count, pre, monkeypatch):
    request = fixture()
    normalized = normalize({"mode": "patch", "config": request["config"], "patches": [
        {"field": "rx_n_taps", "value": count}, {"field": "rx_n_pre", "value": pre}]})
    p = new_engine()
    load_config(p, normalized["config"])
    before = snapshot(p)
    candidate = {"status": "succeeded", "requested_input": request["config"],
                 "input_hash": request["input_hash"], "input_identity_hash": request["input_identity_hash"],
                 "runtime_extensions": request["runtime_extensions"], "resource_bindings": {}}
    monkeypatch.setattr(MyHandler, "do_use_eq", lambda *_: pytest.fail("Incompatible topology reached handler"))
    with pytest.raises(ValueError, match="matching Rx FFE topology"):
        optimizer_action(p, request["runtime_extensions"], "use_eq", candidate)
    assert snapshot(p) == before


def test_cancel_bridge_is_original_checkpoint_and_never_started():
    event = multiprocessing.get_context("spawn").Event()
    checks = []
    def check():
        checks.append(True)
        return event.is_set()
    p = prepare(fixture())
    p.opt_thread = CancelBridge(check)
    assert isinstance(p.opt_thread, OptThread) and p.opt_thread.ident is None
    _report_progress(p, 1, 4, 1)
    assert checks == [True]
    event.set()
    with pytest.raises(OptimizationCancelled):
        _report_progress(p, 2, 4, 1)
    assert p.opt_thread.ident is None


def test_RLM_does_not_change_native_PAM4_source():
    a, b = prepare(fixture("O-PAM4-MMSE")), prepare(fixture("O-PAM4-MMSE-RLM080"))
    assert a.rlm != b.rlm
    np.testing.assert_array_equal(a.bits, b.bits)
    np.testing.assert_array_equal(a.symbols, b.symbols)


@pytest.mark.parametrize("score", [-1000., float("nan"), float("inf")])
def test_native_true_sentinel_is_not_success(tmp_path, monkeypatch, score):
    import pybert.web.optimization as module

    monkeypatch.setattr(module, "coopt", lambda *_args, **_kwargs: ([0.]*6, 0., [0.]*100, score, True, [], []))
    request = fixture() | {"resource_hash": input_hash([]), "frozen_resources": []}
    with pytest.raises(ValueError, match="winner"):
        module.run_optimization("sentinel", request, tmp_path, lambda: False, lambda *args, **kwargs: None)
    record = json.loads((tmp_path / "optimization.json").read_text(encoding="utf-8"))
    assert record["status"] == "failed" and "selected_candidate_id" not in record


def test_unrelated_runtime_error_is_failure_even_when_event_requested(tmp_path, monkeypatch):
    import pybert.web.optimization as module
    from pybert.web.worker import run_worker

    context = multiprocessing.get_context("spawn")
    event = context.Event()
    def fail(*_args, **_kwargs):
        event.set()
        raise RuntimeError("native unrelated failure")
    monkeypatch.setattr(module, "coopt", fail)
    class Connection:
        def send(self, message):
            pass
        def close(self):
            pass
    run_worker("fault", "optimization", fixture() | {"resource_hash": input_hash([]), "frozen_resources": []}, str(tmp_path), event, Connection())
    terminal = json.loads((tmp_path / "terminal.json").read_text(encoding="utf-8"))
    assert terminal["status"] == "failed" and terminal["cancel_requested"] and not terminal["cancel_observed"]


def inert_archive(tmp_path, mmse=False):
    from pybert.web.archive import array_identity, json_bytes
    import pybert.web.optimization as module

    request = fixture("O-PAM4-MMSE" if mmse else "O-NRZ-grid")
    count = 3 if mmse else 100
    prefix = "candidate_000000"
    arrays = {"t_ns_opt": np.array([0., 1.]), "ctle_out_h_tune": np.array([1., 0.]), "clocks_tune": np.array([0., 1.]),
              "curs_ix": np.array([0., 0.]), "curs_amp": np.array([0., 1.]),
              "p_chnl": np.array([.1, .2, .1]), "channel_t_ns": np.array([0., 1., 2.]),
              prefix+"_pulse": np.array([1., 0.]), prefix+"_t_ns": np.array([0., 1.]),
              prefix+"_tx_weights": np.zeros(6), prefix+"_rx_weights": np.ones(count)}
    record = {"schema_version": 1, "opt_id": "inert-container-test", "status": "succeeded", "requested_input": request["config"],
              "effective_input": request["config"], "input_hash": request["input_hash"], "input_identity_hash": request["input_identity_hash"],
              "runtime_extensions": request["runtime_extensions"], "resource_bindings": {}, "source_identity": {}, "packages": {},
              "plan": {}, "model": {}, "adapter_sha": "a"*40, "arrays": {k: array_identity(v) for k,v in arrays.items()},
              "selected_candidate_id": "candidate-000000", "fom": 2.,
              "candidates": [{"candidate_id": "candidate-000000", "arrays_prefix": prefix, "availability": "available", "fom": 2., "ctle_db": 0.}],
              "selected_values": {"tx": [0.]*6, "ffe": [1.]*count, "ctle_db": 0.}}
    (tmp_path / "optimization.json").write_bytes(json_bytes(record))
    np.savez_compressed(tmp_path / "arrays.npz", **arrays)
    module.save_optimization(tmp_path, tmp_path / "test.pybert_opt")
    return record, arrays, (tmp_path / "test.pybert_opt").read_bytes()


@pytest.mark.parametrize("mmse", [False, True])
def test_optimizer_archive_shapes_integrity_and_no_native_load(tmp_path, monkeypatch, mmse):
    import pybert.web.optimization as module

    record, arrays, content = inert_archive(tmp_path, mmse)
    destination = tmp_path / "opened"
    destination.mkdir()
    monkeypatch.setattr(module, "prepare", lambda *_: pytest.fail("Archive read must not load native observers"))
    loaded = module.load_optimization(content, destination)
    assert loaded == record
    assert (destination / "arrays.npz").read_bytes() == (tmp_path / "arrays.npz").read_bytes()
    record["selected_values"]["ffe"] = [1.]
    with pytest.raises(ValueError, match="disagree"):
        module.validate_record(record, arrays)
    with pytest.raises(ValueError, match="Invalid optimization archive"):
        module.load_optimization(b"broken zip", destination)


@pytest.mark.parametrize("raw_schema", [1, 2])
@pytest.mark.parametrize("key,value", [("curs_ix", None), ("curs_amp", None), ("curs_ix", [0.]),
    ("curs_amp", [[0.], [1.]]), ("curs_ix", [1., 1.]), ("curs_amp", [0., .5])])
def test_cursor_archive_rejected_atomically_before_publication(tmp_path, monkeypatch, raw_schema, key, value):
    from fastapi.testclient import TestClient
    from pybert.web.archive import array_identity, json_bytes, sha256
    from pybert.web.server import create_app
    from pybert.web.tasks import Tasks
    import pybert.web.optimization as module

    record, arrays, good = inert_archive(tmp_path)
    manager = Tasks(tmp_path / "tasks")
    monkeypatch.setattr(manager, "start", lambda *_args, **_kwargs: pytest.fail("Archive API started worker"))
    monkeypatch.setattr(module, "prepare", lambda *_: pytest.fail("Archive API loaded native instance"))
    client = TestClient(create_app(manager))
    opened = client.post("/api/optimization-references", content=good)
    assert opened.status_code == 201
    record_id = opened.json()["record_id"]
    before = client.get("/api/state").json()
    directories = set(manager.root.iterdir())
    with zipfile.ZipFile(io.BytesIO(good)) as source:
        envelope = json.loads(source.read("manifest.json"))
    if value is None:
        del arrays[key]
    else:
        arrays[key] = np.asarray(value)
    raw = io.BytesIO()
    np.savez_compressed(raw, **arrays)
    record["arrays"] = {k: array_identity(v) for k, v in arrays.items()}
    record["optimization_raw_schema"] = raw_schema
    envelope.update(record=record, raw_sha256=sha256(raw.getvalue()))
    broken = io.BytesIO()
    with zipfile.ZipFile(broken, "w") as destination:
        destination.writestr("manifest.json", json_bytes(envelope))
        destination.writestr("arrays.npz", raw.getvalue())
    rejected = client.post("/api/optimization-references", content=broken.getvalue())
    assert rejected.status_code == 422 and "cursor" in rejected.json()["detail"]
    assert client.get("/api/state").json() == before
    assert set(manager.root.iterdir()) == directories
    assert client.get(f"/api/optimizations/{record_id}/pulse").status_code == 200
