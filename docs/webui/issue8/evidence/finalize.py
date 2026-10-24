"""Read-only recovery/source audit; copies evidence, never calls coopt/main/COM."""
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from pybert.web.archive import sha256, json_bytes
from pybert.web.config import normalize
from pybert.web.optimization import execution_environment

root = Path(__file__).resolve().parents[4]
out = Path(__file__).parent / "final-source"
out.mkdir(exist_ok=True)
checks, copies = {}, {}
files = [*sorted((root / "src/pybert/web").glob("*.py")),
         *sorted((root / "src/pybert/web/static").glob("*")),
         root / "src/pybert/threads/optimization.py",
         root / "tools/verify_web_optimizer.py", root / "tools/verify_web_optimizer_ui.cjs",
         root / "tools/audit_web_optimizer_delivery.py"]
for path in files:
    if not path.is_file():
        continue
    relative = path.relative_to(root)
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    copies[str(relative)] = sha256(path.read_bytes())
recovery = root / "output/playwright/issue8/final"
originals = [recovery / "O-PAM4-MMSE.pybert_opt", recovery / "O-PAM4-MMSE-RLM080.pybert_opt",
             Path(__file__).parent / "delivery-audit-20261024-130843/local/2e3d0d79-061f-4084-96bc-53d651486c2d.pybert_opt"]
downloads = []
for i, original in enumerate(originals):
    downloaded = recovery / f"reopened-{i}.pybert_opt"
    with zipfile.ZipFile(original) as a, zipfile.ZipFile(downloaded) as b:
        checks[f"archive {i} record exact"] = json.loads(a.read("manifest.json"))["record"] == json.loads(b.read("manifest.json"))["record"]
        checks[f"archive {i} raw bytes exact"] = a.read("arrays.npz") == b.read("arrays.npz")
    downloads.append({"original": str(original), "downloaded": str(downloaded), "downloaded_sha256": sha256(downloaded.read_bytes())})
a = normalize({"mode": "load", "yaml": (root / "output/playwright/issue8/used-reset.yaml").read_text(encoding="utf-8")})
b = normalize({"mode": "load", "yaml": (recovery / "used-reset-final.yaml").read_text(encoding="utf-8")})
checks["YAML config exact"] = a["config"] == b["config"]
checks["YAML runtime exact"] = a["runtime_extensions"] == b["runtime_extensions"]
checks["YAML RLM080 and Use provenance"] = b["runtime_extensions"]["values"]["rlm"] == .8 and "eq_application" in b["runtime_extensions"]["values"]
modes = [json.loads(path.read_text(encoding="utf-8")).get("mode") for path in (Path(__file__).parent / "chrome-v3/local/service").glob("*/request.json")]
checks["final Chrome only normalizations"] = bool(modes) and all(mode in ("defaults", "load", "patch") for mode in modes)
report = {"checks": checks, "failed": [key for key, value in checks.items() if not value],
          "production_code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
          "source_copies_sha256": copies, "execution_environment": execution_environment(), "downloads": downloads,
          "final_Chrome_normalization_modes": modes, "new_coopt_calls": 0, "new_main_calls": 0, "new_COM_numeric_calls": 0,
          "scope": "Final management/UI fixes tested by contracts and state replay; historical numerical batches retain their own executed source. No claim of a new final-source numerical batch."}
(out / "report.json").write_bytes(json_bytes(report))
print(json.dumps({"output": str(out), "checks": len(checks), "failed": report["failed"]}))
assert not report["failed"]
