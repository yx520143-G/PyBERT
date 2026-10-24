"""Freeze #4 resources/cases and exact native COM grid metadata before calculation."""

import copy
import hashlib
import itertools
import json
import shutil
from pathlib import Path

import numpy as np
from skrf import Network
from pychopmarg.config.ieee_8023dj import IEEE_8023dj
from pychopmarg.excel import get_com_params
from pychopmarg.utility.general import mk_combs

from inspect_web_resource_budget import ROOT, identity, plain


def exact_budget(cp):
    grids = [
        mk_combs([t]) for t in zip(cp.tx_taps_min, cp.tx_taps_max, cp.tx_taps_step)
    ]
    filtered, has_zero = 0, False
    for row in itertools.product(*grids):
        comb = np.array(row).ravel()
        if (1 - abs(comb).sum()) >= cp.c0_min:
            filtered += 1
            if not has_zero:
                has_zero = bool(np.allclose(comb, 0))
    n_tx = filtered + (not has_zero)
    return {
        "parameters": plain(cp),
        "tx_grid_lengths": list(map(len, grids)),
        "filtered_grid_count": filtered,
        "zero_in_grid_np_allclose": has_zero,
        "opt_eq_tx_ixs": n_tx,
        "outer_candidate_upper_bound_per_package": n_tx * len(cp.g_DC) * len(cp.g_DC2),
        "gDC_count": len(cp.g_DC),
        "gDC2_count": len(cp.g_DC2),
        "local_search": cp.local_search,
        "timing_search": cp.ts_srch_mode,
        "cost_boundary": "outer candidates only; internal timing/MMSE cost and runtime not measured",
        "calculation_performed": False,
    }


def main():
    target = ROOT / "docs/webui/issue4/fixtures"
    target.mkdir(exist_ok=False)
    local = ROOT / "docs/webui/issue4/local/resources"
    local.mkdir(parents=True, exist_ok=True)
    prior = ROOT / "docs/webui/issue4/evidence/resource-budget-inspection.json"
    sheet = ROOT / "PyChOpMarg/config/config_com_ieee8023dj_PyChOpMarg_vs_MATLAB.xls"
    corrected = {
        "parent_sha256": identity(prior)["sha256"],
        "calculation_performed": False,
        "reason": "Use exact numpy cursor filter and np.allclose no-EQ rule; initial Python sum count superseded. TwoLaneModel is 0–80GHz, s4p is 0–40GHz.",
        "default": exact_budget(IEEE_8023dj),
        "spreadsheet": exact_budget(get_com_params(sheet)),
        "pm_budget_decision_v1": {
            "default": "BLOCKED_BUDGET / NOT_EXECUTED; unchanged required case retained",
            "spreadsheet": "proceed after complete freeze",
            "product_parameter_change": False,
            "product_hard_limit_added": False,
            "source": "PM chat 01a16a69-8a11-71a0-8620-5d157b897926 / 2026-10-24",
        },
    }
    (target / "budget-correction-v2.json").write_text(
        json.dumps(corrected, indent=2), encoding="utf-8"
    )
    specs = [
        (
            "A",
            ROOT / "PyChOpMarg/chnl_data/example2_THRU.s4p",
            "PyChOpMarg ca905e793fcf6330929471317ca32e7611578e5d / chnl_data/example2_THRU.s4p",
            "BSD-3-Clause submodule LICENSE",
        ),
        (
            "B",
            Path(
                "E:/serial-bus-simulator/source/Sam_Palermo_-_ECEN_720__High-Speed_Links_Circuits_and_Systems/project/002_peters_01_0605_B1_thru.s4p"
            ),
            "https://people.engr.tamu.edu/spalermo/ecen689/peters_01_0605_B1_thru.s4p; local course archive README",
            "user local course material; local evaluation only, no redistribution license claimed",
        ),
        (
            "M",
            Path(
                "E:/serdes-equalization-explorer/SignalIntegrity-master/Test/TestSignalIntegrity/TestStatisticalNoise/TwoLaneModel.s8p"
            ),
            "https://github.com/Nubis-Communications/SignalIntegrity / Test/TestSignalIntegrity/TestStatisticalNoise/TwoLaneModel.s8p; header SignalIntegrity v1.5.1",
            "GPL-3-or-later local LICENSE; existing physical model, not measured hardware",
        ),
        (
            "T",
            ROOT / "PyAMI/examples/impulse_response_8ma.txt",
            "PyAMI 5270d713e40bac2be5747bef09b92df79df9085b / examples/impulse_response_8ma.txt",
            "BSD-style submodule LICENSE",
        ),
        (
            "C",
            sheet,
            "PyChOpMarg ca905e793fcf6330929471317ca32e7611578e5d / config original spreadsheet",
            "BSD-3-Clause submodule LICENSE",
        ),
    ]
    resources = {}
    for key, path, source, permission in specs:
        frozen = local / path.name
        if frozen.exists():
            raise FileExistsError(frozen)
        shutil.copyfile(path, frozen)
        row = {
            **identity(frozen),
            "source_path": str(path),
            "source": source,
            "permission": permission,
        }
        if frozen.suffix in (".s4p", ".s8p"):
            net = Network(str(frozen))
            row.update(
                ports=net.nports,
                f_hz=[float(net.f[0]), float(net.f[-1])],
                n_frequency=len(net.f),
                s_unit="dimensionless complex",
                z0_unit="ohm",
                z0_ohm=plain(np.unique(net.z0.real)),
                finite=bool(np.isfinite(net.s).all()),
                source_bytes_unmodified=True,
            )
            if net.nports == 8:
                row["lane_port_convention_0based"] = [[0, 1, 2, 3], [4, 5, 6, 7]]
                row["native_victim_subnetwork_order"] = [[0, 2, 1, 3], [4, 6, 5, 7]]
                row["crosslane_max_abs_s"] = float(abs(net.s[:, :4, 4:]).max())
        elif key == "T":
            row.update(
                time_unit="s",
                ordinate_unit="V/s",
                type_evidence=path.read_text(encoding="utf-8").splitlines()[0],
                native_boundary="H_2_s2p FIXME; preserve exact native direct reproduction and blocked state, no algorithm repair",
            )
        resources[key] = row
    (target / "resources.json").write_text(
        json.dumps(resources, indent=2), encoding="utf-8"
    )
    inherited = ROOT / "docs/webui/issue2/fixtures"
    nrz = json.loads((inherited / "F-NRZ-01.json").read_text(encoding="utf-8"))
    pam = json.loads((inherited / "F-PAM4-01.json").read_text(encoding="utf-8"))
    cases = []

    def case(name, patch, resource_keys, origin="F-NRZ-01", status="PLANNED"):
        config = copy.deepcopy(nrz if origin == "F-NRZ-01" else pam)
        config.update(patch)
        (target / f"{name}.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )
        cases.append(
            {
                "case": name,
                "input": f"{name}.json",
                "inherits": origin,
                "resources": resource_keys,
                "status_before_calculation": status,
                "enabled_analyses": "all #3 analysis_version2 datasets",
                "noise_seed_window_tolerance": "unchanged from inherited fixture",
            }
        )

    a, b, m, t = [resources[k]["path"] for k in ("A", "B", "M", "T")]
    case("F4-SINGLE-NRZ", {"inter_sel": "single", "ch_file": a}, ["A"])
    case("F4-SINGLE-PAM4", {"inter_sel": "single", "ch_file": a}, ["A"], "F-PAM4-01")
    case("F4-CASCADE-AB", {"inter_sel": "multiple", "ch_files": [a, b]}, ["A", "B"])
    case("F4-CASCADE-BA", {"inter_sel": "multiple", "ch_files": [b, a]}, ["B", "A"])
    for lane in (0, 1):
        for fext in (False, True):
            case(
                f"F4-L{lane}-{'ON' if fext else 'OFF'}",
                {
                    "inter_sel": "single",
                    "ch_file": m,
                    "lane_sel": lane,
                    "include_fext": fext,
                },
                ["M"],
            )
    case("F4-PACKAGE", {"inter_sel": "single", "ch_file": a, "pkg_enable": True}, ["A"])
    case("F4-DUO", {"mod_type": "Duo-binary"}, [])
    case(
        "F4-TIME",
        {"inter_sel": "single", "ch_file": t},
        ["T"],
        status="NATIVE_BOUNDARY_PENDING_REPRODUCTION",
    )
    com = [
        {
            "case": "F4-COM-DEFAULT",
            "thru": "A",
            "parameters": "IEEE_8023dj defaults",
            "status": "BLOCKED_BUDGET / NOT_EXECUTED",
            "parameters_ref": "budget-correction-v2.json#default",
        },
        {
            "case": "F4-COM-XLS",
            "thru": "A",
            "config": "C",
            "status": "PLANNED",
            "parameters_ref": "budget-correction-v2.json#spreadsheet",
        },
    ]
    (target / "cases.json").write_text(
        json.dumps(
            {
                "runs": cases,
                "com": com,
                "com_tolerance_db": {"rtol": 1e-10, "atol": 1e-9},
                "cost_policy": "serial direct then one fresh worker; one representative per listed case; no port/rate matrix; preserve failures; no resource/case substitution",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    inherited_hashes = {
        str(p.relative_to(ROOT)): identity(p)["sha256"]
        for p in inherited.iterdir()
        if p.is_file()
    }
    manifest = {
        "frozen_before_calculation": True,
        "calculation_performed": False,
        "base": "9a33d08458aa00782e90169c699857b8b19455a2",
        "inherited_files": inherited_hashes,
        "window_correction_v2_sha256": identity(
            ROOT / "docs/webui/issue3/fixtures/window-correction-v2.json"
        )["sha256"],
        "environment_ref": "../evidence/resource-budget-inspection.json",
        "files": {
            p.name: identity(p)["sha256"] for p in target.iterdir() if p.is_file()
        },
        "resource_bytes": sum(row["bytes"] for row in resources.values()),
        "saved_raw_policy": "ignored local NPZ retained; no cleanup of #2/#3 or failed images",
    }
    (target / "frozen-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "manifest": identity(target / "frozen-manifest.json"),
                "corrected_default_outer_upper_bound": corrected["default"][
                    "outer_candidate_upper_bound_per_package"
                ],
                "cases": len(cases),
                "resource_bytes": manifest["resource_bytes"],
            }
        )
    )


if __name__ == "__main__":
    main()
