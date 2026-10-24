"""Only execute frozen AST seams and explicitly bounded NumPy operations."""

import ast
import contextlib
import copy
import hashlib
import io
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import types
import unittest
import warnings
import zipfile
from datetime import datetime, timezone


def main():
    evidence = Path(__file__).resolve().parent
    root = evidence.parents[3]
    plan = json.loads((evidence / "test-plan.json").read_text(encoding="utf-8"))
    destination = evidence / "runs" / plan["run_id"]
    previous = list((evidence / "runs").glob("*/events.jsonl")) if (evidence / "runs").exists() else []
    destination.mkdir(parents=True, exist_ok=False)
    arrays_dir = destination / "arrays"
    arrays_dir.mkdir()
    hashes = {}
    for name, relative in plan["snapshot_paths"].items():
        raw = (root / relative).read_bytes()
        (destination / name).write_bytes(raw)
        hashes[name] = hashlib.sha256(raw).hexdigest()
    counts = {name: 0 for name in plan["limits"]}
    spent = {name: 0 for name in counts}
    for path in previous:
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["kind"] in spent:
                spent[event["kind"]] += 1
    receipt = {"run_id": plan["run_id"], "git_HEAD": subprocess.check_output(
        ["git", "--no-optional-locks", "rev-parse", "HEAD"], cwd=root).decode().strip(),
        "input_sha256": hashes, "spent_before": spent, "counts": counts, "function_entries": {},
        "stub_entries": {}, "blocked_attempts": [], "NumPy_imports": 0, "stage": "stdlib",
        "executable": sys.executable, "prefix": sys.prefix, "python": sys.version,
        "NumPy_ctypes_import_events": [], "serialization": {}, "task_wall_peak_RSS": "UNKNOWN",
        "scope": "actual AST definitions; no product module body or engine import; bounded real NumPy"}
    (destination / "before.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    events = (destination / "events.jsonl").open("w", encoding="utf-8", newline="\n", buffering=1)
    observations = (destination / "observations.jsonl").open("w", encoding="utf-8", newline="\n", buffering=1)
    stdout = (destination / "stdout.txt").open("w", encoding="utf-8", newline="\n", buffering=1)
    stderr = (destination / "stderr.txt").open("w", encoding="utf-8", newline="\n", buffering=1)
    original_streams = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = stdout, stderr
    started, code, np = time.perf_counter(), 1, None
    paths = {str(root / spec["path"]): name for name, spec in plan["modules"].items()}
    paths.update({str(root / spec["path"]): name for name, spec in plan.get("extra_sources", {}).items()})
    cases = str(evidence / "d2_cases.py")

    def block(reason):
        receipt["blocked_attempts"].append(reason)
        events.write(json.dumps({"kind": "blocked", "reason": reason}) + "\n")
        raise RuntimeError("D2 guard: " + reason)

    def entry(kind, name):
        counts[kind] += 1
        receipt["function_entries"][name] = receipt["function_entries"].get(name, 0) + 1
        events.write(json.dumps({"kind": kind, "name": name}) + "\n")
        if spent[kind] + counts[kind] > plan["limits"][kind]:
            block("cumulative " + kind)

    def snapshot(value):
        if isinstance(value, (np.ndarray, np.generic)):
            raw = value.tobytes(order="C")
            if value.dtype.hasobject or len(raw) > 16 * 1024**2:
                block("observation array budget/type")
            digest = hashlib.sha256(raw).hexdigest()
            path = arrays_dir / (digest + ".bin")
            if not path.exists():
                path.write_bytes(raw)
            return {"array_sha256": digest, "dtype": value.dtype.str, "shape": list(value.shape), "bytes": len(raw)}
        if isinstance(value, dict):
            return {str(key): snapshot(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [snapshot(item) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            return {"nonfinite_float": value.hex()}
        if isinstance(value, complex):
            return {"complex": [snapshot(value.real), snapshot(value.imag)]}
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return {"opaque_type": type(value).__name__}

    class ImportGuard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {"pybert", "pyibisami", "pychopmarg", "scipy", "traits", "chaco",
                                          "parsec", "traitsui", "matplotlib", "PySide6", "pytest"}:
                block("product/external import " + fullname)
            if receipt["stage"] == "execution" and fullname.startswith("numpy.random"):
                block("RNG import " + fullname)
            return None

    def audit(event, args):
        if event in ("ctypes.dlopen", "ctypes.dlsym"):
            if receipt["stage"] == "NumPy_import":
                receipt["NumPy_ctypes_import_events"].append([event, repr(args)])
            else:
                block(event)

    def profile(frame, event, arg):
        filename, name = frame.f_code.co_filename, frame.f_code.co_qualname
        if event == "call":
            if filename == cases and frame.f_code.co_name.startswith("stub_"):
                receipt["stub_entries"][name] = receipt["stub_entries"].get(name, 0) + 1
            if filename in paths and frame.f_code.co_name != "<module>":
                full_name = paths[filename] + "." + name
                if full_name in plan.get("forbidden_definitions", []):
                    block("forbidden definition " + full_name)
                entry(plan.get("function_kinds", {}).get(full_name, "pure"), full_name)
                for key, value in frame.f_locals.items():
                    if isinstance(value, np.ndarray):
                        if value.ndim == 1 and len(value) > 4096:
                            block("vector length " + full_name + ":" + key)
                        if value.ndim == 2 and value.size > 64000:
                            block("matrix size " + full_name + ":" + key)
                for key in ("nspui", "samps_per_ui"):
                    if frame.f_locals.get(key, 0) > 32:
                        block("nspui " + full_name)
                if frame.f_locals.get("height", 0) > 1000:
                    block("Eye height")
            elif filename not in paths and ("/src/pybert/" in filename.replace("\\", "/")
                                            or "/src/pyibisami/" in filename.replace("\\", "/")):
                block("other product execution " + filename + ":" + name)
            if receipt["stage"] == "execution" and "/numpy/random/" in filename.replace("\\", "/"):
                block("RNG execution")
        elif event == "return" and filename in paths and frame.f_code.co_name in plan.get("observe", []):
            state = {key: value for key, value in frame.f_locals.items() if key in ("arrays", "info", "manifest")}
            observations.write(json.dumps({"function": paths[filename] + "." + name,
                                          "event": "return_or_exception", "return": snapshot(arg),
                                          "state": snapshot(state)}, allow_nan=False) + "\n")
        elif event == "c_call" and receipt["stage"] == "execution":
            if str(getattr(arg, "__module__", "")).startswith("numpy.random"):
                block("RNG C call")

    guard = ImportGuard()
    sys.meta_path.insert(0, guard)
    sys.addaudithook(audit)
    sys.setprofile(profile)
    try:
        assert Path(sys.prefix).resolve() == root / ".venv"
        assert not any(name.split(".")[0] in {"numpy", "pybert", "pyibisami", "scipy"} for name in sys.modules)
        environment = json.loads((evidence / "environment.json").read_text(encoding="utf-8"))
        for path, digest in environment["installed_files_sha256"].items():
            assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path
        receipt["stage"] = "NumPy_import"
        import numpy as np  # noqa: PLC0415 -- authorized only after guards and installed-file verification
        receipt.update(NumPy_imports=1, NumPy_version=np.__version__, NumPy_path=np.__file__)
        assert np.__version__ == environment["numpy_metadata_version"]
        real_histogram, real_rfft = np.histogram, np.fft.rfft

        def histogram(values, *args, **kwargs):
            entry("histogram", "numpy.histogram")
            if len(values) > 4096:
                block("histogram input")
            return real_histogram(values, *args, **kwargs)

        def rfft(values, *args, **kwargs):
            entry("rfft", "numpy.fft.rfft")
            if len(values) > 4096:
                block("FFT input")
            return real_rfft(values, *args, **kwargs)

        def forbidden(*args, **kwargs):
            block("unapproved NumPy DSP/RNG")

        np.histogram, np.fft.rfft = histogram, rfft
        np.convolve = np.correlate = np.fft.fft = np.fft.irfft = forbidden
        np.random = types.SimpleNamespace(default_rng=forbidden, seed=forbidden, normal=forbidden)
        receipt["stage"] = "execution"
        modules = {}
        base = dict(np=np, Path=Path, json=json, hashlib=hashlib, copy=copy, time=time, math=math,
                    os=os, tempfile=tempfile, io=io, zipfile=zipfile, warnings=warnings,
                    contextlib=contextlib, datetime=datetime, timezone=timezone,
                    SimpleNamespace=types.SimpleNamespace, monotonic_ns=time.monotonic_ns)
        for name, spec in plan["modules"].items():
            path = root / spec["path"]
            module = types.ModuleType(name)
            module.__dict__.update(base, __file__=str(path))
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            definitions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                           and (spec.get("names") is None or node.name in spec["names"])]
            wrapped = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")],
                                                     level=0), *definitions], type_ignores=[])
            ast.fix_missing_locations(wrapped)
            exec(compile(wrapped, str(path), "exec"), module.__dict__)
            modules[name] = module
        seam = types.ModuleType("d2_under_test")
        seam.__dict__.update(modules=modules, np=np, root=root, evidence=evidence, destination=destination)
        sys.modules[seam.__name__] = seam
        tests = types.ModuleType("d2_cases")
        exec(compile(Path(cases).read_text(encoding="utf-8"), cases, "exec"), tests.__dict__)
        suite = (unittest.defaultTestLoader.loadTestsFromNames(plan["selection"], tests) if plan["selection"]
                 else unittest.defaultTestLoader.loadTestsFromModule(tests))
        result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(suite)
        receipt.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors))
        code = 0 if result.wasSuccessful() and not receipt["blocked_attempts"] else 1
    except BaseException:
        traceback.print_exc(file=stderr)
    finally:
        sys.setprofile(None)
        sys.meta_path.remove(guard)
        sys.stdout, sys.stderr = original_streams
        receipt.update(exit_code=code, elapsed_s=time.perf_counter() - started)
        receipt["loaded_NumPy_extensions"] = {name: str(getattr(module, "__file__", ""))
            for name, module in list(sys.modules.items()) if name.startswith("numpy")
            and str(getattr(module, "__file__", "")).endswith(".pyd")}
        stdout.close()
        stderr.close()
        events.close()
        observations.close()
        receipt["output_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in destination.iterdir() if path.is_file() and path.name not in hashes and path.name != "before.json"}
        receipt["array_output_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                           for path in sorted(arrays_dir.iterdir())}
        receipt["inputs_unchanged_after"] = all(hashlib.sha256((root / relative).read_bytes()).hexdigest() == hashes[name]
            for name, relative in plan["snapshot_paths"].items())
        if not receipt["inputs_unchanged_after"]:
            receipt["exit_code"], code = 1, 1
        receipt["run_output_bytes"] = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
        (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"run": plan["run_id"], "exit_code": code, "counts": counts, "elapsed_s": receipt["elapsed_s"]}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
