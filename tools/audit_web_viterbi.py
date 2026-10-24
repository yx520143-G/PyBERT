"""Audit preserved raw bytes, old schemas and atomic rejection without any simulation."""

import copy
import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from pybert.web.archive import array_identity, json_bytes, read_arrays, sha256, validate_run
from pybert.web.server import create_app
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/webui/issue9/evidence"


def rewrite(source, change):
    with zipfile.ZipFile(io.BytesIO(source)) as archive:
        outer = json.loads(archive.read("manifest.json"))
        arrays = read_arrays(archive.read("arrays.npz"))
    run = outer["run"]
    change(run, arrays)
    raw = io.BytesIO()
    np.savez_compressed(raw, **arrays)
    raw = raw.getvalue()
    original = json_bytes(run)
    outer.update(run=run, source_manifest_utf8=original.decode(), arrays={k: array_identity(v) for k, v in arrays.items()})
    outer["source_files"] = {"manifest.json": sha256(original), "arrays.npz": sha256(raw)}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json_bytes(outer))
        archive.writestr("arrays.npz", raw)
    return output.getvalue()


def main():
    output = EVIDENCE / time.strftime("saved-audit-%Y%m%d-%H%M%S")
    output.mkdir()
    report = {"main_calls": 0, "COM_calls": 0, "checks": [], "archives": []}

    def check(name, passed, detail=None):
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})

    for archive in sorted(EVIDENCE.glob("numerics-*/local/*/saved.pybert_run")):
        manager = Tasks(output / "local" / archive.parent.name)
        manager.start = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("audit must not start any worker"))
        client = TestClient(create_app(manager))
        content = archive.read_bytes()
        opened = client.post("/api/references?name=original.pybert_run", content=content)
        check(str(archive.relative_to(ROOT)) + ": open", opened.status_code == 201, opened.text[:200])
        if opened.status_code != 201:
            continue
        record_id = opened.json()["record_id"]
        source = manager.references.directory(record_id)
        raw = read_arrays((source / "arrays.npz").read_bytes())
        record = manager.manifest(record_id)
        with zipfile.ZipFile(io.BytesIO(content)) as saved:
            check("raw archive bytes", saved.read("arrays.npz") == (source / "arrays.npz").read_bytes())
        result = client.get(f"/api/runs/{record_id}/trellis?position=999999").json()
        enabled = record["effective_input"]["rx_use_viterbi"]
        check("availability", result["availability"] == ("available" if enabled else "disabled"))
        if enabled:
            check("actual symbol boundary", result["position"] == max(0, record["decoding"]["symbol_count"]-10))
            count = record["decoding"]["ber"]["viterbi"]["count"]
            if count:
                first = client.get(f"/api/runs/{record_id}/trellis?error=1").json()
                check("bit/symbol entry", first["selected_error"]["bit_index"] == int(raw["ber.viterbi.errors"][0]))
            check("no-error selection", client.get(f"/api/runs/{record_id}/trellis?error=0").json()["error"] == 0)
        report["archives"].append({"source": str(archive), "sha256": sha256(content), "run_id": record["run_id"],
                                   "raw_array_count": len(raw), "zero_probabilities": int((raw["viterbi.probs"] == 0).sum()) if enabled else None,
                                   "duplicate_symbol_entries": int(len(raw["viterbi.trellis_err_xs"])-len(np.unique(raw["viterbi.trellis_err_xs"]))) if enabled else None})
        if archive.parent.name != "V-PAM4-ERROR":
            continue
        before = client.get("/api/state").json()

        def drop_array(run, arrays):
            del arrays["viterbi.probs"]
            del run["datasets"]["viterbi.probs"]

        changes = {
            "missing raw probability": drop_array,
            "missing bits": lambda r, _a: r["decoding"]["ber"]["viterbi"].pop("test_start_bit"),
            "missing physical axis": lambda r, _a: r["datasets"]["viterbi.sample_times"].update(axis=None),
            "missing BER window": lambda r, _a: r["datasets"]["ber.dfe.bits_reference"].update(window={}),
            "invalid source identity": lambda r, _a: r["actual_source_sha256"].clear(),
            "wrong count": lambda r, _a: r["decoding"]["ber"]["viterbi"].update(count=0),
            "unknown decoding schema": lambda r, _a: r["decoding"].update(schema_version=99),
            "downgrade to raw4": lambda r, _a: r.update(raw_schema_version=4),
            "incomplete run identity": lambda r, _a: r.pop("input_identity_hash"),
        }
        for name, change in changes.items():
            response = client.post("/api/references?name=bad.pybert_run", content=rewrite(content, change))
            check(name, response.status_code == 422, response.json())
            check(name + " atomic inventory", client.get("/api/state").json() == before)
            check(name + " selected source retained", client.get(f"/api/runs/{record_id}").json()["run_id"] == record["run_id"])
        # Explicit controlled old-schema derivatives, not historical numerical reproductions.
        for version in (2, 3, 4):
            def old(run, arrays):
                run["raw_schema_version"] = version
                run.pop("decoding")
                for key in list(arrays):
                    if key.startswith(("viterbi.", "ber.")):
                        del arrays[key]
                        del run["datasets"][key]
            legacy_manager = Tasks(output / "local" / f"raw{version}")
            legacy_client = TestClient(create_app(legacy_manager))
            response = legacy_client.post("/api/references?name=old.pybert_run", content=rewrite(content, old))
            check(f"raw{version} supported", response.status_code == 201, response.text[:200])
            if response.status_code == 201:
                data = legacy_client.get(f"/api/runs/{response.json()['record_id']}/trellis").json()
                check(f"raw{version} not collected", data["availability"] == "not_collected")
    report["failed"] = sum(not row["passed"] for row in report["checks"])
    report["check_count"] = len(report["checks"])
    (output / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({"output": str(output), "checks": report["check_count"], "failed": report["failed"]}))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
