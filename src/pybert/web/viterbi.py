"""Bounded Native ISI decoding records and read-only trellis views."""

import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np

MAX_STATES = 256
MAX_STATE_SAMPLES = 2_000_000
MAX_DENSE_WORK = 25_000_000
MAX_TIME_SAMPLES = 2_000_000
TRELLIS_FIELDS = ("trellis_x", "trellis_y", "trellis_path_xs", "trellis_path_ys",
                  "trellis_state1_ys", "trellis_state2_ys", "trellis_state3_ys",
                  "trellis_state1_probs", "trellis_state2_probs", "trellis_state3_probs",
                  "trellis_err_xs", "trellis_err_ys")
BER_ARRAYS = ("bits_out", "bits_test", "bits_reference", "auto_corr", "errors")
ISI_ARRAYS = ("sample_times", "sample_indices", "sigma", "decision_scaler", "ui", "ts", "nspui", "N", "L",
              "clk_phase_ix", "pulse_resp_curs_ix", "pulse_peak_ix", "decided_levels")
DEBUG_ARRAYS = ("sig_samps", "pulse_resp_samps", "probs", "prevs", "path", "symbols_viterbi", "symbols_dfe")



def plan(config, *, execution=False):
    """Bound the existing dense decoder; never change N or the analysis window."""
    counts = {}
    for key in ("rx_viterbi_symbols", "nbits", "eye_bits", "nspui"):
        value = config.get(key)
        if (type(value) not in (int, float) or type(value) is float and not math.isfinite(value)
                or int(value) != value or value < 1):
            raise ValueError(f"{key}: positive finite integer required.")
        counts[key] = int(value)
    n = counts["rx_viterbi_symbols"]
    alphabets = {"NRZ": 2, "PAM-4": 4, "Duo-binary": 3}
    if config.get("mod_type") not in alphabets:
        raise ValueError("Unsupported Native ISI modulation.")
    levels = alphabets[config["mod_type"]]
    samples = counts["eye_bits"] // (2 if levels == 4 else 1)
    # Avoid constructing an unbounded integer for an untrusted depth.
    states = levels ** int(n) if n <= 16 else None
    row = {"N": int(n), "L": levels, "states": states, "samples_upper_bound": samples,
           "max_states": MAX_STATES, "max_state_samples": MAX_STATE_SAMPLES,
           "max_dense_work": MAX_DENSE_WORK, "max_time_samples": MAX_TIME_SAMPLES}
    if not config["rx_use_viterbi"]:
        return {**row, "availability": "disabled"}
    reason = None
    if states is None or states > MAX_STATES:
        reason = "state count exceeds 256"
    elif samples * states > MAX_STATE_SAMPLES or samples * states * states > MAX_DENSE_WORK:
        reason = "full sample/state dense-work budget exceeded"
    elif counts["nbits"] // (2 if levels == 4 else 1) * counts["nspui"] > MAX_TIME_SAMPLES:
        reason = "native time grid exceeds 2,000,000 samples"
    elif samples < max(2, n):
        reason = "insufficient full analysis samples for native decoder/trellis"
    elif states < 3:
        reason = "native trellis producer requires at least three states"
    if reason and execution:
        raise ValueError(f"viterbi_budget_or_native_limit: {reason}; input retained, no reduction/fallback.")
    return {**row, "availability": "blocked" if reason else "available", "reason": reason}


def extend(engine, captured, arrays, manifest):
    """Collect original outputs and run the original producer against a private sink."""
    from chaco.api import ArrayPlotData
    from pybert.models.bert import update_trellis

    config = manifest["effective_input"]
    enabled = config["rx_use_viterbi"]
    record = {"schema_version": 1, "availability": "available" if enabled else "disabled",
              "reason": None if enabled else "Use Viterbi was disabled for this run; -1 means not calculated",
              "plan": plan(config, execution=True), "ber": {}, "producer": "models.bert / models.viterbi",
              "probability": "native raw state probability, dimensionless; not BER",
              "display": {"initial_symbols": 10, "log10_floor": -20, "raw_unchanged": True}}
    datasets = manifest["datasets"]

    def add(key, value, unit="1", axis=None, window=None, producer="my_run_simulation decoding locals"):
        arr = np.asarray(value)
        if arr.dtype.kind not in "biufc" or not np.isfinite(arr).all():
            raise ValueError(f"{key}: incomplete/nonfinite native decoding output")
        arrays[key] = arr
        datasets[key] = dict(field=key, producer=producer, point="viterbi", kind="raw", dtype=str(arr.dtype),
                             shape=list(arr.shape), unit=unit, axis=axis, window=window or manifest["window"],
                             clock_basis="recovered clock_times / original calc_ber", display_noise=False,
                             availability="available")

    for name in ("dfe", "viterbi"):
        if name not in captured:
            if name == "dfe" or enabled:
                raise ValueError(f"{name}: original BER alignment was not captured")
            record["ber"][name] = {"availability": "disabled", "count": -1}
            continue
        row = captured[name]
        meta = {key: int(value) for key, value in row.items() if key not in BER_ARRAYS}
        window = {"kind": "calc_ber tail", **meta, "indices": "errors relative to test bit window"}
        record["ber"][name] = {"availability": "available", **meta}
        for key in BER_ARRAYS:
            add(f"ber.{name}.{key}", row[key], "bit index" if key == "errors" else "1", window=window,
                producer=f"my_run_simulation.calc_ber({name}) at original call")
    if enabled:
        local = captured["isi"]
        debug = engine.dbg_dict_viterbi
        count = len(debug["sig_samps"])
        record.update(symbol_count=count, state_count=len(debug["decoder"].states),
                      N=int(local["N"]), L=int(local["L"]), decoder_log=debug.get("log", ""))
        window = {"kind": "native decoder symbol window", "symbol_start": 0, "symbol_stop_exclusive": count,
                  "sample_selection": "last eye_uis+1 recovered clocks <= t[-1], then first eye_uis",
                  "voltage_selection": "first t sample >= each actual recovered clock"}
        add("viterbi.symbol_index", np.arange(count), "symbol index", window=window, producer="array axis identity")
        add("viterbi.state_index", np.arange(record["state_count"]), "state index", producer="decoder state identity")
        for key in ISI_ARRAYS:
            axis = "viterbi.symbol_index" if key in ("sample_times", "sample_indices", "decided_levels") else None
            unit = "s" if key in ("sample_times", "ui", "ts") else "V" if key in ("sigma", "decision_scaler", "decided_levels") else "1"
            add(f"viterbi.{key}", local[key], unit, axis, window)
        for key in DEBUG_ARRAYS:
            axis = "viterbi.symbol_index" if key in ("sig_samps", "probs", "prevs", "path", "symbols_viterbi") else None
            add(f"viterbi.{key}", debug[key], "V" if key in ("sig_samps", "pulse_resp_samps") else "1", axis, window,
                producer=f"native dbg_dict_viterbi[{key}]")
        add("viterbi.states", debug["decoder"].states, axis="viterbi.state_index", producer="original ISI decoder.states")
        add("viterbi.trans", debug["decoder"].trans, axis="viterbi.state_index", producer="original ISI decoder.trans")
        sink = SimpleNamespace(rx_use_viterbi=True, dbg_dict_viterbi=debug, mod_type=engine.mod_type,
                               bit_errs_viterbi=engine.bit_errs_viterbi, L=engine.L,
                               rx_viterbi_symbols=engine.rx_viterbi_symbols, plotdata=ArrayPlotData())
        update_trellis(sink)
        for key in TRELLIS_FIELDS:
            add(f"viterbi.{key}", sink.plotdata.get_data(key), window=window, producer="models.bert.update_trellis original producer")
    manifest["decoding"] = record
    manifest["summary"].update(n_errs_viterbi=int(engine.n_errs_viterbi), viterbi_availability=record["availability"])
    validate(manifest, arrays)


def validate(run, arrays):
    """Validate the complete primitive decoding contract before archive publication."""
    record = run.get("decoding")
    if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise ValueError("Missing/unknown decoding schema")
    config = run["effective_input"]
    hashes = {key.replace("\\", "/"): value for key, value in run.get("actual_source_sha256", {}).items()}
    for name in ("models/bert.py", "models/viterbi.py", "web/viterbi.py"):
        value = hashes.get(name)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"Missing actual decoding source identity: {name}")
    if config.get("rx_viterbi_fec"):
        raise ValueError("unsupported_native_fec in archive")
    enabled = config.get("rx_use_viterbi")
    if type(enabled) is not bool or record.get("availability") != ("available" if enabled else "disabled"):
        raise ValueError("Decoding availability/input mismatch")
    expected_plan = plan(config, execution=True)
    if record.get("plan") != expected_plan or not isinstance(record.get("producer"), str):
        raise ValueError("Missing/inconsistent decoding plan/producer")
    if record.get("display") != {"initial_symbols": 10, "log10_floor": -20, "raw_unchanged": True}:
        raise ValueError("Missing/unknown decoding display contract")

    def get(key, *, integer=False, shape=None):
        if key not in arrays:
            raise ValueError(f"Missing decoding array {key}")
        value = arrays[key]
        meta = run["datasets"].get(key, {})
        if meta.get("availability") != "available" or not meta.get("producer") or not isinstance(meta.get("window"), dict):
            raise ValueError(f"{key}: incomplete decoding metadata")
        if integer and value.dtype.kind not in "biu":
            raise ValueError(f"{key}: integer indices/bits required")
        if shape is not None and value.shape != shape:
            raise ValueError(f"{key}: decoding shape mismatch")
        if not np.isfinite(value).all():
            raise ValueError(f"{key}: nonfinite decoding data")
        return value

    for name in ("dfe", "viterbi"):
        row = record.get("ber", {}).get(name)
        if not isinstance(row, dict):
            raise ValueError(f"{name}: missing BER window identity")
        if name == "viterbi" and not enabled:
            if row != {"availability": "disabled", "count": -1} or run["summary"].get("n_errs_viterbi") != -1:
                raise ValueError("Disabled Viterbi must retain -1, never zero errors")
            if any(key.startswith(("viterbi.", "ber.viterbi.")) for key in arrays):
                raise ValueError("Disabled Viterbi contains stale decoder data")
            continue
        for field in ("count", "bit_delay", "test_start_bit", "test_stop_bit", "reference_start_bit", "reference_stop_bit"):
            if type(row.get(field)) is not int or row[field] < 0:
                raise ValueError(f"{name}: invalid BER window {field}")
        length = config["eye_bits"]
        if (row["availability"] != "available" or row["test_start_bit"] != config["nbits"] - length
                or row["test_stop_bit"] != config["nbits"] or row["reference_stop_bit"] != len(arrays["bits"]) - row["bit_delay"]
                or row["reference_start_bit"] != row["reference_stop_bit"] - length):
            raise ValueError(f"{name}: inconsistent BER window/delay")
        prefix = f"ber.{name}."
        test = get(prefix + "bits_test", integer=True, shape=(length,))
        reference = get(prefix + "bits_reference", integer=True, shape=(length,))
        output = get(prefix + "bits_out", integer=True)
        corr = get(prefix + "auto_corr", shape=(length - length // 2,))
        errors = get(prefix + "errors", integer=True, shape=(row["count"],))
        if (output.ndim != 1 or not np.isin(output, [0, 1]).all() or not np.isin(test, [0, 1]).all()
                or not np.array_equal(reference, arrays["bits"][row["reference_start_bit"]:row["reference_stop_bit"]])
                or not np.array_equal(errors, np.flatnonzero(test != reference))
                or row["bit_delay"] >= len(corr) or run["summary"].get(f"n_errs_{name}") != row["count"]):
            raise ValueError(f"{name}: inconsistent BER arrays/count")
        from pybert.utility import resize_zero_pad

        if not np.array_equal(test, resize_zero_pad(output, config["nbits"], pad_front=True)[-length:]):
            raise ValueError(f"{name}: test window does not belong to native output bits")
        if name == "dfe" and not np.array_equal(errors, arrays["bit_errs_dfe"]):
            raise ValueError("DFE error identity mismatch")
        window = {"kind": "calc_ber tail", **{k: v for k, v in row.items() if k != "availability"},
                  "indices": "errors relative to test bit window"}
        if any(run["datasets"][prefix + key]["window"] != window for key in BER_ARRAYS):
            raise ValueError(f"{name}: missing/inconsistent BER dataset windows")
    if not enabled:
        return
    count, states, n, levels = (record.get(k) for k in ("symbol_count", "state_count", "N", "L"))
    if (any(type(v) is not int for v in (count, states, n, levels)) or n != expected_plan["N"]
            or levels != expected_plan["L"] or states != expected_plan["states"] or not n <= count <= expected_plan["samples_upper_bound"]):
        raise ValueError("Invalid decoding symbol/state dimensions")
    if not np.array_equal(get("viterbi.symbol_index", integer=True, shape=(count,)), np.arange(count)):
        raise ValueError("Invalid decoding symbol axis")
    if not np.array_equal(get("viterbi.state_index", integer=True, shape=(states,)), np.arange(states)):
        raise ValueError("Invalid decoding state axis")
    for key in ISI_ARRAYS + DEBUG_ARRAYS + ("states", "trans") + TRELLIS_FIELDS:
        get(f"viterbi.{key}")
    for key in ("probs", "prevs"):
        get(f"viterbi.{key}", integer=key == "prevs", shape=(count, states))
    get("viterbi.states", shape=(states, n))
    get("viterbi.trans", shape=(states, states))
    for key in ("path", "sample_indices"):
        get(f"viterbi.{key}", integer=True, shape=(count,))
    for key in ("sig_samps", "sample_times", "decided_levels", "symbols_viterbi"):
        get(f"viterbi.{key}", shape=(count,))
    get("viterbi.pulse_resp_samps", shape=(n,))
    for key in ("sigma", "decision_scaler", "ui", "ts", "nspui", "N", "L", "clk_phase_ix", "pulse_resp_curs_ix", "pulse_peak_ix"):
        get(f"viterbi.{key}", shape=())
    for key, expected in (("N", n), ("L", levels), ("nspui", config["nspui"])):
        if arrays[f"viterbi.{key}"].item() != expected:
            raise ValueError(f"Inconsistent decoder {key}")
    for key in ("sigma", "decision_scaler", "ui", "ts"):
        if arrays[f"viterbi.{key}"].item() <= 0:
            raise ValueError(f"Invalid decoder {key}")
    for key in ("sig_samps", "sample_times", "sample_indices", "decided_levels", "probs", "prevs", "path", "symbols_viterbi"):
        meta = run["datasets"][f"viterbi.{key}"]
        if meta.get("axis") != "viterbi.symbol_index" or meta["window"].get("symbol_stop_exclusive") != count or meta["window"].get("symbol_start") != 0:
            raise ValueError(f"viterbi.{key}: missing/inconsistent symbol axis/window")
    for key in ("states", "trans"):
        if run["datasets"][f"viterbi.{key}"].get("axis") != "viterbi.state_index":
            raise ValueError(f"viterbi.{key}: missing state axis")
    for key in ("path", "prevs"):
        if np.any((arrays[f"viterbi.{key}"] < 0) | (arrays[f"viterbi.{key}"] >= states)):
            raise ValueError(f"viterbi.{key}: out of state bounds")
    indices, times = arrays["viterbi.sample_indices"], arrays["viterbi.sample_times"]
    if (np.any(indices < 1) or np.any(indices >= len(arrays["t"])) or np.any(np.diff(times) <= 0)
            or np.any(arrays["t"][indices] < times) or np.any(arrays["t"][indices - 1] >= times)
            or not np.array_equal(arrays["viterbi.sig_samps"], arrays["dfe_out"][indices])):
        raise ValueError("Invalid original recovered clock samples/indices")
    if not np.array_equal(get("viterbi.trellis_path_xs", integer=True, shape=(count,)), np.arange(count)):
        raise ValueError("Invalid trellis symbol axis")
    chosen = get("viterbi.trellis_path_ys", integer=True, shape=(count,))
    tx, ty = arrays["viterbi.trellis_x"], arrays["viterbi.trellis_y"]
    if (tx.ndim != 1 or tx.shape != ty.shape or len(tx) % 2 or np.any(tx < 0) or np.any(tx >= count)
            or np.any(ty < 0) or np.any(ty >= states) or np.any(chosen < 0) or np.any(chosen >= states)):
        raise ValueError("Invalid native trellis endpoints/path states")
    probs = arrays["viterbi.probs"]
    if np.any(probs < 0) or np.any(probs > 1):
        raise ValueError("Invalid raw state probabilities")
    for rank in (1, 2, 3):
        ys = get(f"viterbi.trellis_state{rank}_ys", integer=True, shape=(count,))
        values = get(f"viterbi.trellis_state{rank}_probs", shape=(count,))
        if np.any((ys < 0) | (ys >= states)) or not np.array_equal(values, probs[np.arange(count), ys]):
            raise ValueError("Invalid native top-three state/probability identity")
    errors = arrays["ber.viterbi.errors"]
    mapped = errors // 2 if config["mod_type"] == "PAM-4" else errors
    if (not np.array_equal(arrays["viterbi.trellis_err_xs"], mapped)
            or not np.array_equal(arrays["viterbi.trellis_err_ys"], -.25 * np.ones(len(errors)))):
        raise ValueError("Invalid trellis error mapping; PAM4 duplicates must be preserved")


def payload(directory, position=0, error=0):
    """Read a bounded view of immutable original layers; never call the engine."""
    directory = Path(directory)
    run = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    record = run.get("decoding")
    if not record:
        return {"run_id": run["run_id"], "availability": "not_collected", "reason": "该记录未采集 Viterbi / BER 对齐字段"}
    if record["availability"] != "available":
        return {"run_id": run["run_id"], **record}
    count = record["symbol_count"]
    width = min(10, count)
    maximum = max(0, count - width)
    with np.load(directory / "arrays.npz", allow_pickle=False) as arrays:
        errors = arrays["ber.viterbi.errors"]
        if error < 0 or error > len(errors):
            raise ValueError("Error selection is 0 (none) or a 1-based bit-error entry")
        if error:
            position = int(arrays["viterbi.trellis_err_xs"][error - 1])
        position = min(maximum, max(0, position))
        stop = position + width
        traces, probabilities = [], []
        x, y = arrays["viterbi.trellis_x"], arrays["viterbi.trellis_y"]
        # Original producer emits consecutive endpoint pairs, not one connected polyline.
        for ix in range(0, len(x), 2):
            if x[ix + 1] >= position and x[ix] < stop:
                traces.append({"type": "scatter", "mode": "lines", "x": x[ix:ix+2].tolist(), "y": y[ix:ix+2].tolist(),
                               "line": {"color": "#ccd5df", "width": 1}, "showlegend": False, "hoverinfo": "skip"})
        for rank in (1, 2, 3):
            xs = arrays["viterbi.trellis_path_xs"][position:stop]
            ys = arrays[f"viterbi.trellis_state{rank}_ys"][position:stop]
            raw = arrays[f"viterbi.trellis_state{rank}_probs"][position:stop]
            display_log = np.log10(np.maximum(raw, 1e-20))
            traces.append({"type": "scatter", "mode": "markers", "name": f"Top {rank} · raw probability",
                           "x": xs.tolist(), "y": ys.tolist(), "customdata": raw.tolist(),
                           "marker": {"size": 9, "color": display_log.tolist(), "colorscale": "Viridis", "cmin": -20, "cmax": 0,
                                      "showscale": rank == 1, "colorbar": {"title": {"text": "log10(raw)<br>floor −20", "side": "right", "font": {"size": 9}}}},
                           "hovertemplate": "symbol=%{x}<br>state=%{y}<br>raw probability=%{customdata}<extra></extra>"})
            probabilities.append({"rank": rank, "symbol_indices": xs.tolist(), "state_indices": ys.tolist(),
                                  "raw_probabilities": raw.tolist(), "display_log10": display_log.tolist()})
        traces.append({"type": "scatter", "mode": "lines+markers", "name": "Native chosen trellis path",
                       "x": arrays["viterbi.trellis_path_xs"][position:stop].tolist(),
                       "y": arrays["viterbi.trellis_path_ys"][position:stop].tolist(), "line": {"color": "#d34818", "width": 2}})
        mapped = arrays["viterbi.trellis_err_xs"]
        visible = (mapped >= position) & (mapped < stop)
        traces.append({"type": "scatter", "mode": "markers", "name": "Bit-error entries (duplicates retained)",
                       "x": mapped[visible].tolist(), "y": arrays["viterbi.trellis_err_ys"][visible].tolist(),
                       "marker": {"symbol": "x", "color": "#c22", "size": 12}})
        selected_error = None if not error else {"entry": error, "bit_index": int(errors[error-1]), "symbol_index": int(mapped[error-1])}
        return {"run_id": run["run_id"], "availability": "available", "position": position, "max_position": maximum,
                "stop_exclusive": stop, "symbol_count": count, "error": error, "error_count": len(errors),
                "selected_error": selected_error, "ber": record["ber"], "data": traces, "top3": probabilities,
                "state_count": record["state_count"], "probability": record["probability"], "display": record["display"]}
