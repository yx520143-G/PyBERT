"""Retain a bounded pure-test batch with the exact source and zero-call ledger."""

import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from time import perf_counter
import unittest

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
batch = HERE / sys.argv[1]
batch.mkdir()  # Existing receipts must never be overwritten.
test_file = ROOT / "tests/test_ami_getwave_params.py"
core_file = ROOT / "src/pybert/models/bert.py"
for name, path in (("bert.py", core_file), ("test_ami_getwave_params.py", test_file),
                   ("run_batch.py", Path(__file__))):
    (batch / name).write_bytes(path.read_bytes())
started = perf_counter()
spec = importlib.util.spec_from_file_location("pure_ami_tests", test_file)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[2:], module) if sys.argv[2:] else (
    unittest.defaultTestLoader.loadTestsFromTestCase(module.GetWaveParameterTests)
)
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
elapsed = perf_counter() - started
assert not any(name.startswith(("pybert", "pyibisami")) for name in sys.modules)
receipt = {
    "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
    "successful": result.wasSuccessful(), "elapsed_s": elapsed, "pure_parser_calls": module.PARSER_CALLS,
    "source_sha256": {name: hashlib.sha256((batch / name).read_bytes()).hexdigest()
                      for name in ("bert.py", "test_ami_getwave_params.py", "run_batch.py")},
    "new_calls": {name: 0 for name in ("Main", "COM", "coopt_candidates", "AMI_Init", "AMI_GetWave", "AMI_Close",
                                      "real_model_library_load", "engine_construction", "native_numerical_helper")},
    "peak_RSS": "UNKNOWN", "kind": "pure parser/production function tests; no clocks qualification",
}
# Isolate the original production tap lambda as a second defect diagnosis.
old_filters = [node for node in ast.walk(ast.parse(core_file.read_text(encoding="utf-8")))
               if isinstance(node, ast.Lambda) and "tolower" in ast.unparse(node)]
if old_filters:
    raw = ROOT / "docs/webui/issue10/evidence/numerics-20261024-160343/A-NRZ-ADAPT-GetWave/direct/ami-execution.json"
    first = json.loads(raw.read_text(encoding="utf-8"))["calls"][0]["params_out"][0]
    name = module.parse(first)[1][0][0]
    original_filter = eval(compile(ast.Expression(old_filters[0]), "original-tap-filter", "eval"))
    try:
        receipt["original_tap_filter_diagnosis"] = {"input": name, "returned": original_filter(name)}
    except AttributeError as error:
        receipt["original_tap_filter_diagnosis"] = {"input": name, "error": str(error)}
receipt["pure_parser_calls"] = module.PARSER_CALLS
(batch / "tests.log").write_bytes(stream.getvalue().encode("utf-8"))
(batch / "receipt.json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode("utf-8"))
print(stream.getvalue())
print(json.dumps(receipt, indent=2))
raise SystemExit(0 if result.wasSuccessful() else 1)
