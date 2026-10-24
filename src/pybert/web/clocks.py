"""Producer-owned AMI clock records shared by Web consumers and archive validation."""

import copy

import numpy as np


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
    if (not info or info.get("producer_contract_version") != 2 or not snapshot.get("fresh")
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
            "window_indices": selected, "snapshot_phase": snapshot["phase"]}


def eye_selection(context, slice_start, slice_stop):
    """Apply the actual crop and frozen stop to the same producer indices, without seconds rounding."""
    info = context["info"]
    stop = min(slice_stop, info["analysis"]["stop_index"], len(context["raw"]["t"]))
    if type(slice_start) is not int or type(slice_stop) is not int or not 0 <= slice_start <= stop:
        raise ValueError("Invalid actual waveform crop")
    width = 2 * info["nspui"]
    selected = context["window_indices"]
    absolute = selected[(selected >= slice_start) & (selected + width <= stop)]
    relative = absolute - slice_start
    return relative, {"clock_basis": "producer absolute grid indices", "consumed_count": info["consumed_count"],
                      "window_sample_count": len(selected), "eligible_trace_count": len(relative),
                      "trace_count": 0, "absolute_indices": absolute.tolist(), "relative_indices": relative.tolist(),
                      "slice_start": slice_start, "slice_stop": stop, "width": width,
                      "invocation_id": info["invocation_id"], "source_fields": ["ami.clock.sample_indices",
                      "ami.clock.sample_targets_s", "ami.clock.sample_grid_times_s"],
                      "window": dict(info["analysis"]), "availability": "available" if len(relative) else "unavailable",
                      "reason": None if len(relative) else "no_complete_timed_trace"}
