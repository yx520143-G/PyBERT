"""Check source boundaries, sealed bytes and test receipts without importing PyBERT."""

import ast
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
output = HERE / sys.argv[1]
assert not output.exists()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parameter_block(tree, old):
    for owner in ast.walk(tree):
        body = getattr(owner, "body", None)
        if not isinstance(body, list):
            continue
        for index, statement in enumerate(body):
            if old and isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                if statement.target.id == "rx_getwave_params":
                    end = next(i for i in range(index, len(body)) if isinstance(body[i], ast.If))
                    return body, index, end
            if not old and isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Call):
                if isinstance(statement.value.func, ast.Name) and statement.value.func.id == "getwave_parameters":
                    return body, index, index + 1
    raise AssertionError("Returned-parameter boundary not found")


baseline = ast.parse((HERE / "source/baseline-bert.py").read_text(encoding="utf-8"))
red = ast.parse((HERE / "red-02-source-lines/bert.py").read_text(encoding="utf-8"))
current = ast.parse((ROOT / "src/pybert/models/bert.py").read_text(encoding="utf-8"))
body, begin, end = parameter_block(baseline, True)
red_helper = next(n for n in red.body if isinstance(n, ast.FunctionDef) and n.name == "getwave_parameters")
assert ast.dump(ast.Module(body=body[begin:end], type_ignores=[])) == ast.dump(
    ast.Module(body=red_helper.body[1:-1], type_ignores=[])
)
body[begin:end] = [ast.Pass()]
body, begin, end = parameter_block(current, False)
body[begin:end] = [ast.Pass()]
current.body = [n for n in current.body if not (isinstance(n, ast.FunctionDef) and n.name == "getwave_parameters")]


class RootKeyCompatibility(ast.NodeTransformer):
    """Normalize only the four root-key lookups required by tuple paths."""

    changes = 0

    def root_key(self, node):
        return (isinstance(node, ast.Tuple) and len(node.elts) == 1 and
                isinstance(node.elts[0], ast.Constant) and node.elts[0].value in ("cdr_locked", "cdr_ui"))

    def visit_Compare(self, node):
        if self.root_key(node.left) and len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            if isinstance(node.comparators[0], ast.Name) and node.comparators[0].id == "param_vals":
                node.left = node.left.elts[0]
                self.changes += 1
        return self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == "param_vals" and self.root_key(node.slice):
            node.slice = ast.Call(func=ast.Name(id="AmiName", ctx=ast.Load()), args=[node.slice.elts[0]], keywords=[])
            self.changes += 1
        return self.generic_visit(node)


normalizer = RootKeyCompatibility()
normalizer.visit(current)
assert normalizer.changes == 4
for node in baseline.body:
    if isinstance(node, ast.ImportFrom) and node.module == "pyibisami.ami.parser":
        node.names = [name for name in node.names if name.name not in ("AmiLeaf", "AmiNode")]
assert ast.dump(baseline) == ast.dump(current), "Unexpected source/algorithm change outside the agreed boundary"

sealed = ROOT / "docs/webui/issue10/clocks-gate-audit-20261024"
sealed_files = [p for p in sealed.iterdir() if p.is_file()]
assert len(sealed_files) == 4
for path in sealed_files:
    original = subprocess.check_output(["git", "show", "98f30f8:" + path.relative_to(ROOT).as_posix()], cwd=ROOT)
    assert original == path.read_bytes()
old_inputs = json.loads((sealed / "diagnostics.json").read_text(encoding="utf-8"))["input_sha256"]
assert all(digest(Path(path)) == expected for path, expected in old_inputs.items())
batches = []
for path in sorted(HERE.glob("*/receipt.json")):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert all(digest(path.parent / name) == expected for name, expected in receipt["source_sha256"].items())
    assert all(count == 0 for count in receipt["new_calls"].values())
    batches.append({"batch": path.parent.name, **{k: receipt[k] for k in (
        "tests_run", "failures", "errors", "elapsed_s", "pure_parser_calls", "successful")}})
result = {
    "original_extraction_AST_exact": True, "remaining_full_module_AST_exact_after_allowed_normalization": True,
    "normalized_root_lookups": normalizer.changes, "sealed_4_files_original_bytes": True,
    "sealed_7_inputs_unchanged": True, "all_batch_source_hashes_exact": True, "batches": batches,
    "pure_parser_calls_all_batches": sum(b["pure_parser_calls"] for b in batches),
    "measured_batch_elapsed_s_sum": sum(b["elapsed_s"] for b in batches),
    "total_task_wall_and_RSS": "UNKNOWN", "python": sys.version, "parsec_version": version("parsec"),
}
output.write_bytes((json.dumps(result, indent=2) + "\n").encode("utf-8"))
print(json.dumps(result, indent=2))
