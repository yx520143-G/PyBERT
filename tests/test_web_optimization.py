"""Optimizer constraints, exact Native handler fields, archive integrity, and real checkpoints."""

import copy
import json
import multiprocessing
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
    assert report["DFE_weights_applied"] is False
    assert runtime["values"]["eq_application"]["after_input_hash"] == input_hash(actual)


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
