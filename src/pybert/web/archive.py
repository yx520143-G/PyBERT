"""Versioned, lossless primitive run archives. No engine or resource loading."""

import hashlib
import io
import json
import math
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pybert.web.data import adapter_sha
from pybert.web.clocks import clock_features, validate_clock_arrays

MAX_FILE_BYTES = 256 * 1024**2
MAX_ARRAY_BYTES = 768 * 1024**2
MAX_METADATA_BYTES = 16 * 1024**2
FORMAT = "pybert-web-run"


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")


def read_json(content):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    value = json.loads(content, object_pairs_hook=pairs)
    json_bytes(value)  # Reject nonfinite primitive metadata, including JSON NaN.
    return value


def array_identity(array):
    return {"dtype": array.dtype.str, "shape": list(array.shape), "nbytes": array.nbytes,
            "sha256": sha256(array.tobytes(order="C"))}


def read_arrays(content, *, require_finite=True, run=None):
    """Check NPY headers and byte bounds before NumPy can allocate any arrays."""
    arrays = {}
    masked = bool(clock_features(run)) if run is not None else False
    if masked and not require_finite:
        raise ValueError("AMI masked records require the exact field/mask validation, not a global finite bypass")
    total = 0
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for entry in archive.infolist():
            if not entry.filename.endswith(".npy") or entry.filename[:-4] in arrays:
                raise ValueError("NPZ contains an unknown or duplicate entry.")
            with archive.open(entry) as stream:
                version = np.lib.format.read_magic(stream)
                if version not in ((1, 0), (2, 0)):
                    raise ValueError("Unsupported NPY header version.")
                reader = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                          else np.lib.format.read_array_header_2_0)
                shape, _fortran, dtype = reader(stream)
                if dtype.kind not in "biufc" or any(size < 0 for size in shape):
                    raise ValueError("Only primitive numeric arrays are accepted; object/pickle is forbidden.")
                size = math.prod(shape) * dtype.itemsize
                total += size
                if total > MAX_ARRAY_BYTES or stream.tell() + size != entry.file_size:
                    raise ValueError("Array byte budget or NPY shape/body mismatch.")
            array = np.lib.format.read_array(io.BytesIO(archive.read(entry)), allow_pickle=False)
            if require_finite and not (masked and entry.filename == "ui_ests.npy") and not np.isfinite(array).all():
                raise ValueError(f"Nonfinite array: {entry.filename}")
            arrays[entry.filename[:-4]] = array
    if not arrays:
        raise ValueError("No numerical arrays in this record.")
    if masked:
        validate_clock_arrays(run, arrays)
    return arrays


def validate_run(run, arrays):
    """Validate stored contracts without normalizing inputs or rebuilding plots."""
    if not isinstance(run, dict) or not isinstance(run.get("run_id"), str) or not run["run_id"].strip():
        raise ValueError("Missing/invalid source run_id identity.")
    if run.get("legacy"):
        raise ValueError("Legacy缺少完整原输入和物理轴，无法保存/打开为完整Web archive；请保留原文件与可用sidecar。")
    if (run.get("status") != "succeeded" or type(run.get("raw_schema_version")) is not int
            or run["raw_schema_version"] not in (2, 3, 4, 5, 6, 7)):
        raise ValueError("Unsupported run status/raw schema; no executable defaults substituted.")
    if run["raw_schema_version"] < 5 and "decoding" in run:
        raise ValueError("Decoding requires raw schema 5; older schema cannot bypass its validation.")
    if type(run.get("schema_version")) is not int or run["schema_version"] != 1 or type(run.get("draft_revision")) is not int or run["draft_revision"] < 0:
        raise ValueError("Missing/invalid run schema_version or draft_revision.")
    for name, length in (("input_hash", 64), ("native_sha", 40), ("prototype_sha", 40), ("adapter_sha", 40)):
        value = run.get(name)
        if not isinstance(value, str) or len(value) != length or any(char not in "0123456789abcdefABCDEF" for char in value):
            raise ValueError(f"Missing/invalid run identity metadata: {name}")
    for name in ("requested_input", "effective_input", "summary", "datasets", "plots", "window", "packages"):
        if not isinstance(run.get(name), dict):
            raise ValueError(f"Missing required run metadata: {name}")
    for name in ("resources", "warnings"):
        if not isinstance(run.get(name), list):
            raise ValueError(f"Missing required run metadata: {name}")
    if run["raw_schema_version"] >= 4:
        for name in ("input_identity_hash", "resource_hash"):
            value = run.get(name)
            if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
                raise ValueError(f"Missing/invalid run identity metadata: {name}")
        for name in ("resource_bindings", "runtime_extensions", "execution_strategy"):
            if not isinstance(run.get(name), dict):
                raise ValueError(f"Missing required raw4 metadata: {name}")
    if set(arrays) != set(run["datasets"]):
        raise ValueError("Array/dataset inventory mismatch.")
    clock_features(run)
    validate_clock_arrays(run, arrays)
    for key, array in arrays.items():
        dataset = run["datasets"][key]
        required = ("dtype", "shape", "producer", "unit", "window", "clock_basis", "availability")
        if any(field not in dataset for field in required):
            raise ValueError(f"{key}: incomplete dataset contract.")
        if list(array.shape) != dataset["shape"] or np.dtype(dataset["dtype"]) != array.dtype:
            raise ValueError(f"{key}: dtype/shape mismatch.")
        axis = dataset.get("axis")
        if axis and (axis not in arrays or array.ndim == 0 or len(arrays[axis]) != len(array)):
            raise ValueError(f"{key}: missing or mismatched dataset axis.")
    for plot in run["plots"].values():
        for trace in plot.get("traces", []):
            if any(trace.get(field) not in arrays for field in ("x", "y")):
                raise ValueError("Plot references absent data.")
            if len(arrays[trace["x"]]) != len(arrays[trace["y"]]):
                raise ValueError("Plot axes have different lengths.")
        heatmap = plot.get("heatmap")
        if heatmap:
            if any(heatmap.get(field) not in arrays for field in ("x", "y", "z")):
                raise ValueError("Heatmap references absent data.")
            if arrays[heatmap["z"]].shape != (len(arrays[heatmap["y"]]), len(arrays[heatmap["x"]])):
                raise ValueError("Heatmap grid mismatch.")
    if run["raw_schema_version"] >= 5:
        from pybert.web.viterbi import validate

        validate(run, arrays)
    if run["raw_schema_version"] == 7:
        from pybert.web.clock_v3 import validate_publication

        validate_publication(run, arrays)
    return sum(array.nbytes for array in arrays.values())


def atomic_write(path, content):
    """Publish a complete generated file; failure keeps any previous file intact."""
    path = Path(path)
    descriptor, name = tempfile.mkstemp(prefix=".publishing-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def save_archive(directory, destination, subfunctions=None):
    directory = Path(directory)
    raw = (directory / "arrays.npz").read_bytes()
    source = (directory / "manifest.json").read_bytes()
    run = read_json(source)
    features = clock_features(run)
    arrays = read_arrays(raw, run=run)
    validate_run(run, arrays)
    manifest = {
        "format": FORMAT, "archive_schema": 1, "required_features": features,
        "saved_at": datetime.now(timezone.utc).isoformat(), "saved_by_adapter_sha": adapter_sha(),
        "source_files": {"manifest.json": sha256(source), "arrays.npz": sha256(raw)},
        "source_manifest_utf8": source.decode("utf-8"),
        "arrays": {key: array_identity(value) for key, value in arrays.items()},
        "run": run, "subfunctions": subfunctions or {},
        "resource_policy": "references and content hashes only; bytes not embedded; paths are hints",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", json_bytes(manifest))
        archive.writestr("arrays.npz", raw)
    if buffer.tell() > MAX_FILE_BYTES:
        raise ValueError("Archive exceeds 256 MiB; no file published.")
    atomic_write(destination, buffer.getvalue())
    return manifest


def load_archive(content, directory):
    """Stage a fully validated archive; callers publish its record atomically."""
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Archive exceeds 256 MiB.")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) != 2 or {entry.filename for entry in entries} != {"manifest.json", "arrays.npz"}:
                raise ValueError("Archive must contain exactly manifest.json and arrays.npz.")
            limits = {"manifest.json": MAX_METADATA_BYTES, "arrays.npz": MAX_FILE_BYTES}
            if any(entry.file_size > limits[entry.filename] for entry in entries):
                raise ValueError("Archive member exceeds its byte budget.")
            manifest = read_json(archive.read("manifest.json"))
            raw = archive.read("arrays.npz")
        if manifest.get("format") != FORMAT or manifest.get("archive_schema") != 1:
            raise ValueError("Unknown archive format/version; existing records retained.")
        clock_features(manifest["run"], manifest.get("required_features", []))
        if sha256(raw) != manifest["source_files"]["arrays.npz"]:
            raise ValueError("Archive NPZ checksum mismatch.")
        original = manifest["source_manifest_utf8"].encode("utf-8")
        if sha256(original) != manifest["source_files"]["manifest.json"] or read_json(original) != manifest["run"]:
            raise ValueError("Archive source manifest checksum/content mismatch.")
        arrays = read_arrays(raw, run=manifest["run"])
        if {key: array_identity(value) for key, value in arrays.items()} != manifest["arrays"]:
            raise ValueError("Archive array dtype/shape/bytes checksum mismatch.")
        size = validate_run(manifest["run"], arrays)
        directory = Path(directory)
        atomic_write(directory / "manifest.json", original)
        atomic_write(directory / "arrays.npz", raw)
        atomic_write(directory / "archive.json", json_bytes(manifest))
        return manifest["run"], size
    except (zipfile.BadZipFile, KeyError, TypeError, AttributeError, IndexError, EOFError, UnicodeError, OverflowError, RecursionError) as err:
        raise ValueError(f"Invalid archive: {err}") from err
