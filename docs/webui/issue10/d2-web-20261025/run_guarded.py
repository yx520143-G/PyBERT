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
    serialized_dir = destination / "serialized"
    serialized_dir.mkdir()
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
    cases = str(evidence / ("guard_cases.py" if plan.get("guard_only") else "d2_cases.py"))
    copies = {}
    serial_calls = {}

    def retain_bytes(content, kind):
        if not isinstance(content, (bytes, str)):
            return None
        raw = content.encode("utf-8") if isinstance(content, str) else content
        if len(raw) > 16 * 1024**2:
            block("serialized evidence input exceeds16MiB")
        digest = hashlib.sha256(raw).hexdigest()
        path = serialized_dir / (digest + "." + kind)
        if not path.exists():
            path.write_bytes(raw)
            receipt.setdefault("instrumentation_raw_blob_copies", {"calls": 0, "bytes": 0})["calls"] += 1
            receipt["instrumentation_raw_blob_copies"]["bytes"] += len(raw)
        return digest

    def block(reason):
        receipt["blocked_attempts"].append(reason)
        events.write(json.dumps({"kind": "blocked", "reason": reason}) + "\n")
        # A profile exception disables profiling and can be swallowed by a case or unittest.
        # Only this trusted stdlib receipt path runs after a guard; no test/finally/model code resumes.
        sys.setprofile(None)
        try:
            receipt.update(exit_code=86, status="blocked", elapsed_s=time.perf_counter() - started,
                           tests_run=None, failures=None, errors=None,
                           attempted_blocked=reason, product_body_after_block="not executed")
            for stream in (stdout, stderr, events, observations):
                stream.flush()
                stream.close()
            receipt["output_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in destination.iterdir() if path.is_file() and path.name not in hashes
                and path.name not in ("before.json", "receipt.json")}
            receipt["array_output_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                               for path in sorted(arrays_dir.iterdir())}
            receipt["artifact_sha256"] = {
                str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in destination.rglob("*") if path.is_file() and path.parent != destination}
            receipt["inputs_unchanged_after"] = all(
                (root / relative).is_file()
                and hashlib.sha256((root / relative).read_bytes()).hexdigest() == hashes[name]
                for name, relative in plan["snapshot_paths"].items())
            (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                                      encoding="utf-8", newline="\n")
        finally:
            os._exit(86)

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
        if event == "call" and filename in paths and paths[filename] == "pybert.web.archive":
            if name in ("read_arrays", "load_archive", "read_json"):
                content = frame.f_locals.get("content")
                digest = retain_bytes(content, "json" if name == "read_json" else
                                      "npz" if name == "read_arrays" else "pybert_run")
                events.write(json.dumps({"kind": "serialization_input", "name": name,
                                         "input_blob_sha256": digest}) + "\n")
        if filename in paths and paths[filename] == "pybert.web.archive" and name in (
                "sha256", "json_bytes", "read_json", "atomic_write"):
            if event == "call":
                content = frame.f_locals.get("content")
                size = len(content) if isinstance(content, (bytes, str)) else None
                serial_calls[id(frame)] = (time.perf_counter(), size)
                if name == "atomic_write" and size is not None and size > 16 * 1024**2:
                    block("serialized artifact exceeds16MiB")
            elif event == "return" and id(frame) in serial_calls:
                begin, size = serial_calls.pop(id(frame))
                elapsed = time.perf_counter() - begin
                output_size = len(arg) if isinstance(arg, (bytes, str)) else None
                output_digest = retain_bytes(arg, "json") if name == "json_bytes" else None
                item = receipt["serialization"].setdefault(name, {"calls": 0, "elapsed_s": 0.})
                item["calls"] += 1
                item["elapsed_s"] += elapsed
                events.write(json.dumps({"kind": "serialization", "name": name, "input_bytes": size,
                                         "output_bytes": output_size, "elapsed_s": elapsed,
                                         "output_blob_sha256": output_digest,
                                         "event": "return_or_exception"}) + "\n")
        if event in ("c_call", "c_return", "c_exception") and receipt["stage"] == "execution":
            owner = getattr(arg, "__self__", None)
            method = getattr(arg, "__name__", "")
            if isinstance(owner, np.ndarray) and method in ("copy", "__deepcopy__"):
                key = (id(frame), method)
                if event == "c_call":
                    copies[key] = (time.perf_counter(), owner.nbytes)
                elif key in copies:
                    begin, size = copies.pop(key)
                    item = receipt["serialization"].setdefault("host_copy", {"calls": 0, "input_bytes": 0,
                                                                           "elapsed_s": 0., "failed": 0})
                    elapsed = time.perf_counter() - begin
                    item["calls"] += 1
                    item["input_bytes"] += size
                    item["elapsed_s"] += elapsed
                    item["failed"] += event == "c_exception"
                    events.write(json.dumps({"kind": "serialization", "name": "host_copy", "input_bytes": size,
                                             "elapsed_s": elapsed, "event": event, "source": filename}) + "\n")
        if event == "call":
            if plan.get("guard_only") and filename == cases and frame.f_code.co_name == "stub_guard_trigger":
                receipt["guard_only_trigger_entries"] = receipt.get("guard_only_trigger_entries", 0) + 1
                block("guard-only ordinary stdlib callback sentinel")
            if filename == cases and frame.f_code.co_name.startswith("test_"):
                receipt.setdefault("test_methods_started", []).append(name)
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
    def profile_guard(frame, event, arg):
        try:
            profile(frame, event, arg)
        except BaseException as error:
            block("profile instrumentation failure: " + type(error).__name__ + ": " + str(error))

    sys.setprofile(profile_guard)
    try:
        assert Path(sys.prefix).resolve() == root / ".venv"
        assert not any(name.split(".")[0] in {"numpy", "pybert", "pyibisami", "scipy"} for name in sys.modules)
        if plan.get("guard_only"):
            seam = types.ModuleType("d2_under_test")
            seam.__dict__.update(modules={}, np=None, destination=destination)
            sys.modules[seam.__name__] = seam
            tests = types.ModuleType("d2_cases")
            exec(compile(Path(cases).read_text(encoding="utf-8"), cases, "exec"), tests.__dict__)
            suite = unittest.defaultTestLoader.loadTestsFromNames(plan["selection"], tests)
            unittest.TextTestRunner(stream=stderr, verbosity=2).run(suite)
            block("guard-only sentinel failed to stop the batch")
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
        original_sha256 = hashlib.sha256

        def traced_sha256(content=b"", *args, **kwargs):
            caller = sys._getframe(1).f_code.co_filename
            if caller not in paths:
                return original_sha256(content, *args, **kwargs)
            begin = time.perf_counter()
            result = original_sha256(content, *args, **kwargs)
            elapsed = time.perf_counter() - begin
            item = receipt["serialization"].setdefault("hashlib.sha256", {"calls": 0, "input_bytes": 0,
                                                                          "elapsed_s": 0.})
            item["calls"] += 1
            item["input_bytes"] += len(content)
            item["elapsed_s"] += elapsed
            events.write(json.dumps({"kind": "serialization", "name": "hashlib.sha256",
                                     "input_bytes": len(content), "digest_capacity_bytes": result.digest_size,
                                     "elapsed_s": elapsed, "source": caller}) + "\n")
            return result

        hashlib.sha256 = traced_sha256

        def serialization(name, function):
            def call(*args, **kwargs):
                before = time.perf_counter()
                count = receipt["serialization"].setdefault(name, {"calls": 0, "elapsed_s": 0.})
                count["calls"] += 1
                size = sum(value.nbytes for value in kwargs.values() if isinstance(value, np.ndarray))
                if size > 16 * 1024**2:
                    block("NPZ uncompressed input exceeds16MiB")
                stream = args[0] if args else None
                position = stream.tell() if hasattr(stream, "tell") else None
                returned = False
                try:
                    result = function(*args, **kwargs)
                    returned = True
                    return result
                finally:
                    elapsed = time.perf_counter() - before
                    count["elapsed_s"] += elapsed
                    output_size = (len(stream.getbuffer()) if hasattr(stream, "getbuffer") else
                                   Path(stream).stat().st_size if isinstance(stream, (str, Path))
                                   and Path(stream).is_file() else None)
                    if output_size is not None and output_size > 16 * 1024**2:
                        block("serialized artifact exceeds16MiB")
                    digest = None
                    if name.startswith("numpy.savez"):
                        raw_output = (stream.getvalue() if hasattr(stream, "getvalue") else
                                      Path(stream).read_bytes() if isinstance(stream, (str, Path))
                                      and Path(stream).is_file() else None)
                        digest = retain_bytes(raw_output, "npz")
                    events.write(json.dumps({"kind": "serialization", "name": name, "input_array_bytes": size,
                        "output_or_stream_bytes": output_size, "consumed_stream_bytes":
                        stream.tell() - position if position is not None else None,
                        "output_blob_sha256": digest, "elapsed_s": elapsed, "returned": returned}) + "\n")
            return call

        for name in ("savez_compressed", "savez", "load"):
            setattr(np, name, serialization("numpy." + name, getattr(np, name)))
        for name in ("read_magic", "read_array_header_1_0", "read_array_header_2_0", "read_array"):
            setattr(np.lib.format, name, serialization("numpy.format." + name, getattr(np.lib.format, name)))
        modules = {}
        base = dict(np=np, Path=Path, json=json, hashlib=hashlib, copy=copy, time=time, math=math,
                    os=os, tempfile=tempfile, io=io, zipfile=zipfile, warnings=warnings,
                    contextlib=contextlib, datetime=datetime, timezone=timezone, subprocess=subprocess,
                    SimpleNamespace=types.SimpleNamespace, monotonic_ns=time.monotonic_ns)
        base.update({name: getattr(np, name) for name in
                     ("array", "zeros", "where", "diff", "sign", "integer", "log10", "maximum", "pad")})
        for name, spec in plan["modules"].items():
            path = root / spec["path"]
            module = types.ModuleType(name)
            module.__dict__.update(base, __file__=str(path))
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    constant = node.targets[0].id
                    if constant in spec.get("constants", []):
                        allowed = (ast.Constant, ast.Tuple, ast.List, ast.Dict, ast.Name, ast.Load,
                                   ast.BinOp, ast.Add, ast.Mult, ast.Pow)
                        if not all(isinstance(item, allowed) for item in ast.walk(node.value)):
                            block("nonliteral source constant " + constant)
                        module.__dict__[constant] = eval(compile(ast.Expression(node.value), str(path), "eval"),
                                                         {"__builtins__": {}}, module.__dict__)
            definitions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                           and (spec.get("names") is None or node.name in spec["names"])]
            wrapped = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")],
                                                     level=0), *definitions], type_ignores=[])
            ast.fix_missing_locations(wrapped)
            exec(compile(wrapped, str(path), "exec"), module.__dict__)
            modules[name] = module
        for name, constants in plan.get("constant_sources", {}).items():
            for target, spec in constants.items():
                path = root / spec["path"]
                tree = ast.parse(path.read_text(encoding="utf-8"))
                node = next(item for item in tree.body if isinstance(item, ast.Assign)
                            and any(isinstance(left, ast.Name) and left.id == spec["name"] for left in item.targets))
                setattr(modules[name], target, ast.literal_eval(node.value))
        for name in ("pybert", "pybert.web", "pybert.utility", "pybert.models", "chaco", "chaco.api"):
            module = modules.get(name, types.ModuleType(name))
            module.__path__ = []
            sys.modules[name] = module
        for name, module in modules.items():
            sys.modules[name] = module
        sys.modules["chaco.api"].ArrayPlotData = None
        bert_stub = types.ModuleType("pybert.models.bert")
        bert_stub.update_trellis = forbidden
        sys.modules[bert_stub.__name__] = bert_stub
        if "pybert.utility.sigproc" in modules and hasattr(modules["pybert.utility.sigproc"], "resize_zero_pad"):
            sys.modules["pybert.utility"].resize_zero_pad = modules["pybert.utility.sigproc"].resize_zero_pad
        if "pybert.web.archive" in modules:
            modules["pybert.web.archive"].adapter_sha = modules["pybert.web.data"].adapter_sha
            for name in ("clock_features", "validate_clock_arrays"):
                if hasattr(modules["pybert.web.clocks"], name):
                    setattr(modules["pybert.web.archive"], name, getattr(modules["pybert.web.clocks"], name))
        for name in ("pybert.web.analysis", "baseline.analysis"):
            if name in modules:
                eye = "baseline.sigproc" if name.startswith("baseline") else "pybert.utility.sigproc"
                modules[name].calc_eye = modules[eye].calc_eye
                modules[name].safe_log10 = modules["pybert.utility.math"].safe_log10
                if hasattr(modules["pybert.web.clocks"], "period_projection"):
                    modules[name].period_projection = modules["pybert.web.clocks"].period_projection
        for name, links in plan.get("links", {}).items():
            for target, origin in links.items():
                source_module, member = origin.split(":", 1)
                setattr(modules[name], target, getattr(modules[source_module], member))
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
            for path in destination.iterdir()
            if path.is_file() and path.name not in hashes and path.name != "before.json"}
        receipt["array_output_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                                           for path in sorted(arrays_dir.iterdir())}
        receipt["artifact_sha256"] = {str(path.relative_to(destination)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in destination.rglob("*") if path.is_file() and path.parent != destination}
        receipt["inputs_unchanged_after"] = all(
            hashlib.sha256((root / relative).read_bytes()).hexdigest() == hashes[name]
            for name, relative in plan["snapshot_paths"].items())
        if not receipt["inputs_unchanged_after"]:
            receipt["exit_code"], code = 1, 1
        receipt["run_output_bytes"] = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
        (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"run": plan["run_id"], "exit_code": code, "counts": counts, "elapsed_s": receipt["elapsed_s"]}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
