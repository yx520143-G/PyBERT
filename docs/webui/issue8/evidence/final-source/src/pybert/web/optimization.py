"""Bounded native coopt adapter. Candidates never mutate an editable draft or a Run."""

import io
import importlib.metadata
import os
import math
import sys
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from pybert.gui.handler import MyHandler
from pybert.utility import safe_log10
from pybert.threads.optimization import (
    MMSE_TX_LEVEL_V, MMSE_TX_SNR_DB, MMSE_DJ_DUAL_DIRAC_UI, MMSE_RJ_RMS_UI,
    OptThread, coopt, mk_tap_weight_combs,
)
from pybert.web.archive import (
    MAX_ARRAY_BYTES, MAX_FILE_BYTES, MAX_METADATA_BYTES, array_identity, atomic_write,
    json_bytes, read_arrays, read_json, sha256,
)
from pybert.web.config import extensions, input_hash, load_config, new_engine, snapshot, validate
from pybert.web.data import adapter_sha, source_identity
from pybert.web.resources import inspect_channels, projection

MAX_OUTER = 256
MAX_INNER = 256
MAX_EVALUATIONS = 4096


class NativeObservations(dict):
    """Bound retained observation arrays, including their exported pulse axes."""

    def __init__(self, reserved_bytes):
        super().__init__()
        self.used = reserved_bytes

    def charge(self, values, axis=False):
        size = sum(value.nbytes for value in values.values() if isinstance(value, np.ndarray))
        if axis:
            size += values["pulse"].nbytes
        if self.used + size > MAX_ARRAY_BYTES:
            raise ValueError("Native observation storage budget exceeded; partial observations retained.")
        self.used += size

    def update(self, **values):
        owner = self

        class Rows(list):
            def __init__(self, axis):
                super().__init__()
                self.axis = axis

            def append(self, row):
                owner.charge(row, self.axis)
                super().append(row)

        self.charge(values["mmse_context"])
        super().update(values | {"candidates": Rows(True), "mmse_calls": Rows(False)})


class OptimizationCancelled(RuntimeError):
    """Raised only by the original OptThread.stopped checkpoint bridge."""


class CancelBridge(OptThread):
    def __init__(self, check):
        super().__init__()
        self.check = check

    def stopped(self):
        if self.check():
            raise OptimizationCancelled("Native optimization checkpoint observed cancellation.")
        return False


def _range_count(lo, hi, step, field):
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (lo, hi, step)) or lo > hi or step <= 0:
        raise ValueError(f"{field}: finite min<=max and step>0 required.")
    # The native arange may include a final value above max. Match that producer exactly.
    count = math.ceil((hi + step - lo) / step)
    if count > MAX_EVALUATIONS:
        raise ValueError(f"{field}: native enumeration exceeds {MAX_EVALUATIONS} values; budget refused.")
    return len(np.arange(lo, hi + step, step))


def preflight(p):
    c = snapshot(p)
    validate(c | {"enable_com": False}, snapshot(new_engine()), execution=True)
    if c["mod_type"] not in ("NRZ", "PAM-4"):
        raise ValueError("Native optimization supports NRZ/PAM4 in #8; Duo-binary is unavailable here.")
    if c["rx_n_taps"] < 1:
        raise ValueError("rx_n_taps: optimizer requires at least one Rx FFE tap.")
    # Bound the original producer grids before their cached properties allocate them.
    time_samples = p.nui * p.nspui
    frequency_samples = math.ceil((p.f_max * 1e9 + p.f_step * 1e6) / (p.f_step * 1e6))
    mmse_samples = math.ceil((.5 / (p.ui / p.nspui)) / 100e6 + .5)
    if time_samples > 2_000_000 or frequency_samples > 200_001 or mmse_samples > 200_001:
        raise ValueError(f"Optimization grid budget refused: time={time_samples}/2000000, channel frequency={frequency_samples}/200001, MMSE frequency={mmse_samples}/200001; inputs unchanged.")
    if not 0 < p.rlm <= 1:
        raise ValueError("rlm: optimizer requires 0 < RLM <= 1.")
    for field in ("rx_bw_tune", "peak_freq_tune"):
        if c[field] <= 0:
            raise ValueError(f"{field}: must be positive GHz.")
    rows = c["dfe_tap_tuners"]
    prefix = next((i for i, row in enumerate(rows) if not row[0]), len(rows))
    if any(row[0] for row in rows[prefix:]):
        raise ValueError("dfe_tap_tuners: enabled rows must be a continuous prefix; gap rows are not consumed by native coopt.")
    if any(row[0] != (i < c["rx_n_taps"]) for i, row in enumerate(c["ffe_tap_tuners"])):
        raise ValueError("ffe_tap_tuners.enabled: must match the native Ntaps/Npre mapping.")
    counts = {}
    for key in ("tx_tap_tuners", "ffe_tap_tuners"):
        count = 1
        for i, row in enumerate(c[key]):
            if row[0] and not (key == "ffe_tap_tuners" and c["use_mmse"]):
                count *= _range_count(*row[2:5], f"{key}[{i}]")
            if count > MAX_EVALUATIONS:
                raise ValueError(f"{key}: {count} combinations exceeds budget before allocation.")
        counts[key] = count
    peaks = _range_count(c["min_mag_tune"], c["max_mag_tune"], c["step_mag_tune"], "CTLE boost") if c["ctle_enable_tune"] else 1
    # MMSE uses FFE bounds, not the grid steps; do not charge an unused grid.
    inner = 1 if c["use_mmse"] else counts["ffe_tap_tuners"]
    upper = peaks * counts["tx_tap_tuners"]
    if upper > MAX_OUTER or inner > MAX_INNER or upper * inner > MAX_EVALUATIONS:
        raise ValueError(f"Optimization budget refused: outer<={upper}/{MAX_OUTER}, inner<={inner}/{MAX_INNER}, total<={upper*inner}/{MAX_EVALUATIONS}; ranges unchanged.")
    # Bound every exported float64/complex128 array, including all actual MMSE inputs.
    pulse_samples = max(2 * mmse_samples, p.nspui * 105) + 100 * p.nspui
    reserved_bytes = 16 * time_samples + 24 * pulse_samples + 8 * (6 + 100 + 20 + 4)
    context_bytes = 8 * (3 * mmse_samples + 40)
    per_candidate = 16 * pulse_samples + 8 * (6 + 100 + 20)
    if c["use_mmse"]:
        per_candidate += 64 * mmse_samples + 16 * 100  # p_tx, three H, Rx bounds
    estimated_bytes = reserved_bytes + context_bytes + upper * per_candidate
    if estimated_bytes > MAX_ARRAY_BYTES:
        raise ValueError(f"Optimization candidate storage budget refused: conservative estimate {estimated_bytes}/{MAX_ARRAY_BYTES} bytes; ranges unchanged.")
    tx = mk_tap_weight_combs(p.tx_tap_tuners)
    tx = [w for w in tx if 1 - sum(abs(w)) > 0 and 1 - sum(abs(w)) >= max(0, p.tx_c0_min)]
    peak_values = np.arange(c["min_mag_tune"], c["max_mag_tune"] + c["step_mag_tune"], c["step_mag_tune"]) if c["ctle_enable_tune"] else [0.]
    order = [{"candidate_id": f"candidate-{i:06d}", "ctle_db": float(mag), "tx_weights": w.tolist()}
             for i, (mag, w) in enumerate((m, w) for m in peak_values for w in tx)]
    # Let the native no-Tx-combination RuntimeError execute, preserving its real failure.
    rx = [] if c["use_mmse"] else mk_tap_weight_combs(p.ffe_tap_tuners)
    if not c["use_mmse"] and not rx:
        raise ValueError("Rx FFE grid has no nonzero candidate; native implicit identity fallback is unavailable for a bounded search.")
    return {"outer_count": len(order), "rx_inner_count": None if c["use_mmse"] else len(rx) or 1,
            "outer_order": order, "rx_inner_order": [w.tolist() for w in rx], "dfe_prefix": prefix,
            "estimated_candidate_bytes_upper": estimated_bytes,
            "reserved_export_bytes_upper": reserved_bytes,
            "limits": {"max_outer": MAX_OUTER, "max_inner": MAX_INNER, "max_evaluations": MAX_EVALUATIONS,
                       "max_time_samples": 2_000_000, "max_frequency_samples": 200_001, "max_array_bytes": MAX_ARRAY_BYTES}}


def prepare(request):
    p = new_engine()
    config = request["config"]
    if input_hash(config) != request["input_hash"]:
        raise ValueError("Optimization input hash mismatch.")
    identity = input_hash({key: request.get(key, {}) for key in ("config", "runtime_extensions", "resource_bindings")})
    if request.get("input_identity_hash") != identity:
        raise ValueError("Optimization full input identity hash mismatch.")
    load_config(p, config)
    if snapshot(p) != config:
        raise ValueError("Optimization requires the complete normalized effective input.")
    runtime = extensions(request.get("runtime_extensions", {}))
    if "rlm" not in runtime.get("values", {}):
        raise ValueError("Explicit frozen runtime_extensions.values.rlm is required; no native default substituted.")
    p.rlm = runtime["values"]["rlm"]
    initial = runtime["values"].get("optimizer_values", {})
    for key, taps in (("tx", p.tx_tap_tuners), ("ffe", p.ffe_tap_tuners)):
        for tap, value in zip(taps, initial.get(key, [])):
            tap.value = value
    return p


def handler_patch(p, result=None):
    """Run the original Native handler on the private context; return only its actual changes."""
    before = snapshot(p)
    if result is None:
        MyHandler().do_reset_eq(SimpleNamespace(object=p))
    else:
        for tap, value in zip(p.tx_tap_tuners, result[0]):
            tap.value = float(value)
        p.peak_mag_tune = float(result[1])
        for tap, value in zip(p.ffe_tap_tuners, result[2]):
            tap.value = float(value)
        MyHandler().do_use_eq(SimpleNamespace(object=p))
    after = snapshot(p)
    return {key: value for key, value in after.items() if value != before[key]}


def optimizer_action(p, runtime, mode, candidate=None):
    runtime = read_json(json_bytes(runtime))
    if mode == "optimizer_plan":
        p.rlm = runtime.get("values", {}).get("rlm", p.rlm)
        return runtime, {"optimization_plan": preflight(p)}
    if mode == "reset_eq":
        handler_patch(p)
        runtime.setdefault("version", 1)
        runtime.setdefault("values", {})["optimizer_values"] = {
            "tx": [t.value for t in p.tx_tap_tuners], "ffe": [t.value for t in p.ffe_tap_tuners]}
        return runtime, {"action": "native MyHandler.do_reset_eq", "DFE_weights_applied": False}
    if not candidate or candidate.get("status") != "succeeded":
        raise ValueError("Use EQ requires a completed successful optimization record.")
    frozen = prepare(candidate | {"config": candidate["requested_input"]})
    result = candidate["selected_values"]
    for current, source, value in zip(p.tx_tap_tuners, frozen.tx_tap_tuners, result["tx"]):
        current.enabled, current.value = source.enabled, value
    for i, (current, source) in enumerate(zip(p.ffe_tap_tuners, frozen.ffe_tap_tuners)):
        current.enabled = source.enabled
        current.value = result["ffe"][i] if i < len(result["ffe"]) else source.value
    for key in ("peak_freq_tune", "rx_bw_tune", "ctle_enable_tune"):
        setattr(p, key, getattr(frozen, key))
    p.peak_mag_tune = result["ctle_db"]
    # Restore current optimizer constraints after applying. Use EQ only writes actual EQ fields.
    MyHandler().do_use_eq(SimpleNamespace(object=p))
    actual = snapshot(p)
    targets = {key: actual[key] for key in ("tx_taps", "rx_taps", "peak_freq", "peak_mag", "rx_bw", "ctle_enable")}
    load_config(p, candidate["current_config"] | targets)
    runtime.setdefault("version", 1)
    runtime.setdefault("values", {})["eq_application"] = {"version": 1, "opt_id": candidate["opt_id"],
        "candidate_id": candidate["selected_candidate_id"], "before_input_hash": input_hash(candidate["current_config"]),
        "after_input_hash": input_hash(snapshot(p))}
    return runtime, {"action": "native MyHandler.do_use_eq", "source_opt_id": candidate["opt_id"],
                     "candidate_id": candidate["selected_candidate_id"], "applied_fields": list(targets),
                     "DFE_weights_applied": False, "before": {k: candidate["current_config"][k] for k in targets},
                     "after": targets}


def run_optimization(opt_id, request, directory, check, emit):
    directory = Path(directory)
    started = time.time()
    record = {"schema_version": 1, "optimization_raw_schema": 2, "opt_id": opt_id, "status": "failed", "draft_revision": request.get("draft_revision", 0),
              "requested_input": request["config"], "runtime_extensions": request.get("runtime_extensions", {}),
              "resource_bindings": request.get("resource_bindings", {}), "input_hash": request["input_hash"],
              "input_identity_hash": request.get("input_identity_hash"), "resource_hash": request["resource_hash"],
              "resources": request.get("frozen_resources", []), "adapter_sha": adapter_sha(),
              "producer": "pybert.threads.optimization.coopt (Native)", "started_at": started,
              "source_identity": source_identity(),
              "execution_environment": execution_environment(),
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "model": {"bounded_ideal_DFE": True, "MMSE_TX_LEVEL_V": MMSE_TX_LEVEL_V, "MMSE_TX_SNR_DB": MMSE_TX_SNR_DB,
                        "MMSE_DJ_UI": MMSE_DJ_DUAL_DIRAC_UI, "MMSE_RJ_UI": MMSE_RJ_RMS_UI, "aggressors": [],
                        "noise_boundary": "rn enters eta0; fixed Tx/SNR/jitter and empty aggressors differ from full Run/COM",
                        "pulse": "optimization model; MMSE cursor=1 equivalent pulse, not dfe_out/CDR/BER/standard COM"}}
    observations = {}
    arrays = {}
    try:
        p = prepare(request)
        p.observe(lambda e: emit("phase", phase=str(e.new)), "status")
        p.observe(lambda e: emit("log", text=e.new[len(e.old):].rstrip()), "console_log")
        plan = preflight(p)
        observations = NativeObservations(plan["reserved_export_bytes_upper"])
        record.update(plan=plan, effective_input=snapshot(p), score_mode="MMSE" if p.use_mmse else "cursor/ISI grid")
        record["resources"] = inspect_channels(request["config"], request.get("frozen_resources", []))
        projected = projection(request["config"], request.get("frozen_resources", []))
        p.trait_setq(ch_file=projected["ch_file"], ch_files=projected["ch_files"], enable_com=False)
        p.opt_thread = CancelBridge(check)  # Instance(OptThread), never start a second numerical thread.
        emit("phase", phase=f"native coopt; {plan['outer_count']} outer candidates; inner {plan['rx_inner_count']}")
        result = coopt(p, observations=observations)
        tx, peak, rx, fom, valid, _, _ = result
        rows = observations.get("candidates", [])
        if not valid or not rows or not math.isfinite(fom) or fom <= 0 or fom == -1000:
            raise ValueError("Native coopt returned no finite positive valid winner (including -1000 sentinel).")
        eligible = [row for row in rows if math.isfinite(row["fom"]) and row["fom"] > -1000]
        winner = max(eligible, key=lambda row: row["fom"])
        if (float(fom) != winner["fom"] or list(tx) != winner["tx_weights"].tolist() or
                list(rx) != winner["rx_weights"].tolist() or float(peak) != winner["peak_mag"]):
            raise ValueError("Native return and selected candidate identity disagree.")
        for key in ("ctle_out_h_tune", "t_ns_opt", "curs_ix", "curs_amp", "clocks_tune", "p_chnl"):
            arrays[key] = np.asarray(p.plotdata.get_data(key))
        arrays["channel_t_ns"] = p.t_ns[:len(arrays["p_chnl"])]
        arrays["tx_weights"] = np.asarray(tx)
        arrays["rx_weights"] = np.asarray(rx)
        arrays["dfe_weights"] = np.asarray([t.value for t in p.dfe_tap_tuners])
        if len(arrays["t_ns_opt"]) != len(arrays["ctle_out_h_tune"]) or len(arrays["channel_t_ns"]) != len(arrays["p_chnl"]):
            raise ValueError("Native pulse axis length mismatch; no truncated success published.")
        record["use_patch"] = handler_patch(p, result)
        record.update(status="succeeded", selected_candidate_id=f"candidate-{winner['index']:06d}", fom=float(fom),
                      display_db=float(20 * safe_log10(fom)), candidates=[],
                      selected_values={"tx": list(map(float, tx)), "ffe": list(map(float, rx)),
                                       "dfe": [float(t.value) for t in p.dfe_tap_tuners], "ctle_db": float(peak)})
    except Exception as err:
        record.update(status="cancelled" if isinstance(err, OptimizationCancelled) else "failed", error=str(err), error_type=type(err).__name__)
        raise
    finally:
        for row in observations.get("candidates", []):
            prefix = f"candidate_{row['index']:06d}"
            for key in ("pulse", "tx_weights", "rx_weights", "dfe_weights"):
                arrays[f"{prefix}_{key}"] = np.asarray(row[key])
            arrays[f"{prefix}_t_ns"] = p.t_ns[:len(row["pulse"])]
            score = row["fom"]
            record.setdefault("candidates", []).append({"candidate_id": f"candidate-{row['index']:06d}",
                "fom": score if math.isfinite(score) else None, "ctle_db": row["peak_mag"], "arrays_prefix": prefix,
                "availability": "available" if math.isfinite(score) and score > -1000 and all(np.isfinite(row[k]).all() for k in ("pulse", "tx_weights", "rx_weights", "dfe_weights")) else "invalid native candidate"})
        context = observations.get("mmse_context", {})
        record["mmse_context"] = {key: value for key, value in context.items() if not isinstance(value, np.ndarray)}
        for key, value in context.items():
            if isinstance(value, np.ndarray):
                arrays[f"mmse_{key}"] = value
        record["mmse_calls"] = []
        for i, call in enumerate(observations.get("mmse_calls", [])):
            prefix = f"mmse_call_{i:06d}"
            values = {}
            parameters = {key: value for key, value in call.items() if not isinstance(value, np.ndarray) and key != "result_cursor_ix"}
            parameters.update(record["mmse_context"])
            for key, value in call.items():
                if isinstance(value, np.ndarray):
                    arrays[f"{prefix}_{key}"] = value
                    values[key] = array_identity(value)
            for key in ("f_hz", "t_s", "dfe_min", "dfe_max"):
                values[key] = array_identity(arrays[f"mmse_{key}"])
            record["mmse_calls"].append({"candidate_id": f"candidate-{i:06d}", "parameters": parameters,
                "result_cursor_ix": call.get("result_cursor_ix"),
                "arrays_prefix": prefix, "input_hash": input_hash({"arrays": values, "parameters": parameters, "model": record["model"]})})
        record["finished_at"] = time.time()
        record["elapsed_s"] = record["finished_at"] - started
        record["arrays"] = {key: array_identity(value) for key, value in arrays.items()}
        record["array_contracts"] = {key: {"producer": record["producer"], "unit": (
            "ns" if key in ("t_ns_opt", "curs_ix", "channel_t_ns") or key.endswith("_t_ns") else
            "Hz" if key == "mmse_f_hz" else "s" if key == "mmse_t_s" else
            "V (native model; MMSE cursor normalized)" if key in ("ctle_out_h_tune", "p_chnl", "curs_amp", "clocks_tune") or key.endswith(("_pulse", "_p_tx")) else "1"),
            "clock_basis": "optimizer sampling / equivalent pulse; not recovered CDR", "window": "entire producer array"} for key in arrays}
        record["nonfinite_arrays"] = {key: int(np.count_nonzero(~np.isfinite(value))) for key, value in arrays.items() if not np.isfinite(value).all()}
        if record["status"] == "succeeded" and (sum(a.nbytes for a in arrays.values()) > MAX_ARRAY_BYTES or any(not np.isfinite(a).all() for a in arrays.values())):
            record.update(status="failed", error="Nonfinite or over-budget native arrays; candidate unavailable.")
        np.savez_compressed(directory / "arrays.npz", **arrays)
        (directory / "optimization.json").write_bytes(json_bytes(record))
    if record["status"] != "succeeded":
        raise ValueError(record["error"])
    return {"opt_id": opt_id, "selected_candidate_id": record["selected_candidate_id"]}


def execution_environment():
    import pybert
    import pychopmarg
    import pyibisami

    packages = (pybert, pychopmarg, pyibisami)
    modules = {m.__name__: m.__file__ for m in packages}
    sources = {str(path): sha256(path.read_bytes()) for module in packages for path in Path(module.__file__).parent.rglob("*.py")}
    return {"python": sys.executable, "PYTHONPATH": os.environ.get("PYTHONPATH"), "modules": modules,
            "python_source_sha256": sources}


def save_optimization(directory, destination):
    directory = Path(directory)
    record = read_json((directory / "optimization.json").read_bytes())
    raw = (directory / "arrays.npz").read_bytes()
    validate_record(record, read_arrays(raw, require_finite=record.get("status") == "succeeded") if record.get("arrays") else {})
    envelope = {"format": "pybert-web-optimization", "archive_schema": 1, "required_features": [], "record": record, "raw_sha256": sha256(raw)}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", json_bytes(envelope))
        archive.writestr("arrays.npz", raw)
    if buffer.tell() > MAX_FILE_BYTES:
        raise ValueError("Optimization archive exceeds 256 MiB.")
    atomic_write(destination, buffer.getvalue())


def load_optimization(content, directory):
    try:
        return _load_optimization(content, directory)
    except (zipfile.BadZipFile, KeyError, TypeError, AttributeError, IndexError, EOFError, UnicodeError, OverflowError) as err:
        raise ValueError(f"Invalid optimization archive: {err}") from err


def _load_optimization(content, directory):
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("Optimization archive exceeds 256 MiB.")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) != 2 or {e.filename for e in entries} != {"manifest.json", "arrays.npz"} or any(e.file_size > (MAX_METADATA_BYTES if e.filename == "manifest.json" else MAX_FILE_BYTES) for e in entries):
            raise ValueError("Invalid optimization archive members/budget.")
        envelope = read_json(archive.read("manifest.json"))
        raw = archive.read("arrays.npz")
    if envelope.get("format") != "pybert-web-optimization" or type(envelope.get("archive_schema")) is not int or envelope["archive_schema"] != 1 or sha256(raw) != envelope.get("raw_sha256"):
        raise ValueError("Unknown optimization archive/checksum mismatch.")
    if envelope.get("required_features"):
        raise ValueError("Unknown required optimization archive features.")
    record = envelope["record"]
    arrays = read_arrays(raw, require_finite=record.get("status") == "succeeded") if record.get("arrays") else {}
    validate_record(record, arrays)
    # No observer/native operation during archive read. Use revalidates in the serial worker.
    atomic_write(Path(directory) / "optimization.json", json_bytes(record))
    atomic_write(Path(directory) / "arrays.npz", raw)
    return record


def validate_record(record, arrays):
    if type(record.get("optimization_raw_schema", 1)) is not int or record.get("optimization_raw_schema", 1) not in (1, 2):
        raise ValueError("Unknown optimization raw schema.")
    if (type(record.get("schema_version")) is not int or record["schema_version"] != 1 or record.get("status") not in ("succeeded", "failed", "cancelled") or
            not isinstance(record.get("opt_id"), str) or {k: array_identity(a) for k, a in arrays.items()} != record.get("arrays")):
        raise ValueError("Invalid optimization record/arrays.")
    if input_hash(record["requested_input"]) != record.get("input_hash") or input_hash({
            "config": record["requested_input"], "runtime_extensions": record["runtime_extensions"],
            "resource_bindings": record["resource_bindings"]}) != record.get("input_identity_hash"):
        raise ValueError("Optimization archive input hash mismatch.")
    extensions(record["runtime_extensions"])
    if record["status"] != "succeeded":
        return
    for key in ("effective_input", "source_identity", "packages", "plan", "model"):
        if not isinstance(record.get(key), dict):
            raise ValueError(f"Missing optimization metadata: {key}")
    if record["effective_input"] != record["requested_input"] or not isinstance(record.get("adapter_sha"), str) or len(record["adapter_sha"]) != 40:
        raise ValueError("Optimization effective input/source version mismatch.")
    rows = record["candidates"]
    if not rows or len({r["candidate_id"] for r in rows}) != len(rows):
        raise ValueError("Missing/duplicate optimization candidates.")
    winner = next((r for r in rows if r["candidate_id"] == record.get("selected_candidate_id")), None)
    if not winner or winner["availability"] != "available" or not math.isfinite(record["fom"]) or record["fom"] <= 0 or winner["fom"] != record["fom"]:
        raise ValueError("Invalid optimization winner.")
    for row in rows:
        prefix = row["arrays_prefix"]
        if len(arrays[prefix + "_pulse"]) != len(arrays[prefix + "_t_ns"]):
            raise ValueError("Candidate pulse/axis mismatch.")
    if len(arrays["p_chnl"]) != len(arrays["channel_t_ns"]) or len(arrays["ctle_out_h_tune"]) != len(arrays["t_ns_opt"]) or len(arrays["clocks_tune"]) != len(arrays["t_ns_opt"]):
        raise ValueError("Selected pulse/channel/clocks axis mismatch.")
    values = record["selected_values"]
    prefix = winner["arrays_prefix"]
    expected_rx = record["requested_input"]["rx_n_taps"] if record["requested_input"]["use_mmse"] else 100
    if (len(values["tx"]) != 6 or len(values["ffe"]) != expected_rx or
            not np.array_equal(values["tx"], arrays[prefix + "_tx_weights"]) or
            not np.array_equal(values["ffe"], arrays[prefix + "_rx_weights"]) or values["ctle_db"] != winner["ctle_db"] or
            not np.array_equal(arrays["ctle_out_h_tune"], arrays[prefix + "_pulse"])):
        raise ValueError("Selected optimization values/response disagree with native candidate arrays.")
    if record.get("optimization_raw_schema") == 2 and record["requested_input"]["use_mmse"]:
        calls = record.get("mmse_calls", [])
        if len(calls) != len(rows):
            raise ValueError("Incomplete actual MMSE input contexts.")
        for call in calls:
            prefix = call["arrays_prefix"]
            identities = {key: array_identity(arrays[f"{prefix}_{key}"]) for key in ("p_tx", "tx_H", "chnl_H", "ctle_H", "rx_min", "rx_max")}
            identities.update({key: array_identity(arrays[f"mmse_{key}"]) for key in ("f_hz", "t_s", "dfe_min", "dfe_max")})
            if (call["parameters"]["rlm"] != record["runtime_extensions"]["values"]["rlm"] or
                    input_hash({"arrays": identities, "parameters": call["parameters"], "model": record["model"]}) != call["input_hash"]):
                raise ValueError("MMSE actual input context/hash mismatch.")
