"""仅构造、不仿真：首次验收计算前冻结 #2 输入和门槛。"""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import pybert.pybert
import pychopmarg
import pyibisami

from pybert.web import NATIVE_SHA, PROTOTYPE_SHA
from pybert.web.config import input_hash, new_engine, snapshot, yaml_text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue2/fixtures"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Frozen fixture directory already exists; do not overwrite it.")
    OUT.mkdir(parents=True)
    engine = new_engine()
    defaults = snapshot(engine)
    (OUT / "constructed-defaults.json").write_text(json.dumps(defaults, indent=2), encoding="utf-8")
    for name, modulation in (("F-NRZ-01", "NRZ"), ("F-PAM4-01", "PAM-4")):
        p = new_engine()
        for key, value in {
            "bit_rate": 10,
            "mod_type": modulation,
            "pattern": "PRBS-7",
            "seed": 1,
            "nspui": 32,
            "nbits": 15000,
            "eye_bits": 10160,
            "vod": 1,
            "rn": 0.01,
            "pn_mag": 0.01,
            "pn_freq": 11,
            "f_max": 40,
            "f_step": 10,
            "impulse_length": 0,
            "use_window": False,
            "rx_n_taps": 15,
            "rx_n_pre": 5,
            "ctle_enable": True,
            "peak_freq": 5,
            "rx_bw": 12,
            "peak_mag": 1.7,
            "gain": 0.1,
            "n_ave": 100,
            "decision_scaler": 0.5,
            "use_agc": True,
            "sum_ideal": True,
            "cdr_type": "Bang-Bang",
        }.items():
            setattr(p, key, value)
        for tap, enabled, value in zip(
            p.tx_taps, [False, True, True, False, False, False], [0, -0.02, -0.05, 0, 0, 0]
        ):
            tap.enabled, tap.value = enabled, value
        for i, tap in enumerate(p.rx_taps):
            tap.enabled = i < 15
            tap.value = 1.0 if i == 5 else -0.03 if i == 6 else 0.0
        config = snapshot(p)
        (OUT / f"{name}.yaml").write_text(yaml_text(config), encoding="utf-8")
        (OUT / f"{name}.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        extension = {
            "runtime_extensions": {},
            "input_hash": input_hash(config),
            "resources": [],
            "window": {
                "nui": p.nui,
                "eye_uis": p.eye_uis,
                "ignore_samps": (p.nui - p.eye_uis) * p.nspui,
                "ignore_until_s": (p.nui - p.eye_uis) * p.ui,
                "ui_s": p.ui,
            },
            "eye": {"height": 1000, "width": 2 * p.nspui, "display_noise": False},
            "waveform_projection": {
                "default": "last 20 UI",
                "max_points": 4096,
                "rule": "evenly spaced integer indices including endpoints",
            },
        }
        (OUT / f"{name}.extensions.json").write_text(json.dumps(extension, indent=2), encoding="utf-8")
    tolerance = {
        "exact": ["input_hash", "shape", "indices", "bits", "decisions", "counts", "bool", "availability", "eye"],
        "voltage_response_complex": {"rtol": 1e-10, "atol": 1e-12},
        "time_jitter_spectrum": {"rtol": 1e-10, "atol": 1e-18},
        "t_ns_chnl": {"rtol": 1e-10, "atol": 1e-9},
        "ui_ests_ps": {"rtol": 1e-10, "atol": 1e-6},
        "frequency_Hz": {"rtol": 1e-12, "atol": 1e-6},
        "pdf_per_s": {"rtol": 1e-10, "atol": "1e-12/UI"},
        "display": {"rtol": 1e-10, "atol": 1e-10},
        "nonfinite": "invalid; report mask and native failure, never numeric pass",
        "excluded": ["performance", "log timestamps"],
    }
    (OUT / "tolerances.json").write_text(json.dumps(tolerance, indent=2), encoding="utf-8")
    git = lambda *args: subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    prototype_files = git(
        "diff", "--name-only", "457f444b0a6e705532579d4242596d60c9dfa153", PROTOTYPE_SHA
    ).splitlines()
    integration = {
        "native": NATIVE_SHA,
        "prototype": PROTOTYPE_SHA,
        "implementation_base": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "remote": git("remote", "get-url", "origin"),
        "native_is_ancestor": subprocess.run(
            ["git", "merge-base", "--is-ancestor", NATIVE_SHA, "HEAD"], cwd=ROOT, check=False
        ).returncode
        == 0,
        "prototype_is_ancestor": subprocess.run(
            ["git", "merge-base", "--is-ancestor", PROTOTYPE_SHA, "HEAD"], cwd=ROOT, check=False
        ).returncode
        == 0,
        "prototype_files": {path: sha(ROOT / path) for path in prototype_files},
        "fix_commit_files": git("diff-tree", "--no-commit-id", "--name-only", "-r", PROTOTYPE_SHA).splitlines(),
        "note": "PR7 Draft/open; stacked implementation base codex/pybert-signal-chain-webui; PM owns integration order.",
    }
    (OUT / "integration.json").write_text(json.dumps(integration, indent=2), encoding="utf-8")
    env = {
        "python": sys.executable,
        "version": sys.version,
        "platform": platform.platform(),
        "modules": {m.__name__: m.__file__ for m in (pybert.pybert, pychopmarg, pyibisami)},
        "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "native_submodules": git("submodule", "status"),
        "calculation_performed": False,
    }
    (OUT / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
    manifest = {
        "schema": 1,
        "frozen_before_first_calculation": True,
        "files": {path.name: sha(path) for path in sorted(OUT.iterdir())},
    }
    (OUT / "frozen-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"directory": str(OUT), "manifest_sha256": sha(OUT / "frozen-manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
