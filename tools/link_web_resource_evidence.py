"""Append corrected-native provenance to preserved reports, without recalculation."""

import json
from pathlib import Path

from freeze_web_resource_execution import ROOT, OUT, FIX, sha


def main():
    output = OUT / "numeric-corrected-baseline-links-v2.json"
    if output.exists():
        raise FileExistsError(output)
    corrected = OUT / "corrected-native-execution-v2.json"
    baseline = json.loads(corrected.read_text(encoding="utf-8"))
    source = OUT / "verification-source-numeric-v2.py.txt"
    reports = [
        OUT / "numeric-20261024-075721/report.json",
        OUT / "numeric-20261024-075832/report.json",
    ]
    rows = []
    for path in reports:
        report = json.loads(path.read_text(encoding="utf-8"))
        hashes = {
            key.replace("\\", "/"): value
            for key, value in report["actual_sources"].items()
        }
        assert (
            hashes["src/pybert/utility/sparam.py"] == baseline["actual_importer_sha256"]
        )
        assert hashes["tools/verify_web_resources.py"] == sha(source)
        for case in report["cases"]:
            manifest = json.loads(
                (Path(case["worker_directory"]) / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            assert manifest["native_importer_sha"] == baseline["issue13"]["merge"]
            assert (
                case["passed"]
                and case["task"]["worker_exited"]
                and case["task"]["exitcode"] == 0
            )
            rows.append(
                {
                    "case": case["case"],
                    "report": str(path.relative_to(ROOT)),
                    "report_sha256": sha(path),
                    "corrected_native_execution_sha256": sha(corrected),
                    "native_importer_sha": manifest["native_importer_sha"],
                    "run_id": case["task"]["task_id"],
                    "input_hash": case["requested_input_hash"],
                    "raw_comparisons": len(case["raw_comparison"]),
                    "complex_component_checks": len(case["complex_components"]),
                    "independent_raw_checks": len(
                        case["independent_saved_data"]["analysis_raw"]
                    ),
                    "independent_display_checks": len(
                        case["independent_saved_data"]["analysis_display"]
                    )
                    + len(case["independent_saved_data"]["additional_display"]),
                    "direct_elapsed_s": case["direct_elapsed_s"],
                    "worker_elapsed_s": case["task"]["finished_at"]
                    - case["task"]["created_at"],
                    "resources": manifest["resources"],
                    "passed": True,
                }
            )
    result = {
        "main_simulation_performed": False,
        "purpose": "append explicit corrected-native association; original report bytes retained",
        "corrected_native_execution_sha256": sha(corrected),
        "original_execution_v1_sha256": baseline["execution_v1_sha256"],
        "original_fixture_sha256": sha(FIX / "frozen-manifest.json"),
        "executed_driver_source_snapshot_sha256": sha(source),
        "cases": rows,
        "already_established_single_NRZ": {
            "original_report": "numeric-20261024-073225/report.json",
            "original_failure_retained": True,
            "saved_independent_report": "saved-resource-check-20261024-073439/report.json",
            "no_additional_main_run": True,
            "applicability": "4-port path unchanged by #13; later metadata changes can be rebuilt from saved raw",
        },
        "default_COM": "BLOCKED_BUDGET / NOT_EXECUTED",
    }
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "sha256": sha(output),
                "cases": len(rows),
                "all_passed": True,
                "main_simulation_performed": False,
            }
        )
    )


if __name__ == "__main__":
    main()
