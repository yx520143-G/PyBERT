"""Construct and freeze #8 fixtures before the first coopt call. Never optimize here."""

import copy
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import pybert
import pychopmarg
import pyibisami

from pybert.threads.optimization import mk_tap_weight_combs
from pybert.web.archive import json_bytes, sha256
from pybert.web.config import input_hash, load_config, new_engine, snapshot, yaml_text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue8/fixtures/v1"


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    resources = json.loads((ROOT / "docs/webui/issue4/fixtures/resources.json").read_text(encoding="utf-8"))
    resource = resources["A"]
    assert sha256(Path(resource["path"]).read_bytes()) == resource["sha256"]
    cases = {}
    for name, modulation, mmse, rlm, file_channel in (
        ("O-NRZ-grid", "NRZ", False, .95, False),
        ("O-PAM4-MMSE", "PAM-4", True, .95, False),
        ("O-PAM4-MMSE-RLM080", "PAM-4", True, .80, False),
        ("O-FILE-NRZ-grid", "NRZ", False, .95, True),
    ):
        inherited = ROOT / f"docs/webui/issue2/fixtures/F-{'NRZ' if modulation == 'NRZ' else 'PAM4'}-01.json"
        p = new_engine()
        load_config(p, json.loads(inherited.read_text(encoding="utf-8")))
        p.rx_n_taps, p.rx_n_pre = 3, 1
        p.use_mmse = mmse
        p.ctle_enable_tune = True
        p.min_mag_tune, p.max_mag_tune, p.step_mag_tune = 0., 1., 1.
        p.rx_bw_tune, p.peak_freq_tune = 12., 5.
        for i, tap in enumerate(p.tx_tap_tuners):
            tap.enabled = i == 2
            tap.min_val, tap.max_val, tap.step = (-.10, -.05, .05) if i == 2 else (0., 0., 1.)
        for i, tap in enumerate(p.ffe_tap_tuners):
            tap.enabled = i < 3
            tap.min_val, tap.max_val, tap.step = ((1., 1., 1.) if i == 1 else
                                                (-.03, 0., .03) if i == 2 else (0., 0., 1.)) if not mmse else (-1., 1., 1.)
        for i, tap in enumerate(p.dfe_tap_tuners):
            tap.enabled = i < 2
        if file_channel:
            p.inter_sel, p.ch_file = "single", Path(resource["path"]).name
        config = snapshot(p)
        # All native load/observer effects are frozen before computation.
        q = new_engine()
        load_config(q, config)
        assert snapshot(q) == config
        runtime = {"version": 1, "values": {"rlm": rlm}}
        bindings = {"ch_file": resource["sha256"] + ".s4p"} if file_channel else {}
        tx = mk_tap_weight_combs(p.tx_tap_tuners)
        tx = [w for w in tx if 1 - sum(abs(w)) > 0 and 1 - sum(abs(w)) >= p.tx_c0_min]
        rx = None if mmse else [w.tolist() for w in mk_tap_weight_combs(p.ffe_tap_tuners)]
        order = [{"candidate_id": f"candidate-{i:06d}", "ctle_db": float(mag), "tx_weights": w.tolist()}
                 for i, (mag, w) in enumerate((m, w) for m in np.arange(0., 2., 1.) for w in tx)]
        assert len(order) <= 16 and (rx is None or len(rx) <= 16)
        request = dict(config=config, runtime_extensions=runtime, resource_bindings=bindings,
                       input_hash=input_hash(config), draft_revision=0,
                       input_identity_hash=input_hash(dict(config=config, runtime_extensions=runtime, resource_bindings=bindings)))
        (OUT / f"{name}.json").write_bytes(json_bytes(request))
        (OUT / f"{name}.yaml").write_text(yaml_text(config, runtime, bindings), encoding="utf-8")
        cases[name] = {"request_sha256": sha256(json_bytes(request)), "input_hash": request["input_hash"],
                       "inherited": str(inherited.relative_to(ROOT)), "inherited_sha256": sha256(inherited.read_bytes()),
                       "outer_order": order, "rx_inner_order": rx, "outer_count": len(order),
                       "rx_inner_count": None if rx is None else len(rx),
                       "budget": {"max_outer": 16, "max_inner": 16},
                       "resources": [copy.deepcopy(resource)] if file_channel else [],
                       "axes": {"raw": "entire producer arrays; no clipping", "channel_ns": "p.t_ns[:len(p_chnl)]",
                                "candidate_ns": "native t_ns_opt; exact length required", "viewport_ns": [0., 30.],
                                "cursor": "two ns times / two V values", "clocks": "optimizer display sampling marks; not recovered CDR"},
                       "run_window": {"nbits": p.nbits, "eye_bits": p.eye_bits, "nspui": p.nspui, "ui_s": p.ui}}
    manifest = {"schema_version": 1, "before_first_optimization": True, "coopt_calls": 0,
                "base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "cases": cases,
                "tolerances": {"taps_normalization": {"rtol": 1e-10, "atol": 1e-12},
                               "pulse_cursor_V": {"rtol": 1e-10, "atol": 1e-12},
                               "fom": {"rtol": 1e-10, "atol": 1e-12}, "ns": {"rtol": 0, "atol": 1e-9},
                               "display_dB": {"rtol": 1e-10, "atol": 1e-10},
                               "exact": ["hash", "candidate order/id", "tap identity", "shape", "validity mask"],
                               "nonfinite": "unavailable, never allclose"},
                "other_attempts": {"cancel": "request after native progress during O-NRZ-grid expanded within explicit budget; record actual observation/exit, no forced success",
                                   "native_failure": "Tx all disabled produces original no-Tx-combination RuntimeError; preserve failure",
                                   "rlm_run": "same frozen PAM4 source and runtime-only RLM pair; ordinary Run must not read RLM; no improvement requirement"},
                "environment": {"python": sys.executable, "version": sys.version, "platform": platform.platform(),
                                "modules": {m.__name__: m.__file__ for m in (pybert, pychopmarg, pyibisami)},
                                "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                                "gitlinks": subprocess.check_output(["git", "submodule", "status"], cwd=ROOT, text=True).strip()}}
    (OUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"manifest": str(OUT / "manifest.json"), "sha256": sha256((OUT / "manifest.json").read_bytes()), "coopt_calls": 0}))


if __name__ == "__main__":
    main()
