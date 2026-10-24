"""Independent fresh-instance direct coopt vs serial spawn adapter, using frozen #8 inputs."""

import argparse
import ctypes
import importlib.metadata
import json
import multiprocessing
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from pybert.threads.optimization import coopt
from pybert.web.archive import json_bytes, sha256
from pybert.web.config import load_config, new_engine
from pybert.web.data import source_identity
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/webui/issue8/fixtures/v1"


def rss(pid):
    """Read Windows working set without changing the shared dependency environment."""
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (key, ctypes.c_size_t) for key in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
            "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    handle = kernel.OpenProcess(0x410, False, pid)
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    try:
        return counters.PeakWorkingSetSize if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb) else 0
    finally:
        if handle:
            kernel.CloseHandle(handle)


def direct(request, resource, output):
    output = Path(output)
    started = time.time()
    report = {"started_at": started, "python": sys.executable, "PYTHONPATH": os.environ.get("PYTHONPATH"), "source_identity": source_identity()}
    try:
        p = new_engine()
        load_config(p, request["config"])
        p.rlm = request["runtime_extensions"]["values"]["rlm"]
        if resource:
            p.trait_setq(ch_file=resource["path"])
        observations = {}
        result = coopt(p, observations=observations)
        tx, ctle, rx, fom, valid, _, _ = result
        arrays = {key: np.asarray(p.plotdata.get_data(key)) for key in ("p_chnl", "ctle_out_h_tune", "t_ns_opt", "curs_ix", "curs_amp", "clocks_tune")}
        arrays.update(channel_t_ns=p.t_ns[:len(arrays["p_chnl"])], tx_weights=np.asarray(tx), rx_weights=np.asarray(rx),
                      dfe_weights=np.asarray([t.value for t in p.dfe_tap_tuners]))
        candidates = []
        for row in observations["candidates"]:
            prefix = f"candidate_{row['index']:06d}"
            for key in ("pulse", "tx_weights", "rx_weights", "dfe_weights"):
                arrays[f"{prefix}_{key}"] = np.asarray(row[key])
            arrays[f"{prefix}_t_ns"] = p.t_ns[:len(row["pulse"])]
            candidates.append({"candidate_id": f"candidate-{row['index']:06d}", "fom": row["fom"], "ctle_db": row["peak_mag"]})
        for key, value in observations["mmse_context"].items():
            if isinstance(value, np.ndarray):
                arrays[f"mmse_{key}"] = value
        np.savez_compressed(output / "arrays.npz", **arrays)
        winner = max(candidates, key=lambda row: row["fom"])
        report.update(status="succeeded", fom=float(fom), valid=bool(valid), selected_candidate_id=winner["candidate_id"], candidates=candidates,
                      context={key: value for key, value in observations["mmse_context"].items() if not isinstance(value, np.ndarray)},
                      display_db=float(20*np.log10(fom)))
    except Exception as err:
        report.update(status="failed", error=str(err), traceback=traceback.format_exc())
    finally:
        report.update(finished_at=time.time(), elapsed_s=time.time()-started)
        (output / "report.json").write_bytes(json_bytes(report))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append")
    args = parser.parse_args()
    output = ROOT / "docs/webui/issue8/evidence" / time.strftime("numerics-%Y%m%d-%H%M%S")
    output.mkdir(parents=True)
    (output / "local").mkdir()
    freeze = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    report = {"freeze_sha256": sha256((FIXTURES / "manifest.json").read_bytes()), "source_identity": source_identity(),
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "python": sys.executable, "PYTHONPATH": os.environ.get("PYTHONPATH"), "cases": {}, "main_calls": 0, "COM_calls": 0}
    tasks = Tasks(output / "local/adapter")
    for name in args.case or freeze["cases"]:
        fixture = freeze["cases"][name]
        request = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        resource = fixture["resources"][0] if fixture["resources"] else None
        if resource:
            tasks.resources.local(resource["path"])
        target = output / "local" / name
        target.mkdir()
        process = multiprocessing.get_context("spawn").Process(target=direct, args=(request, resource, str(target)))
        process.start()
        peak = 0
        while process.is_alive():
            try:
                peak = max(peak, rss(process.pid))
            except OSError:
                pass
            time.sleep(.05)
        process.join()
        direct_result = json.loads((target / "report.json").read_text(encoding="utf-8"))
        task = tasks.start("optimization", request)
        entry = tasks.tasks[task["task_id"]]
        adapter_peak = 0
        while not entry["done"].wait(.05):
            try:
                adapter_peak = max(adapter_peak, rss(entry["process"].pid))
            except (OSError, ValueError):
                pass
        task = tasks.get(task["task_id"])
        result = tasks.optimization(task["task_id"])
        checks = {"both_succeeded": direct_result["status"] == task["state"] == "succeeded"}
        errors = {}
        if checks["both_succeeded"]:
            with np.load(target / "arrays.npz", allow_pickle=False) as a, np.load(entry["directory"] / "arrays.npz", allow_pickle=False) as b:
                checks["array_inventory"] = set(a.files) == set(b.files)
                for key in a.files:
                    rtol, atol = (0, 1e-9) if "ns" in key else (1e-10, 1e-12)
                    checks[key] = a[key].shape == b[key].shape and np.isfinite(a[key]).all() and np.isfinite(b[key]).all() and np.allclose(a[key], b[key], rtol=rtol, atol=atol)
                    errors[key] = float(np.max(np.abs(a[key]-b[key]))) if a[key].size and a[key].shape == b[key].shape else None
            checks["fom"] = bool(np.isclose(direct_result["fom"], result["fom"], rtol=1e-10, atol=1e-12))
            checks["display_dB"] = bool(np.isclose(direct_result["display_db"], result["display_db"], rtol=1e-10, atol=1e-10))
            checks["selected_identity"] = direct_result["selected_candidate_id"] == result["selected_candidate_id"]
            checks["frozen_order"] = result["plan"]["outer_order"] == fixture["outer_order"]
            checks["inner_order"] = result["plan"]["rx_inner_order"] == (fixture["rx_inner_order"] or [])
            checks["candidate_scores"] = all(np.isclose(a["fom"], b["fom"], rtol=1e-10, atol=1e-12) and a["candidate_id"] == b["candidate_id"] and a["ctle_db"] == b["ctle_db"] for a, b in zip(direct_result["candidates"], result["candidates"]))
            checks["RLM_reached_MMSE_context"] = result["mmse_context"]["rlm"] == request["runtime_extensions"]["values"]["rlm"]
        report["cases"][name] = {"checks": {key: bool(value) for key, value in checks.items()}, "max_errors": errors,
                                  "direct": direct_result, "adapter_task": task, "adapter_record": result,
                                  "peak_rss_bytes": {"direct": peak, "adapter": adapter_peak},
                                  "direct_helper_calls": 1, "adapter_helper_calls": 1 if "plan" in result else 0}
        (output / "report.json").write_bytes(json_bytes(report))
        print(name, task["state"], all(checks.values()), flush=True)
    print(output, flush=True)


if __name__ == "__main__":
    main()
