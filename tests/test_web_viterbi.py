"""No-simulation #9 contracts; raw-run differential evidence lives in tools/."""

import ast
import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from pybert.web.config import extensions, input_hash, normalize, snapshot, new_engine, validate as validate_config
from pybert.web.server import create_app
from pybert.web.tasks import Tasks
from pybert.web.viterbi import extend, payload, plan, validate

ROOT = Path(__file__).resolve().parents[1]
BASE = "3807bd2f54647a491f350cbda7ab61c0752b06f0"


@pytest.fixture
def captured(tmp_path):
    # Explicit primitive producer input, not a numerical/decoder qualification fixture.
    config = json.loads((ROOT / "docs/webui/issue9/fixtures/v1/V-PAM4-ISI.json").read_text(encoding="utf-8"))["config"]
    config.update(nbits=32, eye_bits=24)
    count, states, n = 12, 16, 2
    t = np.arange(32, dtype=float)
    bits = np.zeros(32, dtype=int)
    test = bits[-24:].copy()
    test[2:4] = 1  # Two bit-error entries at the same PAM4 symbol.
    ber = {"bits_out": test.copy(), "bits_test": test, "bits_reference": bits[-24:].copy(),
           "auto_corr": np.zeros(12), "bit_delay": 0, "test_start_bit": 8, "test_stop_bit": 32,
           "reference_start_bit": 8, "reference_stop_bit": 32, "errors": np.array([2, 3]), "count": 2}
    probs = np.zeros((count, states))
    probs[:, :3] = [.6, .3, .1]
    trans = np.zeros((states, states))
    trans[:, 0] = 1
    debug = {"decoder": SimpleNamespace(states=np.zeros((states, n)), trans=trans),
             "sig_samps": np.arange(1., 13.), "pulse_resp_samps": np.array([.5, .1]),
             "probs": probs, "prevs": np.zeros((count, states), dtype=int), "path": np.zeros(count, dtype=int),
             "symbols_viterbi": np.zeros(count), "symbols_dfe": np.zeros(16), "log": ""}
    local = {"sample_times": np.arange(1., 13.), "sample_indices": np.arange(1, 13), "sigma": .1,
             "decision_scaler": .5, "ui": 1., "ts": 1., "nspui": 32, "N": n, "L": 4,
             "clk_phase_ix": 0, "pulse_resp_curs_ix": 2, "pulse_peak_ix": 2, "decided_levels": np.zeros(count)}
    p = SimpleNamespace(rx_use_viterbi=True, rx_viterbi_symbols=n, mod_type="PAM-4", L=4,
                        n_errs_dfe=2, n_errs_viterbi=2, bit_errs_viterbi=ber["errors"], dbg_dict_viterbi=debug)
    arrays = {"bits": bits, "t": t, "dfe_out": t, "bit_errs_dfe": ber["errors"]}
    manifest = {"run_id": "contract", "effective_input": config, "datasets": {}, "window": {},
                "summary": {"n_errs_dfe": 2}, "actual_source_sha256": {k: "a"*64 for k in ("models/bert.py", "models/viterbi.py", "web/viterbi.py")}}
    extend(p, {"dfe": copy.deepcopy(ber), "viterbi": copy.deepcopy(ber), "isi": local}, arrays, manifest)
    return p, arrays, manifest


def save_view(tmp_path, arrays, manifest):
    np.savez_compressed(tmp_path / "arrays.npz", **arrays)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_original_error_mapping_view_clamp_raw_log_and_zero(captured, tmp_path):
    _, arrays, manifest = captured
    save_view(tmp_path, arrays, manifest)
    before = {key: value.tobytes() for key, value in arrays.items()}
    result = payload(tmp_path, 999)
    assert result["position"] == 2 and result["stop_exclusive"] == 12
    assert result["symbol_count"] == 12 != manifest["effective_input"]["eye_bits"]
    assert payload(tmp_path, error=1)["selected_error"] == {"entry": 1, "bit_index": 2, "symbol_index": 1}
    assert payload(tmp_path, error=2)["selected_error"] == {"entry": 2, "bit_index": 3, "symbol_index": 1}
    assert arrays["viterbi.trellis_err_xs"].tolist() == [1, 1]
    assert payload(tmp_path)["error"] == 0
    assert result["top3"][0]["raw_probabilities"] == [.6] * 10
    assert np.allclose(result["top3"][0]["display_log10"], np.log10(.6))
    assert all(arrays[k].tobytes() == value for k, value in before.items())
    with pytest.raises(ValueError, match="1-based"):
        payload(tmp_path, error=3)


@pytest.mark.parametrize("damage", ["source", "missing_bits", "axis", "window", "count", "error_mapping", "states", "sample_time", "schema"])
def test_incomplete_self_consistent_decoding_rejected(captured, damage):
    _, arrays, manifest = captured
    if damage == "source":
        del manifest["actual_source_sha256"]["models/viterbi.py"]
    elif damage == "missing_bits":
        del arrays["ber.viterbi.bits_out"]
    elif damage == "axis":
        manifest["datasets"]["viterbi.probs"]["axis"] = None
    elif damage == "window":
        manifest["datasets"]["ber.dfe.bits_reference"]["window"] = {}
    elif damage == "count":
        manifest["decoding"]["ber"]["dfe"]["count"] = 0
    elif damage == "error_mapping":
        arrays["viterbi.trellis_err_xs"] = np.array([1])
    elif damage == "states":
        arrays["viterbi.path"][0] = 16
    elif damage == "sample_time":
        arrays["viterbi.sample_times"][0] = 1.1
    else:
        manifest["decoding"]["schema_version"] = 99
    with pytest.raises(ValueError):
        validate(manifest, arrays)


def test_disabled_retains_actual_dfe_count_and_old_record_not_collected(captured, tmp_path):
    p, arrays, manifest = captured
    p.n_errs_viterbi = -1
    manifest["effective_input"]["rx_use_viterbi"] = False
    old = {key: value for key, value in arrays.items() if not key.startswith(("viterbi.", "ber."))}
    captured_ber = {key: arrays[f"ber.dfe.{key}"] for key in ("bits_out", "bits_test", "bits_reference", "auto_corr", "errors")}
    captured_ber.update({k: v for k, v in manifest["decoding"]["ber"]["dfe"].items() if k != "availability"})
    manifest["datasets"] = {}
    extend(p, {"dfe": captured_ber}, old, manifest)
    save_view(tmp_path, old, manifest)
    result = payload(tmp_path)
    assert result["availability"] == "disabled" and result["ber"]["viterbi"]["count"] == -1
    assert result["ber"]["dfe"]["count"] == 2
    del manifest["decoding"]
    save_view(tmp_path, old, manifest)
    assert payload(tmp_path)["availability"] == "not_collected"


def test_default_depth_budget_and_no_silent_parameter_change():
    defaults = snapshot(new_engine())
    assert defaults["rx_viterbi_symbols"] == 4
    assert normalize({"mode": "load", "config": defaults | {"rx_use_viterbi": True}})["config"]["rx_viterbi_symbols"] == 4
    assert plan(defaults | {"rx_use_viterbi": True}, execution=True)["states"] == 16
    with pytest.raises(ValueError, match="budget"):
        plan(defaults | {"rx_use_viterbi": True, "mod_type": "PAM-4"}, execution=True)
    for n in (0, -1, 1.5, "2", True):
        with pytest.raises(ValueError):
            validate_config(defaults | {"rx_use_viterbi": True, "rx_viterbi_symbols": n}, defaults, execution=True)
    with pytest.raises(ValueError, match="budget"):
        plan(defaults | {"rx_use_viterbi": True, "rx_viterbi_symbols": 100000}, execution=True)


def test_fec_rejected_in_config_yaml_runtime_and_request(tmp_path):
    defaults = snapshot(new_engine())
    for request in ({"mode": "load", "config": defaults | {"rx_viterbi_fec": True}},
                    {"mode": "load", "yaml": "rx_viterbi_fec: true\n"},
                    {"mode": "defaults", "rx_viterbi_fec": True}):
        with pytest.raises(ValueError, match="unsupported_native_fec"):
            normalize(request)
    with pytest.raises(ValueError, match="unsupported_native_fec"):
        extensions({"version": 1, "values": {"rx_viterbi_fec": True}})
    manager = Tasks(tmp_path)
    client = TestClient(create_app(manager))
    response = client.post("/api/runs", json={"config": defaults, "input_hash": input_hash(defaults), "rx_viterbi_fec": True})
    assert response.status_code == 422 and "unsupported_native_fec" in response.json()["detail"]
    assert manager.active is None and not manager.tasks


def test_original_trellis_producer_body_is_unchanged():
    base = subprocess.check_output(["git", "show", f"{BASE}:src/pybert/models/bert.py"], cwd=ROOT).decode()
    original = base[base.index("    # Viterbi trellis"):base.index("\n\ndef update_eyes")]
    current = (ROOT / "src/pybert/models/bert.py").read_text(encoding="utf-8")
    extracted = current[current.index("    N_PATHS = 3", current.index("def update_trellis")):current.index("\n\ndef update_eyes")]
    assert ast.dump(ast.parse(original.replace("    # Viterbi trellis\n", "").replace("\n    ", "\n").lstrip())) == ast.dump(ast.parse(extracted.replace("\n    ", "\n").lstrip()))
    expected = subprocess.check_output(["git", "show", f"{BASE}:src/pybert/models/viterbi.py"], cwd=ROOT)
    assert expected.replace(b"\r\n", b"\n") == (ROOT / "src/pybert/models/viterbi.py").read_bytes().replace(b"\r\n", b"\n")
