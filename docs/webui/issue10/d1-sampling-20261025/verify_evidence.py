"""Read-only stdlib/Git evidence audit; never import or execute numerical/product definitions."""

import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time


def main():
    evidence = Path(__file__).resolve().parent
    root = evidence.parents[3]
    failures = []
    started = time.perf_counter()

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def git(*args, cwd=root):
        return subprocess.check_output(["git", "--no-optional-locks", *args], cwd=cwd).decode("utf-8")

    def check(condition, message):
        if not condition:
            failures.append(message)

    def hashes(values, label):
        for name, digest in values.items():
            path = Path(name)
            check(path.is_file() and sha(path) == digest, label + ": " + name)
        return len(values)

    startup = json.loads((evidence / "startup.json").read_text(encoding="utf-8"))
    protected = Path(startup["protected_startup_path"])
    check(sha(protected) == startup["protected_startup_sha256"], "external startup record")
    reference = startup["old_raw_map_reference"]
    check(sha(Path(reference["path"])) == reference["sha256"], "old raw reference")
    old_raw = json.loads(Path(reference["path"]).read_text(encoding="utf-8"))[reference["field"]]
    protection = {"raw": hashes(old_raw, "old raw"),
                  "metadata": hashes(startup["old_metadata_sha256"], "old metadata"),
                  "materials_sources": hashes(startup["old_materials_and_installed_source_sha256"], "old material")}
    for state in startup["old_repository_states"]:
        directory = Path(state["path"])
        check(git("rev-parse", "HEAD", "HEAD^{tree}", cwd=directory).splitlines() == state["HEAD_tree"],
              "old repository HEAD/tree " + str(directory))
        check(git("status", "--short", cwd=directory) == state["status"], "old status " + str(directory))
    protection["repositories"] = len(startup["old_repository_states"])
    for name in startup["old_env_cache_dirs"]:
        check(Path(name).is_dir(), "old environment/cache removed " + name)
    protection["env_cache_dirs_present"] = len(startup["old_env_cache_dirs"])
    seal = startup["old30_v2_seal"]
    check(sha(Path(seal["path"])) == seal["sha256"], "old30 v2 seal")

    cumulative = Counter()
    batches = []
    for directory in sorted((evidence / "runs").iterdir()):
        receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        counts = Counter(event["kind"] for event in events if event["kind"] in receipt["counts"])
        check(dict(counts) == {key: value for key, value in receipt["counts"].items() if value},
              "actual event counts " + directory.name)
        check(receipt["spent_before"] == {key: cumulative[key] for key in receipt["spent_before"]},
              "cumulative starts " + directory.name)
        cumulative.update(receipt["counts"])
        for name, digest in receipt["input_sha256"].items():
            check(sha(directory / name) == digest, directory.name + " input " + name)
        for name, digest in receipt["output_sha256"].items():
            check(sha(directory / name) == digest, directory.name + " output " + name)
        for name, digest in receipt.get("array_output_sha256", {}).items():
            check(sha(directory / "arrays" / name) == digest, directory.name + " array " + name)
        check(receipt["inputs_unchanged_after"], directory.name + " changed inputs during execution")
        check(not receipt["blocked_attempts"], directory.name + " guard block")
        launch = evidence / "launches" / directory.name
        launcher = json.loads((launch / "receipt.json").read_text(encoding="utf-8"))
        check(launcher["status"] == "returned" and launcher["exit_code"] == receipt["exit_code"],
              directory.name + " child/launcher status")
        for name, digest in launcher["output_sha256"].items():
            check(sha(launch / name) == digest, directory.name + " launch " + name)
        batches.append({"id": directory.name, "freeze_HEAD": receipt["git_HEAD"], "exit": receipt["exit_code"],
                        "tests": receipt["tests_run"], "failures": receipt["failures"], "errors": receipt["errors"],
                        "counts": receipt["counts"], "child_elapsed_s": receipt["elapsed_s"],
                        "launch_elapsed_s": launcher["elapsed_s"], "NumPy_imports": receipt["NumPy_imports"],
                        "receipt_sha256": sha(directory / "receipt.json")})
    last = evidence / "runs" / batches[-1]["id"]
    current_plan = json.loads((last / "plan.json").read_text(encoding="utf-8"))
    input_bindings = {}
    for name, path in current_plan["snapshot_paths"].items():
        equal = (root / path).read_bytes() == (last / name).read_bytes()
        check(equal, "last green/current binding " + path)
        input_bindings[path] = {"sha256": sha(root / path), "same_as_last_green": equal}
    environment = json.loads((evidence / "environment.json").read_text(encoding="utf-8"))
    installed = hashes({str(root / name): digest for name, digest in environment["installed_files_sha256"].items()},
                       "new NumPy installed file")
    allowed = {"src/pybert/utility/ami_clock.py", "src/pybert/utility/sigproc.py", "src/pybert/models/bert.py",
               "src/pybert/pybert.py", "src/pybert/gui/plot.py"}
    changed = git("diff", "--name-only", startup["baseline_HEAD"] + "...HEAD").splitlines()
    check(all(name in allowed or name.startswith("docs/webui/issue10/d1-sampling-20261025/") for name in changed),
          "scope outside allowed product/evidence files")
    for name in allowed:
        ast.parse((root / name).read_text(encoding="utf-8"), filename=name)
    check(git("ls-tree", "HEAD", "PyAMI", "PyChOpMarg") == startup["gitlinks"], "gitlinks")
    check(not (root / ".git/modules").exists(), "submodules initialized")
    for key, limit in current_plan["cumulative_limits"].items():
        check(cumulative[key] <= limit, "budget " + key)
    check(len(batches) <= 12, "batch budget")
    report = {"scope": "stdlib/hash/AST/Git audit only; no product/NumPy execution", "failures": failures,
              "audited_HEAD_tree": git("rev-parse", "HEAD", "HEAD^{tree}").splitlines(),
              "old_protection": protection, "new_installed_file_hashes": installed, "batches": batches,
              "cumulative_actual": dict(cumulative), "NumPy_imports": sum(row["NumPy_imports"] for row in batches),
              "child_elapsed_sum_s": sum(row["child_elapsed_s"] for row in batches),
              "launch_elapsed_sum_s": sum(row["launch_elapsed_s"] for row in batches),
              "last_green_current_bindings": input_bindings, "audit_elapsed_s": time.perf_counter() - started,
              "task_wall_peak_RSS": "UNKNOWN", "full_Main_GUI_model_qualification": "NOT_EXECUTED / UNKNOWN"}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
