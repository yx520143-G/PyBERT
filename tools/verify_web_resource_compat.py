"""One frozen window helper pair, package enum preflight and native CLI compatibility."""

import json
import os
import pickle
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from pybert.gui.view import traits_view
from pybert.mcp.server import get_config, get_default_config
from pybert.web.config import load_config, new_engine, snapshot, yaml_text
from pychopmarg.config.ieee_8023dj_d3p3 import device_model
from freeze_web_resource_execution import ROOT, FIX, OUT, sha
from verify_web_resources import load_original


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--saved-cli":
        return recheck_cli(Path(sys.argv[2]))
    dest = OUT / time.strftime("light-compat-%Y%m%d-%H%M%S")
    dest.mkdir()
    config = json.loads(
        (
            ROOT / "docs/webui/issue4/local/chrome-inputs/window-helper-only.json"
        ).read_text(encoding="utf-8")
    )
    nrz = json.loads((FIX / "F4-SINGLE-NRZ.json").read_text(encoding="utf-8"))
    assert config == nrz | {"use_window": True}
    original = load_original("src/pybert/pybert.py", "original_pybert.py", dest)
    cli_input = dest / "native-cli.yaml"
    cli_input.write_text(yaml_text(nrz), encoding="utf-8")
    report = {
        "frozen_plan_sha256": sha(FIX / "chrome-and-light-preflight-v3.json"),
        "same_original_resource_case": "F4-SINGLE-NRZ",
        "window_main_simulation": False,
        "CLI_main_simulations_planned": 1,
        "CLI_helper_collector": "default None through unchanged native simulate()",
        "actual_sources": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                ROOT / "src/pybert/pybert.py",
                ROOT / "src/pybert/models/bert.py",
                ROOT / "src/pybert/cli.py",
                ROOT / "src/pybert/mcp/server.py",
                ROOT / "src/pybert/gui/view.py",
                Path(__file__),
            ]
        },
        "native_cli_input_sha256": sha(cli_input),
        "checks": [],
    }
    (dest / "before-calls.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    arrays = {}
    checks = report["checks"]

    def check(name, good):
        checks.append({"check": name, "passed": bool(good)})

    started = time.perf_counter()
    old, current = original.PyBERT(run_simulation=False, gui=False), new_engine()
    for label, engine in (("original", old), ("current", current)):
        load_config(engine, config, snapshot(engine))
        arrays[label + ".h"] = engine.calc_chnl_h()
        for field in (
            "chnl_H",
            "chnl_s",
            "chnl_p",
            "t_ns_chnl",
            "start_ix",
            "chnl_dly",
        ):
            arrays[label + "." + field] = np.asarray(getattr(engine, field))
    for key in [
        k.removeprefix("original.") for k in arrays if k.startswith("original.")
    ]:
        check(
            "window helper exact native match " + key,
            np.array_equal(
                arrays["original." + key], arrays["current." + key], equal_nan=True
            ),
        )
    np.savez(dest / "window-helper-arrays.npz", **arrays)
    report["window_helper_pair_elapsed_s"] = time.perf_counter() - started
    report["package_preflight"] = []
    for group, cases in (
        ("KR", ("A1",)),
        ("C2C", ("A1",)),
        ("CR", ("HL", "HN")),
        ("C2M", ("host", "module")),
    ):
        for case in cases:
            for is_rx in (False, True):
                model = device_model(group, case, is_rx, include_host=True)
                report["package_preflight"].append(
                    {
                        "group": group,
                        "case": case,
                        "is_rx": is_rx,
                        "native_type": type(model).__name__,
                    }
                )
    check(
        "all declared package enum models instantiate",
        len(report["package_preflight"]) == 12,
    )
    check("native GUI view imports", traits_view is not None)
    defaults = get_default_config()
    loaded = get_config(str(cli_input))
    check(
        "MCP existing config functions preserve frozen whole config",
        all(loaded[key] == value for key, value in nrz.items())
        and "bit_rate" in defaults,
    )
    uv = "C:/Users/yx/AppData/Roaming/Python/Python312/Scripts/uv.exe"
    command = [
        uv,
        "run",
        "--extra",
        "web",
        "pybert",
        "sim",
        str(cli_input),
        "--results",
        str(dest / "native-cli.pybert_data"),
    ]
    started = time.perf_counter()
    run = subprocess.run(
        command, cwd=ROOT, capture_output=True, env=os.environ.copy(), timeout=90
    )
    (dest / "native-cli.stdout.txt").write_bytes(run.stdout)
    (dest / "native-cli.stderr.txt").write_bytes(run.stderr)
    report["CLI"] = {
        "command": command,
        "exitcode": run.returncode,
        "elapsed_s": time.perf_counter() - started,
        "result_exists": (dest / "native-cli.pybert_data").exists(),
    }
    check(
        "actual native CLI completed and saved native results",
        run.returncode == 0
        and report["CLI"]["result_exists"]
        and b"Saved results." in run.stdout,
    )
    report["native_GUI_limit"] = (
        "view import plus native CLI plot construction only; no new desktop GUI qualification; prior issue2 GUI exceptions retained and GUI sources unchanged"
    )
    report["passed"] = all(row["passed"] for row in checks)
    (dest / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(dest / "report.json"),
                "passed": report["passed"],
                "checks": len(checks),
                "CLI": report["CLI"],
            }
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


def recheck_cli(directory):
    """The native CLI sets status to Saved results after saving; inspect its saved bytes."""
    target = directory / "saved-cli-check-v2.json"
    if target.exists():
        raise FileExistsError(target)
    original = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    first = json.loads(
        (OUT / "numeric-20261024-073225/report.json").read_text(encoding="utf-8")
    )["cases"][0]
    # This pickle was generated by this exact local CLI invocation, not an uploaded file.
    native = pickle.loads((directory / "native-cli.pybert_data").read_bytes())
    rows = []
    with np.load(Path(first["worker_directory"]) / "arrays.npz") as saved:
        for field, value in native.the_data.arrays.items():
            if np.asarray(value).shape == () and np.asarray(value).item() is None:
                continue
            expected = (
                saved[f"display.{field}.y"] if field.endswith("_H") else saved[field]
            )
            rows.append(
                {
                    "field": field,
                    "passed": bool(np.array_equal(value, expected, equal_nan=True)),
                }
            )
    checks = [
        row
        for row in original["checks"]
        if row["check"] != "actual native CLI completed and saved native results"
    ]
    checks.append(
        {
            "check": "native CLI exited0 and Saved results status with 22 exact saved native responses",
            "passed": original["CLI"]["exitcode"] == 0
            and b"Saved results." in (directory / "native-cli.stdout.txt").read_bytes()
            and len(rows) == 22
            and all(row["passed"] for row in rows),
        }
    )
    report = {
        "original_report_sha256": sha(directory / "report.json"),
        "driver_sha256": sha(Path(__file__)),
        "main_simulation_performed": False,
        "correction": "v1 incorrectly expected Ready after native save_results, which deliberately changes status to Saved results; first saved-only recheck also needed to recognize ArrayPlotData's zero-dimensional None tx_out. Original successful run/cost/failed verifier retained; no main rerun.",
        "unchanged_CLI_cost": original["CLI"],
        "raw_responses": rows,
        "native_tx_out": "pre-existing saved None plotdata field, not a numerical result",
        "inactive_native_COM_sentinel": "CLI's -999 display is not a COM success; enable_com was false",
        "checks": checks,
        "passed": all(row["passed"] for row in checks),
    }
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"report": str(target), "passed": report["passed"], "checks": len(checks)}
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
