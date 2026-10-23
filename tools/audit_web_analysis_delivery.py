"""Record source applicability, retained local raw and immutable freeze hashes for delivery."""

import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/webui/issue3"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    report_path = DOC / "evidence/numeric-20261024-061108/report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    freeze = DOC / "fixtures/frozen-manifest.json"
    frozen = json.loads(freeze.read_text(encoding="utf-8"))
    old = ROOT / "docs/webui/issue2/fixtures"
    old_frozen = json.loads((old / "frozen-manifest.json").read_text(encoding="utf-8"))
    checked = {name:digest(old / name) == value for name,value in old_frozen["files"].items()}
    joint = {}
    for name in ("frozen-manifest.json","window-correction-v2.json","identity-effective-v3.json"):
        path = DOC / "fixtures" / name
        blob = subprocess.check_output(["git","show",f"HEAD:{path.relative_to(ROOT).as_posix()}"],cwd=ROOT)
        joint[name] = dict(sha256=digest(path),commit_blob_matches=hashlib.sha256(blob).hexdigest() == digest(path))
    sources = {str(path.relative_to(ROOT)):digest(path) for path in (ROOT / "src/pybert/web").rglob("*")
               if path.suffix in (".py",".js",".css",".html")}
    raw = [dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=digest(path))
           for path in sorted(DOC.rglob("arrays.npz"))]
    (DOC / "evidence/raw-files-local.json").write_text(json.dumps(raw,indent=2),encoding="utf-8")
    screenshots = [dict(path=path.relative_to(DOC).as_posix(),sha256=digest(path),format=Image.open(path).format,
                        pixel_size=list(Image.open(path).size),bytes=path.stat().st_size)
                   for path in sorted((DOC / "evidence/chrome").glob("*.jpg"))]
    tests = {}
    for path in (DOC / "evidence").glob("*.xml"):
        suites = list(ElementTree.parse(path).getroot().iter("testsuite"))
        tests[path.name] = {key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ("tests","failures","errors","skipped")}
    native_changes = subprocess.check_output(["git","diff","--name-only","35a3b60351836431e4f96136b61708515ec5f77c","--",
        "src/pybert/models","src/pybert/utility","src/pybert/pybert.py","src/pybert/gui","src/pybert/cli.py","src/pybert/mcp"],cwd=ROOT,text=True).strip()
    product_commit = subprocess.check_output(["git","log","-1","--format=%H","--","src/pybert/web"],cwd=ROOT,text=True).strip()
    result = dict(product_code_commit=product_commit,joint_freeze=joint,
        issue2_freeze_unchanged=digest(old / "frozen-manifest.json") == frozen["issue2_freeze_sha256"],
        original_ten_file_checks=checked,unchanged_native_sources=not native_changes,web_sources=sources,
        numeric_report=dict(path=report_path.relative_to(ROOT).as_posix(),sha256=digest(report_path),
            execution_sources_match={key:digest(ROOT / key) == value for key,value in report["execution_sources"].items()},
            cases=[dict(fixture=f["fixture"],raw_and_metadata_checks=len(f["raw_checks"]),display_checks=len(f["display_checks"]),
                        max_abs_raw=max(c.get("max_abs") or 0 for c in f["raw_checks"]),
                        max_abs_display=max(c.get("max_abs") or 0 for c in f["display_checks"]),passed=f["passed"]) for f in report["fixtures"]]),
        tests=tests,python=sys.executable,
        modules={name:importlib.import_module(name).__file__ for name in ("pybert.web.analysis","pybert.pybert","pychopmarg","pyibisami","numpy","scipy")},
        raw_local_files=len(raw),raw_local_bytes=sum(r["bytes"] for r in raw),screenshots=screenshots,
        no_additional_main_simulation="Only identity task 80ecab74-7bd7-4cf9-8871-71752657ab2f. Later runs reuse its saved raw. Lifecycle cancellation was before native simulation.")
    assert all(checked.values()) and all(v["commit_blob_matches"] for v in joint.values())
    assert all(result["numeric_report"]["execution_sources_match"].values()) and not native_changes
    (DOC / "evidence/delivery-applicability.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(dict(raw_files=len(raw),raw_bytes=result["raw_local_bytes"],screenshots=len(screenshots),sources_match=True))


if __name__ == "__main__":
    main()
