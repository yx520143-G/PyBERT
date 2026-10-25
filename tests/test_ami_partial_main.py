"""Real Main/collect/archive consumers with a synthetic AMI helper; no DLL is loaded."""

from copy import deepcopy

import numpy as np
import pytest
from pyibisami.ami.configurator import AMIParamConfigurator

from pybert.models import bert
from pybert.web import archive, clocks, config, data


def synthetic_helper(case):
    def helper(_filename, _cfg, _getwave, ui, ts, response, wave, *, clock_observations, **_kwargs):
        pre, count = 36, len(wave)
        nspui = round(ui / ts)
        start = count // 2
        indices = np.arange(nspui // 2, count, nspui)
        if case == "ber_short":
            indices = np.array([start + nspui // 2, start + 3 * nspui // 2])
        elif case == "fft_gap":
            indices = np.arange(start + (count - start) // 2, count, nspui // 2)
        elif case == "single":
            indices = np.array([start + nspui // 2])
        elif case == "future":
            indices = np.array([count + nspui])
        elif case == "empty":
            indices = np.array([], dtype=int)
        edges = (pre + indices) * ts - ui / 2
        calls = []
        for number, size in ((1, 17), (2, 19), (3, count)):
            chunk = {"epoch": 1, "python_call": number, "c_call": number, "wave_size": size, "status": 1,
                         "returned": True, "phase": "complete", "valid_clocks": edges.tolist() if number == 3 else []}
            calls.append({"python_call": number, "input_samples": size, "completed": True, "chunks": [chunk]})
        clock_observations.update(status="complete", main_entry={"epoch_id": "synthetic-main/init-1",
            "python_calls": 2, "c_calls": 2, "sample_interval_s": ts}, history={"epoch_id": "synthetic-main/init-1", "epoch": 1,
            "sample_interval_s": ts, "python_calls": 3, "c_calls": 3, "ready": True, "invocations": calls})
        impulse = np.zeros_like(response)
        impulse[0] = 1.
        return wave.copy(), edges, impulse, response.copy(), "synthetic test helper; not a real model", ["(model)"]
    return helper


def run_main(monkeypatch, case, *, update_plots=False):
    engine = config.new_engine()
    engine.trait_set(nbits=2048, eye_bits=1024, nspui=8, seed=42, rn=0., pn_mag=0., enable_com=False)
    engine.rx_use_ami = True  # Exercise the real disabled Native equalizer setup.
    engine.trait_setq(rx_use_getwave=True, rx_use_clocks=True)
    engine._rx_cfg = AMIParamConfigurator("""(model (Reserved_Parameters
        (GetWave_Exists (Usage Info) (Type Boolean) (Value True))
        (Init_Returns_Impulse (Usage Info) (Type Boolean) (Value True))
        (Ignore_Bits (Usage Info) (Type Integer) (Value 0))))""")
    monkeypatch.setattr(bert, "run_ami_model", synthetic_helper(case))
    observed, decoding = {}, {}
    bert.my_run_simulation(engine, initial_run=True, update_plots=update_plots, observations=observed, decoding=decoding)
    assert engine.status == "Ready."
    return engine, observed, decoding


def collect_main(monkeypatch, directory, case):
    engine, observed, decoding = run_main(monkeypatch, case)
    inputs = config.snapshot(engine)
    identity = {"run_id": "software-" + case, "draft_revision": 0, "requested_input": inputs, "effective_input": inputs,
                    "input_hash": config.input_hash(inputs), "input_identity_hash": "a" * 64, "resource_hash": "b" * 64,
                    "resource_bindings": {}, "runtime_extensions": {}, "execution_strategy": {}, "warnings": [], "resources": []}
    snapshot = clocks.snapshot_producer(engine, phase="post_Main")
    run = data.collect(engine, observed, directory, identity, decoding=decoding, producer_snapshot=snapshot)
    arrays = archive.read_arrays((directory / "arrays.npz").read_bytes(), run=run)
    archive.validate_run(run, arrays)
    return engine, run, arrays


@pytest.mark.parametrize("case,ber,hist,fft", [
    ("full", True, True, True), ("ber_short", False, True, False),
    ("fft_gap", True, True, False), ("single", False, False, False), ("future", False, False, False),
])
def test_main_to_archive_independent_outcomes(monkeypatch, tmp_path, case, ber, hist, fft):
    engine, run, arrays = collect_main(monkeypatch, tmp_path, case)
    assert run["raw_schema_version"] == 7 and run["decoding"]["schema_version"] == 3
    assert run["summary"]["model_qualification"] == "UNKNOWN"
    outcomes = run["analysis_availability"]
    for name, expected in (("ber", ber), ("histogram", hist), ("spectrum", fft)):
        assert (outcomes[name]["availability"] == "available") is expected
    if not ber:
        assert engine.n_errs_dfe == -1 and run["summary"]["n_errs_dfe"] is None
        assert engine.auto_corr.size == 0 and not engine.bit_errs_dfe.size
        assert not any("ber.dfe." + key in arrays for key in ("bits_test", "bits_reference", "auto_corr", "errors"))
        assert "unavailable" in engine.status_str
    source_json, source_npz = (tmp_path / "manifest.json").read_bytes(), (tmp_path / "arrays.npz").read_bytes()
    destination = tmp_path / "run.pybert-run"
    archive.save_archive(tmp_path, destination)
    reopened = tmp_path / "reopened"
    reopened.mkdir()
    monkeypatch.setattr(bert, "my_run_simulation", lambda *a, **k: pytest.fail("reader must not simulate"))
    loaded, _ = archive.load_archive(destination.read_bytes(), reopened)
    assert loaded["analysis_availability"] == outcomes
    assert (reopened / "manifest.json").read_bytes() == source_json
    assert (reopened / "arrays.npz").read_bytes() == source_npz
    reread = archive.read_arrays(source_npz, run=loaded)
    assert {name: archive.array_identity(value) for name, value in arrays.items()} == {
        name: archive.array_identity(value) for name, value in reread.items()}


def test_all_empty_epoch_keeps_native_route(monkeypatch, tmp_path):
    engine, run, _ = collect_main(monkeypatch, tmp_path, "empty")
    assert engine.ami_clock_info["actual_branch"] == "native"
    assert run["raw_schema_version"] == 5 and "clock_contract" not in run.get("ami", {})


def test_gui_helpers_and_repeat_run_clear_unavailable_ber(monkeypatch):
    engine, _, _ = run_main(monkeypatch, "full", update_plots=True)
    assert engine.auto_corr.size and engine.n_errs_dfe >= 0
    monkeypatch.setattr(bert, "run_ami_model", synthetic_helper("future"))
    captured = {}
    bert.my_run_simulation(engine, initial_run=True, update_plots=True, decoding=captured)
    assert engine.n_errs_dfe == -1 and not engine.auto_corr.size and not engine.bit_errs_dfe.size
    assert captured["dfe"]["availability"] == "unavailable" and captured["dfe"]["bits_out"].size == 0
    assert not engine.dfe_slicer_samps.size and not engine.dfe_slicer_decisions.size
    assert engine.ami_clock_info["run_status"] == "completed"


@pytest.mark.parametrize("failure", ["decision", "cancel"])
def test_main_failure_stays_partial_and_cannot_publish(monkeypatch, tmp_path, failure):
    from pybert.models.dfe import DFE
    engine, _, _ = run_main(monkeypatch, "full")
    original, calls = DFE.decide, []
    def decide(self, value):
        calls.append(value)
        if failure == "decision" and len(calls) == 2:
            raise RuntimeError("actual slicer failure")
        return original(self, value)
    monkeypatch.setattr(DFE, "decide", decide)
    with pytest.raises(RuntimeError, match="failure|aborted"):
        bert.my_run_simulation(engine, initial_run=True, update_plots=False,
                               aborted_sim=lambda: failure == "cancel" and len(calls) == 1)
    snap = clocks.snapshot_producer(engine, phase="Main_exception")
    assert snap["info"]["consumption_status"] == "partial" and snap["info"]["consumed_count"] == 1
    with pytest.raises(ValueError, match="Partial producer"):
        clocks.clock_context(engine, snap)
    terminal = {"status": "cancelled" if failure == "cancel" else "failed"}
    clocks.write_partial(tmp_path, snap, [], terminal)
    assert not (tmp_path / "manifest.json").exists() and not (tmp_path / "arrays.npz").exists()
    partial = archive.read_json((tmp_path / "partial-manifest.json").read_bytes())
    assert partial["status"] == terminal["status"] and partial["evidence_type"] == "diagnostic_partial_only"


@pytest.mark.parametrize("change", ["epoch", "index", "mask", "version", "feature", "qualification", "ber_count", "eye_count"])
def test_saved_contract_tampering_is_rejected(monkeypatch, tmp_path, change):
    _, run, arrays = collect_main(monkeypatch, tmp_path, "ber_short")
    run, arrays = deepcopy(run), {name: value.copy() for name, value in arrays.items()}
    contract = run["ami"]["clock_contract"]
    if change == "epoch":
        contract["origin_observations"]["main_entry"]["epoch_id"] = "other-init"
    elif change == "index":
        arrays["ami.clock.sample_indices"][0] += 1
    elif change == "mask":
        arrays["ami.cdr.period_known"][0] = True
    elif change == "version":
        run["raw_schema_version"] = 6
    elif change == "feature":
        run["required_features"] = []
    elif change == "qualification":
        contract["model_qualification"] = "PASS"
    elif change == "ber_count":
        run["summary"]["n_errs_dfe"] = 0
    else:
        contract["eye_consumers"]["analysis.eye.dfe"]["trace_count"] = 2
    with pytest.raises(ValueError):
        archive.validate_run(run, arrays)
