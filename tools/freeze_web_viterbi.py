"""Freeze complete #9 inputs before any simulation; construction only."""

import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import pybert
import pychopmarg
import pyibisami

from pybert.web.archive import json_bytes, sha256
from pybert.web.config import input_hash, load_config, new_engine, snapshot, yaml_text
from pybert.web.data import source_identity
from pybert.web.viterbi import plan

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue9/fixtures/v1"


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    cases = {}
    for name, base, patch, purpose in (
        ("V-NRZ-ISI", "NRZ", {}, "positive/no-error candidate; report actual counts"),
        ("V-PAM4-ISI", "PAM4", {}, "positive/no-error candidate; report actual counts"),
        ("V-DUO-ISI", "NRZ", {"mod_type": "Duo-binary"}, "bounded native capability, not NRZ alias"),
        ("V-NRZ-ERROR", "NRZ", {"rn": .20}, "preselected error candidate; no seed search if zero errors"),
        ("V-PAM4-ERROR", "PAM4", {"rn": .15}, "preselected error/duplicate-symbol candidate; retain actual result"),
        ("V-DISABLED", "NRZ", {"rx_use_viterbi": False}, "disabled -1 plus current actual DFE count"),
        ("V-CANCEL", "PAM4", {"eye_bits": 50000, "nbits": 60000}, "request on Running Viterbi; no internal immediate-cancel promise"),
    ):
        inherited = ROOT / f"docs/webui/issue2/fixtures/F-{base}-01.json"
        config = json.loads(inherited.read_text(encoding="utf-8"))
        config.update(rx_use_viterbi=True, rx_viterbi_symbols=2)
        config.update(patch)
        p = load_config(new_engine(), config)
        config = snapshot(p)
        q = load_config(new_engine(), config)
        assert config == snapshot(q)
        runtime, bindings = {}, {}
        request = {"config": config, "input_hash": input_hash(config), "draft_revision": 0,
                   "runtime_extensions": runtime, "resource_bindings": bindings,
                   "input_identity_hash": input_hash(dict(config=config, runtime_extensions=runtime, resource_bindings=bindings))}
        (OUT / f"{name}.json").write_bytes(json_bytes(request))
        (OUT / f"{name}.yaml").write_text(yaml_text(config), encoding="utf-8")
        cases[name] = {"purpose": purpose, "request_sha256": sha256(json_bytes(request)),
                       "input_hash": request["input_hash"], "inherited": str(inherited.relative_to(ROOT)),
                       "inherited_sha256": sha256(inherited.read_bytes()), "resources": [],
                       "ui_s": p.ui, "ts_s": p.ui / p.nspui, "nui": p.nui, "eye_uis": p.eye_uis,
                       "budget": plan(config, execution=True),
                       "window": "all actual native last eye_uis recovered clocks, native t-end filtering and truncation; both complete calc_ber tail windows",
                       "config_scope": "complete 112 fields, all taps, CDR/AGC/DFE and nonzero seed/noise are in the immutable request"}
    paths = (pybert, pychopmarg, pyibisami)
    assert all(Path(m.__file__).resolve().is_relative_to(ROOT) for m in paths)
    manifest = {"schema_version": 1, "before_first_simulation": True, "simulation_calls": 0,
                "base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "cases": cases, "raw_schema_version_planned": 5, "decoding_schema_version": 1,
                "native_default_N": new_engine().rx_viterbi_symbols,
                "default_N_validation": "construction/load/save preserve N=4; NRZ budget allowed; PAM4 full-window budget blocked; no unbounded trellis run",
                "tolerances": {"counts_indices_bits_paths_shapes_zero_positions_finite_masks": "exact",
                               "voltage_pulse_sigma": {"rtol": 1e-10, "atol": 1e-12, "unit": "V"},
                               "normalized_symbols": {"rtol": 1e-10, "atol": 1e-12},
                               "sample_times": {"rtol": 0, "atol": 1e-18, "unit": "s"},
                               "probabilities_nonzero": {"rtol": 1e-10, "atol": 0},
                               "zeros": "exact; never swallowed by absolute tolerance",
                               "report": "maximum absolute difference and first mismatch; no relaxed retry"},
                "capture_contract": {"ber": "raw output bits, native padded test/reference windows, auto_corr and bit delay separately at each original call",
                                     "viterbi": "actual sample_times/sampleindices, sig_samps, pulse_resp_samps, sigma, decision_scaler, cursor/phase, ui/ts/L/N, decoded bits",
                                     "decoder": "original states/trans/probs/prevs/path/symbols, primitive arrays only",
                                     "trellis": "original update_results trellis producer, no new probability/path/BER/slicing formula",
                                     "views": "10 symbols initially; actual length clamp; raw/log10 floor -20 separate; repeated PAM4 bitindex//2 retained"},
                "predeclared_faults": ["invalid N/type/overbudget and default N", "API/YAML rx_viterbi_fec=True blocked unsupported_native_fec",
                                       "decoder raise and trellis producer raise injected independently: failed, old success retained",
                                       "sample shortage/top3 native degeneration: preflight block or actual failure, never forged success",
                                       "cancel requested/observed/exit separate; occupied until join", "legacy raw2/3/4 missing decoding remains not-collected",
                                       "self-consistent corrupt archive identities/arrays/axes/windows rejected atomically"],
                "environment": {"python": sys.executable, "version": sys.version, "platform": platform.platform(),
                                "PYTHONPATH": os.environ.get("PYTHONPATH"), "modules": {m.__name__: m.__file__ for m in paths},
                                "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                                "gitlinks": subprocess.check_output(["git", "submodule", "status"], cwd=ROOT, text=True).strip(),
                                "runner": "uv unavailable on host; authorized existing read-only #4 interpreter; no dependency/environment mutation"},
                "preimplementation_source_sha256": source_identity(),
                "execution_source_policy": "save actual source bytes before every numerical batch; freeze-only HEAD is not execution code"}
    (OUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"manifest": str(OUT / "manifest.json"), "sha256": sha256((OUT / "manifest.json").read_bytes()), "simulations": 0}))


if __name__ == "__main__":
    main()
