"""Bounded serial #16 execution. No product mutation or unbudgeted engine calls."""

import importlib
import importlib.metadata
import inspect
import json
import linecache
import os
import sys
import time
import traceback
from pathlib import Path

from external_lane_reference import ISSUE, REFS, ROOT, compare, differential, interpolate, read_touchstone, sha


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def bind(label):
    sources = ISSUE / "local/sources"
    selected = sources / label / "src"
    paths = [selected, sources / "PyAMI/src", sources / "PyChOpMarg/src"]
    sys.path[:0] = [str(p) for p in paths]
    os.environ["PYTHONPATH"] = os.pathsep.join(str(p) for p in paths)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    modules = {name: importlib.import_module(name) for name in
               ("pybert", "pybert.utility.sparam", "pychopmarg", "pyibisami", "numpy", "scipy", "skrf")}
    assert Path(modules["pybert"].__file__).is_relative_to(selected)
    assert Path(modules["pychopmarg"].__file__).is_relative_to(paths[2])
    assert Path(modules["pyibisami"].__file__).is_relative_to(paths[1])
    return {"label": label, "git_commit": REFS[label], "python": sys.executable,
            "python_version": sys.version, "PYTHONPATH": os.environ["PYTHONPATH"],
            "modules": {k: {"file": v.__file__, "sha256": sha(v.__file__)} for k, v in modules.items()},
            "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}}


def guard():
    freeze = json.loads((ISSUE / "freeze-v1.json").read_text(encoding="utf-8"))
    files = dict(freeze["files"])
    amendment = ISSUE / "capture-amendment-v2.json"
    if amendment.exists():
        updated = json.loads(amendment.read_text(encoding="utf-8"))
        assert sha(ISSUE / "freeze-v1.json") == updated["parent_freeze_sha256"]
        assert sha(ISSUE / "evidence/capture-v1.py.txt") == freeze["files"]["tools\\verify_external_lanes.py"]
        files.update(updated["files_override"])
    budget_amendment = ISSUE / "budget-amendment-v3.json"
    if budget_amendment.exists():
        updated = json.loads(budget_amendment.read_text(encoding="utf-8"))
        assert sha(ISSUE / "capture-amendment-v2.json") == updated["capture_amendment_sha256"]
        files.update(updated["files_override"])
    ledger_amendment = ISSUE / "ledger-guard-amendment-v4.json"
    if ledger_amendment.exists():
        updated = json.loads(ledger_amendment.read_text(encoding="utf-8"))
        assert sha(budget_amendment) == updated["budget_amendment_sha256"]
        files.update(updated["files_override"])
    for name, digest in files.items():
        assert sha(ROOT / name) == digest, f"Changed frozen file: {name}"
    for name, digest in freeze["local_source_files"].items():
        assert sha(ISSUE / name) == digest, f"Changed source: {name}"
    return freeze


def reserve(mode, label, selected):
    """Consume the fixed scope once, including failed attempts; no automatic retry."""
    if mode == "importer" and selected:
        raise ValueError("Importer scope is a frozen full batch; individual case selectors are unsupported")
    frozen = guard()
    ledger = ISSUE / "local/execution-ledger.json"
    entries = json.loads(ledger.read_text(encoding="utf-8")) if ledger.exists() else []
    cases = frozen["importer_cases"] if mode == "importer" else frozen["downstream_cases"]
    ids = [c["id"] for c in cases if not selected or c["id"] in selected]
    assert ids and (not selected or set(selected) == set(ids))
    assert label in REFS and (mode != "worker" or label == "final")
    old = {(e["mode"], e["label"], name) for e in entries for name in e["case_ids"]}
    repeated = any((mode, label, name) in old for name in ids)
    attempt_id = "v1"
    if repeated:
        approval = json.loads((ISSUE / "budget-amendment-v3.json").read_text(encoding="utf-8"))
        assert mode == "direct" and label == "pre" and set(ids) == set(approval["retry_case_ids"])
        assert not any(e.get("attempt_id") == "pre-capture-retry-v3" for e in entries)
        attempt_id = "pre-capture-retry-v3"
    entries.append({"mode": mode, "label": label, "case_ids": ids, "attempt_id": attempt_id, "reserved_before_call": True,
                    "reserved_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
    write(ledger, entries)


def importer(label, output, environment):
    import numpy as np
    from pybert.utility.sparam import import_fext, import_freq
    from skrf import Network

    frozen = guard()
    result = {"environment": environment, "cases": [], "calls": {"import_freq": 0, "import_fext": 0},
              "main_invocations": 0, "coopt": 0, "COM": 0, "AMI": 0, "peak_rss": "UNKNOWN"}
    for case in frozen["importer_cases"]:
        f, s, z0, _ = read_touchstone(ROOT / case["original"])
        grid = np.asarray(case["grid_hz"]) if "grid_hz" in case else f
        row = {"case_id": case["id"], "victim": case["victim"], "aggressors": case["aggressors"],
               "renumber": case["renumber"], "input_sha256": sha(ROOT / case["input"]), "checks": []}
        raw = {"original_f": f, "original_single_ended_s": s, "grid_hz": grid}
        started = time.perf_counter()
        try:
            # Verify the independent text reader, without using it to generate expected mapping.
            loaded = Network(str(ROOT / case["original"]))
            row["reader_check"] = compare(loaded.s, s)
            row["reader_frequency"] = compare(loaded.f, f, 1e-12, 1e-6)
            result["calls"]["import_freq"] += 1
            through = import_freq(str(ROOT / case["input"]), lane=case["victim"], renumber=case["renumber"])
            result["calls"]["import_fext"] += 1
            fext = import_fext(str(ROOT / case["input"]), grid, case["victim"], renumber=case["renumber"])
            assert len(fext) == len(case["aggressors"])
            victim = case["physical_lanes"][case["victim"]]
            paths = [("through", through, victim["tx"], victim["rx"], f)] + [
                (f"fext_{j}", actual, case["physical_lanes"][j]["tx"], victim["rx"], grid)
                for j, actual in zip(case["aggressors"], fext)]
            for name, actual, tx, rx, axis in paths:
                expected = differential(s, tx, rx)
                if name != "through":
                    expected = interpolate(f, expected, grid)
                raw.update({name + ".actual_s": actual.s, name + ".expected_s": expected,
                            name + ".f": actual.f, name + ".z0": actual.z0})
                for component in ("real", "imag"):
                    for i in range(2):
                        for j in range(2):
                            row["checks"].append({"path": name, "component": component, "matrix": [i, j],
                                **compare(getattr(actual.s[:, i, j], component), getattr(expected[:, i, j], component))})
                row["checks"].append({"path": name, "component": "frequency", **compare(actual.f, axis, 1e-12, 1e-6)})
                row["checks"].append({"path": name, "component": "z0", **compare(actual.z0, np.full(actual.z0.shape, 2 * z0))})
                # Phase is meaningful only above the predeclared magnitude floor; sign is also
                # checked above through the independently compared real/imaginary components.
                mask = (abs(expected) > frozen["phase_magnitude_floor"]) & (abs(actual.s) > frozen["phase_magnitude_floor"])
                error = np.angle(actual.s[mask] * expected[mask].conj())
                row["checks"].append({"path": name, "component": "phase_rad", "mask_count": int(mask.sum()),
                                      **compare(error, np.zeros_like(error), 0, frozen["phase_atol_rad"])})
            row["passed"] = row["reader_check"]["passed"] and row["reader_frequency"]["passed"] and all(v["passed"] for v in row["checks"])
        except Exception as err:
            row.update(passed=False, error=str(err), traceback=traceback.format_exc())
        row["elapsed_s"] = time.perf_counter() - started
        np.savez_compressed(output / (case["id"] + ".npz"), **raw)
        result["cases"].append(row)
        write(output / "report.json", result)
        print(label, case["id"], row["passed"], row.get("error", ""), flush=True)
        if sum(c["elapsed_s"] for c in result["cases"]) > frozen["budget"]["importer"]["wall_timeout_per_version_s"]:
            raise RuntimeError("Importer wall budget exceeded; no new calls")
    return result


def counter():
    return {"Main": 0, "calc_chnl_h": 0, "import_freq": 0, "import_fext": 0,
            "coopt": 0, "numerical_COM": 0, "compute_com_entries": 0,
            "compute_com_disabled_entries": 0, "AMI_Init": 0, "AMI_GetWave": 0, "PyBERT_constructors": 0}


def count_call(frame, event, costs):
    if event != "call":
        return
    name = frame.f_code.co_name
    owner = frame.f_locals.get("self")
    if name == "__init__" and owner is not None and type(owner).__name__ == "PyBERT":
        costs["PyBERT_constructors"] += 1
    if name == "compute_com" and "pybert" in frame.f_code.co_filename:
        costs["compute_com_entries"] += 1
        if owner is not None and not owner.enable_com:
            costs["compute_com_disabled_entries"] += 1
    field = {"my_run_simulation": "Main", "calc_chnl_h": "calc_chnl_h", "import_freq": "import_freq",
             "import_fext": "import_fext", "coopt": "coopt", "calc_com": "numerical_COM",
             "initialize": "AMI_Init", "getWave": "AMI_GetWave"}.get(name)
    if field and ("pybert" in frame.f_code.co_filename or "pyibisami" in frame.f_code.co_filename):
        costs[field] += 1


def direct(label, output, environment, selected):
    import numpy as np
    import yaml
    from pybert.configuration import PyBertCfg
    from pybert.pybert import PyBERT
    from pybert.models.bert import my_run_simulation

    frozen = guard()
    cases = [c for c in frozen["downstream_cases"] if not selected or c["id"] in selected]
    report = {"environment": environment, "cases": [], "peak_rss": "UNKNOWN"}
    for case in cases:
        directory = output / case["id"]
        directory.mkdir()
        config = json.loads((ROOT / case["config"]).read_text(encoding="utf-8"))
        container = PyBertCfg.__new__(PyBertCfg)
        container.__dict__.update(date_created="", version="11.1.0", **config)
        for field in ("tx_taps", "tx_tap_tuners", "rx_taps", "ffe_tap_tuners", "dfe_tap_tuners"):
            container.__dict__[field] = [tuple(row) for row in config[field]]
        yaml_path = directory / "input.yaml"
        yaml_path.write_text(yaml.dump(container, sort_keys=False, allow_unicode=True), encoding="utf-8")
        row = {"case_id": case["id"], "calls": counter(), "constructors": 0, "passed_producers": False}
        raw, phase_points = {}, []

        def profile(frame, event, result):
            count_call(frame, event, row["calls"])
            if event != "return" or frame.f_back is None:
                return
            caller = frame.f_back
            if frame.f_code.co_name == "trim_impulse" and caller.f_code.co_name == "calc_chnl_h" and "fext_ntwk" in caller.f_locals:
                i = len(phase_points)
                raw.update({f"context.source.fext_{i}_h": result[0].copy(),
                            f"context.source.fext_{i}_start_ix": np.asarray(result[1]),
                            f"context.source.fext_{i}_H": caller.f_locals["fext_H"].copy()})
                phase_points.append(i)
            if frame.f_code.co_name == "convolve" and caller.f_code.co_name == "my_run_simulation" and "h_fext" in linecache.getline(caller.f_code.co_filename, caller.f_lineno):
                i = sum(k.endswith("_voltage") for k in raw)
                raw[f"context.source.fext_{i}_voltage"] = result[:len(caller.f_locals["x"])].copy()
            if frame.f_code.co_name == "my_run_simulation":
                for field in ("x", "noise", "ui", "nui", "nspui", "eye_uis"):
                    if field in frame.f_locals:
                        name = "noise_total" if field == "noise" else field
                        raw["context.source." + name] = np.asarray(frame.f_locals[field]).copy()

        started = time.perf_counter()
        p = None
        try:
            row["constructors"] += 1
            p = PyBERT(run_simulation=False, gui=False)
            p.load_configuration(yaml_path)
            effective = vars(PyBertCfg(p, "", "11.1.0"))
            effective = {k: v for k, v in effective.items() if k not in ("date_created", "version")}
            write(directory / "effective-input.json", effective)
            assert json.loads(json.dumps(effective)) == config, "Native load changed frozen input"
            row["source_functions"] = {name: {"file": inspect.getfile(fn), "sha256": sha(inspect.getfile(fn))}
                                       for name, fn in (("Main", my_run_simulation), ("calc_chnl_h", p.calc_chnl_h))}
            sys.setprofile(profile)
            try:
                my_run_simulation(p, initial_run=True, update_plots=False,
                                  aborted_sim=lambda: time.perf_counter() - started > frozen["budget"]["Main_direct"]["max_per_case_s"])
            finally:
                sys.setprofile(None)
            row["status"] = p.status
            from pybert.web.data import RAW_FIELDS, RESPONSES

            fields = RAW_FIELDS + tuple(f"{point}_{suffix}" for point in RESPONSES for suffix in ("h", "s", "p", "H"))
            for field in fields:
                raw[field] = np.asarray(getattr(p, field)).copy()
            raw["context.source.fext_count"] = np.asarray(len(p.fext_h))
            raw["start_ix"] = np.asarray(p.start_ix)
            row["summary"] = {k: int(getattr(p, k)) for k in ("n_errs_dfe", "n_errs_viterbi")}
            row["window"] = {"ui_s": p.ui, "nui": p.nui, "eye_uis": p.eye_uis,
                             "nspui": p.nspui, "ignore_samps": p.nspui * (p.nui - p.eye_uis),
                             "full_samples": len(p.t), "channel_start_index": p.start_ix}
            row["passed_producers"] = (p.status == "Ready." and len(p.fext_h) == case["fext_count"]
                and len(phase_points) == case["fext_count"] and "context.source.noise_total" in raw
                and sum(k.endswith("_voltage") for k in raw) == case["fext_count"])
        except Exception as err:
            row.update(error=str(err), traceback=traceback.format_exc())
        finally:
            sys.setprofile(None)
            row["elapsed_s"] = time.perf_counter() - started
            row["peak_rss"] = "UNKNOWN"
            if p is not None:
                (directory / "native-console.log").write_text(p.console_log, encoding="utf-8")
            np.savez_compressed(directory / "arrays.npz", **raw)
            write(directory / "report.json", row)
            report["cases"].append(row)
            write(output / "report.json", report)
        print(label, case["id"], row["passed_producers"], row.get("error", ""), flush=True)
        if row["elapsed_s"] > frozen["budget"]["Main_direct"]["max_per_case_s"]:
            raise RuntimeError("Direct wall budget exceeded; no new calls")
    return report


def audited_worker(task_id, operation, request, directory, cancel_event, connection):
    """Audit the real final Web worker process; do not replace its computation."""
    environment = bind("final")
    from pybert.web.worker import run_worker

    counts = counter()
    started = time.perf_counter()
    write(Path(directory) / "actual-environment.json", environment)
    sys.setprofile(lambda frame, event, result: count_call(frame, event, counts))
    try:
        run_worker(task_id, operation, request, directory, cancel_event, connection)
    finally:
        sys.setprofile(None)
        write(Path(directory) / "actual-costs.json", {"calls": counts, "elapsed_s": time.perf_counter() - started,
                                                     "peak_rss": "UNKNOWN"})


def worker(output, environment, selected):
    from pybert.web.tasks import Tasks
    from pybert.web.config import input_hash

    frozen = guard()
    report = {"environment": environment, "cases": []}
    for case in frozen["downstream_cases"]:
        if selected and case["id"] not in selected:
            continue
        config = json.loads((ROOT / case["config"]).read_text(encoding="utf-8"))
        # One manager per case avoids the production two-run cache evicting any evidence.
        manager = Tasks(output / case["id"], worker=audited_worker)
        resource = manager.resources.local(config["ch_file"])
        started = time.perf_counter()
        task = manager.start("run", {"config": config, "input_hash": input_hash(config),
                            "resource_bindings": {"ch_file": resource["resource_id"]}})
        entry = manager.tasks[task["task_id"]]
        while not entry["done"].wait(1):
            if time.perf_counter() - started > frozen["budget"]["worker_timeout_s"]:
                manager.cancel(task["task_id"])
                # Do not release ownership or start another process before actual exit/join.
                write(output / "timeout.json", {"task": task, "cancel_requested": True, "actual_exit": False})
                entry["done"].wait()
                break
        final = manager.get(task["task_id"])
        row = {"case_id": case["id"], "task": final, "directory": str(manager.directory(task["task_id"])),
               "elapsed_s": time.perf_counter() - started, "peak_rss": "UNKNOWN"}
        report["cases"].append(row)
        write(output / "report.json", report)
        print("final", case["id"], final["state"], final.get("error", ""), flush=True)
        if row["elapsed_s"] > frozen["budget"]["worker_timeout_s"]:
            raise RuntimeError("Worker wall budget exceeded; no new calls")
    return report


def main():
    mode, label = sys.argv[1:3]
    if mode == "importer" and len(sys.argv) > 3:
        raise ValueError("Importer scope is a frozen full batch; individual case selectors are unsupported")
    environment = bind(label)
    if mode == "environment":
        write(ISSUE / f"environment-{label}.json", environment)
        print(json.dumps({"label": label, "python": environment["python"], "modules": environment["modules"]}, indent=2))
        return
    output = ISSUE / "local/results" / (label + "-" + mode + "-" + time.strftime("%Y%m%d-%H%M%S"))
    output.mkdir(parents=True)
    write(output / "environment.json", environment)
    reserve(mode, label, sys.argv[3:])
    if mode == "importer":
        importer(label, output, environment)
    elif mode == "direct":
        direct(label, output, environment, sys.argv[3:])
    elif mode == "worker":
        assert label == "final"
        worker(output, environment, sys.argv[3:])
    else:
        raise ValueError(mode)
    print("OUTPUT", output, flush=True)


if __name__ == "__main__":
    main()
