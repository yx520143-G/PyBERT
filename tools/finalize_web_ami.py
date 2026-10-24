"""File-only closeout verification and preservation; never invokes an engine/model."""

import hashlib
import json
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue10/evidence/chrome-v4"
SERVICE = ROOT / ".pybert-web/issue10-chrome-v4"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def same_arrays(left, right):
    with np.load(left, allow_pickle=False) as a, np.load(right, allow_pickle=False) as b:
        shared = sorted(set(a.files) & set(b.files))
        for key in shared:
            assert (a[key].dtype == b[key].dtype and a[key].shape == b[key].shape
                    and a[key].tobytes(order="C") == b[key].tobytes(order="C")), key
        return {"shared_exact": len(shared), "left_only": sorted(set(a.files) - set(b.files)),
                "right_only": sorted(set(b.files) - set(a.files))}


if __name__ == "__main__":
    rows = {}
    for version in (1, 2, 3, 4):
        service = ROOT / f".pybert-web/issue10-chrome-v{version}"
        destination = OUT.parent / f"chrome-v{version}/tasks"
        for request_path in service.glob("*/request.json"):
            directory = request_path.parent
            target = destination / directory.name
            target.mkdir(parents=True, exist_ok=True)
            for source in directory.iterdir():
                if source.is_file():
                    shutil.copyfile(source, target / source.name)
            if version == 4:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:8785/api/tasks/{directory.name}") as response:
                        (target / "observed-task.json").write_bytes(response.read())
                except urllib.error.HTTPError as error:
                    assert error.code == 404
            terminal = read(target / "terminal.json")
            rows[f"v{version}/{directory.name}"] = {"status": terminal["status"],
                "Main": terminal.get("main_invocations", "not recorded"),
                "error": terminal.get("error"), "files": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()}}

    comparisons = {}
    for label, task in (("OPT-FIXED", "58d83a53-d409-447d-b0a6-31c55a469005"),
                        ("OPT-TPE4", "3de6652f-4bf3-42b0-b337-5783194aa2db")):
        comparisons[label] = same_arrays(OUT.parent / f"numerics-20261024-160818/{label}/direct/arrays.npz",
                                         SERVICE / task / "arrays.npz")
    comparisons["NRZ"] = same_arrays(OUT.parent / "numerics-20261024-155041/A-NRZ-Native-GetWave/worker/arrays.npz",
                                     OUT.parent / "chrome-v3/tasks/823bfdbb-bc37-40b6-ae56-12e3bf6b3476/arrays.npz")
    comparisons["PAM4"] = same_arrays(OUT.parent / "numerics-20261024-155041/A-PAM4-Native-Init/worker/arrays.npz",
                                      SERVICE / "f4d00fbb-54d1-47cb-a95f-0cf0945b5aee/arrays.npz")
    for label, path in (("NRZ", OUT.parent / "chrome-v3/tasks/823bfdbb-bc37-40b6-ae56-12e3bf6b3476"),
                        ("PAM4", SERVICE / "f4d00fbb-54d1-47cb-a95f-0cf0945b5aee")):
        config = read(path / "manifest.json")["effective_input"]
        ts = (2 if config["mod_type"] == "PAM-4" else 1) / (config["bit_rate"] * 1e9 * config["nspui"])
        with np.load(path / "arrays.npz", allow_pickle=False) as arrays:
            for key in comparisons[label]["right_only"]:
                assert np.array_equal(arrays[key], np.arange(len(arrays[key[:-4]]), dtype=float) * ts)
        comparisons[label]["new_seconds_axes_exact"] = len(comparisons[label]["right_only"])
    roundtrips = {}
    for label, original, resaved in (
        ("Run", OUT.parent / "chrome-v3/nrz.pybert_run", OUT / "nrz-reopened-resaved.pybert_run"),
        ("Optimization", OUT / "OPT-tpe4.pybert_opt", OUT / "OPT-tpe4-reopened-resaved.pybert_opt"),
    ):
        with zipfile.ZipFile(original) as a, zipfile.ZipFile(resaved) as b:
            assert a.read("arrays.npz") == b.read("arrays.npz")
            first = json.loads(a.read("manifest.json"))
            second = json.loads(b.read("manifest.json"))
            roundtrips[label] = {"arrays_npz_bytes_equal": True, "original_manifest_keys": sorted(first),
                                "resaved_manifest_keys": sorted(second)}
            for key in ("source_manifest_utf8", "source_record"):
                if key in first:
                    assert first[key] == second[key]
                    roundtrips[label][key + "_equal"] = True
            if label == "Optimization":
                assert a.read("manifest.json") == b.read("manifest.json")
                roundtrips[label]["entire_manifest_bytes_equal"] = True

    logs = OUT.parent / "logs"
    logs.mkdir(exist_ok=True)
    for pattern in ("issue10*.log", "chrome*.log"):
        for path in (ROOT / ".pybert-web").glob(pattern):
            shutil.copyfile(path, logs / path.name)
    (OUT / "closeout-checks.json").write_text(json.dumps({"numerical_calls_by_this_verifier": 0,
        "tasks": rows, "comparisons": comparisons, "roundtrips": roundtrips}, indent=2), encoding="utf-8")
    print(json.dumps({"tasks_preserved": len(rows), "comparisons": comparisons, "roundtrips": roundtrips}, indent=2))
