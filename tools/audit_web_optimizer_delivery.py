"""Read-only audit of retained numerical/Chrome originals. No engine computation."""

import ast
import json
import subprocess
import time
import zipfile
from pathlib import Path

import numpy as np

from pybert.web.archive import json_bytes, read_arrays, read_json, sha256
from pybert.web.optimization import save_optimization, load_optimization

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/webui/issue8/evidence"


def main():
    output = EVIDENCE / time.strftime("delivery-audit-%Y%m%d-%H%M%S")
    output.mkdir()
    (output / "local").mkdir()
    checks, details = {}, {}
    def check(name, value):
        checks[name] = bool(value)

    initial = EVIDENCE / "numerics-20261024-122031"
    latest = EVIDENCE / "numerics-20261024-130501"
    report1, report2 = [read_json((path / "report.json").read_bytes()) for path in (initial, latest)]
    numeric_costs = []
    exact_count = 0
    for directory, report in ((initial, report1), (latest, report2)):
        for name, row in report["cases"].items():
            check(f"{directory.name}/{name}/reported", all(row["checks"].values()))
            direct = directory / "local" / name / "arrays.npz"
            adapter = directory / "local/adapter" / row["adapter_task"]["task_id"] / "arrays.npz"
            with np.load(direct, allow_pickle=False) as a, np.load(adapter, allow_pickle=False) as b:
                check(f"{directory.name}/{name}/inventory", set(a.files) == set(b.files))
                for key in a.files:
                    check(f"{directory.name}/{name}/{key}", a[key].dtype == b[key].dtype and a[key].shape == b[key].shape and a[key].tobytes() == b[key].tobytes())
                    exact_count += 1
            numeric_costs.append({"batch": directory.name, "case": name, "direct_calls": 1, "adapter_calls": 1,
                "direct_elapsed_s": row["direct"]["elapsed_s"], "adapter_elapsed_s": row["adapter_record"]["elapsed_s"],
                "adapter_with_spawn_s": row["adapter_task"]["finished_at"]-row["adapter_task"]["created_at"],
                "peak_rss_bytes": row["peak_rss_bytes"]})
    for name in report2["cases"]:
        old, new = report1["cases"][name], report2["cases"][name]
        with np.load(initial / "local/adapter" / old["adapter_task"]["task_id"] / "arrays.npz", allow_pickle=False) as a, np.load(latest / "local/adapter" / new["adapter_task"]["task_id"] / "arrays.npz", allow_pickle=False) as b:
            check(f"MMSE v1-v2 shared/{name}", all(a[k].dtype == b[k].dtype and a[k].tobytes() == b[k].tobytes() for k in a.files))
    main_records = []
    for name in ("PAM4-RLM095", "PAM4-RLM080", "PAM4-used"):
        path = ROOT / f"output/playwright/issue8/{name}.pybert_run"
        with zipfile.ZipFile(path) as archive:
            envelope = read_json(archive.read("manifest.json"))
            raw = archive.read("arrays.npz")
        run = envelope["run"]
        arrays = read_arrays(raw)
        main_records.append((name, run, raw, arrays))
        details[name] = {"run_id": run["run_id"], "array_count": len(arrays), "summary": run["summary"],
                         "lifecycle": run["lifecycle"], "archive_sha256": sha256(path.read_bytes()), "raw_sha256": sha256(raw)}
    a, b = main_records[:2]
    check("RLM ordinary Run full native inputs equal", a[1]["requested_input"] == b[1]["requested_input"])
    check("RLM ordinary Run actually different runtime", a[1]["runtime_extensions"]["values"]["rlm"] == .95 and b[1]["runtime_extensions"]["values"]["rlm"] == .8)
    check("RLM ordinary Run array inventories", set(a[3]) == set(b[3]))
    for key in a[3]:
        check("RLM ordinary Run exact/"+key, a[3][key].dtype == b[3][key].dtype and a[3][key].shape == b[3][key].shape and a[3][key].tobytes() == b[3][key].tobytes())
    check("Use application provenance", main_records[2][1]["runtime_extensions"]["values"]["eq_application"]["opt_id"] == "db86e583-2b31-4671-9765-f9e49667bb6f")
    opt_costs = []
    archives = []
    for batch in ("chrome-v1", "chrome-v2"):
        for directory in sorted((EVIDENCE / batch / "local/service").iterdir()):
            path = directory / "optimization.json"
            if not path.exists():
                continue
            record = read_json(path.read_bytes())
            terminal = read_json((directory / "terminal.json").read_bytes())
            check(f"{batch}/{directory.name}/terminal", terminal["status"] == record["status"])
            saved = output / "local" / f"{directory.name}.pybert_opt"
            save_optimization(directory, saved)
            opened = output / "local" / directory.name
            opened.mkdir()
            restored = load_optimization(saved.read_bytes(), opened)
            check(f"{batch}/{directory.name}/archive record", restored == record)
            check(f"{batch}/{directory.name}/archive raw bytes", (opened / "arrays.npz").read_bytes() == (directory / "arrays.npz").read_bytes())
            task = record.get("task", {})
            opt_costs.append({"opt_id": record["opt_id"], "batch": batch, "status": record["status"],
                              "candidates_scored": len(record.get("candidates", [])), "coopt_called": "plan" in record,
                              "elapsed_s": record.get("elapsed_s"), "spawn_to_exit_s": task.get("finished_at", 0)-task.get("created_at", 0),
                              "peak_rss_bytes": None, "peak_rss_status": "not sampled in Chrome; do not infer from fixture worker peaks"})
            archives.append({"opt_id": record["opt_id"], "path": str(saved.relative_to(ROOT)), "sha256": sha256(saved.read_bytes())})
    # Default-call semantics: strip only optional observational statements/docstrings.
    source = ROOT / "src/pybert/threads/optimization.py"
    baseline = subprocess.check_output(["git", "show", "5fcf8285b042fe1fe92c068b1c3311fa87a50de0:src/pybert/threads/optimization.py"], cwd=ROOT)
    class Strip(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            self.generic_visit(node)
            node.body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str))]
            if node.name == "coopt" and node.args.args[-1].arg == "observations":
                node.args.args.pop()
                node.args.defaults = []
            return node
        def visit_If(self, node):
            if isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) and node.test.left.id == "observations":
                return None
            return self.generic_visit(node)
    check("final native default module AST exact", ast.dump(Strip().visit(ast.parse(source.read_bytes()))) == ast.dump(Strip().visit(ast.parse(baseline))))
    (output / "native-optimization.py").write_bytes(source.read_bytes())
    result = {"checks": checks, "passed": sum(checks.values()), "failed": [key for key, value in checks.items() if not value],
              "exact_direct_adapter_arrays": exact_count, "main_runs": details, "numerical_costs": numeric_costs,
              "Chrome_optimization_costs": opt_costs, "preserved_archives": archives,
              "total_real_coopt_calls": len(numeric_costs)*2 + sum(row["coopt_called"] for row in opt_costs),
              "main_calls": 3, "COM_numeric_calls": 0, "audit_new_coopt_calls": 0,
              "native_source_sha256": sha256(source.read_bytes()), "audit_source_sha256": sha256(Path(__file__).read_bytes())}
    (output / "report.json").write_bytes(json_bytes(result))
    print(json.dumps({"output": str(output), "checks": len(checks), "failed": result["failed"], "total_coopt_calls": result["total_real_coopt_calls"]}))
    assert not result["failed"]


if __name__ == "__main__":
    main()
