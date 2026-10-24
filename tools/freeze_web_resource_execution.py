"""Append execution provenance, then inspect the fixed native resource helpers only."""

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from skrf import Network

from pybert.web import NATIVE_SHA
from pybert.web.config import load_config, new_engine, snapshot
from pybert.utility.sparam import import_freq, import_fext, interp_s2p, thru_is_1to3

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "docs/webui/issue4/fixtures"
OUT = ROOT / "docs/webui/issue4/evidence"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    frozen = json.loads((FIX / "frozen-manifest.json").read_text(encoding="utf-8"))
    assert all(sha(FIX / key) == val for key, val in frozen["files"].items())
    assert all(sha(ROOT / key) == val for key, val in frozen["inherited_files"].items())
    assert not (OUT / "execution-freeze-v1.json").exists()
    sources = [
        *sorted((ROOT / "src/pybert").rglob("*.py")),
        *sorted((ROOT / "src/pybert/web/static").glob("*")),
        ROOT / "tools/freeze_web_resource_execution.py",
    ]
    modules = {
        name: str(Path(importlib.import_module(name).__file__).resolve())
        for name in ("pybert", "pychopmarg", "pyibisami", "numpy", "scipy", "skrf")
    }
    original = {}
    for name in (
        "src/pybert/models/bert.py",
        "src/pybert/pybert.py",
        "src/pybert/utility/sparam.py",
    ):
        raw = subprocess.check_output(["git", "show", f"{NATIVE_SHA}:{name}"], cwd=ROOT)
        dest = OUT / ("native-" + name.replace("/", "_") + ".txt")
        dest.write_bytes(raw)
        original[name] = {
            "file": str(dest.relative_to(ROOT)),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    dependencies = [
        *sorted((ROOT / "PyChOpMarg/src").rglob("*.py")),
        *sorted((ROOT / "PyAMI/src").rglob("*.py")),
    ]
    freeze = {
        "parent_manifest_sha256": sha(FIX / "frozen-manifest.json"),
        "before_first_numerical_run": True,
        "before_resource_helper_precheck": True,
        "python": sys.executable,
        "modules": modules,
        "actual_execution_sources": {str(p.relative_to(ROOT)): sha(p) for p in sources},
        "declared_independent_dependency_sources": {
            str(p.relative_to(ROOT)): sha(p) for p in dependencies
        },
        "lockfile_sha256": sha(ROOT / "uv.lock"),
        "direct_reference": original,
        "collection_change": "optional raw-only capture of already computed FEXT h/H/start_ix, each existing convolution result and final local noise; same order and amplitude; no physics algorithm change",
        "budget_decision": "Default COM remains BLOCKED_BUDGET/NOT_EXECUTED; real original xls only",
        "new_execution_rule": "Every subsequent numeric report binds its own actual sources; preserve this original freeze",
    }
    (OUT / "execution-freeze-v1.json").write_text(
        json.dumps(freeze, indent=2), encoding="utf-8"
    )
    resources = json.loads((FIX / "resources.json").read_text(encoding="utf-8"))
    p = new_engine()
    cfg = json.loads((FIX / "F4-SINGLE-NRZ.json").read_text(encoding="utf-8"))
    load_config(p, cfg, snapshot(p))
    grid = p.f
    reports = []
    for key in ("A", "B", "M"):
        path = resources[key]["path"]
        net = Network(path)
        for lane in range(net.nports // 4):
            extracted = import_freq(path, renumber=False, lane=lane)
            interp = interp_s2p(extracted, grid)
            ports = (
                [4 * lane, 4 * lane + 2, 4 * lane + 1, 4 * lane + 3]
                if net.nports >= 8
                else [0, 1, 2, 3]
            )
            row = {
                "resource": key,
                "sha256": resources[key]["sha256"],
                "victim": lane,
                "actual_subnetwork_to_sdd_21_0based": ports,
                "renumber": False,
                "native_thru_is_1to3_diagnostic": thru_is_1to3(net.subnetwork(ports)),
                "selected_actual_through_pairs_0based": [
                    [ports[0], ports[2]],
                    [ports[1], ports[3]],
                ],
                "sdd_21_formula_note": "native se2mm scale0.5; Sdd21=0.5*(S21-S23-S41+S43) on supplied subnetwork",
                "frequency_coverage_hz": [float(net.f[0]), float(net.f[-1])],
                "requested_grid_hz": [float(grid[0]), float(grid[-1]), len(grid)],
                "native_boundary_policy": "interp_s2p: s11/s22 polar extrapolation capped |S|<=1; s12/s21 polar interpolation with 0 outside measured/model coverage (including DC below fmin); z0 from extrapolated network",
                "above_coverage_samples": int((grid > net.f[-1]).sum()),
                "above_coverage_max_abs_s21": float(
                    abs(interp.s[grid > net.f[-1], 1, 0]).max()
                )
                if (grid > net.f[-1]).any()
                else None,
                "below_coverage_samples": int((grid < net.f[0]).sum()),
                "below_coverage_max_abs_s21": float(
                    abs(interp.s[grid < net.f[0], 1, 0]).max()
                )
                if (grid < net.f[0]).any()
                else None,
                "cascade_rule": "each segment import_freq->interp_s2p on this grid first, then networks[0] ** networks[1] in listed order; no segment time waveform producer",
            }
            if key == "M":
                xtalk = import_fext(path, grid, lane, renumber=False)
                aggressors = [j for j in range(2) if j != lane]
                row["actual_native_fext"] = [
                    {
                        "aggressor_lane": j,
                        "victim_lane": lane,
                        "subnetwork_to_sdd_21_0based": [
                            4 * j,
                            4 * j + 2,
                            4 * lane + 1,
                            4 * lane + 3,
                        ],
                        "differential_max_abs_s21": float(
                            abs(xtalk[i].s[:, 1, 0]).max()
                        ),
                        "nonzero": bool((abs(xtalk[i].s[:, 1, 0]) > 0).any()),
                        "renumber_for_crosslane": False,
                    }
                    for i, j in enumerate(aggressors)
                ]
            reports.append(row)
    (OUT / "native-resource-precheck-v1.json").write_text(
        json.dumps(
            {
                "execution_freeze_sha256": sha(OUT / "execution-freeze-v1.json"),
                "kind": "native resource-helper precheck only; no time-domain/COM calculation",
                "reports": reports,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "freeze_sha256": sha(OUT / "execution-freeze-v1.json"),
                "precheck_sha256": sha(OUT / "native-resource-precheck-v1.json"),
                "fext": [
                    r.get("actual_native_fext") for r in reports if r["resource"] == "M"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
