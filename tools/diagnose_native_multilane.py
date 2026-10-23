"""Original resource helper evidence for #13, with no link simulation or COM."""

import hashlib
import importlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from skrf import Network

from pybert.utility.sparam import import_freq, import_fext

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/native13/evidence"
SOURCE = Path(
    "C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/local/resources/TwoLaneModel.s8p"
)
EXPECTED_SHA = "0f6cbb032432eadc8c1bee4f382ef25e3c06fe0718fae07fc835e495067d5abf"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physical_difference(net, near, far):
    a, b = near
    c, d = far
    s = net.s
    result = np.empty((len(net.f), 2, 2), complex)
    result[:, 0, 0] = 0.5 * (s[:, a, a] - s[:, a, b] - s[:, b, a] + s[:, b, b])
    result[:, 0, 1] = 0.5 * (s[:, a, c] - s[:, a, d] - s[:, b, c] + s[:, b, d])
    result[:, 1, 0] = 0.5 * (s[:, c, a] - s[:, c, b] - s[:, d, a] + s[:, d, b])
    result[:, 1, 1] = 0.5 * (s[:, c, c] - s[:, c, d] - s[:, d, c] + s[:, d, d])
    return result


def main():
    phase = sys.argv[1]
    assert phase in ("before", "after")
    path = OUT / f"real-M-{phase}.json"
    if path.exists():
        raise FileExistsError(path)
    local = OUT.parent / "local"
    local.mkdir(exist_ok=True)
    resource = local / "TwoLaneModel.s8p"
    if not resource.exists():
        shutil.copyfile(SOURCE, resource)
    assert sha(SOURCE) == sha(resource) == EXPECTED_SHA
    net = Network(str(resource))
    zero = net.copy()
    zero.s[:, :4, 4:] = 0
    zero.s[:, 4:, :4] = 0
    zero_path = local / "diagnostic-only-zero-crosslane.s8p"
    zero.write_touchstone(str(zero_path), write_z0=True, form="ri")
    arrays = {"f_hz": net.f}
    rows = []
    for victim in (0, 1):
        aggressor = 1 - victim
        near = (4 * victim, 4 * victim + 2)
        far = (4 * victim + 1, 4 * victim + 3)
        a_near = (4 * aggressor, 4 * aggressor + 2)
        actual = import_freq(str(resource), lane=victim, renumber=False)
        expected = physical_difference(net, near, far)
        fext = import_fext(str(resource), net.f, victim, renumber=False)[0]
        expected_fext = physical_difference(net, a_near, far)
        disconnected = import_fext(str(zero_path), net.f, victim, renumber=False)[0]
        prefix = f"v{victim}"
        arrays.update(
            {
                prefix + "_actual_s": actual.s,
                prefix + "_expected_s": expected,
                prefix + "_actual_fext_s": fext.s,
                prefix + "_expected_fext_s": expected_fext,
                prefix + "_zero_crosslane_fext_s": disconnected.s,
            }
        )
        row = {
            "victim": victim,
            "aggressor": aggressor,
            "near_pair_0based": near,
            "far_pair_0based": far,
            "victim_max_abs_actual_s21": float(abs(actual.s[:, 1, 0]).max()),
            "victim_max_abs_expected_s21": float(abs(expected[:, 1, 0]).max()),
            "victim_complex_allclose": bool(
                np.allclose(actual.s, expected, rtol=2e-12, atol=2e-12)
            ),
            "fext_complex_allclose": bool(
                np.allclose(fext.s, expected_fext, rtol=2e-12, atol=2e-12)
            ),
            "fext_max_abs_actual_s21": float(abs(fext.s[:, 1, 0]).max()),
            "fext_max_abs_expected_s21": float(abs(expected_fext[:, 1, 0]).max()),
            "zero_crosslane_native_fext_max_abs_s21": float(
                abs(disconnected.s[:, 1, 0]).max()
            ),
            "zero_crosslane_native_fext_exact_zero": bool(
                np.array_equal(disconnected.s[:, 1, 0], np.zeros(len(net.f)))
            ),
            "z0_victim_equal_pair_sums": bool(
                np.array_equal(
                    actual.z0,
                    np.stack(
                        [
                            net.z0[:, near[0]] + net.z0[:, near[1]],
                            net.z0[:, far[0]] + net.z0[:, far[1]],
                        ],
                        axis=1,
                    ),
                )
            ),
            "z0_fext_equal_pair_sums": bool(
                np.array_equal(
                    fext.z0,
                    np.stack(
                        [
                            net.z0[:, a_near[0]] + net.z0[:, a_near[1]],
                            net.z0[:, far[0]] + net.z0[:, far[1]],
                        ],
                        axis=1,
                    ),
                )
            ),
        }
        rows.append(row)
    raw = local / f"real-M-{phase}.npz"
    np.savez_compressed(raw, **arrays)
    sources = [
        ROOT / "src/pybert/utility/sparam.py",
        ROOT / "tests/test_multilane_physical.py",
        Path(__file__),
    ]
    result = {
        "phase": phase,
        "base": "9a33d08458aa00782e90169c699857b8b19455a2",
        "head_at_execution": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in sources},
        "python": sys.executable,
        "modules": {
            name: str(Path(importlib.import_module(name).__file__).resolve())
            for name in ("pybert", "pychopmarg", "pyibisami", "skrf", "numpy")
        },
        "versions": {
            n: importlib.metadata.version(n) for n in ("pipbert", "scikit-rf", "numpy")
        },
        "resource": {
            "source": str(SOURCE),
            "local": str(resource),
            "sha256": EXPECTED_SHA,
            "bytes": resource.stat().st_size,
            "origin": "SignalIntegrity Test/TestSignalIntegrity/TestStatisticalNoise/TwoLaneModel.s8p; GPL-3-or-later, local evaluation; existing model, no hardware qualification",
        },
        "diagnostic_zero_crosslane": {
            "path": str(zero_path),
            "sha256": sha(zero_path),
            "acceptance_resource_substitution": False,
        },
        "raw": {"path": str(raw), "sha256": sha(raw), "bytes": raw.stat().st_size},
        "main_simulation_performed": False,
        "com_performed": False,
        "oracle": "independent physical differential wave excitation difference, all four complex S and pair-sum z0",
        "rows": rows,
    }
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"phase": phase, "report_sha256": sha(path), "rows": rows}))
    if phase == "after" and not all(
        all(
            row[k]
            for k in (
                "victim_complex_allclose",
                "fext_complex_allclose",
                "zero_crosslane_native_fext_exact_zero",
                "z0_victim_equal_pair_sums",
                "z0_fext_equal_pair_sums",
            )
        )
        for row in rows
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
