"""Freeze complete bounded Chrome inputs before any #5 main computation."""

import copy
import json
import subprocess
import time
from pathlib import Path
from urllib.request import Request, urlopen

from pybert.web.archive import json_bytes, sha256
from pybert.web.config import input_hash


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / "docs/webui/issue5/fixtures/chrome-execution-v1"
    output.mkdir(exist_ok=False)

    def normalize(body):
        request = Request("http://127.0.0.1:8770/api/normalize", data=json_bytes(body), headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            return json.load(response)

    defaults = normalize({"mode": "defaults"})
    resources = json.loads((root / "docs/webui/issue4/fixtures/resources.json").read_text(encoding="utf-8"))
    resource = resources["A"]
    assert sha256(Path(resource["path"]).read_bytes()) == resource["sha256"]
    binding = {"ch_file": resource["sha256"] + ".s4p"}
    runtime = {"version": 1, "values": defaults["runtime_defaults"]}
    report = {"before_main_computation": True, "created_at": time.time(), "adapter_HEAD": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
              "main_calls_planned": {"PAM4": 1, "NRZ": 1, "NRZ_cancel_attempt": 1}, "COM_calls_planned": 0,
              "cancel_policy": "request in original DFE/CDR interval; record actual observation/exit or natural completion, including any extra cost",
              "portability_change": "only active channel reference becomes original_name; bytes/hash and all physical inputs unchanged",
              "resource": resource, "cases": {},
              "inherited_tolerances_file": "docs/webui/issue2/fixtures/tolerances.json",
              "inherited_tolerances_sha256": sha256((root / "docs/webui/issue2/fixtures/tolerances.json").read_bytes()),
              "actual_sources": {str(path.relative_to(root)): sha256(path.read_bytes()) for path in [Path(__file__),*root.glob("src/pybert/web/*.py"),*root.glob("src/pybert/web/static/*"),root / "src/pybert/models/bert.py",root / "src/pybert/pybert.py",root / "src/pybert/utility/sparam.py"] if path.is_file()}}
    for name, source in (("NRZ", "F4-SINGLE-NRZ"), ("PAM4", "F4-SINGLE-PAM4")):
        path = root / f"docs/webui/issue4/fixtures/{source}.json"
        original = json.loads(path.read_text(encoding="utf-8"))
        config = copy.deepcopy(original)
        config["ch_file"] = Path(resource["path"]).name
        assert config["enable_com"] is False
        normalized = normalize({"mode": "load", "config": config, "runtime_extensions": runtime, "resource_bindings": binding})
        assert normalized["input_hash"] == input_hash(config)
        request = {key: normalized[key] for key in ("config", "input_hash", "input_identity_hash", "runtime_extensions", "resource_bindings")}
        (output / f"{name}.json").write_bytes(json_bytes(request))
        (output / f"{name}.yaml").write_text(normalized["yaml"], encoding="utf-8")
        report["cases"][name] = {"original_fixture": str(path.relative_to(root)), "original_sha256": sha256(path.read_bytes()),
                                 "complete_request": request, "yaml_sha256": sha256((output / f"{name}.yaml").read_bytes()),
                                 "original_effective_windows": {"nbits": config["nbits"], "nspui": config["nspui"], "eye_bits": config["eye_bits"]}}
    blocked = copy.deepcopy(report["cases"]["NRZ"]["complete_request"]["config"])
    blocked.update(ctle_sel="File", use_ctle_file=True, ctle_file="known-native-blocked.csv")
    result = normalize({"mode": "load", "config": blocked, "runtime_extensions": runtime, "resource_bindings": binding})
    (output / "CTLE-BLOCKED.yaml").write_text(result["yaml"], encoding="utf-8")
    report["preflight_case"] = {"input_hash": result["input_hash"], "expected": "native CTLE File gate; zero main simulation calls"}
    (output / "manifest.json").write_bytes(json_bytes(report))
    print(json.dumps({"freeze": str(output / "manifest.json"), "sha256": sha256((output / "manifest.json").read_bytes()), "main_calls_performed": 0, "COM_calls_performed": 0}))


if __name__ == "__main__":
    main()
