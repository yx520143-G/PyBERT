"""Pure saved-data/AST diagnosis. No application imports, model objects or native helpers."""

import ast
import hashlib
import json
import re
import sys
import time
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from parsec import generate, many, regex, string

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OLD = Path("C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator")
PROBE = ROOT / "docs/webui/issue10/evidence/numerics-20261024-160343"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expression(node, namespace):
    return eval(compile(ast.fix_missing_locations(ast.Expression(node)), "saved-source-expression", "eval"), namespace)


def exception(call):
    try:
        call()
    except (AttributeError, ValueError) as error:
        return {"type": type(error).__name__, "message": str(error)}
    raise AssertionError("Expected the saved-source defect to reproduce")


if __name__ == "__main__":
    started = time.monotonic()
    core = ROOT / "src/pybert/models/bert.py"
    parser = OLD / "PyAMI/src/pyibisami/ami/parser.py"
    wrapper = OLD / "PyAMI/src/pyibisami/ami/model.py"
    files = [core, parser, wrapper]
    for side in ("direct", "worker"):
        files += list((PROBE / "A-NRZ-ADAPT-GetWave" / side).glob("ami-execution.*"))
    before = {str(p): digest(p) for p in files}

    # Execute only the parser combinator grammar, not the PyAMI module/configurator.
    grammar = parser.read_text(encoding="utf-8").splitlines()[84:143]
    parse_ns = dict(re=re, generate=generate, many=many, regex=regex, string=string)
    exec(compile("from __future__ import annotations\n" + "\n".join(grammar), "pinned-parser-grammar-only", "exec"), parse_ns)
    core_tree = ast.parse(core.read_text(encoding="utf-8"))
    visitor = next(n for n in ast.walk(core_tree) if isinstance(n, ast.FunctionDef) and n.name == "get_numeric_values")
    visit_ns = {"AmiName": str, "AmiNode": object, "AmiLeaf": type("AmiLeafStub", (), {})}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[visitor], type_ignores=[])), "pinned-visitor-only", "exec"), visit_ns)
    tap_filter = next(n for n in ast.walk(core_tree) if isinstance(n, ast.Lambda) and "tolower" in ast.unparse(n))
    pair_loop = next(n for n in ast.walk(core_tree) if isinstance(n, ast.For) and "pairwise" in ast.unparse(n.iter))
    predicate = next(n.value for n in ast.walk(core_tree) if isinstance(n, ast.AnnAssign)
                     and isinstance(n.target, ast.Name) and n.target.id == "ami_getwave_clocks")
    datasets = {}
    arrays = {}
    for side in ("direct", "worker"):
        path = PROBE / "A-NRZ-ADAPT-GetWave" / side
        record = json.loads((path / "ami-execution.json").read_text(encoding="utf-8"))
        with np.load(path / "ami-execution.npz", allow_pickle=False) as saved:
            arrays[side] = {key: saved[key].copy() for key in saved.files}
        clocks = arrays[side]["ami.call0.clocks"]
        complete = clocks[:312 * 48].reshape(312, 48)
        positional = clocks[np.arange(len(clocks)) % 48 < 40]  # diagnosis only, never a replacement clock vector
        parsed = [parse_ns["ami_parse"](s) for s in record["calls"][0]["params_out"]]
        assert all(isinstance(node, tuple) for result in parsed for node in result[1])
        original_predicate = expression(predicate, {"self": SimpleNamespace(rx_use_ami=True, rx_use_getwave=True,
                                                                          rx_use_clocks=True), "clock_times": clocks})
        _, (left, right) = next(expression(pair_loop.iter, {"pairwise": pairwise, "clock_times": clocks}))
        datasets[side] = {
            "raw_npz_sha256": digest(path / "ami-execution.npz"), "clock_count": len(clocks),
            "finite": bool(np.isfinite(clocks).all()), "zero_values": int((clocks == 0).sum()),
            "minus_one_values": int((clocks == -1).sum()), "zero_intervals": int((np.diff(clocks) == 0).sum()),
            "negative_intervals": int((np.diff(clocks) < 0).sum()),
            "complete_48_slot_blocks": 312, "first40_positive_and_increasing_each": bool(
                (complete[:, :40] > 0).all() and (np.diff(complete[:, :40], axis=1) > 0).all()),
            "last8_zero_each": bool((complete[:, 40:] == 0).all()),
            "trailing24_positive_increasing": bool((clocks[312 * 48:] > 0).all() and (np.diff(clocks[312 * 48:]) > 0).all()),
            "diagnostic_position_subset_count": len(positional), "diagnostic_position_subset_monotonic": bool((np.diff(positional) > 0).all()),
            "first_s": float(clocks[0]), "last_s": float(clocks[-1]),
            "subset_is_not_a_qualified_or_repaired_vector": True,
            "params_out_count": len(parsed), "first_root": parsed[0][0],
            "first_leaf_names": [n[0] for n in parsed[0][1]], "leaf_runtime_type": type(parsed[0][1][0]).__name__,
            "visitor_failure": exception(lambda: visit_ns["get_numeric_values"]("", parsed[0][1][0])),
            "tap_filter_failure": exception(lambda: expression(tap_filter, {})(parsed[0][1][0][0])),
            "AmiName_is_runtime_str": True, "str_has_contains": hasattr(str, "contains"),
            "weak_native_clock_predicate": bool(original_predicate),
            "pairwise_operand_shapes": [list(left.shape), list(right.shape)],
            "pairwise_scalar_sentinel_check_failure": exception(lambda: bool(left == -1)),
            "historical_DLL_calls_not_new": {name: sum(c["method"] == name for c in record["dll_calls"])
                                             for name in ("AMI_Init", "AMI_GetWave")},
        }
    assert arrays["direct"].keys() == arrays["worker"].keys()
    assert all(arrays["direct"][k].dtype == arrays["worker"][k].dtype and
               arrays["direct"][k].shape == arrays["worker"][k].shape and
               arrays["direct"][k].tobytes() == arrays["worker"][k].tobytes() for k in arrays["direct"])

    # Replay only the original list append and final slice expressions against plain Python buffers.
    wrapper_tree = ast.parse(wrapper.read_text(encoding="utf-8"))
    getwave = next(n for n in ast.walk(wrapper_tree) if isinstance(n, ast.FunctionDef) and n.name == "getWave")
    extend = next(n for n in ast.walk(getwave) if isinstance(n, ast.Call) and ast.unparse(n.func) == "clock_times.extend")
    slice_node = next(n for n in ast.walk(getwave) if isinstance(n, ast.Subscript) and ast.unparse(n.value) == "clock_times")
    ns = {"clock_times": [], "wave_out": [0] * 4, "self": SimpleNamespace(_samps_per_bit=1)}
    for buffer in ([0., 1., -1., 0., 0., 0., 0., 0., 0., 0.], [2., 3., -1., 0., 0., 0., 0., 0., 0., 0.]):
        ns["_clock_times"] = buffer
        expression(extend, ns)
    join_stub = {"kind": "Python-only contract example, not a model/DLL/fixture",
                 "IBIS_valid_prefixes": [[0., 1.], [2., 3.]],
                 "original_wrapper_result": expression(slice_node, ns),
                 "demonstrates": "whole buffer append plus UI truncation retains terminator/padding and loses later valid ticks"}
    assert join_stub["original_wrapper_result"] == [0., 1., -1., 0.]
    after = {str(p): digest(p) for p in files}
    assert before == after
    assert not any(name.startswith(("pybert", "pyibisami")) for name in sys.modules)
    snapshot = PROBE / "execution-source/src/pybert/models/bert.py"
    source_match = ast.dump(ast.parse(snapshot.read_text(encoding="utf-8"))) == ast.dump(core_tree)
    result = {"scope": "saved data, source AST and plain Python stubs only; no qualification", "datasets": datasets,
              "direct_worker_raw_exact_arrays": len(arrays["direct"]), "wrapper_expression_stub": join_stub,
              "current_core_AST_equals_saved_execution_source": source_match,
              "inputs_unchanged": True, "input_sha256": before,
              "new_calls": {key: 0 for key in ("Main", "COM", "coopt", "AMI_Init", "AMI_GetWave", "real_library_load",
                                               "engine_construction", "native_numerical_helper")},
              "pure_parser_calls": sum(d["params_out_count"] for d in datasets.values()),
              "elapsed_s": time.monotonic() - started, "numpy_version": np.__version__}
    (OUT / "diagnostics.json").write_bytes((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"datasets": datasets, "direct_worker_exact_arrays": len(arrays["direct"]),
                      "wrapper_stub": join_stub, "new_calls": result["new_calls"], "elapsed_s": result["elapsed_s"]}, indent=2))
