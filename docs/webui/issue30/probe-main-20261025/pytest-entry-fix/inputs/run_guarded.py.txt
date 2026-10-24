"""Run only the actual production pure coordinator, extracted by AST, under guards."""

import ast
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import traceback
import types
import unittest


def main():
    root = Path(__file__).resolve().parents[4]
    evidence = Path(__file__).parent
    run_id, *selection = sys.argv[1:]
    destination = evidence / "runs" / run_id
    destination.mkdir(parents=True, exist_ok=False)
    source = root / "src/pybert/utility/ibisami.py"
    test = root / "tests/test_ami_probe_main.py"
    inputs = {}
    original_files = {
        "source.py.txt": source, "bert.py.txt": root / "src/pybert/models/bert.py",
        "test.py.txt": test, "runner.py.txt": Path(__file__), "plan.json": evidence / "test-plan.json",
        "venv.cfg.txt": root / ".venv/pyvenv.cfg",
    }
    for name, path in original_files.items():
        raw = path.read_bytes()
        (destination / name).write_bytes(raw)
        inputs[name] = hashlib.sha256(raw).hexdigest()
    receipt = {
        "run_id": run_id, "selection": selection, "input_sha256": inputs,
        "executable": sys.executable, "python": sys.version, "prefix": sys.prefix,
        "sys_path": sys.path, "blocked_attempts": [], "pure_production_calls": {}, "stub_calls": {},
        "test_python_calls": {},
        "scope": "AST-extracted actual production coordinator; plain Python stubs; no full helper",
        "preload": "stdlib only; platform/system library internals not fully traced",
        "preloaded_forbidden_modules": [name for name in sys.modules
                                        if name.split(".")[0] in {"pybert", "pyibisami", "numpy", "ctypes"}],
        "task_wall_peak_RSS": "UNKNOWN",
    }
    (destination / "before.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    started = time.perf_counter()
    output, errors = io.StringIO(), io.StringIO()
    code = 1

    def blocked(reason):
        receipt["blocked_attempts"].append(reason)
        raise RuntimeError("C1 pure-seam guard: " + reason)

    class Guard:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split(".")[0] in {
                "pybert", "pyibisami", "pychopmarg", "numpy", "scipy", "ctypes", "parsec",
                "traits", "traitsui", "PySide6", "chaco", "matplotlib",
            }:
                blocked("import " + fullname)
            return None

    def audit(event, args):
        if event in ("ctypes.dlopen", "ctypes.dlsym"):
            blocked(event)

    def profile(frame, event, arg):
        if event != "call":
            return
        filename = Path(frame.f_code.co_filename).as_posix()
        if filename == test.as_posix():
            name = frame.f_code.co_qualname
            receipt["test_python_calls"][name] = receipt["test_python_calls"].get(name, 0) + 1
        if filename == test.as_posix() and frame.f_code.co_name == "count":
            name = frame.f_locals["name"]
            receipt["stub_calls"][name] = receipt["stub_calls"].get(name, 0) + 1
        if filename == source.as_posix():
            name = frame.f_code.co_qualname
            if name not in {"<module>", "_AMIProbeMainError", "_AMIProbeMainError.__init__", "_run_probe_main"}:
                blocked("production execution " + name)
            if name not in {"<module>", "_AMIProbeMainError"}:
                counts = receipt["pure_production_calls"]
                counts[name] = counts.get(name, 0) + 1
        elif "/src/pybert/" in filename or "/src/pyibisami/" in filename:
            blocked("other production execution " + frame.f_code.co_qualname)

    guard = Guard()
    sys.meta_path.insert(0, guard)
    sys.addaudithook(audit)
    sys.setprofile(profile)
    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = output, errors
    test_module = None
    try:
        assert not receipt["preloaded_forbidden_modules"]
        assert Path(sys.prefix).resolve() == root / ".venv"
        syntax = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        definitions = [node for node in syntax.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                       and node.name in {"_AMIProbeMainError", "_run_probe_main"}]
        extracted = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")],
                                                  level=0), *definitions], type_ignores=[])
        ast.fix_missing_locations(extracted)
        scope = {"deepcopy": deepcopy, "IMP_RESP_GETW": "impulse", "OUT_RESP_GETW": "output"}
        exec(compile(extracted, str(source), "exec"), scope)  # noqa: S102 -- authorized exact AST seam
        seam = types.ModuleType("c1_under_test")
        seam.coordinator = scope.get("_run_probe_main")
        seam.error_type = scope.get("_AMIProbeMainError")
        seam.source_path = str(source)
        seam.caller_path = str(root / "src/pybert/models/bert.py")
        seam.baseline_path = str(evidence / "inputs")
        sys.modules[seam.__name__] = seam
        test_module = types.ModuleType("c1_tests")
        exec(compile(test.read_text(encoding="utf-8"), str(test), "exec"), test_module.__dict__)
        loader = unittest.TestLoader()
        suite = (loader.loadTestsFromNames(selection, test_module) if selection
                 else loader.loadTestsFromModule(test_module))
        result = unittest.TextTestRunner(stream=errors, verbosity=2).run(suite)
        receipt.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors))
        code = 0 if result.wasSuccessful() and not receipt["blocked_attempts"] else 1
        receipt["final_test_stub_counts"] = test_module.COUNTS
        receipt["final_test_events"] = test_module.EVENTS
        receipt["case_events"] = test_module.CASES
    except BaseException:
        errors.write(traceback.format_exc())
    finally:
        sys.setprofile(None)
        sys.meta_path.remove(guard)
        sys.stdout, sys.stderr = original_stdout, original_stderr
        receipt.update(exit_code=code, elapsed_s=time.perf_counter() - started)
        receipt["restricted_actual_calls"] = {name: 0 for name in (
            "run_ami_model_full", "PyAMI_production_methods", "AMIModel_Initializer_instances",
            "model_module_body_response_keys", "NumPy_SciPy_DSP", "grammar_engine_Main_COM_coopt",
            "C_model_DLL", "model_download_compile", "CLI_GUI_service_browser",
        )}
        for name, text in (("stdout.txt", output.getvalue()), ("stderr.txt", errors.getvalue())):
            (destination / name).write_bytes(text.encode("utf-8"))
        receipt["output_sha256"] = {
            name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
            for name in ("stdout.txt", "stderr.txt")
        }
        for name, digest in inputs.items():
            assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest
            assert hashlib.sha256(original_files[name].read_bytes()).hexdigest() == digest
        (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"run": run_id, "exit_code": code, "pure_calls": receipt["pure_production_calls"],
                      "elapsed_s": receipt["elapsed_s"]}))
    return code


if __name__ == "__main__":
    sys.exit(main())
