"""Capture one authorized dependency command and immutable input/output bytes."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    """Keep unique batches and share identical input snapshots by their SHA256."""
    root = Path(__file__).resolve().parents[4]
    evidence = Path(__file__).parent
    run_id, *command = sys.argv[1:]
    assert command and run_id and Path(run_id).name == run_id
    destination = evidence / "commands" / run_id
    destination.mkdir(parents=True, exist_ok=False)
    inputs = {}
    sources = [root / "pyproject.toml", root / "uv.lock", root / ".gitmodules", Path(__file__),
               evidence / "verify_source.py"]
    sources += [evidence / name for name in (
        "source-inputs.json", "environment-bootstrap-plan.json", "install-plan.json",
    ) if (evidence / name).exists()]
    for source in sources:
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        snapshot = evidence / "inputs" / (digest + ".txt")
        snapshot.parent.mkdir(exist_ok=True)
        if snapshot.exists():
            assert snapshot.read_bytes() == raw
        else:
            snapshot.write_bytes(raw)
        inputs[str(source.relative_to(root))] = {"sha256": digest, "snapshot": str(snapshot.relative_to(evidence))}
    receipt = {
        "command": command, "cwd": str(root), "outer_python": sys.executable, "inputs": inputs,
        "environment": {key: os.environ.get(key) for key in (
            "UV_CACHE_DIR", "UV_LINK_MODE", "UV_PROJECT_ENVIRONMENT", "PIP_CACHE_DIR",
            "PIP_DISABLE_PIP_VERSION_CHECK", "PYTHONPATH", "TMP", "TEMP", "PYTHONDONTWRITEBYTECODE",
        )},
        "scope": "ordinary package installation/build or source metadata; no product/model entry",
        "installer_system_library_activity": "not fully traced; model/product budget is separate",
        "total_task_wall_and_peak_RSS": "UNKNOWN",
    }
    (destination / "command.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    started = time.perf_counter()
    with (destination / "stdout.txt").open("wb") as stdout, (destination / "stderr.txt").open("wb") as stderr:
        result = subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr, check=False)
    receipt.update(exit_code=result.returncode, elapsed_s=time.perf_counter() - started)
    receipt["output_sha256"] = {
        name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
        for name in ("stdout.txt", "stderr.txt")
    }
    (destination / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run": run_id, "exit_code": result.returncode, "elapsed_s": receipt["elapsed_s"]}))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
