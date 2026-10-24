"""Final saved-byte/source applicability audit. No simulation or decoder calls."""

import ast
import json
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

import numpy as np

from pybert.web.archive import json_bytes, sha256, validate_run, read_arrays
from pybert.web.data import source_identity

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/webui/issue9/evidence"
BASE = "3807bd2f54647a491f350cbda7ab61c0752b06f0"


def git_file(ref, path):
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT).decode("utf-8")


def native_equivalent():
    original = ast.parse(git_file(BASE, "src/pybert/models/bert.py"))
    current = ast.parse((ROOT / "src/pybert/models/bert.py").read_text(encoding="utf-8"))
    old_run = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == "my_run_simulation")
    run = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == "my_run_simulation")
    run.args.args.pop()
    run.args.defaults.pop()
    run.body[0] = old_run.body[0]
    trellis = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == "update_trellis")
    results = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == "update_results")
    results.body[-1:] = trellis.body[1:]
    current.body.remove(trellis)

    class RemoveCapture(ast.NodeTransformer):
        def visit_If(self, node):
            if any(isinstance(n, ast.Name) and n.id in ("decoding", "sample_indices") for n in ast.walk(node.test)):
                return None
            return self.generic_visit(node)

        def visit_Assign(self, node):
            if any(isinstance(n, ast.Name) and n.id == "sample_indices" for target in node.targets for n in ast.walk(target)):
                return None
            return self.generic_visit(node)

        def visit_FunctionDef(self, node):
            if node.name == "calc_ber":
                node.args.args.pop()
            return self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "calc_ber":
                node.args.pop()
            return self.generic_visit(node)

    return ast.dump(RemoveCapture().visit(current)) == ast.dump(original)


def function_ast(source, name):
    return ast.dump(next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name))


def main():
    output = EVIDENCE / time.strftime("delivery-audit-%Y%m%d-%H%M%S")
    output.mkdir()
    report = {"product_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_identity": source_identity(), "main_calls": 0, "COM_calls": 0, "checks": [], "cases": [], "chrome": []}

    def check(name, passed, detail=None):
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})

    check("full native AST equivalent after removing only capture and rejoining original trellis", native_equivalent())
    check("original decoder file unchanged", git_file(BASE, "src/pybert/models/viterbi.py").splitlines() == (ROOT / "src/pybert/models/viterbi.py").read_text(encoding="utf-8").splitlines())
    for path, function in (("src/pybert/web/data.py", "collect"), ("src/pybert/web/worker.py", "run_worker"), ("src/pybert/web/viterbi.py", "extend")):
        check(f"numeric d1a5979 {function} unchanged in final product", function_ast(git_file("d1a5979", path), function) == function_ast((ROOT / path).read_text(encoding="utf-8"), function))
    total = 0
    for source in sorted(EVIDENCE.glob("numerics-*/local/*/reference.npz")):
        directory = source.parent
        adapter = directory / "adapter"
        run = json.loads((adapter / "manifest.json").read_text(encoding="utf-8"))
        arrays = read_arrays((adapter / "arrays.npz").read_bytes())
        validate_run(run, arrays)
        with np.load(source, allow_pickle=False) as reference:
            check(directory.name + " inventory", set(reference.files) == set(arrays))
            for key in reference.files:
                a, b = reference[key], arrays[key]
                check(directory.name + " / " + key, a.dtype == b.dtype and a.shape == b.shape and a.tobytes(order="C") == b.tobytes(order="C"))
                total += 1
        with zipfile.ZipFile(directory / "saved.pybert_run") as archive:
            check(directory.name + " archive NPZ exact", archive.read("arrays.npz") == (adapter / "arrays.npz").read_bytes())
        report["cases"].append({"case": directory.name, "run_id": run["run_id"], "summary": run["summary"], "actual_source_sha256": run["actual_source_sha256"]})
    report["exact_array_count"] = total
    for version in (1, 2):
        folder = EVIDENCE / f"chrome-v{version}"
        for path in sorted(folder.glob("local/service/*/manifest.json")):
            if not (path.parent / "request.json").exists():
                continue
            run = json.loads(path.read_text(encoding="utf-8"))
            arrays = read_arrays((path.parent / "arrays.npz").read_bytes())
            validate_run(run, arrays)
            report["chrome"].append({"version": version, "run_id": run["run_id"], "summary": run["summary"],
                                      "lifecycle": run["lifecycle"], "source": run["actual_source_sha256"]})
            check("Chrome source pre-execution table exact", run["actual_source_sha256"] == json.loads((folder / "before-execution.json").read_text(encoding="utf-8"))["source_identity"])
        for image in sorted((ROOT / "output/playwright/issue9").glob("*.jpg")):
            if (int(image.name[:2]) >= 11) == (version == 2):
                shutil.copyfile(image, folder / image.name)
    for name, run_id in (("PAM4-ISI", "5db36403-7f3f-4ac8-a9c7-d3c36c99ad53"), ("PAM4-ERROR", "a371f8c8-a6bc-4497-950e-26153fc1958b"), ("PAM4-DISABLED", "59df53f4-d978-42a2-9abc-df073389a70d")):
        source = EVIDENCE / "chrome-v1/local/service" / run_id
        with zipfile.ZipFile(ROOT / "output/playwright/issue9" / (name + ".pybert_run")) as archive:
            for field in ("manifest.json", "arrays.npz"):
                raw = archive.read("arrays.npz") if field == "arrays.npz" else json.loads(archive.read("manifest.json"))["source_manifest_utf8"].encode()
                check(f"Chrome download {name} / {field} exact", raw == (source / field).read_bytes())
    with zipfile.ZipFile(ROOT / "output/playwright/issue9/PAM4-ERROR.pybert_run") as old, zipfile.ZipFile(ROOT / "output/playwright/issue9/PAM4-ERROR-v2.pybert_run") as new:
        check("final UI resave original raw bytes exact", old.read("arrays.npz") == new.read("arrays.npz"))
        check("final UI resave original source manifest exact", json.loads(old.read("manifest.json"))["source_manifest_utf8"] == json.loads(new.read("manifest.json"))["source_manifest_utf8"])
    for relative in report["source_identity"]:
        target = output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / relative, target)
    shutil.copyfile(__file__, output / "verifier.py")
    report["failed"] = sum(not row["passed"] for row in report["checks"])
    report["check_count"] = len(report["checks"])
    (output / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({"output": str(output), "checks": report["check_count"], "failed": report["failed"], "exact_arrays": total}))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
