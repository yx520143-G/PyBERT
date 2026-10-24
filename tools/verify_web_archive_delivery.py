"""Audit completed browser runs and downloads without starting any engine work."""

import json
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import numpy as np

from pybert.web.archive import array_identity, json_bytes, sha256


def main():
    root = Path(__file__).resolve().parents[1]
    evidence = root / "docs/webui/issue5/evidence"
    output = evidence / time.strftime("chrome-raw-audit-%Y%m%d-%H%M%S")
    output.mkdir(exist_ok=False)
    service = evidence / "chrome-v2/local/service"
    old = Path("C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/evidence")
    baselines = {"NRZ": next((old / "numeric-20261024-073225/F4-SINGLE-NRZ/worker").iterdir()),
                 "PAM4": next((old / "numeric-20261024-075832/F4-SINGLE-PAM4/worker").iterdir())}
    report = {"simulation_calls": 0, "COM_calls": 0, "tasks": {}, "runs": {}, "checks": [],
              "actual_source_sha256": {str(path.relative_to(root)): sha256(path.read_bytes()) for path in [Path(__file__),*root.glob("src/pybert/web/*.py"),*root.glob("src/pybert/web/static/*")] if path.is_file()}}

    def get(path):
        with urlopen("http://127.0.0.1:8770/api/" + path) as response:
            return json.load(response)

    def check(label, value):
        report["checks"].append({"check": label, "passed": bool(value)})

    state = get("state")
    report["state"] = state
    for path in service.glob("*/request.json"):
        try:
            task = get("tasks/" + path.parent.name)
        except HTTPError as err:
            report["tasks"][path.parent.name] = {"availability": f"HTTP {err.code}", "request_sha256": sha256(path.read_bytes())}
            continue
        report["tasks"][path.parent.name] = task
        (output / f"task-{path.parent.name}.json").write_bytes(json_bytes(task))
    for row in state["runs"]:
        run_id = row["run_id"]
        directory = service / run_id
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        name = "PAM4" if manifest["effective_input"]["mod_type"] == "PAM-4" else "NRZ"
        expected = json.loads((root / f"docs/webui/issue5/fixtures/chrome-execution-v1/{name}.json").read_text(encoding="utf-8"))
        source = baselines[name]
        before = {file: sha256((source / file).read_bytes()) for file in ("manifest.json", "arrays.npz")}
        with np.load(directory / "arrays.npz", allow_pickle=False) as actual, np.load(source / "arrays.npz", allow_pickle=False) as reference:
            identities = {key: {**array_identity(actual[key]), "exact_original": key in reference and array_identity(actual[key]) == array_identity(reference[key])} for key in actual.files}
            check(f"{name} all original raw/display/axes/masks dtype/shape/bytes exact", set(actual.files) == set(reference.files) and all(item["exact_original"] for item in identities.values()))
        baseline = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        check(f"{name} complete requested/effective fixture exact", manifest["requested_input"] == expected["config"] == manifest["effective_input"])
        check(f"{name} runtime/bindings exact", manifest["runtime_extensions"] == expected["runtime_extensions"] and manifest["resource_bindings"] == expected["resource_bindings"])
        check(f"{name} inherited window exact", manifest["window"] == baseline["window"])
        check(f"{name} all nonperformance summary exact", {k:v for k,v in manifest["summary"].items() if not k.startswith("performance")} == {k:v for k,v in baseline["summary"].items() if not k.startswith("performance")})
        check(f"{name} AGC output separated", manifest["requested_input"]["decision_scaler"] == .5 and manifest["summary"]["final_level_v"] != .5)
        with zipfile.ZipFile(root / f"output/playwright/{name}-real.pybert_run") as archive:
            stored = json.loads(archive.read("manifest.json"))
            check(f"{name} actual Chrome download NPZ bytes exact", sha256(archive.read("arrays.npz")) == sha256((directory / "arrays.npz").read_bytes()))
            check(f"{name} actual Chrome download complete manifest exact", stored["run"] == manifest and stored["source_manifest_utf8"].encode("utf-8") == (directory / "manifest.json").read_bytes())
        check(f"{name} original baseline files unchanged", before == {file:sha256((source / file).read_bytes()) for file in before})
        report["runs"][name] = {"run_id": run_id, "directory": str(directory), "baseline": str(source), "original_files_sha256": before,
                                 "actual_source_sha256": manifest.get("actual_source_sha256"), "arrays": identities, "summary": manifest["summary"]}
        (output / f"{name}-manifest.json").write_bytes((directory / "manifest.json").read_bytes())
    with zipfile.ZipFile(root / "output/playwright/PAM4-while-NRZ-draft.pybert_run") as archive, zipfile.ZipFile(root / "output/playwright/PAM4-real.pybert_run") as first:
        check("saving old PAM4 while editing NRZ preserves original manifest/NPZ exactly", archive.read("arrays.npz") == first.read("arrays.npz") and json.loads(archive.read("manifest.json"))["run"] == json.loads(first.read("manifest.json"))["run"])
    numerical = [row for row in report["tasks"].values() if row.get("operation") == "run"]
    report["costs"] = [{"task_id": row["task_id"], "state": row["state"], "request_hash": row["request_hash"], "elapsed_s": row["finished_at"]-row["created_at"], "worker_exited": row["worker_exited"]} for row in numerical]
    check("two real successes and one actual cancelled main; one CTLE preflight failure", sorted(row["state"] for row in numerical) == ["cancelled", "failed", "succeeded", "succeeded"])
    check("no COM tasks started", not state["com_tasks"])
    report["passed"] = all(row["passed"] for row in report["checks"])
    (output / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({"report": str(output / "report.json"), "passed": report["passed"], "checks": len(report["checks"]), "costs": report["costs"]}))


if __name__ == "__main__":
    main()
