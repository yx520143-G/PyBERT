"""Real frozen spreadsheet COM and the time-domain native boundary, serially."""

import contextlib
import importlib
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from pybert.models.com import calc_com
from pybert.utility.sparam import import_channel
from pybert.web.config import load_config, new_engine, snapshot
from pybert.web.tasks import Tasks
from freeze_web_resource_execution import ROOT, OUT, FIX, sha


def main():
    directory = OUT / time.strftime("native-tools-%Y%m%d-%H%M%S")
    directory.mkdir()
    resources = json.loads((FIX / "resources.json").read_text(encoding="utf-8"))
    for row in resources.values():
        assert sha(Path(row["path"])) == row["sha256"]
    freeze = {
        "before_first_COM_calculation": True,
        "fixture_sha256": sha(FIX / "frozen-manifest.json"),
        "corrected_execution_sha256": sha(OUT / "corrected-native-execution-v2.json"),
        "budget_correction_sha256": sha(FIX / "budget-correction-v2.json"),
        "case": "F4-COM-XLS",
        "thru": resources["A"],
        "configuration": resources["C"],
        "scalar_db_tolerance": {"rtol": 1e-10, "atol": 1e-9},
        "engine_processes": 1,
        "parameters": "exact original spreadsheet; no search/physical settings changed",
        "default_COM": "BLOCKED_BUDGET / NOT_EXECUTED",
        "python": sys.executable,
        "modules": {
            name: importlib.import_module(name).__file__
            for name in ("pybert", "pychopmarg", "pyibisami")
        },
        "sources": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [
                *sorted((ROOT / "src/pybert/web").glob("*.py")),
                ROOT / "src/pybert/models/com.py",
                Path(__file__),
            ]
        },
    }
    (directory / "execution-freeze.json").write_text(
        json.dumps(freeze, indent=2), encoding="utf-8"
    )
    report = {
        "execution_freeze_sha256": sha(directory / "execution-freeze.json"),
        "default_COM": "BLOCKED_BUDGET / NOT_EXECUTED",
    }
    config = json.loads((FIX / "F4-TIME.json").read_text(encoding="utf-8"))
    engine = new_engine()
    load_config(engine, config, snapshot(engine))
    boundary = {
        "case": "F4-TIME",
        "resource_sha256": resources["T"]["sha256"],
        "header_units": resources["T"]["type_evidence"],
        "sample_period_s": float(engine.t[1]),
        "grid_hz": [float(engine.f[0]), float(engine.f[-1]), len(engine.f)],
        "main_simulation_performed": False,
    }
    try:
        network = import_channel(
            resources["T"]["path"],
            engine.t[1],
            engine.f,
            renumber=config["renumber"],
            lane=config["lane_sel"],
        )
        boundary.update(
            native_returned_network=True,
            shape=list(network.s.shape),
            finite=bool(np.isfinite(network.s).all()),
            status="UNVERIFIED_NATIVE_TIME_SEMANTICS",
            reason="H_2_s2p FIXME and step/impulse physical equivalence not independently established",
        )
    except Exception as err:
        boundary.update(
            status="NATIVE_BLOCKED",
            error=str(err),
            error_type=type(err).__name__,
            traceback=traceback.format_exc(),
        )
    report["time_boundary"] = boundary
    (directory / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    os.environ["PYCHOPMARG_PROCS"] = "1"
    counters = {}

    def profile(frame, event, value):
        if (
            event == "return"
            and frame.f_code.co_name == "__call__"
            and frame.f_globals.get("__name__") == "pychopmarg.com"
        ):
            native = frame.f_locals["self"]
            counters.update(
                n_fom_evals=native.n_fom_evals,
                num_tx_combs=native.num_tx_combs,
                package_cases=native.com_rslts.get("case_coms"),
                local_search=native.com_params.local_search,
            )

    try:
        print("F4-COM-XLS direct original calc_com", flush=True)
        start = time.perf_counter()
        with (
            (directory / "direct-merged-console.log").open(
                "w", encoding="utf-8"
            ) as console,
            contextlib.redirect_stdout(console),
            contextlib.redirect_stderr(console),
        ):
            sys.setprofile(profile)
            try:
                value = calc_com(
                    resources["A"]["path"], cfg_file=resources["C"]["path"]
                )
            finally:
                sys.setprofile(None)
        report["direct"] = {
            "value_db": float(value),
            "elapsed_s": time.perf_counter() - start,
            "producer_counters": counters,
        }
        assert math.isfinite(value) and value != -999
        (directory / "report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print("F4-COM-XLS fresh spawn worker", flush=True)
        manager = Tasks(directory / "worker")
        thru = manager.resources.local(resources["A"]["path"])
        cfg = manager.resources.local(resources["C"]["path"])
        task = manager.start(
            "com",
            {
                "thru_resource_id": thru["resource_id"],
                "config_resource_id": cfg["resource_id"],
                "parameter_source": "spreadsheet",
            },
        )
        manager.tasks[task["task_id"]]["done"].wait()
        final = manager.get(task["task_id"])
        report["worker_task"] = final
        assert final["state"] == "succeeded", final.get("error", final)
        result = json.loads(
            (manager.tasks[task["task_id"]]["directory"] / "com.json").read_text(
                encoding="utf-8"
            )
        )
        report["worker_result"] = result
        report["comparison"] = {
            "rtol": 1e-10,
            "atol_db": 1e-9,
            "absolute_difference_db": abs(float(value) - result["value_db"]),
            "passed": bool(
                np.isclose(value, result["value_db"], rtol=1e-10, atol=1e-9)
            ),
        }
        report["passed"] = (
            report["comparison"]["passed"]
            and final["worker_exited"]
            and final["exitcode"] == 0
        )
    except Exception as err:
        report.update(passed=False, error=str(err), traceback=traceback.format_exc())
    (directory / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "report": str(directory / "report.json"),
                "passed": report["passed"],
                "direct": report.get("direct"),
                "time_boundary": boundary["status"],
                "error": report.get("error"),
            }
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
