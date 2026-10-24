"""Read-only reuse of accepted real data; writes new #5 evidence, never simulates."""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

import pybert
from pybert.web import archive
from pybert.web.data import plot_payload
from pybert.web.legacy_results import load_legacy, legacy_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktrees", type=Path, default=Path("C:/Users/yx/.codex/worktrees"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "docs/webui/issue5/evidence" / time.strftime("saved-roundtrip-%Y%m%d-%H%M%S")
    output.mkdir(parents=True)
    local = output / "local"
    local.mkdir()
    sources = {
        "issue2-NRZ": args.worktrees / "pybert-issue2-native/serial-bus-simulator/docs/webui/issue2/evidence/numeric-20261024-050800/F-NRZ-01",
        "issue3-NRZ": args.worktrees / "pybert-issue3-analysis/serial-bus-simulator/docs/webui/issue3/evidence/numeric-20261024-065914/F-NRZ-01",
        "issue3-PAM4": args.worktrees / "pybert-issue3-analysis/serial-bus-simulator/docs/webui/issue3/evidence/numeric-20261024-065914/F-PAM4-01",
        "issue4-core-COM": args.worktrees / "pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/evidence/chrome-20261024/c3cadfdc-13e8-4ed9-bee3-b3b11462cd96",
        "issue4-PAM4": next((args.worktrees / "pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/evidence/numeric-20261024-075832/F4-SINGLE-PAM4/worker").iterdir()),
    }
    report = {"simulation_calls": 0, "COM_calls": 0, "python": sys.executable, "pybert_module": pybert.__file__,
              "actual_sources": {str(path.relative_to(root)): archive.sha256(path.read_bytes()) for path in [Path(__file__),*root.glob("src/pybert/web/*.py")]},
              "archive_module": archive.__file__, "sources": {}, "errors": []}
    start = time.perf_counter()
    for name, source in sources.items():
        row = {"source": str(source)}
        report["sources"][name] = row
        try:
            before = {file: archive.sha256((source / file).read_bytes()) for file in ("manifest.json", "arrays.npz")}
            row["source_files_sha256"] = before
            subfunctions = {}
            if name == "issue4-core-COM":
                child = source.parent / "a803f4ca-83f2-4031-a31c-af5213fc71d8"
                task_path = source.parent / "final-idle.json"
                task = json.loads(task_path.read_text(encoding="utf-8"))["tasks"][child.name]
                subfunctions = {"captured_at": time.time(), "linked_tasks": {child.name: {
                    "task_availability": "available", "task": task, "task_source_sha256": archive.sha256(task_path.read_bytes()),
                    "terminal.json": {"availability": "not_produced"},
                    "files": {file: {"availability": "available", "record": json.loads((child / file).read_text(encoding="utf-8")),
                                      "source_sha256": archive.sha256((child / file).read_bytes())}
                              for file in ("com-input.json", "com.json")}}}}
            destination = local / f"{name}.pybert_run"
            stored = archive.save_archive(source, destination, subfunctions)
            reopened = local / name
            reopened.mkdir()
            run, size = archive.load_archive(destination.read_bytes(), reopened)
            with np.load(source / "arrays.npz", allow_pickle=False) as original, np.load(reopened / "arrays.npz", allow_pickle=False) as restored:
                row["arrays"] = {key: {**archive.array_identity(original[key]), "exact": archive.array_identity(original[key]) == archive.array_identity(restored[key])}
                                 for key in original.files}
            row["raw_display_exact"] = all(item["exact"] for item in row["arrays"].values())
            row["plots_exact"] = {key: plot_payload(source, key) == plot_payload(reopened, key) for key in run["plots"]}
            row["metadata_exact"] = (source / "manifest.json").read_bytes() == (reopened / "manifest.json").read_bytes()
            row["NPZ_bytes_exact"] = before["arrays.npz"] == archive.sha256((reopened / "arrays.npz").read_bytes())
            row["source_unchanged"] = before == {file: archive.sha256((source / file).read_bytes()) for file in before}
            row["array_bytes"] = size
            row["archive_path"] = str(destination)
            row["archive_sha256"] = archive.sha256(destination.read_bytes())
            row["subtasks_exact"] = stored["subfunctions"] == json.loads((reopened / "archive.json").read_text(encoding="utf-8"))["subfunctions"]
        except Exception as err:
            row["error"] = f"{type(err).__name__}: {err}"
            report["errors"].append({name: row["error"]})
        (output / "report.json").write_bytes(archive.json_bytes(report))
    native = args.worktrees / "pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/evidence/light-compat-20261024-091034/native-cli.pybert_data"
    legacy_dir = local / "legacy-native"
    legacy_dir.mkdir()
    try:
        run, size = load_legacy(native.read_bytes(), legacy_dir, trusted=True)
        report["legacy"] = {"source": str(native), "sha256": archive.sha256(native.read_bytes()), "contract": legacy_report(legacy_dir),
                            "plots": len(run["plots"]), "array_bytes": size}
    except Exception as err:
        report["errors"].append({"legacy": str(err)})
    report["elapsed_s"] = time.perf_counter() - start
    report["passed"] = not report["errors"] and all(row["raw_display_exact"] and row["metadata_exact"] and row["NPZ_bytes_exact"] and row["source_unchanged"] and all(row["plots_exact"].values()) and row["subtasks_exact"] for row in report["sources"].values())
    (output / "report.json").write_bytes(archive.json_bytes(report))
    print(json.dumps({"report": str(output / "report.json"), "passed": report["passed"], "errors": report["errors"], "elapsed_s": report["elapsed_s"]}))


if __name__ == "__main__":
    main()
