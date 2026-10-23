"""Freeze #3 inputs and contracts before any analysis or control simulation."""

import hashlib
import importlib
import importlib.metadata
import json
import sys
from pathlib import Path

from pybert.web.config import input_hash

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs/webui/issue3/fixtures"
OLD = ROOT / "docs/webui/issue2/fixtures"
RAW = Path("C:/Users/yx/.codex/worktrees/pybert-issue2-native/serial-bus-simulator")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    DEST.mkdir(parents=True, exist_ok=False)
    frozen = json.loads((OLD / "frozen-manifest.json").read_text(encoding="utf-8"))
    assert all(digest(OLD / name) == value for name, value in frozen["files"].items())
    inputs = {}
    for name in ("F-NRZ-01", "F-PAM4-01"):
        config = json.loads((OLD / f"{name}.json").read_text(encoding="utf-8"))
        source = RAW / f"docs/webui/issue2/evidence/numeric-20261024-050800/{name}"
        inputs[name] = dict(config=config, input_hash=input_hash(config), source=str(source),
                            source_raw_sha256=digest(source / "arrays.npz"),
                            source_manifest_sha256=digest(source / "manifest.json"))
    control = json.loads(json.dumps(inputs["F-NRZ-01"]["config"]))
    control.update(rx_n_taps=1, rx_n_pre=0)
    for i, tap in enumerate(control["rx_taps"]):
        tap[0] = i == 0
        if i == 0:
            tap[1] = 1.0
    inputs["F-NRZ-IDENTITY"] = dict(config=control, input_hash=input_hash(control),
                                    changes=["rx_n_taps", "rx_n_pre", "rx_taps"],
                                    base="F-NRZ-01")
    manifest = dict(
        schema=1, frozen_before_analysis=True, base="35a3b60351836431e4f96136b61708515ec5f77c",
        issue2_freeze_sha256=digest(OLD / "frozen-manifest.json"), inputs=inputs,
        context="schema2 complete source.x, local decision_scaler/mod_type/mask and per-point crossings/axes",
        windows={"NRZ": dict(nui=15000, eye_uis=10160, ignore_samps=154880, ignore_until_s=4840e-10),
                 "PAM4": dict(nui=7500, eye_uis=5080, ignore_samps=77440, ignore_until_s=2420e-10)},
        display_noise=dict(seed=34003, generator="numpy.random.default_rng PCG64", sigma_v=0.001,
                           realization="one full waveform length normal(0,0.001,N), cached per run; separate from global RNG"),
        eye=dict(height=1000, width="2*nspui", y_max="1.1*max(abs(windowed waveform))",
                 y_scale="1000//(2*y_max)", y_offset=500,
                 clock="nominal waveform crossing for chnl/tx/ctle/ffe; DFE recovered clocks, nominal fallback if empty"),
        tolerances=json.loads((OLD / "tolerances.json").read_text(encoding="utf-8")),
        additional_tolerances=dict(bathtub=dict(rtol=1e-8, atol=0), relative_clock_frequency=dict(rtol=1e-12, atol="1e-6*UI")),
        unavailable_policy="Preserve nonfinite raw with mask/reason; no zero fill, dropping points, changing seed/window/tolerance. Helper failure is dataset unavailable, original native failure is failed run.",
        bounded_checks=["two saved full fixtures independent helpers", "one identity-FFE simulation",
                        "no crossing", "insufficient window", "DFE nominal clock fallback", "nonfinite", "zero CDR normalization"],
        python=sys.executable, python_version=sys.version,
        modules={name: importlib.import_module(name).__file__ for name in
                 ("pybert.pybert", "pybert.web.data", "numpy", "scipy", "pyibisami", "pychopmarg")},
        packages={p.metadata["Name"]: p.version for p in importlib.metadata.distributions()},
    )
    (DEST / "frozen-manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    print(digest(DEST / "frozen-manifest.json"))


if __name__ == "__main__":
    main()
