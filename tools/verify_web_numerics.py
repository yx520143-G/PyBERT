"""#2 冻结门槛下对照固定原生 producer；保留每次结果和失败。"""

import hashlib
import importlib.metadata
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from pybert.web import NATIVE_SHA
from pybert.web.config import input_hash, load_config, new_engine, snapshot
from pybert.web.data import CATALOG, collect
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/webui/issue2/fixtures"
EVIDENCE = ROOT / "docs/webui/issue2/evidence"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / "execution-freeze.json"
    if path.exists():
        return
    frozen = json.loads((FIXTURES / "frozen-manifest.json").read_text(encoding="utf-8"))
    assert all(digest(FIXTURES / key) == value for key, value in frozen["files"].items())
    native = subprocess.check_output(["git", "show", f"{NATIVE_SHA}:src/pybert/models/bert.py"], cwd=ROOT)
    (EVIDENCE / "native-bert.py.txt").write_bytes(native)
    payload = {"parent_manifest_sha256": digest(FIXTURES / "frozen-manifest.json"),
                   "native_sha": NATIVE_SHA, "original_bert_sha256": hashlib.sha256(native).hexdigest(),
                   "implementation_base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                   "execution_sources": {str(p.relative_to(ROOT)): digest(p) for p in
                                      [*sorted((ROOT / "src/pybert/web").glob("*.py")), ROOT / "src/pybert/models/bert.py"]},
                   "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                   "python": sys.executable, "catalog": CATALOG, "frozen_before_calculation": True,
                   "tolerances_sha256": digest(FIXTURES / "tolerances.json"),
                   "note": "追加冻结，不替换原fixture/seed/window/tolerance；每次执行另记实际源码hash。"}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("execution-freeze", digest(path), flush=True)


def native_reference(config, directory):
    """Load the exact original source, capturing actual callee returns via Python profiling."""
    source_path = directory / "native_bert.py"
    source_path.write_bytes((EVIDENCE / "native-bert.py.txt").read_bytes())
    spec = importlib.util.spec_from_file_location("pybert.models.reference_bert", source_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    p = new_engine()
    load_config(p, config, snapshot(p))
    effective = snapshot(p)
    assert input_hash(effective) == input_hash(config)
    observations = {}
    points = iter(("chnl", "tx", "ctle", "dfe"))

    def profile(frame, event, result):
        if event == "return" and frame.f_code.co_name == "calc_jitter" and frame.f_back.f_code.co_name == "my_run_simulation":
            local = frame.f_back.f_locals
            observations["source"] = {k: local[k] for k in
                                      ("x", "ideal_signal", "ideal_xings", "ideal_xings_jit", "xing_mask", "ui", "nspui", "nui", "eye_uis", "pattern_len", "rel_thresh", "decision_scaler", "mod_type", "xing_min_t")}
            point = next(points)
            observations[point] = {"ofst": local["ofst"], "actual_xings": local["actual_xings"],
                                       "actual_xings_jit": local["actual_xings_jit"], "t_jitter": result[1],
                                       "bin_centers": result[15], "spectrum_freqs": result[12], "tie": result[0],
                                       "tie_ind": result[8], "valid": True}

    sys.setprofile(profile)
    try:
        module.my_run_simulation(p, initial_run=True, update_plots=False)
    finally:
        sys.setprofile(None)
    assert p.status == "Ready.", p.status
    identity = {"run_id": "direct-reference", "draft_revision": 0, "requested_input": config,
                    "effective_input": effective, "input_hash": input_hash(config)}
    return collect(p, observations, directory, identity)


def compare(reference, candidate, ui):
    report = []
    with np.load(reference / "arrays.npz") as a, np.load(candidate / "arrays.npz") as b:
        assert set(a.files) == set(b.files)
        for key in a.files:
            x, y = a[key], b[key]
            exact = x.dtype.kind in "biu" or any(v in key for v in (".counts", "decisions", "bit_errs", "waveform_indices")) or key in ("bits", "clocks", "lockeds")
            rtol, atol = 1e-10, 1e-12
            category = "voltage_response_complex"
            if key.startswith("display."):
                category, atol = "display", 1e-10
            elif key == "t_ns_chnl" or key.startswith("axis."):
                category, atol = "t_ns_chnl", 1e-9
            elif key == "ui_ests":
                category, atol = "ui_ests_ps", 1e-6
            elif key == "f" or key.endswith(".spectrum_freqs"):
                category, rtol, atol = "frequency_Hz", 1e-12, 1e-6
            elif key.startswith(("jitter_ext_", "jitter_")) and "spectrum" not in key:
                category, atol = "pdf_per_s", 1e-12 / ui
            elif key in ("t", "t_irfft", "clock_times") or any(s in key for s in ("spectrum_", "thresh_", ".ofst", "xings", ".t_jitter", ".tie", ".bin_centers")) or key.split("_")[0] in ("isi", "dcd", "pj", "rj", "pjDD", "rjDD", "mu", "dj"):
                category, atol = "time_jitter_spectrum", 1e-18
            finite = bool(np.isfinite(x).all() and np.isfinite(y).all())
            same_shape = x.shape == y.shape
            passed = finite and same_shape
            first_bad = None
            max_abs = max_rel = None
            if same_shape:
                difference = np.abs(x.astype(complex) - y.astype(complex))
                good = (x == y) if exact else difference <= atol + rtol * np.abs(x)
                passed = passed and bool(good.all())
                if x.size:
                    max_abs = float(difference.max())
                    max_rel = float(np.max(difference / np.maximum(np.abs(x), np.finfo(float).tiny)))
                    if not good.all():
                        first_bad = np.argwhere(~good)[0].tolist()
            report.append({"dataset": key, "category": "exact" if exact else category, "rtol": 0 if exact else rtol,
                               "atol": 0 if exact else atol, "shape_reference": list(x.shape), "shape_worker": list(y.shape),
                               "finite_count_reference": int(np.isfinite(x).sum()), "finite_count_worker": int(np.isfinite(y).sum()),
                               "nonfinite_mask_reference": np.flatnonzero(~np.isfinite(x)).tolist(),
                               "nonfinite_mask_worker": np.flatnonzero(~np.isfinite(y)).tolist(),
                               "max_absolute_error": max_abs, "max_relative_error": max_rel, "first_failure_index": first_bad, "passed": passed})
    return report


def main():
    freeze()
    if "--freeze-only" in sys.argv:
        return
    out = EVIDENCE / ("numeric-" + time.strftime("%Y%m%d-%H%M%S"))
    out.mkdir()
    tasks = Tasks(out / "workers")
    report = {"execution_freeze_sha256": digest(EVIDENCE / "execution-freeze.json"), "fixtures": [],
              "actual_sources": {str(p.relative_to(ROOT)): digest(p) for p in [*sorted((ROOT / "src/pybert/web").glob("*.py")), ROOT / "src/pybert/models/bert.py"]}}
    for name in ("F-NRZ-01", "F-PAM4-01"):
        print(name, "direct native reference", flush=True)
        config = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        direct = out / name
        direct.mkdir()
        entry = {"fixture": name, "input_hash": input_hash(config), "passed": False}
        try:
            native_reference(config, direct)
            print(name, "spawn worker", flush=True)
            task = tasks.start("run", {"config": config, "input_hash": input_hash(config)})
            tasks.tasks[task["task_id"]]["done"].wait()
            final = tasks.get(task["task_id"])
            entry["task"] = final
            if final["state"] != "succeeded":
                raise RuntimeError(final.get("error", final["state"]))
            extension = json.loads((FIXTURES / f"{name}.extensions.json").read_text(encoding="utf-8"))
            entry["arrays"] = compare(direct, tasks.directory(task["task_id"]), extension["window"]["ui_s"])
            a = json.loads((direct / "manifest.json").read_text(encoding="utf-8"))
            b = json.loads((tasks.directory(task["task_id"]) / "manifest.json").read_text(encoding="utf-8"))
            entry["summary_reference"], entry["summary_worker"] = a["summary"], b["summary"]
            entry["passed"] = all(row["passed"] for row in entry["arrays"]) and a["input_hash"] == b["input_hash"] and a["window"] == b["window"] and a["datasets"] == b["datasets"]
        except Exception as err:
            import traceback
            entry.update(error=str(err), traceback=traceback.format_exc())
        report["fixtures"].append(entry)
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(name, "passed=", entry["passed"], entry.get("error", ""), flush=True)
    print("report", out / "report.json", flush=True)
    if not all(f["passed"] for f in report["fixtures"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
