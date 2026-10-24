"""Native Rx GetWave sampling and its producer-owned analysis coordinates."""

import numpy as np


def new_clock_info(requested=False, mode="native", origin=None):
    """Start a fresh producer record; no plan is evidence of completed consumption."""
    return {"requested": bool(requested), "mode": mode, "role": "main", "main_origin": origin,
            "format_status": "not_checked", "consumption_status": "not_attempted", "consumed_count": 0,
            "actual_branch": "not_attempted", "reason": None, "full_analysis_eligible": False}


def plan_ami_clocks(info, edges, t_grid, symbol_ui, ignore_ui, nspui, window, *, modulation="NRZ", profile=None):
    """Map edge plus half a symbol UI to the first available absolute grid index."""
    def reject(reason, invalid_format=False):
        info.update(reason=reason, eligible=False)
        if invalid_format:
            info["format_status"] = "invalid"
        raise ValueError(reason)

    try:
        edges = np.array(edges, dtype=float, copy=True)
    except (TypeError, ValueError):
        reject("malformed_clocks", True)
    info["edges_s"] = edges
    if edges.ndim != 1 or not np.all(np.isfinite(edges)) or np.any(edges < 0) or np.any(np.diff(edges) <= 0):
        reject("malformed_clocks", True)
    info["format_status"] = "valid"
    grid = np.array(t_grid, dtype=float, copy=True)
    if grid.ndim != 1 or not len(grid) or not np.all(np.isfinite(grid)) or np.any(np.diff(grid) <= 0):
        reject("invalid_grid")
    ignore_ui = 0.0 if ignore_ui is None else ignore_ui
    if not np.isfinite(symbol_ui) or symbol_ui <= 0 or not np.isfinite(ignore_ui) or ignore_ui < 0 or nspui <= 0:
        reject("invalid_timing")
    if not info["requested"] or info["mode"] != "rx_getwave":
        reject("unsupported_mode")
    if info["main_origin"] != "c1_fresh_main":
        reject("unknown_origin")
    start, stop = window["start_index"], window["stop_index"]
    fft_start, fft_stop = window["fft_slice"]
    if not (0 <= start < stop <= len(grid) and grid[0] <= window["start_s"] <= window["stop_s"] <= grid[-1]
            and start <= fft_start <= fft_stop <= stop and window["required_decisions"] > 0
            and window["required_eye_traces"] > 0):
        reject("invalid_window")
    info.update(grid_s=grid, symbol_ui_s=symbol_ui, ignore_ui=ignore_ui, nspui=nspui,
                analysis={**window, "fft_slice": tuple(window["fft_slice"])},
                sample_indices=np.array([], dtype=int), sample_grid_times_s=np.array([]),
                consumed_tick_positions=np.array([], dtype=int), period_s=np.full(len(grid), np.nan),
                period_known=np.zeros(len(grid), dtype=bool), use_native=False)
    if not len(edges):
        info.update(format_status="no_clocks", reason="no_clocks", use_native=True, eligible=False,
                    targets_s=np.array([]), planned_indices=np.array([], dtype=int),
                    planned_tick_positions=np.array([], dtype=int), deferred_reasons=[], last_tick_status="none")
        return info
    declared = profile
    if modulation == "NRZ" and declared is None:
        declared = {"ignore_ui_units": "symbol_ui", "nominal_eye_offset_ui": 0, "mapping": "native_nrz"}
    if (modulation not in {"NRZ", "PAM4"} or declared is None
            or declared.get("ignore_ui_units") != "symbol_ui" or declared.get("nominal_eye_offset_ui") != 0
            or declared.get("mapping") != {"NRZ": "native_nrz", "PAM4": "native_pam4"}.get(modulation)):
        info["profile_status"] = "UNKNOWN: Ignore_UI units, nominal offset and slicer mapping require declaration"
        reject("unsupported_profile")
    targets = edges + symbol_ui / 2
    in_record = (targets >= grid[0]) & (targets <= grid[-1])
    positions = np.flatnonzero(in_record)
    indices = np.searchsorted(grid, targets[in_record], side="left")
    info.update(targets_s=targets, planned_tick_positions=positions, planned_indices=indices,
                deferred_reasons=[None if ok else "before_record" if target < grid[0] else "future"
                                  for target, ok in zip(targets, in_record)],
                planned_ready=targets[in_record] >= ignore_ui * symbol_ui,
                quantization_delay_s=grid[indices] - targets[in_record], profile=dict(declared),
                profile_source="software_declaration" if profile is not None else "nrz_ui_contract",
                model_qualification="UNKNOWN", eligible=bool(len(indices)),
                reason=None if len(indices) else "out_of_record",
                last_tick_status="planned" if in_record[-1] else "deferred")
    if np.any(np.diff(indices) <= 0):
        reject("unsupported_resolution")
    return info


def consume_ami_clocks(info, waveform, decide, check_cancel=None):
    """Consume actual samples, keeping every completed decision even when a later step fails."""
    grid = info["grid_s"]
    waveform = np.asarray(waveform)
    if waveform.ndim != 1 or len(waveform) != len(grid) or info["use_native"]:
        info["reason"] = "invalid_consumer_input"
        raise ValueError("invalid_consumer_input")
    info["actual_branch"] = "ami"
    indices, positions, samples, decisions, bits = [], [], [], [], []
    attempts = 0
    loop_finished = False
    try:
        for tick, index in zip(info["planned_tick_positions"], info["planned_indices"]):
            info["last_attempted_tick_position"] = int(tick)
            if check_cancel is not None:
                check_cancel()
            attempts += 1
            value = waveform[index]
            decision, returned_bits = decide(value)
            bits.extend(returned_bits)
            positions.append(int(tick))
            indices.append(int(index))
            samples.append(value)
            decisions.append(decision)
        loop_finished = True
    except BaseException as error:
        info.update(reason="consumption_failed", error_type=type(error).__name__, error_message=str(error))
        raise
    finally:
        indices = np.asarray(indices, dtype=int)
        positions = np.asarray(positions, dtype=int)
        targets = info["targets_s"][positions]
        actual_times = grid[indices]
        period = np.full(len(grid), np.nan)
        known = np.zeros(len(grid), dtype=bool)
        for left in range(len(indices) - 1):
            if positions[left + 1] == positions[left] + 1:
                interval = slice(indices[left], indices[left + 1])
                period[interval] = info["edges_s"][positions[left + 1]] - info["edges_s"][positions[left]]
                known[interval] = True
        clocks = np.zeros(len(grid))
        clocks[indices] = 1
        ready = targets >= info["ignore_ui"] * info["symbol_ui_s"]
        window = info["analysis"]
        inside = (ready & (targets >= window["start_s"]) & (targets <= window["stop_s"])
                  & (actual_times >= window["start_s"]) & (actual_times <= window["stop_s"])
                  & (indices >= window["start_index"]) & (indices < window["stop_index"]))
        analysis_indices = indices[inside]
        eye_indices = analysis_indices[analysis_indices + 2 * info["nspui"] <= window["stop_index"]]
        fft_start, fft_stop = window["fft_slice"]
        period_eligible = fft_stop - fft_start >= 2 and bool(np.all(known[fft_start:fft_stop]))
        full = (loop_finished and len(analysis_indices) >= window["required_decisions"]
                and len(eye_indices) >= window["required_eye_traces"] and period_eligible)
        info.update(sample_indices=indices, consumed_tick_positions=positions, consumed_count=len(indices),
                    sample_grid_times_s=actual_times, sample_targets_s=targets,
                    sample_quantization_delay_s=actual_times - targets, adaptation_ready=ready,
                    sample_values=np.asarray(samples), decisions=np.asarray(decisions), bits=list(bits),
                    clock_mask=clocks, period_s=period, period_known=known,
                    analysis_sample_indices=analysis_indices[-window["required_decisions"]:],
                    eye_sample_indices=eye_indices, eye_eligible_trace_count=len(eye_indices),
                    eye_trace_count=0, eye_status="not_attempted", attempted_count=attempts,
                    period_window_eligible=period_eligible, loop_finished=loop_finished,
                    full_analysis_eligible=bool(full), consumption_status="completed" if full else "partial")
        info.setdefault("model_lock_status", "unavailable")
        if len(positions) and positions[-1] == len(info["edges_s"]) - 1:
            info["last_tick_status"] = "consumed"
        elif info["deferred_reasons"][-1] is not None:
            info["last_tick_status"] = "deferred"
        else:
            info["last_tick_status"] = "not_consumed"
        if loop_finished:
            info["reason"] = None if full else "insufficient_coverage"
    if not info["full_analysis_eligible"]:
        raise ValueError("insufficient_coverage")
    return info


def ami_eye_data(info, waveform, ignore_samps, height, y_max, calc_eye):
    """Draw timed traces from producer indices in this exact waveform crop, or report unavailable."""
    info.update(eye_status="not_attempted", eye_trace_count=0)
    absolute = np.asarray(info["eye_sample_indices"])
    relative = absolute - ignore_samps
    width = 2 * info["nspui"]
    usable = ((relative >= 0) & (relative + width <= len(waveform))
              & (absolute + width <= info["analysis"]["stop_index"]))
    relative = relative[usable]
    info["eye_relative_indices"] = relative
    info["eye_eligible_trace_count"] = len(relative)
    if not info["full_analysis_eligible"] or len(relative) < info["analysis"]["required_eye_traces"]:
        info.update(eye_status="unavailable", eye_reason="insufficient_timed_traces")
        return None
    try:
        image = calc_eye(info["symbol_ui_s"], info["nspui"], height, waveform, y_max, clock_indices=relative)
    except BaseException:
        info.update(eye_status="partial", eye_trace_count=None, eye_reason="eye_calculation_failed")
        raise
    info.update(eye_status="completed", eye_trace_count=len(relative), eye_reason=None)
    return image
