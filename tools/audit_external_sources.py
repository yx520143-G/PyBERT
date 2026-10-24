"""Read-only byte/AST provenance audit of fixed #16 exports and permutations."""

import ast
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import numpy as np

from external_lane_reference import ISSUE, ROOT, REFS, read_touchstone, sha
from verify_external_lanes import write


def git_blobs(repository, requests):
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=repository,
                            input=("\n".join(requests) + "\n").encode(), capture_output=True, check=True)
    data, offset, blobs = result.stdout, 0, []
    for _ in requests:
        end = data.index(b"\n", offset)
        header = data[offset:end].split()
        assert len(header) == 3 and header[1] == b"blob"
        length = int(header[2])
        blobs.append(data[end + 1:end + 1 + length])
        offset = end + 1 + length + 1
    return blobs


def main():
    specs = [(k, ROOT, v) for k, v in REFS.items()] + [
        ("PyAMI", Path("E:/serial-bus-simulator/PyAMI"), "5270d713e40bac2be5747bef09b92df79df9085b"),
        ("PyChOpMarg", Path("E:/serial-bus-simulator/PyChOpMarg"), "ca905e793fcf6330929471317ca32e7611578e5d")]
    audit = {"Main": 0, "importer": 0, "exports": [], "permutations": [], "AST": {}}
    for label, repository, revision in specs:
        directory = ISSUE / "local/sources" / label
        files = sorted(p for p in directory.rglob("*") if p.is_file())
        blobs = git_blobs(repository, [revision + ":" + p.relative_to(directory).as_posix() for p in files])
        rows = []
        with zipfile.ZipFile(directory.with_suffix(".zip")) as archive:
            for path, original in zip(files, blobs):
                actual = path.read_bytes()
                equal = actual == original
                eol = actual.replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n")
                rows.append({"path": path.relative_to(directory).as_posix(), "actual_sha256": sha(path),
                             "git_blob_sha256": hashlib.sha256(original).hexdigest(), "byte_exact": equal,
                             "only_EOL_difference": not equal and eol,
                             "zip_export_exact": actual == archive.read(path.relative_to(directory).as_posix()),
                             "read_only": not bool(path.stat().st_mode & 0o200)})
        audit["exports"].append({"label": label, "git_revision": revision, "files": rows,
                                 "byte_exact": sum(r["byte_exact"] for r in rows),
                                 "only_EOL_difference": sum(r["only_EOL_difference"] for r in rows),
                                 "unexplained": sum(not (r["byte_exact"] or r["only_EOL_difference"]) for r in rows),
                                 "zip_sha256": sha(directory.with_suffix(".zip"))})
    for resource in json.loads((ISSUE / "resources.json").read_text(encoding="utf-8")):
        f, s, z, _ = read_touchstone(ROOT / resource["original"])
        for variant in resource["variants"]:
            vf, vs, vz, _ = read_touchstone(ROOT / variant["path"])
            mapping = variant["new_to_original_0based"]
            audit["permutations"].append({"resource": resource["id"], "variant": variant["numbering"],
                                         "full_matrix_bitwise_equal": np.array_equal(vs, s[:, mapping][:, :, mapping]),
                                         "frequency_bitwise_equal": np.array_equal(f, vf), "z0_equal": z == vz})
    functions = {}
    for label in REFS:
        path = ISSUE / "local/sources" / label / "src/pybert/utility/sparam.py"
        functions[label] = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef)}
    for name in ("cap_mag", "mon_mag", "sdd_21", "thru_is_1to3", "se2mm", "interp_s2p", "H_2_s2p", "pulse_response", "import_channel", "import_freq", "import_fext"):
        audit["AST"][name] = {"pre_post_equal": functions["pre"][name] == functions["post"][name],
                              "post_final_equal": functions["post"][name] == functions["final"][name]}
    actual_freeze = ISSUE / "freeze-v1.json"
    blob = git_blobs(ROOT, ["f1ddcab05b6fff8493f9a8c860c75b6b05675b8f:docs/webui/issue16/freeze-v1.json"])[0]
    audit["freeze_bytes"] = {"actual_sha256": sha(actual_freeze), "git_LF_sha256": hashlib.sha256(blob).hexdigest(),
                              "byte_exact": actual_freeze.read_bytes() == blob,
                              "EOL_normalized_equal": actual_freeze.read_bytes().replace(b"\r\n", b"\n") == blob.replace(b"\r\n", b"\n")}
    audit["passed_provenance"] = all(r["unexplained"] == 0 and all(f["zip_export_exact"] for f in r["files"]) for r in audit["exports"])
    write(ISSUE / "evidence/source-applicability.json", audit)
    print(json.dumps({"exports": [{k: r[k] for k in ("label", "byte_exact", "only_EOL_difference", "unexplained")} for r in audit["exports"]], "freeze_bytes": audit["freeze_bytes"], "permutations": audit["permutations"]}, indent=2))


if __name__ == "__main__":
    main()
