"""Append identity/axis and bounded clocks-probe fixtures; preserve earlier freezes."""

import copy
import json
from pathlib import Path

from pybert.web.archive import json_bytes, sha256
from pybert.web.config import yaml_text
from pybert.web.data import source_identity
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / "docs/webui/issue10/fixtures/v2-executable"
OUT = ROOT / "docs/webui/issue10/fixtures/v3-closeout"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=False)
    manager = Tasks(ROOT / ".pybert-web/issue10-acceptance")
    models = json.loads((PREVIOUS / "model-resources.json").read_text(encoding="utf-8"))
    manager.resources.items.update({row["resource_id"]: row for row in models.values()})
    cases = {}
    names = ["A-NRZ-Native-GetWave", "A-PAM4-Native-Init", "OPT-FIXED", "OPT-TPE4"]
    for name in [*names, "A-NRZ-ADAPT-GetWave"]:
        source = name if name in names else "A-NRZ-Native-GetWave"
        request = json.loads((PREVIOUS / f"{source}.json").read_text(encoding="utf-8"))
        if name == "A-NRZ-ADAPT-GetWave":
            model = request["runtime_extensions"]["values"]["ami_models"]["rx"]
            for key, value in (("dfe_mode", 2), ("ctle_mode", 1)):
                next(row for row in model["parameters"] if row["path"] == ["Model_Specific", key])["value"] = value
                next(row for row in model["search"] if row["path"] == ["Model_Specific", key])["value"] = value
        result = manager.normalize({"mode": "load", **{k: request[k] for k in ("config", "runtime_extensions", "resource_bindings")}})
        frozen = {k: result[k] for k in ("config", "runtime_extensions", "resource_bindings", "input_hash", "input_identity_hash")}
        frozen["draft_revision"] = 0
        (OUT / f"{name}.json").write_bytes(json_bytes(frozen))
        (OUT / f"{name}.yaml").write_text(yaml_text(frozen["config"], frozen["runtime_extensions"], frozen["resource_bindings"]), encoding="utf-8")
        cases[name] = {"request_sha256": sha256(json_bytes(frozen)), "source_case": source,
                       "model_check": result["ami_models"], "library_checks": len(result["ami_models"])}
    manifest = {"version": 3, "cases": cases, "before_first_closeout_call": True,
                "previous_manifest_sha256": sha256((PREVIOUS / "manifest.json").read_bytes()), "source": source_identity(),
                "tolerances": json.loads((PREVIOUS / "manifest.json").read_text(encoding="utf-8"))["tolerances"],
                "identity_change": "parameter_model_hash now binds complete IBIS selection + AMI/binary bytes, besides complete directory hash; default physical parameters unchanged",
                "new_probe": "NRZ dfe_mode=2 and ctle_mode=1, all original seed/noise/windows unchanged. Observe actual clocks/params; native parsing failures preserved, no algorithm repair.",
                "additional_budget": {"clocks_probe_Main": 2, "closeout_browser_Main_max": 4,
                                      "optional_optimizer_direct_metadata_only_recheck_evaluations_max": 5,
                                      "freeze_library_checks": sum(row["library_checks"] for row in cases.values()), "freeze_Init_GetWave": 0},
                "unexecuted": ["PAM4 valid model clocks", "non-Windows", "GetWave-only", "Ts4"],
                "policy": "Neither probe nor new explicit identity fields upgrade prior source/failed rows. Compare new helper axes from original ts separately; preserve previous arrays."}
    (OUT / "manifest.json").write_bytes(json_bytes(manifest))
    (OUT / "model-resources.json").write_bytes((PREVIOUS / "model-resources.json").read_bytes())
    print(json.dumps({"manifest": str(OUT / "manifest.json"), "sha256": sha256((OUT / "manifest.json").read_bytes()), "Init_GetWave": 0}))
