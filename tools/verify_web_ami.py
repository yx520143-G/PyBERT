"""Independent native instances versus the Web child, using committed complete AMI inputs."""

import copy
import json
import multiprocessing
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from pybert.web.archive import json_bytes, sha256, save_archive
from pybert.web.config import input_hash, snapshot, yaml_text
from pybert.web.data import collect, source_identity
from pybert.web.tasks import Tasks
from pybert.web.ami import Execution

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.verify_web_optimizer import rss
FIXTURES = ROOT / "docs/webui/issue10/fixtures/v2-executable"


def direct(task_id, operation, request, directory, cancel, pipe):
    from pybert.pybert import PyBERT
    from pybert.models.bert import my_run_simulation
    from pybert.threads.optimization import coopt

    p = PyBERT(run_simulation=False, gui=False)
    c = copy.deepcopy(request["config"])
    runtime = request["runtime_extensions"]["values"]
    model_report = request["direct_model_reports"]
    execution = Execution()
    status = {"status": "failed"}
    started = time.time()
    try:
        for side, model in runtime.get("ami_models", {}).items():
            bundle = next(r for r in request["frozen_resources"] if r["field"] == side + "_model_bundle")
            root = Path(bundle["worker_path"])
            report = model_report[side]
            c[side + "_ibis_file"] = str(root / model["selection"]["ibis_path"])
            c[side + "_ami_file"] = str(root / report["ami_path"])
            c[side + "_dll_file"] = str(root / report["binary_path"])
        path = Path(directory, "direct.yaml")
        path.write_text(yaml_text(c), encoding="utf-8")
        p.load_configuration(path)
        for side, model in runtime.get("ami_models", {}).items():
            ibis = getattr(p, "_" + side + "_ibis")
            for key in ("comp", "pin", "mod"):
                assert getattr(ibis, key) == model["selection"][key]
            cfg = getattr(p, "_" + side + "_cfg")
            cfg.sim_corner = model["sim_corner"]
            for row in model["parameters"]:
                if row["editable"]:
                    cfg.set_param_val(list(row["path"]), row["value"])
                assert cfg.fetch_param_val(list(row["path"])) == row["value"]
            # This is the original mode observer, after native YAML's tuner restoration.
            if c[side + "_use_ami"]:
                setattr(p, side + "_use_ami", False)
                setattr(p, side + "_use_ami", True)
            for tuner in getattr(p, side + "_ami_tap_tuners"):
                row = next(r for r in model["search"] if r["path"] == list(tuner.branch_names))
                for key in ("enabled", "value", "min_val", "max_val", "step"):
                    setattr(tuner, key, row[key])
        for key in ("rlm", "rx_use_clocks", "ami_opt_trials"):
            setattr(p, key, runtime[key])
        effective = snapshot(p)
        effective.update({key: request["config"][key] for side in ("tx", "rx") for key in (side + "_ibis_file", side + "_ami_file", side + "_dll_file")})
        assert effective == request["config"], "direct effective snapshot differs from frozen normalized input"
        (Path(directory) / "effective.json").write_bytes(json_bytes(effective))
        observations, decoding = {}, {}
        with execution.capture():
            if operation == "run":
                my_run_simulation(p, initial_run=True, update_plots=False, observations=observations, decoding=decoding)
                assert p.status == "Ready."
            else:
                result = coopt(p, observations=observations)
                assert result[4]
                arrays = {}
                for row in observations["candidates"]:
                    for key in ("pulse", "tx_weights", "rx_weights", "dfe_weights"):
                        arrays[f"candidate_{row['index']:06d}_{key}"] = row[key]
                arrays.update(execution.arrays)
                np.savez_compressed(Path(directory) / "arrays.npz", **arrays)
                status["result"] = {"fom": float(result[3]), "trials": len(observations["candidates"])}
        execution.write(directory, model_report)
        if operation == "run":
            identity = {"run_id": task_id, "requested_input": request["config"], "effective_input": effective,
                        "input_hash": request["input_hash"], "input_identity_hash": request["input_identity_hash"],
                        "resource_hash": request["resource_hash"], "resources": request["frozen_resources"],
                        "runtime_extensions": request["runtime_extensions"], "resource_bindings": request["resource_bindings"],
                        "execution_strategy": {}, "warnings": []}
            collect(p, observations, directory, identity, decoding=decoding, ami=(execution, model_report) if model_report else None)
        status.update(status="succeeded")
    except Exception as error:
        status.update(error=str(error), traceback=traceback.format_exc())
        execution.write(directory, model_report)
    finally:
        status.update(elapsed_s=time.time() - started, main_calls=1 if operation == "run" else 0,
                      helper_calls=len(execution.calls), library_calls=execution.library_calls)
        Path(directory, "direct-report.json").write_bytes(json_bytes(status))
        pipe.send({"task_id": task_id, "kind": "terminal", "cancel_observed": False, **status})
        pipe.close()


def run_case(manager, operation, request, name):
    started = time.time()
    task = manager.start(operation, request)
    entry = manager.tasks[task["task_id"]]
    peak = 0
    while not entry["done"].wait(.02):
        peak = max(peak, rss(entry["process"].pid))
        if time.time() - started > 180:
            raise TimeoutError("Declared wall budget exceeded; worker evidence retained; no replacement success.")
    result = manager.get(task["task_id"])
    result.update(name=name, peak_rss_bytes=peak, outer_elapsed_s=time.time() - started)
    return result, entry["directory"]


def main():
    out = ROOT / f"docs/webui/issue10/evidence/numerics-{time.strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True)
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    # Actual execution source is captured before the first task, independent of the fixture-generation code.
    source = source_identity()
    for path in (ROOT / "src/pybert").rglob("*.py"):
        target = out / "execution-source" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (out / "before.json").write_bytes(json_bytes({"fixture_manifest_sha256": sha256((FIXTURES / "manifest.json").read_bytes()),
                                                   "actual_source": source, "main_budget": 22, "optimization_evaluations_per_path": [1, 4]}))
    models = json.loads((FIXTURES / "model-resources.json").read_text(encoding="utf-8"))
    results = {}
    for name in sys.argv[1:] or manifest["cases"]:
        request = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        assert sha256((FIXTURES / f"{name}.json").read_bytes()) == manifest["cases"][name]["request_sha256"]
        pair = {}
        directories = {}
        for path_name, worker in (("direct", direct), ("worker", None)):
            manager = Tasks(ROOT / f".pybert-web/issue10-{out.name}-{name}-{path_name}", **({"worker": worker} if worker else {}))
            manager.resources.items.update(copy.deepcopy({r["resource_id"]: r for r in models.values()}))
            # Copy only already-frozen bytes into this service's own content store.
            for model in models.values():
                src = ROOT / ".pybert-web/issue10-acceptance/resources" / model["resource_id"]
                shutil.copytree(src, manager.resources.root / model["resource_id"])
            supplied = copy.deepcopy(request)
            supplied["direct_model_reports"] = manifest["cases"][name]["model_check"]
            supplied["frozen_resources"] = manager.resources.for_run(request["config"], request["resource_bindings"])
            supplied["resource_hash"] = input_hash([{k: row[k] for k in ("field", "index", "sha256")} for row in supplied["frozen_resources"]])
            operation = ("direct_optimization" if worker else "optimization") if name.startswith("OPT") else "run"
            result, directory = run_case(manager, operation, supplied, name)
            pair[path_name] = result
            directories[path_name] = directory
            target = out / name / path_name
            shutil.copytree(directory, target)
        compare = {"status": "not compared; actual path failed"}
        if all(r["state"] == "succeeded" for r in pair.values()):
            with np.load(directories["direct"] / "arrays.npz", allow_pickle=False) as a, np.load(directories["worker"] / "arrays.npz", allow_pickle=False) as b:
                keys = set(a.files) if name.startswith("OPT") else set(a.files) - {"display.run_id"}
                mismatches = []
                maxabs = 0.0
                for key in keys:
                    if key not in b or a[key].shape != b[key].shape:
                        mismatches.append(key + ": missing/shape")
                        continue
                    unit = ""
                    if not name.startswith("OPT"):
                        unit = json.loads((directories["direct"] / "manifest.json").read_text(encoding="utf-8"))["datasets"][key]["unit"]
                    atol, rtol = (1e-18, 0) if unit == "s" else (1e-12, 1e-10)
                    if a[key].dtype.kind in "biu":
                        equal = np.array_equal(a[key], b[key])
                    else:
                        equal = np.allclose(a[key], b[key], rtol=rtol, atol=atol)
                    if not equal:
                        mismatches.append(key)
                    if a[key].size and a[key].dtype.kind != "b":
                        maxabs = max(maxabs, float(np.max(np.abs(a[key] - b[key]))))
                compare = {"status": "passed" if not mismatches else "failed", "arrays": len(keys), "mismatches": mismatches, "max_absolute_difference": maxabs}
            if not name.startswith("OPT"):
                save_archive(directories["worker"], out / name / "saved.pybert_run")
        results[name] = {"tasks": pair, "comparison": compare}
        (out / "report.json").write_bytes(json_bytes(results))
        print(json.dumps({"case": name, "states": {k: v["state"] for k, v in pair.items()}, "comparison": compare}), flush=True)
    print(json.dumps({"output": str(out)}))


if __name__ == "__main__":
    main()
