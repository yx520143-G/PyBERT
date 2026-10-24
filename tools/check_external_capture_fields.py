"""No-engine AST check of fields requested by #16's direct capture."""

import ast
import json

from external_lane_reference import ISSUE, REFS, sha
from verify_external_lanes import write


def value(node, symbols):
    if isinstance(node, ast.Name):
        return symbols[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return value(node.left, symbols) + value(node.right, symbols)
    return ast.literal_eval(node)


def main():
    reports = []
    for label in REFS:
        root = ISSUE / "local/sources" / label / "src/pybert"
        symbols = {}
        for node in ast.parse((root / "web/data.py").read_text(encoding="utf-8")).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("RAW_FIELDS", "RESPONSES", "WAVEFORMS"):
                symbols[node.targets[0].id] = value(node.value, symbols)
        fields = symbols["RAW_FIELDS"] + tuple(f"{p}_{s}" for p in symbols["RESPONSES"] for s in ("h", "s", "p", "H"))
        declared, assigned = set(), set()
        for filename in ("pybert.py", "models/bert.py"):
            tree = ast.parse((root / filename).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "PyBERT":
                    for member in node.body:
                        if isinstance(member, ast.Assign):
                            declared.update(t.id for t in member.targets if isinstance(t, ast.Name))
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self" and isinstance(node.ctx, ast.Store):
                    assigned.add(node.attr)
        missing = sorted(set(fields) - declared - assigned)
        reports.append({"version": label, "field_count": len(fields), "fields": list(fields),
                        "missing": missing, "passed": not missing,
                        "source_sha256": {f: sha(root / f) for f in ("pybert.py", "models/bert.py", "web/data.py")}})
    write(ISSUE / "evidence/no-engine-capture-fields.json", {"method": "AST only: PyBERT class declarations and self assignments; post/final successful captures separately prove runtime existence", "Main": 0, "constructors": 0, "reports": reports})
    print(json.dumps([{k: r[k] for k in ("version", "field_count", "missing", "passed")} for r in reports]))
    assert all(r["passed"] for r in reports)


if __name__ == "__main__":
    main()
