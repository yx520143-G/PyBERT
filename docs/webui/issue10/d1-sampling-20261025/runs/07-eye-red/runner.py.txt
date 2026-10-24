"""Execute only frozen D1 pure definitions and bounded NumPy work, with actual entry counts."""

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import types
import unittest


def main():
    evidence = Path(__file__).resolve().parent
    root = evidence.parents[3]
    run_id, *selection = sys.argv[1:]
    destination = evidence / "runs" / run_id
    previous = list((evidence / "runs").glob("*/events.jsonl")) if (evidence / "runs").exists() else []
    destination.mkdir(parents=True, exist_ok=False)
    plan = json.loads((evidence / "test-plan.json").read_text(encoding="utf-8"))
    environment = json.loads((evidence / "environment.json").read_text(encoding="utf-8"))
    source = root / "src/pybert/utility/ami_clock.py"
    eye_source = root / "src/pybert/utility/sigproc.py"
    baseline = evidence / "inputs/sigproc.baseline.py.txt"
    cases = evidence / "d1_cases.py"
    original_files = {name: root / path for name, path in plan["snapshot_paths"].items()}
    input_hashes = {}
    for name, path in original_files.items():
        raw = path.read_bytes()
        (destination / name).write_bytes(raw)
        input_hashes[name] = hashlib.sha256(raw).hexdigest()
    spent = {kind: 0 for kind in ("pure", "calc_eye", "histogram", "rfft")}
    for trace in previous:
        for line in trace.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event["kind"] in spent:
                spent[event["kind"]] += 1
    receipt = {"run_id": run_id, "selection": selection, "input_sha256": input_hashes,
               "git_HEAD": subprocess.check_output(["git", "--no-optional-locks", "rev-parse", "HEAD"],
                                                   cwd=root, text=True).strip(),
               "executable": sys.executable, "prefix": sys.prefix, "python": sys.version,
               "sys_path": sys.path, "spent_before": spent, "counts": {k: 0 for k in spent},
               "function_entries": {}, "test_stub_entries": {}, "blocked_attempts": [],
               "NumPy_imports": 0, "NumPy_ctypes_import_events": [], "stage": "stdlib",
               "scope": "actual AST-extracted D1 helpers and calc_eye only; bounded real NumPy",
               "task_wall_peak_RSS": "UNKNOWN", "system_library_trace": "not complete"}
    (destination / "before.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    trace = (destination / "events.jsonl").open("w", encoding="utf-8", newline="\n", buffering=1)
    output = (destination / "stdout.txt").open("w", encoding="utf-8", newline="\n", buffering=1)
    errors = (destination / "stderr.txt").open("w", encoding="utf-8", newline="\n", buffering=1)
    started = time.perf_counter()
    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = output, errors
    code = 1
    np = None

    def block(reason):
        receipt["blocked_attempts"].append(reason)
        trace.write(json.dumps({"kind": "blocked", "reason": reason}) + "\n")
        raise RuntimeError("D1 guard: " + reason)

    def entry(kind, name):
        receipt["counts"][kind] += 1
        receipt["function_entries"][name] = receipt["function_entries"].get(name, 0) + 1
        trace.write(json.dumps({"kind": kind, "name": name}) + "\n")
        if spent[kind] + receipt["counts"][kind] > plan["cumulative_limits"][kind]:
            block("cumulative budget " + kind)

    class ImportGuard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {
                "pybert", "pyibisami", "pychopmarg", "scipy", "parsec", "traits", "traitsui",
                "chaco", "PySide6", "pytest", "matplotlib",
            }:
                block("import " + fullname)
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
        filename = Path(frame.f_code.co_filename).as_posix()
        if event == "c_call" and receipt["stage"] == "execution":
            if str(getattr(arg, "__module__", "")).startswith("numpy.random"):
                block("RNG call")
        if event != "call":
            return
        if receipt["stage"] == "execution" and "/numpy/random/" in filename:
            block("RNG execution")
        if filename == source.as_posix():
            if frame.f_code.co_name != "<module>":
                entry("pure", frame.f_code.co_qualname)
                if frame.f_locals.get("nspui", 0) > 32:
                    block("planner nspui")
                for name in ("edges", "t_grid", "waveform", "period_ps", "native_x", "native_y"):
                    value = frame.f_locals.get(name)
                    if value is not None and hasattr(value, "__len__") and len(value) > 4096:
                        block("array length " + name)
        elif filename in {eye_source.as_posix(), baseline.as_posix()}:
            if frame.f_code.co_name not in {"<module>", "calc_eye"}:
                block("non-eye signal helper")
            if frame.f_code.co_name == "calc_eye":
                entry("calc_eye", "baseline.calc_eye" if filename == baseline.as_posix() else "candidate.calc_eye")
                if len(frame.f_locals["ys"]) > 4096 or frame.f_locals["height"] > 64:
                    block("Eye input/height")
                if frame.f_locals["samps_per_ui"] > 32:
                    block("Eye nspui")
        elif "/src/pybert/" in filename or "/src/pyibisami/" in filename:
            block("other production execution " + frame.f_code.co_qualname)
        if filename == cases.as_posix() and frame.f_code.co_name.startswith("stub_"):
            name = frame.f_code.co_name
            receipt["test_stub_entries"][name] = receipt["test_stub_entries"].get(name, 0) + 1

    guard = ImportGuard()
    sys.meta_path.insert(0, guard)
    sys.addaudithook(audit)
    sys.setprofile(profile)
    try:
        assert Path(sys.prefix).resolve() == root / ".venv"
        assert not [n for n in sys.modules if n.split(".")[0] in {"numpy", "pybert", "pyibisami", "scipy"}]
        for path, digest in environment["installed_files_sha256"].items():
            assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path
        receipt["stage"] = "NumPy_import"
        import numpy as np  # noqa: PLC0415 -- explicitly authorized and recorded after the import guard
        receipt["NumPy_imports"] = 1
        assert np.__version__ == environment["numpy_metadata_version"]
        receipt["NumPy_version"], receipt["NumPy_path"] = np.__version__, np.__file__
        real_histogram, real_rfft = np.histogram, np.fft.rfft

        def histogram(values, *args, **kwargs):
            if len(values) > 4096:
                block("histogram length")
            entry("histogram", "numpy.histogram")
            return real_histogram(values, *args, **kwargs)

        def rfft(values, *args, **kwargs):
            if len(values) > 4096:
                block("FFT length")
            entry("rfft", "numpy.fft.rfft")
            return real_rfft(values, *args, **kwargs)

        def forbidden(*args, **kwargs):
            block("unapproved NumPy DSP")

        np.histogram, np.fft.rfft = histogram, rfft
        np.convolve = np.correlate = np.fft.fft = np.fft.irfft = forbidden
        receipt["stage"] = "execution"

        def extract(path, names=None):
            syntax = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            definitions = [n for n in syntax.body if isinstance(n, ast.FunctionDef)
                           and (names is None or n.name in names)]
            wrapped = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")],
                                                     level=0), *definitions], type_ignores=[])
            ast.fix_missing_locations(wrapped)
            aliases = ("array", "zeros", "where", "diff", "sign", "integer")
            scope = {"np": np, **{name: getattr(np, name) for name in aliases}}
            exec(compile(wrapped, str(path), "exec"), scope)  # noqa: S102 -- actual frozen pure definitions
            return {node.name: scope[node.name] for node in definitions}

        seam = types.ModuleType("d1_under_test")
        seam.functions, seam.np = extract(source), np
        seam.baseline_eye = extract(baseline, {"calc_eye"})["calc_eye"]
        seam.candidate_eye = extract(eye_source, {"calc_eye"})["calc_eye"]
        seam.root, seam.evidence = root, evidence
        sys.modules[seam.__name__] = seam
        tests = types.ModuleType("d1_cases")
        exec(compile(cases.read_text(encoding="utf-8"), str(cases), "exec"), tests.__dict__)
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromNames(selection, tests) if selection else loader.loadTestsFromModule(tests)
        result = unittest.TextTestRunner(stream=errors, verbosity=2).run(suite)
        receipt.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors))
        code = 0 if result.wasSuccessful() and not receipt["blocked_attempts"] else 1
    except BaseException:
        traceback.print_exc(file=errors)
    finally:
        sys.setprofile(None)
        sys.meta_path.remove(guard)
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        receipt.update(exit_code=code, elapsed_s=time.perf_counter() - started)
        receipt["loaded_NumPy_extensions"] = {
            name: str(getattr(module, "__file__", "")) for name, module in list(sys.modules.items())
            if name.startswith("numpy") and str(getattr(module, "__file__", "")).endswith(".pyd")}
        receipt["restricted_actual_entries"] = {name: 0 for name in (
            "PyBERT_Main_full_entries", "DFE_construct_run_dfe_decode", "run_ami_model_PyAMI_model_module",
            "grammar_SciPy_other_DSP", "model_C_DLL_COM_coopt", "Web_GUI_CLI_services_browser_model_download",
        )}
        output.close()
        errors.close()
        trace.close()
        receipt["output_sha256"] = {name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
                                    for name in ("stdout.txt", "stderr.txt", "events.jsonl")}
        receipt["inputs_unchanged_after"] = all(
            hashlib.sha256(path.read_bytes()).hexdigest() == input_hashes[name]
            for name, path in original_files.items())
        if not receipt["inputs_unchanged_after"]:
            receipt["exit_code"], code = 1, 1
        (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                                  encoding="utf-8", newline="\n")
    print(json.dumps({"run": run_id, "exit_code": code, "counts": receipt["counts"],
                      "elapsed_s": receipt["elapsed_s"]}))
    return code


if __name__ == "__main__":
    sys.exit(main())
