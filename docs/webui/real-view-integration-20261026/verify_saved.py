"""Recheck retained acceptance evidence without running the numerical engine."""

import json
import zipfile

import numpy as np

from verify_native import OUT, ROOT, digest, verify_sources, write


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def cli_result(path):
    text = path.read_text(encoding="utf-8")
    assert "### Error" not in text, path
    return json.loads(text.split("### Result\n", 1)[1].split("\n###", 1)[0])


verify_sources()
report = {"cases": {}, "web_main_invocations": 0, "direct_main_invocations": 0}
report["frozen_source_and_input_hashes_verified"] = len(read(OUT / "freeze.json")["source_hashes"])
manifests = {}
for name in ("A", "B", "C"):
    directory = OUT / "local" / name
    manifest = read(directory / "manifest.json")
    manifests[name] = manifest
    task, terminal, request = (read(directory / f"{key}.json") for key in ("task", "terminal", "request"))
    assert task["state"] == "succeeded" and task["worker_exited"] and task["exitcode"] == 0
    assert terminal["main_invocations"] == 1
    assert request["config"] == manifest["requested_input"] == manifest["effective_input"]
    assert request["input_hash"] == manifest["input_hash"]
    assert request["input_identity_hash"] == manifest["input_identity_hash"]
    with zipfile.ZipFile(directory / "result.pybert_run") as archive:
        assert archive.read("arrays.npz") == (directory / "arrays.npz").read_bytes()
    with np.load(directory / "arrays.npz", allow_pickle=False) as arrays:
        count = len(arrays.files)
        levels = np.unique(arrays["context.source.x"]).tolist()
    report["cases"][name] = {
        "run_id": manifest["run_id"], "input_hash": manifest["input_hash"],
        "input_identity_hash": manifest["input_identity_hash"], "arrays": count,
        "source_levels": levels, "main_seconds": next(p["elapsed_s"] for p in terminal["phase_ledger"] if p["phase"] == "Main"),
        "task_seconds": task["finished_at"] - task["created_at"],
        "archive_arrays_exact": True, "arrays_sha256": digest(directory / "arrays.npz"),
    }
    report["web_main_invocations"] += terminal["main_invocations"]
    if name in ("A", "C"):
        direct = read(OUT / f"{name}-direct-comparison.json")
        assert direct["passed"] and all(row["exact"] for row in direct["arrays"])
        report["direct_main_invocations"] += direct["main_attempts"]
        report["cases"][name]["direct_exact_arrays"] = len(direct["arrays"])
        report["cases"][name]["direct_seconds"] = direct["elapsed_seconds"]
assert report["web_main_invocations"] == 3 and report["direct_main_invocations"] == 2
assert len(report["cases"]["A"]["source_levels"]) == 2
assert len(report["cases"]["C"]["source_levels"]) == 4

for field in ("requested_input", "effective_input"):
    a, b = (manifests[name][field] for name in ("A", "B"))
    assert [key for key in a if a[key] != b[key]] == ["peak_mag"]
assert manifests["A"]["input_hash"] != manifests["B"]["input_hash"]
report["parameter_change"] = read(OUT / "A-B-parameter-change.json")

browser = ROOT / "output/playwright/real-views"
run_posts = [line for line in (browser / "server.stdout.log").read_text(encoding="utf-8").splitlines()
             if '"POST /api/runs HTTP/1.1"' in line]
assert len(run_posts) == 3
report["http_run_posts"] = len(run_posts)
(OUT / "http-run-posts.txt").write_text("\n".join(run_posts) + "\n", encoding="utf-8")
post = cli_result(browser / "C-browser-post.txt")
assert len(post["runs"]) == 1 and not post["errors"]
request = post["runs"][0]
assert request["body"]["config"] == manifests["C"]["requested_input"]
assert request["body"]["input_identity_hash"] == manifests["C"]["input_identity_hash"]
assert request["response"]["task_id"] == manifests["C"]["run_id"]
write(OUT / "C-browser-post.json", post)

checks = []
for path in sorted(browser.glob("*-check-*.txt")):
    result = cli_result(path)
    checks.append({"artifact": path.name, "sha256": digest(path), **result})
for path in (browser / "AB-compare-response.txt",):
    result = cli_result(path)
    checks.append({"artifact": path.name, "sha256": digest(path), **result})
report["browser_checks"] = len(checks)
write(OUT / "browser-checks.json", checks)
reopened = read(OUT / "archive-roundtrip.json")
assert reopened["raw_npz_bytes_exact"] and reopened["sha256"] == report["cases"]["A"]["arrays_sha256"]
archive_browser = cli_result(browser / "archive-browser-check.txt")
assert archive_browser["record_id"] == reopened["record_id"]
assert archive_browser["draft_unchanged"] and archive_browser["revision_unchanged"]
assert archive_browser["extra_run_posts"] == 0
report["archive"] = {**reopened, **archive_browser}
report["browser_interruption"] = {
    "occurred_after": "A/B succeeded and the two-run CTLE comparison passed",
    "preserved": "server-received requests; saved raw arrays and archives; per-view CLI coordinate-check results",
    "not_preserved": "A/B full browser-side network observer memory before export",
    "recovery": "separate headless browser; no repeated A/B Main",
}
report["peak_memory"] = "not measured"
report["passed"] = True
write(OUT / "acceptance-summary.json", report)
print(json.dumps({key: value for key, value in report.items() if key != "cases"}, ensure_ascii=False))
