"""Same-Init NRZ results with independent analyses; raw6 remains a separate contract."""

from copy import deepcopy

import numpy as np

from pybert.utility.ami_clock import ANALYSIS_BOUNDARY_BASIS, analysis_sample_mask, epoch_analysis_bounds, map_same_epoch_clocks

FEATURE = "ami-clock-independent-v3"
ARRAY_FIELDS = ("edges_s", "targets_s", "sample_indices", "consumed_tick_positions", "sample_targets_s",
                "sample_grid_times_s", "sample_quantization_delay_s", "analysis_sample_indices",
                "window_sample_indices", "eye_sample_indices", "sample_values", "decisions", "bits", "adaptation_ready",
                "analysis_epoch_bounds_s")
MAPPING_ARRAYS = ("raw_epoch_edges_s", "main_returned_edges_s", "tick_sources", "main_local_edges_s",
                  "epoch_targets_s", "sample_epoch_times_s", "targets_s", "planned_tick_positions",
                  "planned_indices", "planned_ready", "quantization_delay_s")
FIELDS = ("producer_contract_version", "invocation_id", "epoch_basis", "requested", "mode", "role", "main_origin",
          "format_status", "actual_branch", "eligible", "run_status", "consumption_status", "consumed_count",
          "loop_finished", "full_analysis_eligible", "reason", "symbol_ui_s", "ignore_ui", "nspui", "analysis",
          "profile", "profile_source", "model_qualification", "ber_eligible", "ber_status", "deferred_reasons",
          "last_tick_status", "analysis_boundary_basis")


def equal(actual, expected, name):
    """Coordinate and raw-array identity includes dtype/shape/bytes, including NaN payloads."""
    actual, expected = np.asarray(actual), np.asarray(expected)
    if actual.dtype != expected.dtype or actual.shape != expected.shape or actual.tobytes() != expected.tobytes():
        raise ValueError("AMI v3 array identity mismatch: " + name)


def validate_info(info, raw):
    """Check source algebra and observed values; never invoke a model, slicer, Eye or FFT."""
    from pybert.web.clocks import validate_period

    if (type(info.get("producer_contract_version")) is not int or info.get("producer_contract_version") != 3
            or not isinstance(info.get("invocation_id"), str)
            or not info["invocation_id"] or info.get("main_origin") != "same_init_after_probes"
            or info.get("role") != "main" or info.get("mode") != "rx_getwave" or info.get("requested") is not True
            or info.get("actual_branch") != "ami" or info.get("format_status") != "valid"
            or info.get("eligible") is not True or info.get("run_status") != "completed"
            or info.get("consumption_status") != "completed" or info.get("loop_finished") is not True
            or info.get("analysis_boundary_basis") != ANALYSIS_BOUNDARY_BASIS
            or info.get("model_qualification") != "UNKNOWN" or info.get("profile") != {
                "ignore_ui_units": "symbol_ui", "nominal_eye_offset_ui": 0, "mapping": "native_nrz"}):
        raise ValueError("Incomplete or unsupported AMI v3 producer")
    t, wave, known = raw["t"], raw["dfe_out"], np.asarray(info["period_known"])
    if wave.shape != t.shape or wave.ndim != 1 or not np.isfinite(wave).all():
        raise ValueError("Incomplete Main waveform")
    mapping = map_same_epoch_clocks(info["origin_observations"], t, info["symbol_ui_s"], info["ignore_ui"])
    if not len(mapping["raw_epoch_edges_s"]):
        raise ValueError("All-empty epoch clocks belong to the Native fallback")
    for name, value in mapping.items():
        if name == "consumption_permission":
            value = "software_nrz_contract_v3; model qualification UNKNOWN"
        if isinstance(value, np.ndarray):
            equal(info["origin_mapping"][name], value, name)
        elif info["origin_mapping"].get(name) != value:
            raise ValueError("Inconsistent AMI v3 origin mapping: " + name)
    equal(info["edges_s"], mapping["raw_epoch_edges_s"], "raw epoch ticks")
    equal(info["targets_s"], mapping["targets_s"], "local target display")
    indices, positions = np.asarray(info["sample_indices"]), np.asarray(info["consumed_tick_positions"])
    equal(indices, mapping["planned_indices"], "all completed sample indices")
    equal(positions, mapping["planned_tick_positions"], "all completed tick positions")
    if type(info["consumed_count"]) is not int or info["consumed_count"] != len(indices):
        raise ValueError("Inconsistent AMI consumed count")
    for name, expected in (("sample_grid_times_s", t[indices]), ("sample_targets_s", mapping["targets_s"][positions]),
                           ("sample_quantization_delay_s", mapping["quantization_delay_s"]),
                           ("sample_values", wave[indices])):
        equal(info[name], expected, name)
    equal(raw["clock_times"], t[indices], "host clock_times")
    decisions, bits = np.asarray(info["decisions"]), np.asarray(info["bits"])
    if (decisions.shape != indices.shape or bits.shape != indices.shape
            or (bits.size and bits.dtype.kind not in "iu")
            or not np.isfinite(decisions).all() or not np.isin(bits, (0, 1)).all()
            or not np.array_equal(decisions, np.sign(wave[indices]))
            or not np.array_equal(bits, (decisions > 0).astype(int))):
        raise ValueError("Inconsistent original NRZ samples, decisions or bits")
    window = info["analysis"]
    start, stop, required, traces = (window[name] for name in
        ("start_index", "stop_index", "required_decisions", "required_eye_traces"))
    first, last = window["fft_slice"]
    if (any(type(value) is not int for value in (start, stop, required, traces, first, last, info["nspui"]))
            or not 0 <= start < stop <= len(t) or not start <= first <= last <= stop
            or min(required, traces, info["nspui"]) < 1
            or not t[0] <= window["start_s"] <= window["stop_s"] <= t[-1]):
        raise ValueError("Invalid frozen AMI v3 analysis window")
    ready, inside = analysis_sample_mask({**info, "grid_s": t}, indices, positions)
    equal(info["analysis_epoch_bounds_s"], epoch_analysis_bounds({**info, "grid_s": t}), "epoch window bounds")
    selected = indices[inside]
    equal(info["adaptation_ready"], ready, "readiness")
    equal(info["window_sample_indices"], selected, "window samples")
    equal(info["analysis_sample_indices"], selected[-required:], "final W samples")
    equal(info["eye_sample_indices"], selected[selected + 2 * info["nspui"] <= stop], "Eye eligibility")
    eligible = len(selected) >= required
    if info["ber_eligible"] is not eligible or info.get("ber_status") != {
            "availability": "available" if eligible else "unavailable",
            "reason": None if eligible else "insufficient_frozen_ber_decisions"}:
        raise ValueError("BER availability does not match the frozen sample window")
    compact = validate_period(t, raw["ui_ests"], known)
    mask, period = np.zeros(len(t), dtype=bool), np.full(len(t), np.nan)
    for left in range(len(indices) - 1):
        if positions[left + 1] == positions[left] + 1:
            segment = slice(indices[left], indices[left + 1])
            mask[segment] = True
            period[segment] = info["edges_s"][positions[left + 1]] - info["edges_s"][positions[left]]
    equal(known, mask, "period mask")
    equal(raw["ui_ests"][known], period[known] * 1e12, "known period values")
    full = eligible and len(info["eye_sample_indices"]) >= traces and last - first >= 2 and bool(np.all(known[first:last]))
    if info["full_analysis_eligible"] is not full:
        raise ValueError("Inconsistent legacy completeness observation")
    return {"version": 3, "info": info, "raw": raw, "known_compact": compact, "window_indices": selected}


def live_context(engine, snapshot):
    info = snapshot["info"]
    raw = snapshot["raw"]
    for name in ("t", "ui_ests", "ami_period_known", "clock_times", "dfe_out", "ffe_out"):
        if name not in raw:
            raise ValueError("Missing AMI v3 host snapshot: " + name)
        equal(getattr(engine, name), raw[name], "host snapshot " + name)
    equal(info["grid_s"], raw["t"], "producer grid")
    equal(info["period_known"], raw["ami_period_known"], "host mask")
    equal(raw["dfe_out"], raw["ffe_out"], "Rx AMI slicer waveform")
    context = validate_info(info, raw)
    return {**context, "snapshot_phase": snapshot["phase"], "eye_consumers": snapshot.setdefault("eye_consumers", {})}


def store_context(context, arrays, datasets):
    """Save primitive metadata and exact numeric arrays; clocks in the receipt use NPZ slices."""
    info, raw = context["info"], context["raw"]
    def add(key, value, unit, axis=None):
        value = np.asarray(value)
        arrays[key] = value
        datasets[key] = {"field": key, "dtype": str(value.dtype), "shape": list(value.shape), "unit": unit, "axis": axis,
            "producer": "same Init AMI v3 host snapshot", "point": "cdr", "kind": "raw", "availability": "available",
            "clock_basis": "epoch target / actual Main grid indices", "window": dict(info["analysis"]),
            "display_noise": False, "invocation_id": info["invocation_id"], "source_fields": [key]}
    add("ui_ests", raw["ui_ests"], "ps", "t")
    datasets["ui_ests"].update(numerical_availability="masked", mask_field="ami.cdr.period_known",
        known_count=len(context["known_compact"][0]), unknown_count=len(raw["t"]) - len(context["known_compact"][0]))
    add("ami.cdr.period_known", info["period_known"], "bool", "t")
    for name in ARRAY_FIELDS:
        add("ami.clock." + name, np.asarray(info[name], dtype=int) if name == "bits" else info[name],
            "s" if name.endswith("_s") else "V" if name == "sample_values" else "1")
    mapping = info["origin_mapping"]
    for name in MAPPING_ARRAYS:
        add("ami.origin." + name, mapping[name], "s" if name.endswith("_s") else "1")
    for name, value in zip(("known_grid_indices", "known_times_s", "known_period_ps"), context["known_compact"]):
        add("ami.cdr." + name, value, "sample index" if name.endswith("indices") else "s" if name.endswith("_s") else "ps")
    receipt = deepcopy(info["origin_observations"])
    offset = 0
    for call in receipt["history"]["invocations"]:
        for chunk in call["chunks"]:
            count = len(chunk.pop("valid_clocks"))
            chunk["clock_slice"] = [offset, offset + count]
            offset += count
    return {"version": 3, **{name: deepcopy(info[name]) for name in FIELDS},
            "array_fields": {name: "ami.clock." + name for name in ARRAY_FIELDS},
            "origin_observations": receipt,
            "origin_mapping": {name: deepcopy(value) for name, value in mapping.items() if name not in MAPPING_ARRAYS},
            "origin_array_fields": {name: "ami.origin." + name for name in MAPPING_ARRAYS},
            "period_field": "ui_ests", "mask_field": "ami.cdr.period_known", "grid_field": "t",
            "waveform_field": "dfe_out", "snapshot_phase": context["snapshot_phase"],
            "eye_consumers": context["eye_consumers"]}


def stored_context(run, arrays):
    """Strict v3 reader, with no execution or historical repair."""
    from pybert.web.clocks import clock_features

    clock_features(run)
    contract = run["ami"]["clock_contract"]
    if (contract.get("array_fields") != {name: "ami.clock." + name for name in ARRAY_FIELDS}
            or contract.get("origin_array_fields") != {name: "ami.origin." + name for name in MAPPING_ARRAYS}
            or contract.get("period_field") != "ui_ests" or contract.get("mask_field") != "ami.cdr.period_known"
            or contract.get("grid_field") != "t" or contract.get("waveform_field") != "dfe_out"):
        raise ValueError("Invalid AMI v3 array references")
    try:
        info = {**contract, **{name: arrays[field] for name, field in contract["array_fields"].items()},
                "origin_mapping": {**contract["origin_mapping"],
                    **{name: arrays[field] for name, field in contract["origin_array_fields"].items()}},
                "period_known": arrays["ami.cdr.period_known"]}
        receipt = deepcopy(contract["origin_observations"])
        edges, offset = info["edges_s"], 0
        for call in receipt["history"]["invocations"]:
            for chunk in call["chunks"]:
                start, stop = chunk.pop("clock_slice")
                if (type(start) is not int or type(stop) is not int or start != offset
                        or not start <= stop <= len(edges) or "valid_clocks" in chunk):
                    raise ValueError("Invalid AMI receipt clock slices")
                chunk["valid_clocks"] = edges[start:stop].tolist()
                offset = stop
        if offset != len(edges):
            raise ValueError("Incomplete AMI receipt clock slices")
        info["origin_observations"] = receipt
        if info["bits"].dtype.kind not in "iu":
            raise ValueError("AMI v3 saved bits must be primitive integers")
        raw = {name: arrays[name] for name in ("t", "ui_ests", "clock_times", "dfe_out")}
        context = validate_info(info, raw)
        for name, expected in zip(("known_grid_indices", "known_times_s", "known_period_ps"), context["known_compact"]):
            equal(arrays["ami.cdr." + name], expected, name)
        for name, value in arrays.items():
            if value.dtype.kind not in "biufc" or name != "ui_ests" and not np.isfinite(value).all():
                raise ValueError("Invalid numeric array outside the masked period exception: " + name)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("Incomplete AMI v3 source/array contract") from error
    return {**context, "snapshot_phase": "stored contract; no new Main invocation",
            "eye_consumers": contract.get("eye_consumers", {})}


def analysis_availability(run):
    """Execution completion and each analysis have separate, user-visible meanings."""
    contract = run["ami"]["clock_contract"]
    count = contract["consumed_count"]
    result = {"main": {"availability": "available", "reason": None, "execution": "completed"},
              "sampling": {"availability": "available" if count else "unavailable",
                           "reason": None if count else "no_in_record_tick", "execution": "completed", "count": count},
              "ber": dict(contract["ber_status"])}
    for name, source in (("eye_collect", "collect.eye.dfe"), ("eye_analysis", "analysis.eye.dfe")):
        row = contract["eye_consumers"][source]
        result[name] = {key: row[key] for key in
            ("availability", "reason", "eligible_trace_count", "required_trace_count", "trace_count")}
    for name, row in contract["period_analysis"].items():
        result[name] = {key: row[key] for key in ("availability", "reason")}
    return result


def validate_publication(run, arrays):
    """Validate independent outcome claims against saved dependencies, without regenerating plots."""
    from pybert.web.clocks import eye_selection

    context = stored_context(run, arrays)
    info, config, t = context["info"], run["effective_input"], arrays["t"]
    window, nspui, ui = info["analysis"], info["nspui"], info["symbol_ui_s"]
    required, nbits = config["eye_bits"], config["nbits"]
    start = (nbits - required) * nspui
    expected_window = {"start_index": start, "stop_index": len(t), "start_s": (nbits - required) * ui,
                       "stop_s": float(t[-1]), "required_decisions": required,
                       "required_eye_traces": max(1, required - 2),
                       "fft_slice": [start + nspui, max(start + nspui, len(t) - nspui)]}
    if (config["mod_type"] != "NRZ" or config["rx_use_viterbi"] or config["nspui"] != nspui
            or ui != 1. / (config["bit_rate"] * 1e9) or info["origin_mapping"]["sample_interval_s"] != ui / nspui
            or len(t) != nbits * nspui or {**window, "fft_slice": list(window["fft_slice"])} != expected_window
            or run["summary"].get("model_qualification") != "UNKNOWN"
            or run["summary"].get("dfe_ber") != info["ber_status"]):
        raise ValueError("AMI v3 configuration, qualification or frozen analysis window mismatch")
    hashes = {key.replace("\\", "/"): value for key, value in run.get("actual_source_sha256", {}).items()}
    for name in ("models/bert.py", "utility/ami_clock.py", "web/clock_v3.py", "web/clocks.py", "web/data.py", "web/analysis.py"):
        value = hashes.get(name)
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("Missing AMI v3 source identity: " + name)
    equal(arrays["ffe_out"], arrays["dfe_out"], "saved Rx AMI slicer waveform")
    selected = info["analysis_sample_indices"]
    equal(arrays["dfe_slicer_samps"], arrays["dfe_out"][selected], "saved slicer sample window")
    equal(arrays["dfe_slicer_decisions"], info["decisions"][np.searchsorted(info["sample_indices"], selected)],
          "saved slicer decisions")
    expected_clocks = np.zeros(len(t))
    expected_clocks[info["sample_indices"]] = 1
    equal(arrays["clocks"], expected_clocks, "saved clock mask")
    try:
        consumers = info["eye_consumers"]
        if set(consumers) != {"collect.eye.dfe", "analysis.eye.dfe"}:
            raise ValueError("Missing AMI Eye consumer outcome")
        for row in consumers.values():
            relative, expected = eye_selection(context, start, len(t))
            for name in ("invocation_id", "slice_start", "slice_stop", "width", "absolute_indices", "relative_indices",
                         "window", "consumed_count", "window_sample_count", "eligible_trace_count", "required_trace_count"):
                if row[name] != expected[name]:
                    raise ValueError("Inconsistent saved Eye consumer: " + name)
            reason = expected["reason"] if len(relative) < expected["required_trace_count"] else None
            if reason is None:
                ys = arrays["dfe_out"][start:expected["slice_stop"]]
                y_max = 1.1 * max(abs(ys))
                if y_max <= 0 or 1000 // (2 * y_max) <= 0:
                    reason = "unusable_eye_voltage_scale"
            if (row["availability"] != ("unavailable" if reason else "available") or row["reason"] != reason
                    or row["trace_count"] != (0 if reason else len(relative))
                    or row["trace_status"] != ("not_attempted" if reason else "completed")):
                raise ValueError("Saved Eye outcome disagrees with its own coverage")
            if reason is None:
                counts = arrays["eye.dfe.counts"]
                if counts.shape != (1000, 2 * nspui) or not np.isfinite(counts).all() or np.any(counts < 0):
                    raise ValueError("Available Eye is missing its count grid")
        period_meta = info["period_analysis"]
        if set(period_meta) != {"histogram", "spectrum"}:
            raise ValueError("Missing independent period analysis outcomes")
        known = info["period_known"]
        positions = np.arange(len(t))
        inside = ((positions >= start) & (positions < len(t)) & (t >= window["start_s"]) & (t <= window["stop_s"]))
        hist_indices = np.flatnonzero(known & inside)
        hist = period_meta["histogram"]
        if (hist["availability"] != ("available" if len(hist_indices) else "unavailable")
                or hist["reason"] != (None if len(hist_indices) else "no_known_period")):
            raise ValueError("Histogram outcome disagrees with known periods")
        equal(arrays["cdr.histogram.grid_indices"], hist_indices, "histogram sample indices")
        equal(arrays["cdr.histogram.input_period_ps"], arrays["ui_ests"][hist_indices], "histogram source values")
        counts, edges = arrays["cdr.histogram.counts"], arrays["cdr.histogram.edges"]
        if (len(hist_indices) and (counts.shape != (100,) or edges.shape != (101,) or counts.sum() != len(hist_indices)
                                  or np.any(counts < 0)) or not len(hist_indices) and (counts.size or edges.size)):
            raise ValueError("Invalid saved histogram counts/edges")
        first, stop = window["fft_slice"]
        reason = ("insufficient_fft_window" if stop - first < 2 else "outside_analysis_window"
                  if not np.all(inside[first:stop]) else "unknown_period" if not np.all(known[first:stop]) else None)
        spectrum = period_meta["spectrum"]
        if spectrum["availability"] != ("unavailable" if reason else "available") or spectrum["reason"] != reason:
            raise ValueError("Spectrum outcome disagrees with its frozen window")
        fft_indices = positions[first:stop] if reason is None else np.array([], dtype=int)
        equal(arrays["cdr.spectrum.grid_indices"], fft_indices, "FFT sample indices")
        equal(arrays["cdr.spectrum.input_period_ps"], arrays["ui_ests"][fft_indices], "FFT input values")
        length = (stop - first) // 2 + 1 if reason is None else 0
        if arrays["cdr.spectrum.raw"].shape != (length,) or arrays["cdr.spectrum.frequency_Hz"].shape != (length,):
            raise ValueError("Invalid saved FFT result dimensions")
        if run.get("analysis_availability") != analysis_availability(run):
            raise ValueError("Missing or inconsistent independent analysis summary")
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError("Incomplete independent AMI analysis publication") from error
