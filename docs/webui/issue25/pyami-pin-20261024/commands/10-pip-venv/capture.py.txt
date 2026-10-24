"""Capture one explicitly authorized install/metadata command without product imports."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    """Keep each command, raw output, input hashes, and elapsed time separately."""
    root = Path(__file__).resolve().parents[4]
    run_id, *command = sys.argv[1:]
    assert command and run_id and Path(run_id).name == run_id
    destination = Path(__file__).parent / "commands" / run_id
    destination.mkdir(parents=True, exist_ok=False)
    inputs = {}
    for name in ("pyproject.toml", "uv.lock", ".gitmodules"):
        raw = (root / name).read_bytes()
        (destination / (name.lstrip(".") + ".txt")).write_bytes(raw)
        inputs[name] = hashlib.sha256(raw).hexdigest()
    (destination / "capture.py.txt").write_bytes(Path(__file__).read_bytes())
    receipt = {
        "command": command,
        "cwd": str(root),
        "outer_python": sys.executable,
        "input_sha256": inputs,
        "environment": {
            key: os.environ.get(key)
            for key in (
                "UV_CACHE_DIR", "UV_LINK_MODE", "UV_PROJECT_ENVIRONMENT",
                "PIP_CACHE_DIR", "PIP_DISABLE_PIP_VERSION_CHECK", "PYTHONPATH",
            )
        },
        "scope": "ordinary package install/build or metadata; no model execution",
        "total_task_wall_and_peak_RSS": "UNKNOWN",
    }
    (destination / "command.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    started = time.perf_counter()
    with (destination / "stdout.txt").open("wb") as stdout, (destination / "stderr.txt").open("wb") as stderr:
        result = subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr, check=False)
    receipt["exit_code"] = result.returncode
    receipt["elapsed_s"] = time.perf_counter() - started
    receipt["output_sha256"] = {
        name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
        for name in ("stdout.txt", "stderr.txt")
    }
    (destination / "receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run": run_id, "exit_code": result.returncode, "elapsed_s": receipt["elapsed_s"]}))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
