"""Independent original-engine vs serial worker comparison for frozen #9 cases."""

import argparse
import importlib.metadata
import json
import multiprocessing
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from pybert.models.bert import my_run_simulation, update_trellis
from pybert.web.archive import array_identity, json_bytes, save_archive, load_archive, sha256
from pybert.web.config import load_config, new_engine
from pybert.web.data import collect, source_identity
from pybert.web.tasks import Tasks
from pybert.web.viterbi import TRELLIS_FIELDS
from tools.verify_web_optimizer import rss

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/webui/issue9/fixtures/v1"


def direct(request, directory):
    """The reference reads native locals/debug/plotdata, without web.viterbi.extend."""
    directory = Path(directory)
    started = time.time()
    report = {"started_at": started, "python": sys.executable, "source_identity": source_identity()}
    try:
        p = load_config(new_engine(), request["config"])
        observations, decoding = {}, {}
        my_run_simulation(p, initial_run=True, update_plots=False, observations=observations, decoding=decoding)
        if p.status != "Ready.":
            raise RuntimeError(p.status)
        identity = {**request, "run_id": "direct", "warnings": [], "resources": [], "resource_hash": "0" * 64,
                    "effective_input": request["config"], "requested_input": request["config"]}
        collect(p, observations, directory, identity)
        with np.load(directory / "arrays.npz", allow_pickle=False) as saved:
            arrays = {key: saved[key] for key in saved.files}
        for name in ("dfe", "viterbi"):
            if name in decoding:
                for key, value in decoding[name].items():
                    if isinstance(value, np.ndarray):
                        arrays[f"ber.{name}.{key}"] = value
        if p.rx_use_viterbi:
            debug = p.dbg_dict_viterbi
            for key, value in decoding["isi"].items():
                arrays[f"viterbi.{key}"] = np.asarray(value)
            for key, value in debug.items():
                if key not in ("decoder", "log"):
                    arrays[f"viterbi.{key}"] = np.asarray(value)
            arrays["viterbi.states"] = np.asarray(debug["decoder"].states)
            arrays["viterbi.trans"] = np.asarray(debug["decoder"].trans)
            arrays["viterbi.symbol_index"] = np.arange(len(debug["sig_samps"]))
            arrays["viterbi.state_index"] = np.arange(len(debug["decoder"].states))
            update_trellis(p)
            for key in TRELLIS_FIELDS:
                arrays[f"viterbi.{key}"] = np.asarray(p.plotdata.get_data(key))
        np.savez_compressed(directory / "reference.npz", **arrays)
        report.update(status="succeeded", n_errs_dfe=int(p.n_errs_dfe), n_errs_viterbi=int(p.n_errs_viterbi),
                      ber={name: {k: v for k, v in row.items() if not isinstance(v, np.ndarray)}
                           for name, row in decoding.items() if name in ("dfe", "viterbi")},
                      arrays={k: array_identity(v) for k, v in arrays.items()})
    except Exception as err:
        report.update(status="failed", error=str(err), traceback=traceback.format_exc())
    finally:
        report.update(elapsed_s=time.time() - started, finished_at=time.time(), peak_working_set_bytes=rss(os.getpid()) or None)
        (directory / "report.json").write_bytes(json_bytes(report))


def compare(key, a, b):
    result = {"shape_a": list(a.shape), "shape_b": list(b.shape), "dtype_a": str(a.dtype), "dtype_b": str(b.dtype)}
    if a.shape != b.shape or a.dtype != b.dtype:
        return {**result, "passed": False, "first_mismatch": "shape/dtype"}
    exact = (a.dtype.kind in "biu" or key.endswith(("sample_indices", "path", "prevs"))
             or "trellis_" in key and not key.endswith("probs"))
    probability = key.endswith("probs") or key == "viterbi.trans"
    sample_time = key == "viterbi.sample_times"
    tolerance = {"rtol": 0 if sample_time else 1e-10, "atol": 1e-18 if sample_time else 0 if probability else 1e-12}
    masks = np.array_equal(np.isfinite(a), np.isfinite(b)) and np.array_equal(a == 0, b == 0)
    same = a == b if exact else np.isclose(a, b, **tolerance)
    bad = np.argwhere(~same)
    return {**result, "passed": bool(masks and same.all()), "exact": exact, "tolerance": tolerance,
            "zero_and_finite_masks_exact": bool(masks), "bytes_exact": a.tobytes() == b.tobytes(),
            "max_abs_diff": float(np.max(np.abs(a.astype(complex) - b.astype(complex)))) if a.size else 0.,
            "first_mismatch": bad[0].tolist() if len(bad) else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append")
    args = parser.parse_args()
    output = ROOT / "docs/webui/issue9/evidence" / time.strftime("numerics-%Y%m%d-%H%M%S")
    output.mkdir(parents=True)
    local = output / "local"
    local.mkdir()
    # Save bytes before starting either side. This includes dirty source and the verifier.
    source = output / "source"
    identities = source_identity()
    for relative in identities:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / relative, target)
    shutil.copyfile(__file__, output / "verify_web_viterbi.py")
    report = {"freeze_sha256": sha256((FIXTURES / "manifest.json").read_bytes()), "source_identity": identities,
              "verifier_sha256": sha256(Path(__file__).read_bytes()), "python": sys.executable,
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "main_calls": 0, "COM_calls": 0, "cases": {}}
    (output / "before-execution.json").write_bytes(json_bytes(report))
    manager = Tasks(local / "adapter")
    context = multiprocessing.get_context("spawn")
    for name in args.case or ["V-NRZ-ISI", "V-PAM4-ISI", "V-DUO-ISI", "V-NRZ-ERROR", "V-PAM4-ERROR", "V-DISABLED"]:
        request_path = FIXTURES / f"{name}.json"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        expected = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))["cases"][name]
        assert sha256(request_path.read_bytes()) == expected["request_sha256"]
        directory = local / name
        directory.mkdir()
        process = context.Process(target=direct, args=(request, str(directory)))
        started = time.time()
        process.start()
        report["main_calls"] += 1
        process.join(180)
        if process.is_alive():
            process.terminate()
            process.join()
            result = {"status": "resource_timeout", "error": "direct 180s bound; terminated, not success"}
        else:
            result = json.loads((directory / "report.json").read_text(encoding="utf-8"))
        row = {"direct": result, "direct_exitcode": process.exitcode, "direct_spawn_elapsed_s": time.time()-started}
        process.close()
        task = manager.start("run", request)
        report["main_calls"] += 1
        entry = manager.tasks[task["task_id"]]
        peak = 0
        worker_started = time.time()
        budget_timeout = False
        while not entry["done"].wait(.05):
            try:
                peak = max(peak, rss(entry["process"].pid))
            except (OSError, ValueError):
                pass
            if time.time() - worker_started > 180:
                budget_timeout = True
                manager.cancel(task["task_id"])
                if not entry["done"].wait(10):
                    # Test harness budget termination, never cooperative cancellation evidence.
                    entry["process"].terminate()
                if not entry["done"].wait(10):
                    raise RuntimeError(f"{name}: worker exit still unconfirmed after test budget termination")
                break
        status = manager.get(task["task_id"])
        row.update(adapter=status, adapter_peak_working_set_bytes=peak or None, adapter_budget_timeout=budget_timeout)
        if status["state"] == "succeeded" and result["status"] == "succeeded":
            manifest = manager.manifest(task["task_id"])
            with np.load(directory / "reference.npz", allow_pickle=False) as a, np.load(entry["directory"] / "arrays.npz", allow_pickle=False) as b:
                row["inventory_exact"] = set(a.files) == set(b.files)
                row["arrays"] = {key: compare(key, a[key], b[key]) for key in a.files if key in b.files}
                row["missing"] = sorted(set(a.files) - set(b.files))
                row["extra"] = sorted(set(b.files) - set(a.files))
            row["ber_exact"] = all(manifest["decoding"]["ber"][name] == {"availability": "available", **values}
                                    for name, values in result["ber"].items())
            row["counts_exact"] = all(manifest["summary"][key] == result[key] for key in ("n_errs_dfe", "n_errs_viterbi"))
            archive = directory / "saved.pybert_run"
            save_archive(entry["directory"], archive)
            opened = directory / "opened"
            opened.mkdir()
            load_archive(archive.read_bytes(), opened)
            row["archive_bytes_exact"] = all((opened / f).read_bytes() == (entry["directory"] / f).read_bytes() for f in ("manifest.json", "arrays.npz"))
            # Preserve evidence before the generic two-run temporary cache evicts older successes.
            shutil.copytree(entry["directory"], directory / "adapter")
            row["passed"] = row["inventory_exact"] and row["ber_exact"] and row["counts_exact"] and row["archive_bytes_exact"] and all(v["passed"] for v in row["arrays"].values())
        else:
            row["passed"] = False
        report["cases"][name] = row
        (output / "report.json").write_bytes(json_bytes(report))
        print(json.dumps({"case": name, "direct": result["status"], "adapter": status["state"], "passed": row["passed"], "output": str(output)}), flush=True)
    print(str(output), flush=True)


if __name__ == "__main__":
    main()
