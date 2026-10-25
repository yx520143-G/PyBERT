"""Compare retained baseline arrays and current results, without running any engine."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = Path(r"C:\Users\yx\.codex\worktrees\pybert-final-parity\serial-bus-simulator")
OLD = Path(r"C:\Users\yx\.codex\worktrees\pybert-issue2-native\serial-bus-simulator\docs\webui\issue2\evidence\numeric-20261024-050800")
BASE = "1bc905d577d2f3bd9471421cfbf3d422d4e6080e"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2), encoding="utf-8")


rows, inputs = [], []
for name, folder in (("F-NRZ-01", "fixed-v2"), ("F-PAM4-01", "pam4-v3")):
    current = OUT / folder / "local" / name / "arrays.npz"
    old = OLD / name / "arrays.npz"
    for path in (old, current):
        inputs.append(dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path)))
write("saved-comparison-inputs.json", dict(inputs=inputs, comparison="all original fields; exact dtype/shape/C-order bytes",
                                          simulation_calls=0, source_sha256=sha(Path(__file__))))
for name, folder in (("F-NRZ-01", "fixed-v2"), ("F-PAM4-01", "pam4-v3")):
    checks = []
    with np.load(OLD / name / "arrays.npz") as old, np.load(OUT / folder / "local" / name / "arrays.npz") as current:
        for key in old.files:
            a = old[key]
            b = current[key] if key in current else None
            equal = b is not None and a.shape == b.shape and a.dtype == b.dtype and a.tobytes() == b.tobytes()
            checks.append(dict(field=key, passed=equal, missing=b is None,
                               max_absolute_difference=float(np.max(np.abs(a.astype(complex) - b.astype(complex))))
                               if b is not None and a.shape == b.shape and a.size else None))
        rows.append(dict(fixture=name, checks=checks, original_fields=len(old.files),
                         additional_current_fields=sorted(set(current.files) - set(old.files)),
                         passed=all(item["passed"] for item in checks)))
write("saved-baseline-comparison.json", dict(cases=rows, input_manifest_sha256=sha(OUT / "saved-comparison-inputs.json"),
                                             main_calls=0, COM_calls=0))

unchanged = []
for rel in ("models/dfe.py", "models/cdr.py", "models/viterbi.py", "models/com.py", "utility/math.py", "utility/jitter.py",
            "utility/channel.py", "configuration.py", "threads/sim.py", "gui/handler.py", "gui/view.py"):
    path = "src/pybert/" + rel
    old = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
    current = subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT)
    unchanged.append(dict(path=path, git_blob_bytes_exact=old == current,
                          AST_exact=ast.dump(ast.parse(old)) == ast.dump(ast.parse(current))))
write("unchanged-core.json", unchanged)
print(json.dumps({"baseline_cases": [{"fixture": row["fixture"], "fields": row["original_fields"], "passed": row["passed"],
                                       "failures": [x for x in row["checks"] if not x["passed"]]} for row in rows],
                  "unchanged_core": unchanged}))
