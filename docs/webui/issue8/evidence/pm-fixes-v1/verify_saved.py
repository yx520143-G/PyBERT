"""Actual saved archives + observer-only Use/API regression; zero numerical runs."""
import ast
import copy
import io
import json
import subprocess
import zipfile
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

import pybert.web.optimization as module
from pybert.web.archive import array_identity, json_bytes, sha256
from pybert.web.config import normalize, input_hash, new_engine, load_config, snapshot
from pybert.web.server import create_app
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).parent
LOCAL = OUT / "local"
LOCAL.mkdir(exist_ok=True)
checks, archives, faults, topology = {}, [], [], []


def check(name, value):
    checks[name] = bool(value)


def no_worker(*_args, **_kwargs):
    raise AssertionError("Saved-record regression must not start a worker or computation.")


def unpack(content):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        envelope = json.loads(archive.read("manifest.json"))
        raw = archive.read("arrays.npz")
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    return envelope, raw, arrays


def pack(envelope, arrays):
    envelope = copy.deepcopy(envelope)
    raw = io.BytesIO()
    np.savez_compressed(raw, **arrays)
    envelope["record"]["arrays"] = {k: array_identity(v) for k, v in arrays.items()}
    envelope["record"]["array_contracts"] = {k: v for k, v in envelope["record"].get("array_contracts", {}).items() if k in arrays}
    envelope["raw_sha256"] = sha256(raw.getvalue())
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json_bytes(envelope))
        archive.writestr("arrays.npz", raw.getvalue())
    return output.getvalue(), envelope["record"]


baseline = subprocess.check_output(["git", "show", "238b1cab5e346a937eb1f13884912ca73c43d433:src/pybert/web/optimization.py"], cwd=ROOT)
old = vars(module).copy()
nodes = [node for node in ast.parse(baseline).body if isinstance(node, ast.FunctionDef) and node.name in ("validate_record", "optimizer_action")]
exec(compile(ast.Module(body=nodes, type_ignores=[]), "fixed-238b1cab-reproduction", "exec"), old)
(OUT / "before-optimization.py").write_bytes(baseline)
(OUT / "after-optimization.py").write_bytes((ROOT / "src/pybert/web/optimization.py").read_bytes())

paths = sorted((OUT.parent / "delivery-audit-20261024-130843/local").glob("*.pybert_opt"))
paths += [ROOT / f"output/playwright/issue8/final/{name}.pybert_opt" for name in ("O-PAM4-MMSE", "O-PAM4-MMSE-RLM080")]
for index, path in enumerate(paths):
    envelope, raw, arrays = unpack(path.read_bytes())
    source = envelope["record"]
    manager = Tasks(LOCAL / str(index))
    manager.start = no_worker
    manager.normalize = normalize  # Exercise original observers inline; no numerical worker.
    client = TestClient(create_app(manager))
    opened = client.post("/api/optimization-references", content=path.read_bytes())
    check(f"{index}/original accepted", opened.status_code == 201)
    rid = opened.json()["record_id"]
    restored = client.get(f"/api/optimizations/{rid}").json()
    check(f"{index}/status preserved", restored["status"] == source["status"])
    exported = client.get(f"/api/optimizations/{rid}/archive")
    saved, saved_raw, _ = unpack(exported.content)
    check(f"{index}/roundtrip exact", saved["record"] == source and saved_raw == raw)
    pulse = client.get(f"/api/optimizations/{rid}/pulse")
    check(f"{index}/pulse availability", pulse.status_code == (200 if source["status"] == "succeeded" else 422))
    archives.append({"path": str(path), "sha256": sha256(path.read_bytes()), "status": source["status"],
                     "raw_schema": source.get("optimization_raw_schema", 1), "array_count": len(arrays)})
    if source["status"] != "succeeded":
        continue
    # Real MMSE raw1 and both raw2 records plus one grid, using original selected values.
    if path.stem in ("db86e583-2b31-4671-9765-f9e49667bb6f", "2e3d0d79-061f-4084-96bc-53d651486c2d", "O-PAM4-MMSE", "O-PAM4-MMSE-RLM080"):
        current = copy.deepcopy(source["requested_input"])
        current["rn"] = .02
        response = client.post("/api/optimizer-actions/use_eq", json={"config": current, "runtime_extensions": source["runtime_extensions"], "record_id": rid})
        result = response.json()
        check(f"{index}/compatible Use accepted", response.status_code == 200)
        report, actual = result["import_report"], result["config"]
        targets = set(report["applied_fields"])
        check(f"{index}/actual report and hash", report["after"] == {k: actual[k] for k in targets} and result["runtime_extensions"]["values"]["eq_application"]["after_input_hash"] == input_hash(actual))
        check(f"{index}/unrelated and DFE retained", all(actual[k] == current[k] for k in set(current) - targets) and actual["dfe_tap_tuners"] == current["dfe_tap_tuners"])
        for count, pre in ((1, 0), (3, 0), (3, 2)):
            changed = normalize({"mode": "patch", "config": current, "patches": [{"field": "rx_n_taps", "value": count}, {"field": "rx_n_pre", "value": pre}]})["config"]
            p = new_engine()
            load_config(p, changed)
            old_runtime, old_report = old["optimizer_action"](p, source["runtime_extensions"], "use_eq", source | {"current_config": changed})
            old_actual = snapshot(p)
            rejected = client.post("/api/optimizer-actions/use_eq", json={"config": changed, "runtime_extensions": source["runtime_extensions"], "record_id": rid})
            check(f"{index}/topology {count},{pre} rejected", rejected.status_code == 422 and "matching Rx FFE topology" in rejected.json()["detail"])
            topology.append({"source": str(path), "current_topology": [count, pre], "before_fix_accepted": True,
                             "before_fix_report_matches_final": old_report["after"] == {k: old_actual[k] for k in old_report["after"]},
                             "after_fix_status": rejected.status_code, "detail": rejected.json()["detail"]})
    if path.stem not in ("db86e583-2b31-4671-9765-f9e49667bb6f", "O-PAM4-MMSE"):
        continue
    before = client.get("/api/state").json()
    directories = set(manager.root.iterdir())
    for key, mode in (("curs_ix", "missing"), ("curs_amp", "missing"), ("curs_ix", "short"),
                      ("curs_amp", "rank2"), ("curs_ix", "wrong_value"), ("curs_amp", "wrong_value")):
        altered = dict(arrays)
        if mode == "missing":
            del altered[key]
        elif mode == "short":
            altered[key] = arrays[key][:1]
        elif mode == "rank2":
            altered[key] = arrays[key].reshape(2, 1)
        else:
            altered[key] = arrays[key] + 1.
        content, bad_record = pack(envelope, altered)
        old["validate_record"](bad_record, altered)
        target = LOCAL / f"bad-{index}-{key}-{mode}.pybert_opt"
        target.write_bytes(content)
        rejected = client.post("/api/optimization-references", content=content)
        check(f"{index}/{key}/{mode}/cursor rejected", rejected.status_code == 422 and "cursor" in rejected.json()["detail"])
        check(f"{index}/{key}/{mode}/atomic", client.get("/api/state").json() == before and set(manager.root.iterdir()) == directories)
        faults.append({"source": str(path), "raw_schema": source.get("optimization_raw_schema", 1), "mutation": [key, mode],
                       "self_consistent_sha256": sha256(content), "before_fix_accepted": True, "after_fix_status": rejected.status_code})

report = {"code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "checks": checks, "failed": [k for k, v in checks.items() if not v], "archives": archives,
          "topology_reproductions": topology, "cursor_faults": faults,
          "before_source_sha256": sha256(baseline), "after_source_sha256": sha256((OUT / "after-optimization.py").read_bytes()),
          "verifier_sha256": sha256(Path(__file__).read_bytes()), "execution_environment": module.execution_environment(),
          "new_coopt_calls": 0, "new_main_calls": 0, "new_COM_numeric_calls": 0,
          "boundary": "API uses original observer-only normalize inline; worker start forbidden. Historical physics arrays unchanged; no final-source numerical rerun."}
(OUT / "saved-report.json").write_bytes(json_bytes(report))
print(json.dumps({"checks": len(checks), "failed": report["failed"], "archives": len(archives), "topology_cases": len(topology), "cursor_faults": len(faults)}))
assert not report["failed"]
