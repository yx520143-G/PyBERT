"""Inspect actual resources/COM parameter grids without running a numerical engine."""

import dataclasses
import hashlib
import importlib
import importlib.metadata
import itertools
import json
import math
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
from skrf import Network

from pychopmarg.config.ieee_8023dj import IEEE_8023dj
from pychopmarg.excel import get_com_params
from pychopmarg.utility.general import mk_combs

ROOT = Path(__file__).resolve().parents[1]


def plain(value):
    if dataclasses.is_dataclass(value):
        return plain(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return plain(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def identity(path):
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def budget(cp):
    grids = [
        mk_combs([trip])
        for trip in zip(cp.tx_taps_min, cp.tx_taps_max, cp.tx_taps_step)
    ]
    # Same cursor filter as COM.__init__; enumerate scalar grid metadata only.
    valid = sum(
        1
        for row in itertools.product(*grids)
        if 1 - sum(abs(float(v[0])) for v in row) >= cp.c0_min
    )
    no_eq_extra = not all(any(float(v[0]) == 0 for v in grid) for grid in grids)
    return {
        "parameters": plain(cp),
        "tx_grid_lengths": [len(g) for g in grids],
        "unfiltered_tx_grid": math.prod(map(len, grids)),
        "valid_tx_candidates": valid + no_eq_extra,
        "fom_evaluations_full_search_per_package": (valid + no_eq_extra)
        * len(cp.g_DC)
        * len(cp.g_DC2),
        "package_cases": len(cp.zp_cases) if cp.zp_cases else 1,
        "local_search": cp.local_search,
        "timing_search": cp.ts_srch_mode,
        "helper_has_cancellation_callback": False,
        "calculation_performed": False,
    }


def main():
    directory = ROOT / "docs/webui/issue4/evidence"
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / "resource-budget-inspection.json"
    if output.exists():
        raise FileExistsError(output)
    paths = [
        ROOT / "PyChOpMarg/chnl_data/example2_THRU.s4p",
        Path(
            "E:/serdes-equalization-explorer/SignalIntegrity-master/Test/TestSignalIntegrity/TestStatisticalNoise/TwoLaneModel.s8p"
        ),
        ROOT / "PyAMI/examples/impulse_response_8ma.txt",
    ]
    resources = []
    for path in paths:
        row = identity(path)
        if path.suffix in (".s4p", ".s8p"):
            net = Network(str(path))
            row.update(
                ports=net.nports,
                frequencies=len(net.f),
                f_min_hz=float(net.f[0]),
                f_max_hz=float(net.f[-1]),
                finite=bool(np.isfinite(net.s).all()),
                z0_ohm=plain(np.unique(net.z0.real)),
            )
        resources.append(row)
    spreadsheet = (
        ROOT / "PyChOpMarg/config/config_com_ieee8023dj_PyChOpMarg_vs_MATLAB.xls"
    )
    modules = {
        n: str(Path(importlib.import_module(n).__file__).resolve())
        for n in ("pybert", "pychopmarg", "pyibisami")
    }
    assert all(Path(p).is_relative_to(ROOT) for p in modules.values())
    report = {
        "calculation_performed": False,
        "python": sys.executable,
        "version": sys.version,
        "platform": platform.platform(),
        "PYTHONPATH": os.environ.get("PYTHONPATH"),
        "modules": modules,
        "packages": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        "base": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "resources": resources,
        "spreadsheet": identity(spreadsheet),
        "com_defaults": budget(IEEE_8023dj),
        "com_spreadsheet": budget(get_com_params(spreadsheet)),
        "source_hashes": {
            str(p.relative_to(ROOT)): identity(p)["sha256"]
            for p in [
                ROOT / "src/pybert/models/com.py",
                ROOT / "PyChOpMarg/src/pychopmarg/com.py",
                ROOT / "PyChOpMarg/src/pychopmarg/config/ieee_8023dj.py",
            ]
        },
    }
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(output),
                "budgets": {
                    k: {a: v for a, v in report[k].items() if a != "parameters"}
                    for k in ("com_defaults", "com_spreadsheet")
                },
            }
        )
    )


if __name__ == "__main__":
    main()
