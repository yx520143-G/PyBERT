"""Replay saved primitive capture into schema2 metadata, without any simulation/decoding."""

import copy
import io
import json
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient

from pybert.web.archive import json_bytes, read_arrays, save_archive, sha256, validate_run
from pybert.web.data import source_identity
from pybert.web.server import create_app
from pybert.web.tasks import Tasks
from pybert.web.viterbi import BER_ARRAYS, DEBUG_ARRAYS, ISI_ARRAYS, extend, payload

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/webui/issue9/evidence"


def main():
    output = EVIDENCE / time.strftime("metadata-audit-%Y%m%d-%H%M%S")
    output.mkdir()
    local = output / "local"
    local.mkdir()
    report = {"product_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "source_identity": source_identity(), "main_calls": 0, "COM_calls": 0,
              "mode": "derived metadata from saved primitive capture; not a new execution", "checks": [], "cases": []}
    for relative in report["source_identity"]:
        target = output / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "src/pybert" / relative, target)
    shutil.copyfile(__file__, output / "verifier.py")

    def check(name, passed):
        report["checks"].append({"name": name, "passed": bool(passed)})
        if not passed:
            raise AssertionError(name)

    sources = sorted(EVIDENCE.glob("numerics-*/local/*/adapter/manifest.json"))
    sources += sorted(p for p in (EVIDENCE / "chrome-v1/local/service").glob("*/manifest.json")
                      if (p.parent / "request.json").exists())
    for index, path in enumerate(sources):
        original = {name: (path.parent / name).read_bytes() for name in ("manifest.json", "arrays.npz")}
        run = json.loads(original["manifest.json"])
        arrays = read_arrays(original["arrays.npz"])
        validate_run(run, arrays)
        before = {key: (value.dtype.str, value.shape, value.tobytes()) for key, value in arrays.items()}
        old_payload = payload(path.parent)
        enabled = run["effective_input"]["rx_use_viterbi"]
        check(f"{index} legacy warning", not enabled or "schema 1" in old_payload["metadata_warning"])
        captured = {}
        for name, row in run["decoding"]["ber"].items():
            if row["availability"] == "available":
                captured[name] = {key: arrays[f"ber.{name}.{key}"] for key in BER_ARRAYS}
                captured[name].update({key: value for key, value in row.items() if key != "availability"})
        debug = {}
        if enabled:
            captured["isi"] = {key: arrays[f"viterbi.{key}"] for key in ISI_ARRAYS}
            debug = {key: arrays[f"viterbi.{key}"] for key in DEBUG_ARRAYS}
            debug.update(decoder=SimpleNamespace(states=arrays["viterbi.states"], trans=arrays["viterbi.trans"]),
                         log=run["decoding"]["decoder_log"])
        engine = SimpleNamespace(rx_use_viterbi=enabled, rx_viterbi_symbols=run["effective_input"]["rx_viterbi_symbols"],
                                 mod_type=run["effective_input"]["mod_type"], L=run["decoding"].get("L"),
                                 n_errs_viterbi=run["summary"]["n_errs_viterbi"], dbg_dict_viterbi=debug,
                                 bit_errs_viterbi=arrays.get("ber.viterbi.errors", []))
        run = copy.deepcopy(run)
        run["metadata_derivation"] = {"kind": report["mode"], "source_manifest_sha256": sha256(original["manifest.json"]),
                                      "source_arrays_sha256": sha256(original["arrays.npz"]),
                                      "metadata_adapter_source_sha256": next(value for key, value in report["source_identity"].items() if key.replace("\\", "/") == "web/viterbi.py"),
                                      "original_execution_source_preserved": True}
        extend(engine, captured, arrays, run)
        validate_run(run, arrays)
        for key, identity in before.items():
            check(f"{index} raw exact {key}", (arrays[key].dtype.str, arrays[key].shape, arrays[key].tobytes()) == identity)
        check(f"{index} only new axis", set(arrays) - set(before) == ({"viterbi.dfe_symbol_index"} if enabled else set()))
        derived = local / str(index)
        derived.mkdir()
        (derived / "manifest.json").write_bytes(json_bytes(run))
        np.savez_compressed(derived / "arrays.npz", **arrays)
        saved = derived / "derived.pybert_run"
        save_archive(derived, saved)
        manager = Tasks(derived / "service")
        client = TestClient(create_app(manager))
        opened = client.post("/api/references?name=derived.pybert_run", content=saved.read_bytes())
        check(f"{index} schema2 HTTP open", opened.status_code == 201)
        record_id = opened.json()["record_id"]
        directory = manager.directory(record_id)
        check(f"{index} opened manifest exact", (directory / "manifest.json").read_bytes() == (derived / "manifest.json").read_bytes())
        check(f"{index} opened raw exact", (directory / "arrays.npz").read_bytes() == (derived / "arrays.npz").read_bytes())
        view = client.get(f"/api/runs/{record_id}/trellis").json()
        check(f"{index} view no legacy warning", not view.get("metadata_warning"))
        second = derived / "resaved.pybert_run"
        save_archive(directory, second)
        with zipfile.ZipFile(saved) as first, zipfile.ZipFile(second) as last:
            check(f"{index} resaved raw exact", first.read("arrays.npz") == last.read("arrays.npz"))
            check(f"{index} resaved source exact", json.loads(first.read("manifest.json"))["source_manifest_utf8"] == json.loads(last.read("manifest.json"))["source_manifest_utf8"])
        if enabled:
            inventory = manager.references.index()
            for damage in ("axis", "window", "mapping", "schema"):
                with zipfile.ZipFile(saved) as archive:
                    envelope, raw = json.loads(archive.read("manifest.json")), archive.read("arrays.npz")
                bad = envelope["run"]
                if damage == "axis":
                    bad["datasets"]["viterbi.symbols_dfe"]["axis"] = None
                elif damage == "window":
                    bad["datasets"]["viterbi.symbols_dfe"]["window"] = bad["datasets"]["viterbi.sig_samps"]["window"]
                elif damage == "mapping":
                    bad["decoding"]["dfe_decisions"]["decoder_start_symbol"] = 0
                else:
                    bad["decoding"]["schema_version"] = 1
                source = json_bytes(bad)
                envelope["source_manifest_utf8"] = source.decode()
                envelope["source_files"]["manifest.json"] = sha256(source)
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, "w") as archive:
                    archive.writestr("manifest.json", json_bytes(envelope))
                    archive.writestr("arrays.npz", raw)
                refused = client.post("/api/references?name=bad.pybert_run", content=buffer.getvalue())
                check(f"{index} {damage} corrupt HTTP refused", refused.status_code == 422)
                check(f"{index} {damage} old inventory retained", manager.references.index() == inventory)
        check(f"{index} no tasks/workers", not manager.tasks and manager.active is None)
        check(f"{index} historical source files unchanged", all((path.parent / name).read_bytes() == content for name, content in original.items()))
        report["cases"].append({"source": str(path.relative_to(ROOT)), "run_id": run["run_id"],
                                 "derivation": run["metadata_derivation"], "original_arrays_exact": len(before),
                                 "original_dfe_metadata": json.loads(original["manifest.json"])["datasets"].get("viterbi.symbols_dfe"),
                                 "revised_dfe_metadata": run["datasets"].get("viterbi.symbols_dfe"),
                                 "decoder_tail": run["decoding"].get("dfe_decisions"), "legacy_warning": old_payload.get("metadata_warning")})
    report.update(check_count=len(report["checks"]), failed=0)
    (output / "report.json").write_bytes(json_bytes(report))
    print(json.dumps({"output": str(output), "cases": len(sources), "checks": report["check_count"], "failed": 0,
                      "main_calls": 0, "COM_calls": 0}))


if __name__ == "__main__":
    main()
