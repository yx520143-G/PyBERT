"""Launch one frozen guarded batch with a hard 60 second timeout; retain failed/partial evidence."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    evidence = Path(__file__).resolve().parent
    root = evidence.parents[3]
    plan = json.loads((evidence / "test-plan.json").read_text(encoding="utf-8"))
    run_id = plan["run_id"]
    launches = evidence / "launches"
    previous = list(launches.iterdir()) if launches.exists() else []
    if len(previous) >= 16:
        raise RuntimeError("D2 dynamic batch budget exhausted")
    destination = launches / run_id
    destination.mkdir(parents=True, exist_ok=False)
    for name, digest in plan["source_test_runner_raw_sha256"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
    changed = subprocess.run(["git", "--no-optional-locks", "diff", "--exit-code", "HEAD", "--",
                              *plan["source_test_runner_raw_sha256"].keys(),
                              str((evidence / "test-plan.json").relative_to(root))],
                             cwd=root, capture_output=True)
    assert changed.returncode == 0, "freeze inputs must be committed before the batch"
    command = [sys.executable, "-I", "-B", str(evidence / "run_guarded.py"), run_id, *plan["selection"]]
    before = {"command": command, "timeout_s": 60,
              "plan_sha256": hashlib.sha256((evidence / "test-plan.json").read_bytes()).hexdigest(),
              "scope": "hard bounded child; no product imports in launcher", "task_wall_peak_RSS": "UNKNOWN"}
    (destination / "before.json").write_text(json.dumps(before, indent=2) + "\n", encoding="utf-8", newline="\n")
    started = time.perf_counter()
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=60)
        code, output, errors, status = result.returncode, result.stdout, result.stderr, "returned"
    except subprocess.TimeoutExpired as error:
        code, output, errors, status = None, error.stdout or b"", error.stderr or b"", "timeout"
    (destination / "stdout.txt").write_bytes(output)
    (destination / "stderr.txt").write_bytes(errors)
    guard_check = None
    if plan.get("guard_only"):
        child = evidence / "runs" / run_id
        child_receipt = json.loads((child / "receipt.json").read_text(encoding="utf-8"))
        forbidden = ("sentinel-body.txt", "sentinel-caught.txt", "sentinel-after.txt", "sentinel-next-case.txt")
        guard_check = (code == 86 and child_receipt.get("status") == "blocked"
                       and child_receipt.get("guard_only_trigger_entries") == 1
                       and (child / "sentinel-before.txt").read_text(encoding="utf-8") == "started\n"
                       and not any((child / name).exists() for name in forbidden)
                       and len(child_receipt.get("test_methods_started", [])) == 1)
    receipt = {**before, "exit_code": code, "status": status, "elapsed_s": time.perf_counter() - started,
               "guard_only_verification_passed": guard_check,
               "output_sha256": {name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
                                 for name in ("stdout.txt", "stderr.txt")},
               "timeout_note": "events.jsonl and line-buffered child logs retain actual starts; timeout is never pass"}
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt))
    return 1 if code is None else code


if __name__ == "__main__":
    sys.exit(main())
