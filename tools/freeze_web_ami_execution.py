"""Add executable bindings/full dynamic state before the first adapter numerical batch."""

import copy
import json
import shutil
from pathlib import Path

from pybert.web.archive import json_bytes, sha256
from pybert.web.config import input_hash, yaml_text
from pybert.web.optimization import execution_environment
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/webui/issue10/fixtures/v2-executable"


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    manager = Tasks(ROOT / ".pybert-web/issue10-acceptance")
    source = json.loads((ROOT / "docs/webui/issue10/fixtures/v1/manifest.json").read_text(encoding="utf-8"))
    models = {}
    for side in ("tx", "rx"):
        row = manager.resources.local_model(str(Path(source["models"][side]["ibis"]).parent))
        models[side] = row
    (OUT / "model-resources.json").write_bytes(json_bytes(models))
    cases = {}

    def freeze(name, request):
        result = manager.normalize({"mode": "load", **{k: request[k] for k in ("config", "runtime_extensions", "resource_bindings")}})
        frozen = {k: result[k] for k in ("config", "input_hash", "input_identity_hash", "runtime_extensions", "resource_bindings")}
        frozen["draft_revision"] = 0
        (OUT / f"{name}.json").write_bytes(json_bytes(frozen))
        (OUT / f"{name}.yaml").write_text(yaml_text(frozen["config"], frozen["runtime_extensions"], frozen["resource_bindings"]), encoding="utf-8")
        cases[name] = {"request_sha256": sha256(json_bytes(frozen)), "input_identity_hash": frozen["input_identity_hash"],
                       "model_check": result["ami_models"], "library_checks": len(result["ami_models"]),
                       "source_v1": name if name in source["cases"] else "A-NRZ-Native-Init"}
        print(json.dumps({"frozen": name, "model_checks": len(result["ami_models"])}), flush=True)
        return frozen

    for name in source["cases"]:
        request = json.loads((ROOT / f"docs/webui/issue10/fixtures/v1/{name}.json").read_text(encoding="utf-8"))
        for side in ("tx", "rx"):
            if request["config"][side + "_sel"] == "ibis":
                request["resource_bindings"][side + "_model_bundle"] = models[side]["resource_id"]
        freeze(name, request)
    request = json.loads((OUT / "A-NRZ-Native-Init.json").read_text(encoding="utf-8"))
    request["config"]["seed"] = 12345
    request["config"]["tx_tap_tuners"] = [[False, *row[1:]] for row in request["config"]["tx_tap_tuners"]]
    request["config"]["ctle_enable_tune"] = False
    freeze("OPT-FIXED", request)
    request = copy.deepcopy(request)
    model = request["runtime_extensions"]["values"]["ami_models"]["rx"]
    next(row for row in model["parameters"] if row["path"] == ["Model_Specific", "ctle_mode"])["value"] = 1
    next(row for row in model["search"] if row["path"] == ["Model_Specific", "ctle_mode"])["value"] = 1
    next(row for row in model["search"] if row["path"] == ["Model_Specific", "ctle_mag"]).update(enabled=True, min_val=0.0, max_val=12.0, step=6.0, value=0.0)
    freeze("OPT-TPE4", request)
    environment = execution_environment()
    manifest = {"version": 2, "v1_manifest_sha256": sha256((ROOT / "docs/webui/issue10/fixtures/v1/manifest.json").read_bytes()),
                "before_first_adapter_numeric_batch": True, "cases": cases, "environment": environment,
                "actual_source": environment["python_source_sha256"],
                "prior_cost": {"Main": 1, "direct_rx_GetWave": 1, "early_peak": "UNKNOWN", "direct_preflight_library_checks": 1,
                               "incomplete_v2_freeze_library_checks": 1, "incomplete_v2_reason": "Traits list leaked over IPC; failed get deepcopy; original retained",
                               "this_freeze_library_checks": sum(c["library_checks"] for c in cases.values()), "this_freeze_Init_or_GetWave": 0},
                "changes_from_v1": ["content-addressed complete model bundles + complete dynamic parameters/search defaults",
                                    "native AMI observer normalization included in requested tuner state",
                                    "optimizer: seed12345, all native Tx search disabled, native CTLE search disabled; TPE4 uses ctle_mode1, ctle_mag0..12 step6"],
                "budget": source["budget"], "tolerances": source["tolerances"],
                "chrome_presets": ["A-NRZ-Native-GetWave", "A-PAM4-Native-Init"],
                "coverage_policy": "report each actually executed row; valid/invalid clocks observed. No seed/window/tolerance change after results."}
    for name in ("src/pybert/web", "src/pybert/models", "src/pybert/threads", "src/pybert/utility"):
        for path in (ROOT / name).rglob("*.py"):
            target = OUT / "execution-source" / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    (OUT / "manifest.json").write_bytes(json_bytes(manifest))
    print(json.dumps({"manifest": str(OUT / "manifest.json"), "sha256": sha256((OUT / "manifest.json").read_bytes()), "main_calls": 0}))


if __name__ == "__main__":
    main()
