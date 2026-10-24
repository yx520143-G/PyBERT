"""Append the accepted #13 native importer baseline without rewriting #4 inputs."""

import importlib
import json
import subprocess
from pathlib import Path

import numpy as np
from skrf import Network

from pybert.web import NATIVE_IMPORTER_SHA
from pybert.utility import sparam
from pybert.web.config import load_config, new_engine, snapshot
from freeze_web_resource_execution import ROOT, FIX, OUT, sha
from verify_web_resources import load_original


def main():
    target = OUT / "corrected-native-execution-v2.json"
    if target.exists():
        raise FileExistsError(target)
    frozen = json.loads((FIX / "frozen-manifest.json").read_text(encoding="utf-8"))
    assert all(sha(FIX / key) == value for key, value in frozen["files"].items())
    assert all(
        sha(ROOT / key) == value for key, value in frozen["inherited_files"].items()
    )
    resources = json.loads((FIX / "resources.json").read_text(encoding="utf-8"))
    assert all(sha(Path(row["path"])) == row["sha256"] for row in resources.values())
    reference_dir = ROOT / "docs/webui/issue4/local/corrected-reference-v2"
    reference_dir.mkdir(exist_ok=False)
    original = load_original(
        "src/pybert/pybert.py", "original_pybert.py", reference_dir
    )
    assert (
        original.import_channel is sparam.import_channel
        and original.import_fext is sparam.import_fext
    )
    actual = Path(sparam.__file__).resolve()
    accepted = subprocess.check_output(
        ["git", "show", f"{NATIVE_IMPORTER_SHA}:src/pybert/utility/sparam.py"], cwd=ROOT
    ).decode("utf-8")
    assert actual.read_text(encoding="utf-8").replace("\r\n", "\n") == accepted.replace(
        "\r\n", "\n"
    )
    sources = [
        *sorted((ROOT / "src/pybert").rglob("*.py")),
        *sorted((ROOT / "src/pybert/web/static").glob("*")),
        ROOT / "tools/verify_web_resources.py",
        ROOT / "tools/verify_web_analysis.py",
        Path(__file__),
    ]
    raw = list((ROOT / "docs/webui/issue4").rglob("*.npz"))
    result = {
        "version": 2,
        "frozen_before_affected_main_calculation": True,
        "fixture_parent_sha256": sha(FIX / "frozen-manifest.json"),
        "execution_v1_sha256": sha(OUT / "execution-freeze-v1.json"),
        "old_wrong_native_diagnostic_sha256": sha(OUT / "native-port-boundary-v2.json"),
        "issue13": {
            "issue": "https://github.com/yx520143-G/PyBERT/issues/13",
            "pr": "https://github.com/yx520143-G/PyBERT/pull/14",
            "accepted_head": "92c317401e723e13b5a04a809547dc77f4cf8269",
            "merge": NATIVE_IMPORTER_SHA,
            "pm_review": "https://github.com/yx520143-G/PyBERT/pull/14#pullrequestreview-5635615740",
            "accepted_tree": "5934889453131a2e7b1ea6daeeabfce8ce83f9de",
        },
        "branch": subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip(),
        "merged_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "native_change": "only accepted 8/12-port caller selection/renumber mapping; helper formula, 4-port, VITA and all other physics unchanged",
        "direct_reference_policy": "original 1bc PyBERT/bert frames with the accepted corrected native import_channel/import_fext actually bound; historical erroneous multi-lane values are not new expected outputs",
        "direct_reference_corrected_import_channel_binding": True,
        "direct_reference_corrected_import_fext_binding": True,
        "actual_importer_module": str(actual),
        "actual_importer_sha256": sha(actual),
        "modules": {
            name: str(Path(importlib.import_module(name).__file__).resolve())
            for name in ("pybert", "pychopmarg", "pyibisami")
        },
        "actual_sources": {str(p.relative_to(ROOT)): sha(p) for p in sources},
        "resources_unchanged": {key: row["sha256"] for key, row in resources.items()},
        "raw_preservation": {
            "files": [
                {
                    "path": str(p.relative_to(ROOT)),
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                }
                for p in raw
            ],
            "count": len(raw),
            "bytes": sum(p.stat().st_size for p in raw),
        },
        "affected_case_status_at_freeze": {
            name: "NOT_EXECUTED"
            for name in ("F4-L0-OFF", "F4-L0-ON", "F4-L1-OFF", "F4-L1-ON")
        },
        "default_COM_status": "BLOCKED_BUDGET / NOT_EXECUTED",
        "unchanged": "all original inputs/resource bytes, seed/noise, tables, windows, tolerances; old freeze and failures preserved",
        "existing_single_NRZ_applicability": "existing direct/worker raw and saved independent proof retained; 4-port native branch unchanged, no main rerun merely for baseline metadata",
    }
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    p = new_engine()
    cfg = json.loads((FIX / "F4-L0-OFF.json").read_text(encoding="utf-8"))
    load_config(p, cfg, snapshot(p))
    net = Network(resources["M"]["path"])
    reports = []
    for victim in (0, 1):
        aggressor = 1 - victim
        thru = sparam.import_freq(resources["M"]["path"], renumber=False, lane=victim)
        xtalk = sparam.import_fext(resources["M"]["path"], p.f, victim, renumber=False)[
            0
        ]
        ports = [4 * aggressor, 4 * victim + 1, 4 * aggressor + 2, 4 * victim + 3]
        reports.append(
            {
                "victim": victim,
                "aggressor": aggressor,
                "victim_native_subnetwork": list(range(4 * victim, 4 * victim + 4)),
                "fext_native_subnetwork": ports,
                "victim_pair_input": [4 * victim, 4 * victim + 2],
                "victim_pair_output": [4 * victim + 1, 4 * victim + 3],
                "fext_count": 1,
                "fext_max_abs_s21_on_frozen_grid": float(abs(xtalk.s[:, 1, 0]).max()),
                "victim_max_abs_s21_on_resource_grid": float(
                    abs(thru.s[:, 1, 0]).max()
                ),
                "resource_coverage_hz": [float(net.f[0]), float(net.f[-1])],
                "requested_grid_hz": [float(p.f[0]), float(p.f[-1]), len(p.f)],
                "above_resource_coverage": False,
                "renumber": False,
            }
        )
    precheck = OUT / "corrected-native-precheck-v2.json"
    precheck.write_text(
        json.dumps(
            {
                "parent_sha256": sha(target),
                "main_simulation_performed": False,
                "native_helper_precheck_only": True,
                "reports": reports,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "freeze": str(target),
                "sha256": sha(target),
                "precheck_sha256": sha(precheck),
                "M_status": "all four NOT_EXECUTED at freeze",
                "raw_count": len(raw),
                "raw_bytes": result["raw_preservation"]["bytes"],
            }
        )
    )


if __name__ == "__main__":
    main()
