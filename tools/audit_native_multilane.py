"""Record #13 source boundaries and the applicability of preserved red/green evidence."""

import ast
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/native13/evidence"
BASE = "9a33d08458aa00782e90169c699857b8b19455a2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nodes(source):
    return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}


def main():
    path = OUT / "source-applicability.json"
    if path.exists():
        raise FileExistsError(path)
    filename = "src/pybert/utility/sparam.py"
    baseline = subprocess.check_output(["git", "show", f"{BASE}:{filename}"], cwd=ROOT).decode("utf-8")
    current = (ROOT / filename).read_text(encoding="utf-8")
    old, new = nodes(baseline), nodes(current)
    unchanged = {name: ast.dump(old[name]) == ast.dump(new[name]) for name in old if name not in ("import_freq", "import_fext")}
    vita_old = next(node for node in old["import_freq"].body if isinstance(node, ast.If) and "vita_end" in ast.unparse(node.test))
    vita_new = next(node for node in new["import_freq"].body if isinstance(node, ast.If) and "vita_end" in ast.unparse(node.test))
    unchanged["import_freq VITA branch"] = ast.dump(vita_old) == ast.dump(vita_new)
    for ports in (4, 2):
        before = next(node for node in old["import_freq"].body if isinstance(node, ast.If) and ast.unparse(node.test) == f"rs == {ports}")
        after = next(node for node in new["import_freq"].body if isinstance(node, ast.If) and ast.unparse(node.test) == f"rs == {ports}")
        unchanged[f"import_freq {ports}-port branch"] = ast.dump(before) == ast.dump(after)
    before = json.loads((OUT / "real-M-before.json").read_text(encoding="utf-8"))
    after = json.loads((OUT / "real-M-after.json").read_text(encoding="utf-8"))
    red_source = OUT / "red-physical-test-source.py.txt"
    diagnostic_source = OUT / "diagnostic-source-v1.py.txt"
    test = ROOT / "tests/test_multilane_physical.py"
    diagnostic = ROOT / "tools/diagnose_native_multilane.py"
    applicability = {
        "red_source_snapshot_matches_execution_hash": sha(red_source) == before["source_hashes"]["tests/test_multilane_physical.py"],
        "diagnostic_source_snapshot_matches_before_and_after": sha(diagnostic_source) == before["source_hashes"]["tools/diagnose_native_multilane.py"] == after["source_hashes"]["tools/diagnose_native_multilane.py"],
        "physical_test_AST_unchanged_after_formatting": ast.dump(ast.parse(red_source.read_text(encoding="utf-8"))) == ast.dump(ast.parse(test.read_text(encoding="utf-8"))),
        "diagnostic_AST_unchanged_after_formatting": ast.dump(ast.parse(diagnostic_source.read_text(encoding="utf-8"))) == ast.dump(ast.parse(diagnostic.read_text(encoding="utf-8"))),
        "production_matches_after_diagnostic_source_hash": sha(ROOT / filename) == after["source_hashes"][filename],
        "same_real_M_resource_bytes": before["resource"]["sha256"] == after["resource"]["sha256"] == sha(Path(after["resource"]["local"])),
    }
    tests = {}
    for name in ("red-baseline", "green-physical", "green-regression"):
        xml = OUT / f"{name}.xml"
        suite = ET.parse(xml).getroot().find("testsuite")
        tests[name] = {"sha256": sha(xml), **{key: suite.attrib[key] for key in ("tests", "failures", "errors", "skipped", "time")}}
    files = [ROOT / filename, ROOT / "tests/test_multilane_sparam.py", test,
             ROOT / "tests/test_singlelane_physical.py", diagnostic, Path(__file__)]
    result = {"base": BASE, "head_at_audit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "scope": "8/12-port caller port selection, related docs and physical regression only",
              "unchanged_AST": unchanged, "applicability": applicability, "tests": tests,
              "sources": {str(p.relative_to(ROOT)): sha(p) for p in files},
              "evidence": {p.name: sha(p) for p in (OUT / "real-M-before.json", OUT / "real-M-after.json", red_source, diagnostic_source)},
              "static_checks": {"ruff_select": "E4,E7,E9,F", "ruff_exit_code": 0,
                  "ruff_targets": [filename, "tests/test_multilane_physical.py", "tests/test_singlelane_physical.py", "tools/diagnose_native_multilane.py"],
                  "compileall_same_targets_exit_code": 0},
              "cost": "helper-only diagnostics and 49 relevant tests; no time-domain simulation or COM", "passed": all(unchanged.values()) and all(applicability.values())}
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"report_sha256": sha(path), "passed": result["passed"], "tests": tests}))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
