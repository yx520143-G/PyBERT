"""Audit actual Chrome artifacts without launching a numerical engine or browser."""

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue4/evidence/chrome-20261024"
UI = ROOT / "output/playwright"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def cli_result(name):
    raw = (UI / name).read_text(encoding="utf-8")
    value = json.loads(raw.split("### Result", 1)[1].split("### Ran", 1)[0].strip())
    return (
        json.loads(value) if isinstance(value, str) and value.startswith("{") else value
    )


def main():
    target = OUT / "browser-audit-v1.json"
    if target.exists():
        raise FileExistsError(target)
    checks = []

    def check(name, good):
        checks.append({"check": name, "passed": bool(good)})

    cases = {
        "chrome-AB": "57183d8c-6a6d-4567-b0d6-628f55c48c61",
        "chrome-BA": "16b97811-8219-41bb-9a96-1e8571e98cf5",
        "chrome-single-after-COM": "c3cadfdc-13e8-4ed9-bee3-b3b11462cd96",
    }
    plan = read(ROOT / "docs/webui/issue4/fixtures/chrome-and-light-preflight-v3.json")
    numeric = read(
        ROOT / "docs/webui/issue4/evidence/numeric-20261024-075832/report.json"
    )
    nrz = read(ROOT / "docs/webui/issue4/evidence/numeric-20261024-073225/report.json")
    previous = {
        r["case"]: Path(r["worker_directory"]) for r in numeric["cases"] + nrz["cases"]
    }
    names = {
        "chrome-AB": "F4-CASCADE-AB",
        "chrome-BA": "F4-CASCADE-BA",
        "chrome-single-after-COM": "F4-SINGLE-NRZ",
    }
    raw = []
    for name, run_id in cases.items():
        manifest = read(OUT / run_id / "manifest.json")
        expected = read(ROOT / plan["cases"][name]["file"])
        check(
            name + " frozen input hashes",
            all(
                manifest[key] == plan["cases"][name][key]
                for key in ("input_hash", "input_identity_hash")
            ),
        )
        check(
            name + " whole 95-field request/runtime/bindings",
            all(
                manifest[key] == expected[key]
                for key in ("runtime_extensions", "resource_bindings")
            )
            and manifest["requested_input"] == expected["config"]
            and len(manifest["requested_input"]) == 95,
        )
        check(
            name + " real completed worker",
            manifest["cancellation"]["worker_exited"]
            and not manifest["cancellation"]["cancel_requested"],
        )
        with (
            np.load(OUT / run_id / "arrays.npz") as actual,
            np.load(previous[names[name]] / "arrays.npz") as reference,
        ):
            fields = sorted(set(actual.files) | set(reference.files))
            rows = [
                {
                    "field": key,
                    "passed": key in actual.files
                    and key in reference.files
                    and np.array_equal(actual[key], reference[key], equal_nan=True),
                }
                for key in fields
            ]
            raw.append(
                {
                    "case": name,
                    "reference_directory": str(previous[names[name]]),
                    "fields": rows,
                }
            )
            check(
                name
                + " all saved raw arrays exactly match independently verified prior worker",
                all(r["passed"] for r in rows),
            )
    loaded, rejected = (
        cli_result("38-reloaded-localstorage.txt"),
        cli_result("39-rejected-localstorage.txt"),
    )
    expected = read(ROOT / plan["cases"]["chrome-single-after-COM"]["file"])
    check(
        "downloaded YAML actual reload preserves entire config/runtime/ordered bindings",
        all(
            loaded[key] == expected[key]
            for key in ("config", "runtime_extensions", "resource_bindings")
        ),
    )
    check(
        "unsafe object rejection preserves whole prior draft/name", loaded == rejected
    )
    check(
        "Save As Escape retains original name",
        cli_result("35-save-as-escape-name.txt") == "F-NRZ-01.yaml",
    )
    check(
        "Save and Save As downloaded identical bytes",
        (
            UI.parent.parent / ".playwright-cli/issue4-resource-roundtrip.yaml"
        ).read_bytes()
        == (OUT / "download-resource-roundtrip.yaml").read_bytes(),
    )
    unbound, bound = (
        cli_result("40-unbound-localstorage.txt"),
        cli_result("42-explicit-base-localstorage.txt"),
    )
    check(
        "unbound references do not resolve from cwd/name/inventory",
        unbound["config"] == expected["config"] and not unbound["resource_bindings"],
    )
    check(
        "explicit base binds active references only",
        bound["config"] == expected["config"]
        and bound["resource_bindings"]
        == {
            key: expected["resource_bindings"][key]
            for key in ("ch_file", "com_cfg_file")
        },
    )
    legacy = cli_result("43-legacy-localstorage.txt")
    check(
        "safe legacy alias/delta/100-tap/inactive missing models",
        legacy["config"]
        == read(
            ROOT / "docs/webui/issue4/local/chrome-inputs/legacy-inactive-expected.json"
        )["config"],
    )
    duplicate = cli_result("54-duplicate-BBA-localstorage.txt")
    check(
        "browser duplicate retains B/B/A and repeated content IDs",
        duplicate["config"]["ch_files"]
        == [expected["config"]["ch_files"][0], *expected["config"]["ch_files"]]
        and duplicate["resource_bindings"]["ch_files"]
        == [
            expected["resource_bindings"]["ch_files"][0],
            *expected["resource_bindings"]["ch_files"],
        ],
    )
    transitions = read(OUT / "run-child-transitions.json")
    check(
        "core joined before distinct COM child creation and immutable manifest",
        transitions["immutable_core"]
        and transitions["child"]["created_at"]
        >= transitions["parent"]["worker_exit_confirmed_at"]
        and (OUT / "core-before-child-finished.json").read_bytes()
        == (OUT / "core-after-child-finished.json").read_bytes(),
    )
    pending = cli_result("26-COM-helper-cancel-pending.txt")
    final = read(OUT / "final-idle.json")
    cancelled = final["tasks"][pending["before"]["task_id"]]
    check(
        "actual helper cancel request -> observe -> exit; no published value",
        pending["before"]["phase"].startswith("native COM helper")
        and pending["pending"]["cancel_requested"]
        and not pending["pending"]["cancel_observed"]
        and not pending["pending"]["worker_exited"]
        and cancelled["state"] == "cancelled"
        and cancelled["cancel_requested_at"]
        <= cancelled["cancel_observed_at"]
        <= cancelled["worker_exit_confirmed_at"]
        and not (OUT / cancelled["task_id"] / "com.json").exists(),
    )
    core_pending = cli_result("51-core-DFE-cancel-pending.txt")
    core = final["tasks"][core_pending["before"]["task_id"]]
    check(
        "actual DFE cancel exits and creates no COM child",
        core_pending["before"]["phase"] == "Running DFE/CDR..."
        and core["state"] == "cancelled"
        and core["worker_exited"]
        and core["cancel_observed"]
        and {t["task_id"] for t in final["state"]["com_tasks"]}
        == set(core_pending["previous_com_ids"]),
    )
    file_task = final["tasks"]["0521cea2-bd79-48c3-9202-41ae1a33d0fd"]
    check(
        "enabled native CTLE File rejected before main and worker exits",
        file_task["state"] == "failed"
        and file_task["worker_exited"]
        and "native File path" in file_task["error"],
    )
    for task in final["state"]["com_tasks"]:
        if task["state"] == "succeeded":
            result = read(OUT / task["task_id"] / "com.json")
            check(
                "real spreadsheet scalar " + task["task_id"],
                result["value_db"] == -15.419984103278814 and task["exitcode"] == 0,
            )
    check("final backend numerical slot idle", final["state"]["active_task_id"] is None)
    check(
        "COM details preserve open state across real poll after UI fix",
        cli_result("64-COM-details-persist-final.txt")["after_poll"] == "",
    )
    environment = cli_result("66-browser-environment.txt")
    check(
        "installed Chrome viewport 1280x720 scale1",
        "Chrome/155." in environment["ua"]
        and (environment["width"], environment["height"], environment["dpr"])
        == (1280, 720, 1),
    )
    ui_copy = OUT / "ui"
    ui_copy.mkdir(exist_ok=False)
    for path in UI.iterdir():
        if path.is_file():
            shutil.copyfile(path, ui_copy / path.name)
    shutil.copyfile(
        ROOT / ".playwright-cli/console-2026-10-24T00-45-52-658Z.log",
        ui_copy / "initial-console.log",
    )
    report = {
        "checks": checks,
        "raw_comparisons": raw,
        "browser": environment,
        "plan": plan["cases"],
        "screenshots_pixel_inspected": [
            "10-AB-frequency.png",
            "11-AB-impulse.png",
            "12-AB-wave.png",
            "13-AB-eye.png",
            "14-AB-jitter.png",
            "21-independent-COM-success.png",
            "23-invalid-COM-failed.png",
            "26-COM-helper-cancel-pending.png",
            "33-core-child-success.png",
            "47-native-File-blocked.png",
            "51-core-DFE-cancel-pending.png",
            "64-COM-failure-details-final.png",
            "66-two-real-runs-compare.png",
        ],
        "retained_attempts": [
            "first COM cancel reached prevalidation only",
            "first DFE-cancel observer mistook Run normalization completion and missed its intended interval; that real Run and its real COM succeeded and are retained",
            "first UI-fix recheck was started while dialog hidden; competing subsequent toggle check failed and was retained; final isolated recheck passed",
        ],
        "extra_lifecycle_success_run": "c630ff19-02aa-4e21-89b3-a1842a74e78a; same frozen single input, no new numerical qualification",
        "ab_ba_comparison": "actual separate runs matched their independently verified reference arrays; the final UI two-run overlay uses the retained single and lifecycle-attempt single because the normal two-core cache had evicted AB/BA",
        "default_COM": "BLOCKED_BUDGET / NOT_EXECUTED",
        "UI_only_fix": {
            "path": "src/pybert/web/static/resources.js",
            "sha256": hashlib.sha256(
                (ROOT / "src/pybert/web/static/resources.js").read_bytes()
            ).hexdigest(),
            "reason": "retain expanded COM history details across status polling; no numerical producer change",
        },
        "passed": all(r["passed"] for r in checks),
    }
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "file": str(target),
                "passed": report["passed"],
                "checks": len(checks),
                "failed": [r["check"] for r in checks if not r["passed"]],
            }
        )
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
