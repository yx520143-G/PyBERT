"""Export existing raw-schema-2 records for browser recovery; no numerical work."""
import json
import zipfile
from pathlib import Path

from pybert.web.optimization import save_optimization
from pybert.web.archive import json_bytes

root = Path(__file__).resolve().parents[5]
batch = root / "docs/webui/issue8/evidence/numerics-20261024-130501"
report = json.loads((batch / "report.json").read_text(encoding="utf-8"))
output = root / "output/playwright/issue8/final"
output.mkdir(exist_ok=True)
for name, case in report["cases"].items():
    save_optimization(batch / "local/adapter" / case["adapter_task"]["task_id"], output / f"{name}.pybert_opt")
with zipfile.ZipFile(output / "O-PAM4-MMSE.pybert_opt") as source:
    envelope = json.loads(source.read("manifest.json"))
    envelope["archive_schema"] = 999
    raw = source.read("arrays.npz")
with zipfile.ZipFile(output / "unknown.pybert_opt", "w") as archive:
    archive.writestr("manifest.json", json_bytes(envelope))
    archive.writestr("arrays.npz", raw)
print(json.dumps({"output": str(output), "new_coopt": 0, "new_main": 0, "new_COM": 0}))
