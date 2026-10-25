"""Producer-owned AMI clock records shared by Web consumers and archive validation."""

import copy
import io

import numpy as np

CLOCK_FIELDS = ("edges_s", "targets_s", "sample_indices", "consumed_tick_positions", "sample_targets_s",
                "sample_grid_times_s", "sample_quantization_delay_s", "analysis_sample_indices")


def validate_period(t, period_ps, known):
    """Validate the exact dense masked exception; return compact references without changing raw bytes."""
    t, period_ps, known = np.asarray(t), np.asarray(period_ps), np.asarray(known)
    if (t.ndim != 1 or t.dtype.kind not in "fiu" or not np.isfinite(t).all()
            or period_ps.dtype.kind != "f" or known.dtype.kind != "b"
            or period_ps.shape != t.shape or known.shape != t.shape
            or not np.isfinite(period_ps[known]).all() or np.any(period_ps[known] <= 0)
            or not np.isnan(period_ps[~known]).all()):
        raise ValueError("AMI period requires a same-grid bool mask, positive finite known and NaN unknown values")
    indices = np.flatnonzero(known)
    return indices, t[indices], period_ps[indices]


def snapshot_producer(engine, previous_invocation=None, phase="unknown"):
    """Copy only already stored host values; never evaluate a missing engine property on a failure path."""
    state = getattr(engine, "ami_clock_info", None)
    info = copy.deepcopy(dict(state)) if isinstance(state, dict) else None
    stored = vars(engine)
    raw = {}
    for name in ("t", "ui_ests", "ami_period_known", "clock_times", "clocks", "dfe_out", "ffe_out"):
        value = stored.get(name, stored.get("_traits_cache_" + name))
        if value is not None:
            raw[name] = np.asarray(value).copy()
    if "t" not in raw and info is not None and "grid_s" in info:
        raw["t"] = np.asarray(info["grid_s"]).copy()
    invocation = info.get("invocation_id") if info is not None else None
    return {"info": info, "raw": raw, "phase": phase, "previous_invocation": previous_invocation,
            "fresh": bool(invocation and invocation != previous_invocation)}


def clock_context(engine, snapshot=None):
    """Accept current producer evidence before any raw or mathematical consumer chooses its route."""
    current = getattr(engine, "ami_clock_info", None)
    if not current:
        if (getattr(engine, "rx_use_ami", False) and getattr(engine, "rx_use_getwave", False)
                and getattr(engine, "rx_use_clocks", False)):
            raise ValueError("Requested AMI clocks have no producer evidence")
        return None  # Historical Native callers retain their original finite/raw4 path, without new claims.
    if snapshot is None and current.get("actual_branch") == "native":
        snapshot = snapshot_producer(engine, phase="native_collect")
    info = snapshot.get("info") if isinstance(snapshot, dict) else None
    if (not info or info.get("producer_contract_version") not in (2, 3) or not snapshot.get("fresh")
            or not isinstance(info.get("invocation_id"), str) or not info["invocation_id"]
            or info["invocation_id"] != current.get("invocation_id")):
        raise ValueError("Missing, stale or unsupported producer invocation")
    if info.get("run_status") != "completed" or info.get("consumption_status") != "completed":
        raise ValueError("Partial producer is diagnostic evidence, not a complete analysis input")
    if info.get("actual_branch") == "native":
        if not info.get("native_returned"):
            raise ValueError("Native execution did not actually return")
        if info.get("requested") and info.get("mode") == "rx_getwave":
            if (info.get("format_status") != "no_clocks" or not info.get("use_native")
                    or len(info.get("edges_s", [None]))):
                raise ValueError("Only legal empty clocks permit the Native fallback")
        return None
    if info["producer_contract_version"] == 3:
        from pybert.web.clock_v3 import live_context

        return live_context(engine, snapshot)
    if (info.get("actual_branch") != "ami" or info.get("role") != "main"
            or info.get("main_origin") != "c1_fresh_main" or info.get("mode") != "rx_getwave"
            or not info.get("requested") or info.get("format_status") != "valid"
            or not info.get("eligible") or not info.get("full_analysis_eligible")):
        raise ValueError("Unsupported AMI clock origin, branch or analysis eligibility")
    raw = snapshot["raw"]
    for name in ("t", "ui_ests", "ami_period_known", "clock_times"):
        if name not in raw or np.asarray(getattr(engine, name)).tobytes() != raw[name].tobytes():
            raise ValueError("Host producer snapshot no longer matches " + name)
    t, period, known = raw["t"], raw["ui_ests"], info["period_known"]
    compact = validate_period(t, period, known)
    if not len(compact[0]):
        raise ValueError("All-unknown producer period is diagnostic only")
    if (not np.array_equal(raw["ami_period_known"], known) or not np.array_equal(info["grid_s"], t)
            or np.any(np.diff(t) <= 0) or not np.array_equal(period[known], info["period_s"][known] * 1e12)):
        raise ValueError("Producer grid, mask or ps units disagree")
    indices = np.asarray(info["sample_indices"])
    positions = np.asarray(info["consumed_tick_positions"])
    targets, times = np.asarray(info["sample_targets_s"]), np.asarray(info["sample_grid_times_s"])
    edges, all_targets = np.asarray(info["edges_s"]), np.asarray(info["targets_s"])
    if (indices.ndim != 1 or indices.dtype.kind not in "iu" or not len(indices)
            or info["consumed_count"] != len(indices) or np.any(np.diff(indices) <= 0)
            or np.any(indices < 0) or np.any(indices >= len(t))
            or positions.shape != indices.shape or positions.dtype.kind not in "iu"
            or np.any(np.diff(positions) <= 0) or np.any(positions < 0) or np.any(positions >= len(edges))
            or targets.shape != indices.shape or times.shape != indices.shape
            or edges.ndim != 1 or not np.isfinite(edges).all() or np.any(edges < 0) or np.any(np.diff(edges) <= 0)
            or not np.array_equal(all_targets, edges + info["symbol_ui_s"] / 2)
            or not np.array_equal(targets, all_targets[positions]) or not np.array_equal(times, t[indices])
            or not np.array_equal(raw["clock_times"], times) or np.any(targets < t[0]) or np.any(targets > t[-1])
            or np.any(times < targets) or np.any(t[indices[indices > 0] - 1] >= targets[indices > 0])
            or not np.array_equal(info["sample_quantization_delay_s"], times - targets)):
        raise ValueError("Invalid producer sample indices, targets or actual grid times")
    window = info["analysis"]
    first, stop, required = window["start_index"], window["stop_index"], window["required_decisions"]
    if (any(type(value) is not int for value in (first, stop, required, info["nspui"]))
            or not 0 <= first < stop <= len(t) or required < 1 or info["nspui"] < 1
            or not t[0] <= window["start_s"] <= window["stop_s"] <= t[-1]):
        raise ValueError("Invalid frozen producer analysis window")
    inside = ((indices >= first) & (indices < stop) & (targets >= window["start_s"])
              & (targets <= window["stop_s"]) & (times >= window["start_s"]) & (times <= window["stop_s"])
              & (targets >= info["ignore_ui"] * info["symbol_ui_s"]))
    selected = indices[inside]
    if len(selected) < required or not np.array_equal(info["analysis_sample_indices"], selected[-required:]):
        raise ValueError("Producer final W sample selection is incomplete or inconsistent")
    profile = info.get("profile", {})
    if (profile.get("ignore_ui_units") != "symbol_ui" or profile.get("nominal_eye_offset_ui") != 0
            or profile.get("mapping") not in ("native_nrz", "native_pam4")):
        raise ValueError("Missing declared units, zero eye offset or slicer mapping")
    return {"version": 2, "info": info, "raw": raw, "known_compact": compact,
            "window_indices": selected, "snapshot_phase": snapshot["phase"],
            "eye_consumers": snapshot.setdefault("eye_consumers", {})}


def eye_selection(context, slice_start, slice_stop):
    """Apply the actual crop and frozen stop to the same producer indices, without seconds rounding."""
    info = context["info"]
    t = context["raw"]["t"]
    time_stop = int(np.searchsorted(t, info["analysis"]["stop_s"], side="right"))
    stop = min(slice_stop, info["analysis"]["stop_index"], len(t), time_stop)
    if type(slice_start) is not int or type(slice_stop) is not int or not 0 <= slice_start <= stop:
        raise ValueError("Invalid actual waveform crop")
    width = 2 * info["nspui"]
    selected = context["window_indices"]
    absolute = selected[(selected >= slice_start) & (selected + width <= stop)]
    relative = absolute - slice_start
    required = info["analysis"]["required_eye_traces"] if context["version"] == 3 else 1
    return relative, {"clock_basis": "producer absolute grid indices", "consumed_count": info["consumed_count"],
                      "window_sample_count": len(selected), "eligible_trace_count": len(relative),
                      "trace_count": 0, "absolute_indices": absolute.tolist(), "relative_indices": relative.tolist(),
                      "slice_start": slice_start, "slice_stop": stop, "width": width,
                      "invocation_id": info["invocation_id"], "source_fields": ["ami.clock.sample_indices",
                      "ami.clock.sample_targets_s", "ami.clock.sample_grid_times_s"],
                      "window": dict(info["analysis"]), "trace_status": "not_attempted",
                      "availability": "unavailable",
                      "required_trace_count": required,
                      "reason": "no_complete_timed_trace" if not len(relative) else
                                "insufficient_timed_traces" if len(relative) < required else "not_calculated"}


def period_projection(context, t, period_ps, ui):
    """Keep histogram and raw FFT availability independent, using the frozen producer windows."""
    t, period_ps = np.asarray(t), np.asarray(period_ps)
    known = context["info"]["period_known"]
    validate_period(t, period_ps, known)
    window = context["info"]["analysis"]
    first, stop = window["start_index"], window["stop_index"]
    if type(first) is not int or type(stop) is not int or not 0 <= first < stop <= len(t):
        raise ValueError("Invalid frozen histogram bounds")
    indices = np.arange(len(t))
    inside = ((indices >= first) & (indices < stop) & (t >= window["start_s"]) & (t <= window["stop_s"]))
    selected = np.flatnonzero(known & inside)
    hist = {"availability": "unavailable", "reason": "no_known_period", "indices": selected,
            "values_ps": period_ps[selected], "counts": np.array([], dtype=int), "edges": np.array([]),
            "window": {"start_index": first, "stop_index": stop,
                       "start_s": window["start_s"], "stop_s": window["stop_s"]},
            "weighting": "one count per known grid sample; not one count per edge interval"}
    if len(selected):
        hist["counts"], hist["edges"] = np.histogram(hist["values_ps"], bins=100)
        hist.update(availability="available", reason=None)
    fft_first, fft_stop = window["fft_slice"]
    spectrum = {"availability": "unavailable", "reason": None, "raw": np.array([], dtype=complex),
                "frequency_hz": np.array([]), "relative_frequency": np.array([]),
                "indices": np.array([], dtype=int), "input_period_ps": np.array([]),
                "sample_interval_s": None, "origin_s": None,
                "window": {"start_index": fft_first, "stop_index": fft_stop},
                "uniform_grid_validation": None}
    if type(fft_first) is not int or type(fft_stop) is not int or not 0 <= fft_first <= fft_stop <= len(t):
        spectrum["reason"] = "invalid_fft_bounds"
    elif fft_stop - fft_first < 2:
        spectrum["reason"] = "insufficient_fft_window"
    elif not np.all(inside[fft_first:fft_stop]):
        spectrum["reason"] = "outside_analysis_window"
    elif not np.all(known[fft_first:fft_stop]):
        spectrum["reason"] = "unknown_period"
    elif t.dtype.kind in "iu" and np.any(t[1:] <= t[:-1]):
        spectrum["reason"] = "nonuniform_grid"
    else:
        ts = float(t[1] - t[0]) if len(t) >= 2 else None
        if ts is None or not np.isfinite(ts) or ts <= 0:
            spectrum["reason"] = "unknown_or_nonpositive_sample_interval"
        else:
            steps = np.diff(t)
            if t.dtype.kind in "iu":
                increasing = bool(np.all(t[1:] > t[:-1]) and np.all(steps > 0))
                equal = bool(np.all(steps == steps[0]))
                uniform = increasing and equal
                spectrum["uniform_grid_validation"] = {
                    "rule": "exact integer intervals; zero floating timestamp tolerance",
                    "reference": "original t[1]-t[0]; every interval in the original full grid",
                    "timestamp_dtype": t.dtype.str, "strictly_increasing": increasing,
                    "integer_intervals_equal": equal, "max_bound_s": 0., "max_interval_error_s": None}
            else:
                # Each rounded timestamp and subtraction contributes at most one conservative ULP.
                # Compare both intervals' endpoint/subtraction uncertainty; never change t or the reference ts.
                timestamp_ulps = np.spacing(np.abs(t))
                step_ulps = np.spacing(np.abs(steps))
                bounds = (timestamp_ulps[:-1] + timestamp_ulps[1:] + timestamp_ulps[0] + timestamp_ulps[1]
                          + step_ulps + step_ulps[0])
                errors = np.abs(steps - ts)
                increasing = bool(np.all(steps > 0))
                finite = bool(np.isfinite(bounds).all() and np.isfinite(errors).all()
                              and np.isfinite(steps).all())
                spectrum["uniform_grid_validation"] = {
                    "rule": "one ULP per endpoint and subtraction for tested and reference intervals",
                    "reference": "original t[1]-t[0]; every interval in the original full grid",
                    "timestamp_dtype": t.dtype.str, "strictly_increasing": increasing,
                    "max_interval_error_s": float(np.max(errors)) if np.isfinite(errors).all() else None,
                    "max_bound_s": float(np.max(bounds)) if np.isfinite(bounds).all() else None}
                uniform = finite and increasing and not np.any(errors > bounds)
            if not uniform:
                spectrum["reason"] = "nonuniform_grid"
            else:
                values = period_ps[fft_first:fft_stop]
                raw = np.fft.rfft(values)
                frequency = np.arange(len(raw)) / (len(values) * ts)
                spectrum.update(availability="available", reason=None, raw=raw, frequency_hz=frequency,
                                relative_frequency=frequency[1:] * ui, sample_interval_s=ts,
                                origin_s=float(t[fft_first]), indices=indices[fft_first:fft_stop],
                                input_period_ps=values)
    return {"histogram": hist, "spectrum": spectrum}


def period_segments(t, period_ps, known, limit=4096):
    """Sample known ordinals evenly, then split by the original gaps; singleton traces are markers."""
    if type(limit) is not int or not 1 <= limit <= 4096:
        raise ValueError("Period display point limit must be within 1..4096")
    indices, _times, _values = validate_period(t, period_ps, known)
    meta = {"availability": "unavailable", "reason": "no_known_period", "selected_points": 0,
            "known_points": len(indices), "known_segment_count": 0, "display_segment_count": 0,
            "omitted_segments": 0, "singleton_mode": "markers", "limit": limit,
            "allocation": "evenly spaced known ordinals including endpoints; split at original unknown gaps"}
    if not len(indices):
        return [], meta
    groups = np.cumsum(np.concatenate((np.array([True]), np.diff(indices) > 1)))
    ordinals = np.unique(np.linspace(0, len(indices) - 1, min(limit, len(indices)), dtype=int))
    cuts = np.flatnonzero(np.diff(groups[ordinals]) != 0) + 1
    segments = np.split(indices[ordinals], cuts)
    meta.update(availability="available", reason=None, selected_points=len(ordinals),
                known_segment_count=int(groups[-1]), display_segment_count=len(segments),
                omitted_segments=int(groups[-1]) - len(segments))
    return segments, meta


def store_clock_context(context, arrays, datasets):
    """Store the exact masked raw exception and its producer-owned coordinate arrays."""
    if context["version"] == 3:
        from pybert.web.clock_v3 import store_context

        return store_context(context, arrays, datasets)
    info, raw = context["info"], context["raw"]
    t = raw["t"]
    full = dict(scope="full_record", time_axis="t", start_index=0, stop_index=len(t),
                start_s=float(t[0]), stop_s_inclusive=float(t[-1]))

    def add(key, value, unit, axis=None, **extra):
        arrays[key] = value
        datasets[key] = dict(field=key, producer="fresh Main ami_clock_info host snapshot", point="cdr",
            kind="raw", dtype=str(value.dtype), shape=list(value.shape), unit=unit, axis=axis,
            window=dict(full), clock_basis="producer absolute grid indices", display_noise=False,
            availability="available", source_fields=[key], invocation_id=info["invocation_id"], **extra)

    count = len(context["known_compact"][0])
    add("ui_ests", raw["ui_ests"], "ps", "t", numerical_availability="masked",
        mask_field="ami.cdr.period_known", known_count=count, unknown_count=len(t) - count)
    add("ami.cdr.period_known", info["period_known"], "bool", "t")
    for name in CLOCK_FIELDS:
        add("ami.clock." + name, info[name], "s" if name.endswith("_s") else "sample index")
    for name, values, unit, axis in zip(("known_grid_indices", "known_times_s", "known_period_ps"),
            context["known_compact"], ("sample index", "s", "ps"),
            (None, None, "ami.cdr.known_times_s")):
        add("ami.cdr." + name, values, unit, axis)
        datasets["ami.cdr." + name].update(kind="compact reference", source_fields=["t", "ui_ests",
                                                              "ami.cdr.period_known"])
    fields = ("requested", "mode", "role", "main_origin", "format_status", "eligible", "actual_branch",
              "consumption_status", "consumed_count", "run_status", "full_analysis_eligible", "reason",
              "last_tick_status", "deferred_reasons", "ignore_ui", "symbol_ui_s", "nspui", "analysis", "profile",
              "profile_source", "model_qualification", "epoch_basis", "producer_contract_version", "invocation_id")
    return {"version": 2, **{name: copy.deepcopy(info.get(name)) for name in fields},
            "array_fields": {name: "ami.clock." + name for name in CLOCK_FIELDS},
            "period_field": "ui_ests", "mask_field": "ami.cdr.period_known", "grid_field": "t",
            "snapshot_phase": context["snapshot_phase"], "eye_consumers": context["eye_consumers"]}


def clock_features(run, archive_features=()):
    """Version, actual branch and required feature are one indivisible stored contract."""
    ami = run.get("ami")
    contract = ami.get("clock_contract") if isinstance(ami, dict) else None
    features = run.get("required_features", [])
    if type(features) is not list:
        raise ValueError("required_features must be a list of supported feature names")
    masked = run.get("raw_schema_version") in (6, 7)
    if masked:
        if run["raw_schema_version"] == 7:
            from pybert.web.clock_v3 import FEATURE

            if (type(run["raw_schema_version"]) is not int or features != [FEATURE]
                    or not isinstance(contract, dict) or type(contract.get("version")) is not int
                    or contract["version"] != 3 or contract.get("producer_contract_version") != 3
                    or type(contract.get("producer_contract_version")) is not int
                    or contract.get("actual_branch") != "ami" or contract.get("main_origin") != "same_init_after_probes"):
                raise ValueError("raw7 requires AMI same-Init clock contract3 and its feature together")
            if archive_features != () and archive_features != features:
                raise ValueError("Unsupported or mismatched required archive features")
            return list(features)
        if (type(run.get("raw_schema_version")) is not int
                or features != ["ami-clock-grid-v2"] or not isinstance(contract, dict)
                or type(contract.get("version")) is not int or contract["version"] != 2
                or contract.get("actual_branch") != "ami"):
            raise ValueError("raw6 requires AMI clock_contract2 and ami-clock-grid-v2 together")
    elif features or contract is not None:
        raise ValueError("AMI clock contract/feature cannot be downgraded or attached to a Native raw version")
    if archive_features != () and archive_features != features:
        raise ValueError("Unsupported or mismatched required archive features")
    return list(features)


def validate_clock_arrays(run, arrays):
    """Validate stored references without rebuilding decisions, Eye, histogram or FFT."""
    if not clock_features(run):
        return
    if run["raw_schema_version"] == 7:
        from pybert.web.clock_v3 import stored_context

        stored_context(run, arrays)
        return
    contract = run["ami"]["clock_contract"]
    if (contract.get("array_fields") != {name: "ami.clock." + name for name in CLOCK_FIELDS}
            or contract.get("period_field") != "ui_ests" or contract.get("grid_field") != "t"
            or contract.get("mask_field") != "ami.cdr.period_known"
            or contract.get("producer_contract_version") != 2 or not contract.get("invocation_id")
            or contract.get("main_origin") != "c1_fresh_main" or contract.get("role") != "main"
            or contract.get("mode") != "rx_getwave" or contract.get("format_status") != "valid"
            or not contract.get("requested") or not contract.get("eligible")
            or contract.get("run_status") != "completed" or contract.get("consumption_status") != "completed"
            or not contract.get("full_analysis_eligible")):
        raise ValueError("Incomplete saved producer clock contract")
    profile = contract.get("profile", {})
    if (type(contract.get("nspui")) is not int or contract["nspui"] < 1
            or not np.isfinite(contract["symbol_ui_s"]) or contract["symbol_ui_s"] <= 0
            or not np.isfinite(contract["ignore_ui"]) or contract["ignore_ui"] < 0
            or profile.get("ignore_ui_units") != "symbol_ui" or profile.get("nominal_eye_offset_ui") != 0
            or profile.get("mapping") not in ("native_nrz", "native_pam4")):
        raise ValueError("Invalid saved producer units, offset or mapping declaration")
    required = ("t", "ui_ests", "clock_times", "ami.cdr.period_known", "ami.cdr.known_grid_indices",
                "ami.cdr.known_times_s", "ami.cdr.known_period_ps", *contract["array_fields"].values())
    if any(name not in arrays for name in required):
        raise ValueError("Missing saved AMI producer arrays")
    for name, value in arrays.items():
        if value.dtype.kind not in "biufc" or name != "ui_ests" and not np.isfinite(value).all():
            raise ValueError("Nonfinite/nonnumeric array outside the exact ui_ests exception: " + name)
    t, known = arrays["t"], arrays["ami.cdr.period_known"]
    compact = validate_period(t, arrays["ui_ests"], known)
    if not len(compact[0]):
        raise ValueError("All-unknown AMI period is diagnostic only")
    for name, expected in zip(("known_grid_indices", "known_times_s", "known_period_ps"), compact):
        value = arrays["ami.cdr." + name]
        if value.dtype != expected.dtype or value.shape != expected.shape or value.tobytes() != expected.tobytes():
            raise ValueError("Saved known compact reference mismatch: " + name)
    values = {name: arrays[field] for name, field in contract["array_fields"].items()}
    indices, targets, times = (values[name] for name in ("sample_indices", "sample_targets_s", "sample_grid_times_s"))
    positions, edges = values["consumed_tick_positions"], values["edges_s"]
    if (indices.ndim != 1 or indices.dtype.kind not in "iu" or not len(indices)
            or np.any(indices < 0) or np.any(indices >= len(t)) or np.any(np.diff(indices) <= 0)
            or contract["consumed_count"] != len(indices) or np.any(np.diff(t) <= 0)
            or positions.shape != indices.shape or positions.dtype.kind not in "iu"
            or np.any(positions < 0) or np.any(positions >= len(edges)) or np.any(np.diff(positions) <= 0)
            or targets.shape != indices.shape or times.shape != indices.shape
            or edges.ndim != 1 or edges.dtype.kind != "f" or np.any(edges < 0) or np.any(np.diff(edges) <= 0)
            or not np.array_equal(values["targets_s"], edges + contract["symbol_ui_s"] / 2)
            or not np.array_equal(targets, values["targets_s"][positions])
            or not np.array_equal(times, t[indices]) or not np.array_equal(arrays["clock_times"], times)
            or np.any(targets < t[0]) or np.any(targets > t[-1]) or np.any(times < targets)
            or np.any(t[indices[indices > 0] - 1] >= targets[indices > 0])
            or not np.array_equal(values["sample_quantization_delay_s"], times - targets)):
        raise ValueError("Invalid saved producer indices/targets/grid times")
    window = contract["analysis"]
    start, stop, count = window["start_index"], window["stop_index"], window["required_decisions"]
    if (any(type(value) is not int for value in (start, stop, count)) or not 0 <= start < stop <= len(t)
            or count < 1 or not t[0] <= window["start_s"] <= window["stop_s"] <= t[-1]):
        raise ValueError("Invalid saved frozen analysis window")
    inside = ((indices >= start) & (indices < stop) & (targets >= window["start_s"])
              & (targets <= window["stop_s"]) & (times >= window["start_s"]) & (times <= window["stop_s"])
              & (targets >= contract["ignore_ui"] * contract["symbol_ui_s"]))
    if len(indices[inside]) < count or not np.array_equal(values["analysis_sample_indices"], indices[inside][-count:]):
        raise ValueError("Saved final W producer indices disagree")


def stored_clock_context(run, arrays):
    """Read an already saved contract for analysis; never generate a new invocation or execution claim."""
    if not clock_features(run):
        return None
    if run["raw_schema_version"] == 7:
        from pybert.web.clock_v3 import stored_context

        return stored_context(run, arrays)
    validate_clock_arrays(run, arrays)
    contract = run["ami"]["clock_contract"]
    info = {**contract, **{name: arrays[field] for name, field in contract["array_fields"].items()},
            "period_known": arrays["ami.cdr.period_known"]}
    indices, targets, times = (info[name] for name in ("sample_indices", "sample_targets_s", "sample_grid_times_s"))
    window = info["analysis"]
    inside = ((indices >= window["start_index"]) & (indices < window["stop_index"])
              & (targets >= window["start_s"]) & (targets <= window["stop_s"])
              & (times >= window["start_s"]) & (times <= window["stop_s"])
              & (targets >= info["ignore_ui"] * info["symbol_ui_s"]))
    return {"version": 2, "info": info, "raw": {"t": arrays["t"], "ui_ests": arrays["ui_ests"]},
            "window_indices": indices[inside], "snapshot_phase": "stored contract; no new Main invocation",
            "eye_consumers": contract.setdefault("eye_consumers", {})}


def write_partial(directory, snapshot, phases, terminal):
    """Preserve host-owned failure evidence in independent files, never a succeeded run archive."""
    from pathlib import Path
    from pybert.web.archive import array_identity, atomic_write, json_bytes

    directory = Path(directory)
    raw_path, manifest_path = directory / "partial-arrays.npz", directory / "partial-manifest.json"
    if raw_path.exists() or manifest_path.exists():
        raise FileExistsError("Existing partial evidence retained; refusing overwrite")
    if terminal.get("status") not in ("failed", "cancelled"):
        raise ValueError("Partial evidence requires an actual failed/cancelled terminal state")
    arrays, unavailable = {}, {}

    def pack(value, field):
        if isinstance(value, (np.ndarray, np.generic)) or isinstance(value, float) and not np.isfinite(value):
            value = np.asarray(value)
            if value.dtype.kind not in "biufc":
                unavailable[field] = "Object/nonnumeric array cannot be serialized safely without pickle"
                return {"availability": "unavailable", "reason": unavailable[field]}
            arrays[field] = value
            return {"array_field": field}
        if isinstance(value, dict):
            return {str(key): pack(item, field + "." + str(key)) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [pack(item, field + "." + str(index)) for index, item in enumerate(value)]
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        unavailable[field] = "Unsupported host value type: " + type(value).__name__
        return {"availability": "unavailable", "reason": unavailable[field]}

    record = {"format": "pybert-partial-clock-diagnostic", "schema_version": 1,
              "status": terminal["status"], "evidence_type": "diagnostic_partial_only",
              "run_qualification": "not evaluated", "phase": snapshot.get("phase"),
              "fresh": snapshot.get("fresh"), "producer": pack(snapshot.get("info"), "producer"),
              "raw": pack(snapshot.get("raw", {}), "raw"),
              "eye_consumers": pack(snapshot.get("eye_consumers", {}), "eye_consumers"),
              "phases_at_snapshot": pack(phases, "phases"), "terminal_at_snapshot": pack(terminal, "terminal"),
              "unavailable_fields": unavailable,
              "buffer_scope": "host producer raw; full ABI buffers remain separate B diagnostics"}
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    record["arrays"] = {key: array_identity(value) for key, value in arrays.items()}
    atomic_write(raw_path, buffer.getvalue())
    atomic_write(manifest_path, json_bytes(record))
    return record
