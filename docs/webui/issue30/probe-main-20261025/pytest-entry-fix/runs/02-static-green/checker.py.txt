"""Check collection paths as data only; never import pytest, conftest or product code."""

import ast
import fnmatch
import hashlib
import json
from pathlib import Path
import sys
import time
import tomllib


def main():
    repair = Path(__file__).resolve().parent
    evidence = repair.parent
    root = evidence.parents[3]
    run_id = sys.argv[1]
    destination = repair / "runs" / run_id
    destination.mkdir(parents=True, exist_ok=False)
    old = root / "tests/test_ami_probe_main.py"
    relocated = evidence / "guarded_probe_main_cases.py"
    paths = {
        "checker.py.txt": Path(__file__), "plan.json": repair / "static-plan.json",
        "startup.json": repair / "startup.json", "runner.py.txt": evidence / "run_guarded.py",
        "source.py.txt": root / "src/pybert/utility/ibisami.py",
        "bert.py.txt": root / "src/pybert/models/bert.py", "pyproject.toml.txt": root / "pyproject.toml",
        "Makefile.txt": root / "Makefile", "conftest.py.txt": root / "tests/conftest.py",
        "venv.cfg.txt": root / ".venv/pyvenv.cfg",
    }
    for name, path in (("old-test.py.txt", old), ("relocated-cases.py.txt", relocated)):
        if path.exists():
            paths[name] = path
    inputs = {}
    for name, path in paths.items():
        raw = path.read_bytes()
        (destination / name).write_bytes(raw)
        inputs[name] = hashlib.sha256(raw).hexdigest()
    census = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((root / "tests").rglob("*.py"))}
    census_raw = (json.dumps(census, indent=2) + "\n").encode("utf-8")
    (destination / "tests-census.json").write_bytes(census_raw)
    inputs["tests-census.json"] = hashlib.sha256(census_raw).hexdigest()
    before = {"run": run_id, "input_sha256": inputs, "executable": sys.executable,
              "prefix": sys.prefix, "python": sys.version, "sys_path": sys.path,
              "scope": "static AST/path checks only; no pytest collection, imports or test execution",
              "task_wall_peak_RSS": "UNKNOWN"}
    (destination / "before.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8", newline="\n")
    started = time.perf_counter()
    startup = json.loads((repair / "startup.json").read_text(encoding="utf-8"))
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["pytest"]["ini_options"]
    patterns = config.get("python_files", ["test_*.py", "*_test.py"])
    collected = [p for p in census if any(fnmatch.fnmatch(Path(p).name, pattern) for pattern in patterns)]
    offenders = []
    for name in collected:
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "c1_under_test":
                offenders.append({"path": name, "line": node.lineno})
    runner = ast.parse((evidence / "run_guarded.py").read_text(encoding="utf-8"))
    original_runner = ast.parse((repair / "inputs/run_guarded.py.txt").read_text(encoding="utf-8"))
    target = next(node for node in ast.walk(runner) if isinstance(node, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "test" for t in node.targets))
    expected = ast.parse('test = evidence / "guarded_probe_main_cases.py"').body[0].value
    runner_points_to_relocated = ast.dump(target.value) == ast.dump(expected)
    original_target = next(node for node in ast.walk(original_runner) if isinstance(node, ast.Assign)
                           and any(isinstance(t, ast.Name) and t.id == "test" for t in node.targets))
    target.value = original_target.value
    original_tests = dict(startup["tests_python_sha256"])
    original_tests.pop("tests/test_ami_probe_main.py")
    checks = {
        "no_injected_module_import_in_default_tests": not offenders,
        "runner_only_file_removed_from_tests": not old.exists(),
        "relocated_cases_byte_exact": relocated.exists() and hashlib.sha256(relocated.read_bytes()).hexdigest()
                                     == startup["original_case_sha256"],
        "relocated_name_outside_default_patterns": not any(fnmatch.fnmatch(relocated.name, p) for p in patterns),
        "runner_points_to_relocated_cases": runner_points_to_relocated,
        "runner_AST_only_path_changed_guards_identical": ast.dump(runner) == ast.dump(original_runner),
        "other_tests_and_conftest_unchanged": census == original_tests,
        "pytest_config_Makefile_and_product_bytes_unchanged": all(
            hashlib.sha256((root / p).read_bytes()).hexdigest() == digest
            for p, digest in startup["unchanged_raw_sha256"].items()),
        "new_bare_environment": Path(sys.prefix).resolve() == root / ".venv",
    }
    code = 0 if all(checks.values()) else 1
    stdout = json.dumps({"checks": checks, "injected_imports_in_collected_paths": offenders}, indent=2) + "\n"
    (destination / "stdout.txt").write_text(stdout, encoding="utf-8", newline="\n")
    (destination / "stderr.txt").write_bytes(b"")
    for name, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == inputs[name]
    receipt = {**before, "checks": checks, "exit_code": code, "elapsed_s": time.perf_counter() - started,
               "output_sha256": {n: hashlib.sha256((destination / n).read_bytes()).hexdigest()
                                 for n in ("stdout.txt", "stderr.txt")},
               "pure_coordinator_and_stubs": 0, "pytest_collection_calls": 0,
               "restricted_actual_calls": startup["restricted_budget"],
               "proof_limit": "path/config/source proof only; full pytest/conftest runtime health is not established"}
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"run": run_id, "exit_code": code, "checks": checks, "elapsed_s": receipt["elapsed_s"]}))
    return code


if __name__ == "__main__":
    sys.exit(main())
