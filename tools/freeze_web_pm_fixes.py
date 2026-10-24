"""Adversarial metadata fixtures from a real archive; original arrays/source remain unchanged."""

import io
import json
import zipfile
from pathlib import Path

from pybert.web.archive import json_bytes, sha256


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    output = root / "docs/webui/issue5/evidence/pm-fixes-v6/local/fixtures"
    output.mkdir(exist_ok=False, parents=True)
    source = root / "output/playwright/NRZ-real.pybert_run"
    original = source.read_bytes()
    report = {"source": str(source), "source_sha256": sha256(original), "main_calls": 0, "COM_calls": 0, "fixtures": {}}
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        for name, value in (("missing-input_hash", None), ("integer-input_hash", 123)):
            manifest = json.loads(archive.read("manifest.json"))
            if value is None:
                del manifest["run"]["input_hash"]
            else:
                manifest["run"]["input_hash"] = value
            manifest["source_manifest_utf8"] = json_bytes(manifest["run"]).decode("utf-8")
            manifest["source_files"]["manifest.json"] = sha256(manifest["source_manifest_utf8"].encode("utf-8"))
            path = output / f"{name}.pybert_run"
            with zipfile.ZipFile(path, "w") as target:
                target.writestr("manifest.json", json_bytes(manifest))
                target.writestr("arrays.npz", archive.read("arrays.npz"))
            report["fixtures"][name] = {"path": str(path), "sha256": sha256(path.read_bytes()), "only_changed_input_hash_metadata": True}
    channel = Path("C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/local/resources/example2_THRU.s4p")
    different = output / "example2_THRU.s4p"
    different.write_bytes(channel.read_bytes() + b"\n! #5 PM regression resource B: different bytes, never simulated\n")
    report["resources"] = {"A": {"path": str(channel), "sha256": sha256(channel.read_bytes())}, "B": {"path": str(different), "sha256": sha256(different.read_bytes())}}
    assert original == source.read_bytes()
    (output.parent.parent / "fixture-report.json").write_bytes(json_bytes(report))
    print(json.dumps({"fixture_report": str(output.parent.parent / "fixture-report.json"), "main_calls": 0, "COM_calls": 0}))
