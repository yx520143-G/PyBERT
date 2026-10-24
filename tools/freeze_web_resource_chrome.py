"""Freeze portable browser references and one bounded native-window helper case."""

import copy
import json
import pickle
import subprocess
from pathlib import Path

from pybert.configuration import PyBertCfg
from pybert.web.config import input_hash, new_engine, normalize, yaml_text
from freeze_web_resource_execution import ROOT, OUT, FIX, sha


def main():
    target = FIX / "chrome-and-light-preflight-v3.json"
    if target.exists():
        raise FileExistsError(target)
    resources = json.loads((FIX / "resources.json").read_text(encoding="utf-8"))
    directory = ROOT / "docs/webui/issue4/local/chrome-inputs"
    directory.mkdir(exist_ok=False)
    defaults = new_engine()
    runtime = {
        "version": 1,
        "values": {
            key: getattr(defaults, key)
            for key in ("rlm", "rx_use_clocks", "ami_opt_trials")
        },
    }
    ids = {
        key: row["sha256"] + Path(row["path"]).suffix.lower()
        for key, row in resources.items()
    }
    names = {key: Path(row["path"]).name for key, row in resources.items()}
    nrz = json.loads(
        (ROOT / "docs/webui/issue2/fixtures/F-NRZ-01.json").read_text(encoding="utf-8")
    )
    ab = copy.deepcopy(nrz)
    ab.update(inter_sel="multiple", ch_files=[names["A"], names["B"]])
    ba = copy.deepcopy(ab)
    ba["ch_files"].reverse()
    single = copy.deepcopy(ba)
    single.update(
        inter_sel="single",
        ch_file=names["A"],
        enable_com=True,
        com_cfg_file=resources["C"]["path"],
    )
    fixtures = {"chrome-AB": ab, "chrome-BA": ba, "chrome-single-after-COM": single}
    bindings = {
        "chrome-AB": {"ch_files": [ids["A"], ids["B"]]},
        "chrome-BA": {"ch_files": [ids["B"], ids["A"]]},
        "chrome-single-after-COM": {
            "ch_files": [ids["B"], ids["A"]],
            "ch_file": ids["A"],
            "com_cfg_file": ids["C"],
        },
    }
    for key, config in fixtures.items():
        (directory / f"{key}.json").write_text(
            json.dumps(
                {
                    "config": config,
                    "runtime_extensions": runtime,
                    "resource_bindings": bindings[key],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    (directory / "relative-unbound.yaml").write_text(
        yaml_text(single), encoding="utf-8"
    )
    (directory / "unknown-object.yaml").write_text(
        "!!python/object:unknown.Unsafe {}\n", encoding="utf-8"
    )
    (directory / "invalid-com.xls").write_bytes(
        b"Intentional invalid spreadsheet for failure retention; never a positive resource fixture.\n"
    )
    legacy = copy.deepcopy(nrz)
    legacy.update(
        tx_ibis_file="missing-old-tx.ibs",
        rx_dll_file="missing-old-rx.dll",
        ctle_enable=False,
        ctle_sel="file",
        use_ctle_file=True,
        ctle_file="missing-old-ctle.csv",
        tx_eq_sel="native",
        rx_eq_sel="native",
    )
    legacy.pop("inter_sel")
    legacy["use_ch_file"] = False
    delta = legacy.pop("delta_t_ui")
    legacy["delta_t"] = delta * defaults.ui * 1e12
    expected = normalize({"mode": "load", "config": legacy})
    container = PyBertCfg.__new__(PyBertCfg)
    container.__dict__.update(legacy)
    (directory / "legacy-inactive.pybert_cfg").write_bytes(pickle.dumps(container))
    (directory / "legacy-inactive-expected.json").write_text(
        json.dumps(expected, indent=2), encoding="utf-8"
    )
    window = copy.deepcopy(
        json.loads((FIX / "F4-SINGLE-NRZ.json").read_text(encoding="utf-8"))
    )
    window["use_window"] = True
    (directory / "window-helper-only.json").write_text(
        json.dumps(window, indent=2), encoding="utf-8"
    )
    plan = {
        "before_browser_main_runs": True,
        "fixture_parent_sha256": sha(FIX / "frozen-manifest.json"),
        "corrected_execution_sha256": sha(OUT / "corrected-native-execution-v2.json"),
        "frozen_resource_hashes": {
            key: row["sha256"] for key, row in resources.items()
        },
        "runtime_defaults_explicit": "constructor values; Native inactive extensions, no physical change",
        "portable_ref_policy": "same immutable resources; browser upload names replace absolute references; inactive BA list retained in subsequent single mode",
        "cases": {
            key: {
                "file": str((directory / f"{key}.json").relative_to(ROOT)),
                "input_hash": input_hash(config),
                "input_identity_hash": input_hash(
                    {
                        "config": config,
                        "runtime_extensions": runtime,
                        "resource_bindings": bindings[key],
                    }
                ),
            }
            for key, config in fixtures.items()
        },
        "planned_actions": [
            "Native full YAML load; upload A/B; modify and restore Vod; AB Run and Responses/Results/Jitter",
            "explicit reorder BA then Run and compare; register C by explicit local path",
            "independent real XLS COM; invalid XLS failed child and actual COM cancellation retain old success",
            "single A Run-after-COM with serial core/child and immutable core",
            "Save/Save As/Escape/download/load, unbound relative YAML, explicit base, safe legacy and unknown-object rejection",
            "native blocked CTLE File failed Run and cooperative core Abort retain selected success",
        ],
        "extra_cases_are_lifecycle_only": "failure/cancel and inactive compatibility presets are not additional numerical qualifications",
        "lightweight_domain_check": {
            "window": "window-helper-only.json; direct original calc_chnl_h vs current; no main simulation",
            "package_enums": "KR/C2C A1, CR HL/HN, C2M host/module native device_model preflight only; numeric qualification remains KR/A1",
        },
        "files": {
            p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
            for p in directory.iterdir()
            if p.is_file()
        },
        "chrome": {
            "browser": "installed Chrome, headed",
            "viewport": {"width": 1280, "height": 720},
            "device_scale_factor": 1,
        },
        "actual_sources": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                *sorted((ROOT / "src/pybert/web").rglob("*.py")),
                *sorted((ROOT / "src/pybert/web/static").glob("*")),
                Path(__file__),
            ]
        },
        "head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "default_COM": "BLOCKED_BUDGET / NOT_EXECUTED",
    }
    target.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "plan": str(target),
                "sha256": sha(target),
                "input_files": len(plan["files"]),
            }
        )
    )


if __name__ == "__main__":
    main()
