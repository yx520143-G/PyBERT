"""Native Rx GetWave sampling and its producer-owned analysis coordinates."""

from fractions import Fraction
from time import monotonic_ns

import numpy as np

ANALYSIS_BOUNDARY_BASIS = "exact Main grid timestamps use their epoch sample; off-grid bounds use one rounded pre-duration + local time"


def new_clock_info(requested=False, mode="native", origin=None, *, contract_version=2):
    """Start a fresh producer record; no plan is evidence of completed consumption."""
    if type(contract_version) is not int or contract_version not in (2, 3):
        raise ValueError("unsupported producer contract")
    return {"producer_contract_version": contract_version, "invocation_id": str(monotonic_ns()),
            "epoch_basis": "analysis invocation identifier; not the model Init epoch",
            "requested": bool(requested), "mode": mode, "role": "main", "main_origin": origin,
            "format_status": "not_checked", "consumption_status": "not_attempted", "consumed_count": 0,
            "actual_branch": "not_attempted", "reason": None, "full_analysis_eligible": False,
            "run_status": "not_completed"}


def map_same_epoch_clocks(observations, t_grid, symbol_ui, ignore_ui):
    """Observe probe/Main coordinates from actual calls; this is not a timed-consumption permission."""
    def require(condition):
        if not condition:
            raise ValueError("invalid_origin_evidence")

    try:
        entry, history = observations["main_entry"], observations["history"]
        calls = history["invocations"]
        ts = history["sample_interval_s"]
        require(observations["status"] == "complete" and history["ready"] is True
                and bool(history["epoch_id"]) and entry["epoch_id"] == history["epoch_id"]
                and np.isfinite(ts) and ts > 0 and entry["sample_interval_s"] == ts
                and entry["python_calls"] == 2 and history["python_calls"] == 3 and len(calls) == 3)
        raw, sources, sample_counts, c_call = [], [], [], 0
        for number, invocation in enumerate(calls, 1):
            require(invocation["completed"] is True and invocation["python_call"] == number
                    and type(invocation["input_samples"]) is int and invocation["input_samples"] > 0)
            count = 0
            for chunk in invocation["chunks"]:
                c_call += 1
                require(chunk["epoch"] == history["epoch"] and chunk["python_call"] == number
                        and chunk["c_call"] == c_call and chunk["returned"] is True
                        and chunk["status"] == 1 and chunk["phase"] == "complete"
                        and type(chunk["wave_size"]) is int and chunk["wave_size"] > 0)
                count += chunk["wave_size"]
                raw.extend(chunk["valid_clocks"])
                sources.extend([(number, c_call)] * len(chunk["valid_clocks"]))
            require(count == invocation["input_samples"])
            sample_counts.append(count)
            if number == 2:
                require(entry["c_calls"] == c_call)
        require(history["c_calls"] == c_call)
        edges, grid = np.array(raw, dtype=float), np.array(t_grid, dtype=float, copy=True)
        require(edges.ndim == 1 and np.all(np.isfinite(edges)) and not np.any(edges < 0)
                and not np.any(np.diff(edges) <= 0))
        require(grid.ndim == 1 and len(grid) == sample_counts[2] and np.all(np.isfinite(grid))
                and np.array_equal(grid, np.arange(len(grid)) * ts) and np.all(np.diff(grid) > 0))
        ignore_ui = 0.0 if ignore_ui is None else ignore_ui
        require(np.isfinite(symbol_ui) and symbol_ui > 0 and np.isfinite(ignore_ui) and ignore_ui >= 0)
        pre_samples = sum(sample_counts[:2])
        pre_time = pre_samples * ts
        epoch_targets = edges + symbol_ui / 2
        epoch_grid = (pre_samples + np.arange(len(grid))) * ts
        # One scalar, rounded once from the binary inputs: do not round T_pre separately and
        # accidentally move a Main-local readiness threshold across an adjacent epoch target.
        readiness_epoch = float(pre_samples * Fraction(float(ts))
                                + Fraction(float(ignore_ui)) * Fraction(float(symbol_ui)))
        targets = epoch_targets - pre_time
        require(np.isfinite(readiness_epoch) and np.all(np.isfinite(epoch_targets))
                and np.all(np.isfinite(epoch_grid)) and np.all(np.diff(epoch_grid) > 0))
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError("invalid_origin_evidence") from error
    # Compare one absolute coordinate system. Subtracting T_pre before ceil can move an exact
    # epoch-grid hit one sample later through cancellation/independent local-grid rounding.
    in_record = (epoch_targets >= epoch_grid[0]) & (epoch_targets <= epoch_grid[-1])
    positions = np.flatnonzero(in_record)
    indices = np.searchsorted(epoch_grid, epoch_targets[in_record], side="left")
    if np.any(np.diff(indices) <= 0):
        raise ValueError("unsupported_resolution")
    return {"status": "mapped", "epoch_id": history["epoch_id"], "sample_interval_s": ts,
            "pre_samples": pre_samples, "pre_time_s": pre_time, "main_samples": sample_counts[2],
            "raw_epoch_edges_s": edges, "tick_sources": np.array(sources, dtype=int).reshape(-1, 2),
            "main_returned_edges_s": np.array([tick for chunk in calls[2]["chunks"]
                                                for tick in chunk["valid_clocks"]]),
            "main_local_edges_s": edges - pre_time, "targets_s": targets,
            "epoch_targets_s": epoch_targets, "sample_epoch_times_s": epoch_grid[indices],
            "comparison_basis": "epoch target against (pre_samples + sample_index) * Init ts",
            "readiness_threshold_epoch_s": readiness_epoch,
            "planned_tick_positions": positions, "planned_indices": indices,
            "planned_ready": epoch_targets[in_record] >= readiness_epoch,
            "quantization_delay_s": epoch_grid[indices] - epoch_targets[in_record],
            "deferred_reasons": [None if ok else "before_record" if target < epoch_grid[0] else "future"
                                  for target, ok in zip(epoch_targets, in_record)],
            "readiness_basis": "Main-local Ignore_Bits * symbol_UI threshold, compared in epoch coordinates",
            "model_qualification": "UNKNOWN", "consumption_permission": "unsupported_pending_contract"}


def plan_ami_clocks(info, edges, t_grid, symbol_ui, ignore_ui, nspui, window, *, modulation="NRZ", profile=None):
    """Map edge plus half a symbol UI to the first available absolute grid index."""
    def reject(reason, invalid_format=False):
        info.update(dict(reason=reason, eligible=False))
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
    start, stop = window["start_index"], window["stop_index"]
    fft_start, fft_stop = window["fft_slice"]
    if not (0 <= start < stop <= len(grid) and grid[0] <= window["start_s"] <= window["stop_s"] <= grid[-1]
            and start <= fft_start <= fft_stop <= stop and window["required_decisions"] > 0
            and window["required_eye_traces"] > 0):
        reject("invalid_window")
    info.update(dict(grid_s=grid, symbol_ui_s=symbol_ui, ignore_ui=ignore_ui, nspui=nspui,
                analysis={**window, "fft_slice": tuple(window["fft_slice"])},
                sample_indices=np.array([], dtype=int), sample_grid_times_s=np.array([]),
                consumed_tick_positions=np.array([], dtype=int), period_s=np.full(len(grid), np.nan),
                period_known=np.zeros(len(grid), dtype=bool), use_native=False))
    if info["producer_contract_version"] == 3 and (info["main_origin"] != "same_init_after_probes"
                                                  or "origin_observations" not in info):
        reject("invalid_origin_evidence")
    if info["main_origin"] == "same_init_after_probes" and "origin_observations" in info:
        try:
            mapping = map_same_epoch_clocks(info["origin_observations"], grid, symbol_ui, ignore_ui)
            if not np.array_equal(edges, mapping["main_returned_edges_s"]):
                raise ValueError("main_clocks_receipt_mismatch")
            info["origin_mapping"] = mapping
        except ValueError as error:
            info["origin_mapping"] = {"status": "unavailable", "reason": str(error)}
            reject("invalid_origin_evidence")
        # A probe can supply a Main-boundary tick even when Main itself returned no clocks.
        if len(mapping["raw_epoch_edges_s"]):
            if info["producer_contract_version"] != 3:
                reject("unsupported_origin_mapping")
            declared = {"ignore_ui_units": "symbol_ui", "nominal_eye_offset_ui": 0, "mapping": "native_nrz"}
            if modulation != "NRZ" or profile is not None and profile != declared:
                reject("unsupported_profile")
            info.update({"edges_s": mapping["raw_epoch_edges_s"], "targets_s": mapping["targets_s"],
                         "planned_tick_positions": mapping["planned_tick_positions"],
                         "planned_indices": mapping["planned_indices"], "planned_ready": mapping["planned_ready"],
                         "quantization_delay_s": mapping["quantization_delay_s"],
                         "deferred_reasons": mapping["deferred_reasons"], "profile": declared,
                         "profile_source": "nrz_ui_contract", "model_qualification": "UNKNOWN", "eligible": True,
                         "reason": None, "last_tick_status": "planned" if mapping["deferred_reasons"][-1] is None else "deferred"})
            mapping["consumption_permission"] = "software_nrz_contract_v3; model qualification UNKNOWN"
            info["analysis_epoch_bounds_s"] = epoch_analysis_bounds(info)
            info["analysis_boundary_basis"] = ANALYSIS_BOUNDARY_BASIS
            return info
    if not len(edges):
        info.update(dict(format_status="no_clocks", reason="no_clocks", use_native=True, eligible=False,
                    targets_s=np.array([]), planned_indices=np.array([], dtype=int),
                    planned_tick_positions=np.array([], dtype=int), deferred_reasons=[], last_tick_status="none"))
        return info
    if info["main_origin"] != "c1_fresh_main":
        reject("unsupported_origin_mapping" if info["main_origin"] == "same_init_after_probes" else "unknown_origin")
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
    info.update(dict(targets_s=targets, planned_tick_positions=positions, planned_indices=indices,
                deferred_reasons=[None if ok else "before_record" if target < grid[0] else "future"
                                  for target, ok in zip(targets, in_record)],
                planned_ready=targets[in_record] >= ignore_ui * symbol_ui,
                quantization_delay_s=grid[indices] - targets[in_record], profile=dict(declared),
                profile_source="software_declaration" if profile is not None else "nrz_ui_contract",
                model_qualification="UNKNOWN", eligible=bool(len(indices)),
                reason=None if len(indices) else "out_of_record",
                last_tick_status="planned" if in_record[-1] else "deferred"))
    if np.any(np.diff(indices) <= 0):
        reject("unsupported_resolution")
    return info


def epoch_analysis_bounds(info):
    """An exact grid timestamp denotes its epoch sample; other bounds retain their local time."""
    mapping, window = info["origin_mapping"], info["analysis"]
    grid, ts = info["grid_s"], mapping["sample_interval_s"]
    pre = mapping["pre_samples"] * Fraction(float(mapping["sample_interval_s"]))
    bounds = []
    for name in ("start_s", "stop_s"):
        value = window[name]
        index = int(np.searchsorted(grid, value, side="left"))
        bounds.append((mapping["pre_samples"] + index) * ts if index < len(grid) and grid[index] == value
                      else float(pre + Fraction(float(value))))
    return np.asarray(bounds)


def analysis_sample_mask(info, indices, positions):
    """Select the frozen window in the same epoch coordinates used for F5 ceil/readiness."""
    mapping, window = info["origin_mapping"], info["analysis"]
    targets = mapping["epoch_targets_s"][positions]
    first, stop = epoch_analysis_bounds(info)
    ready = targets >= mapping["readiness_threshold_epoch_s"]
    times = info["grid_s"][indices]
    inside = (ready & (targets >= first) & (targets <= stop)
              & (times >= window["start_s"]) & (times <= window["stop_s"])
              & (indices >= window["start_index"]) & (indices < window["stop_index"]))
    return ready, inside


def consume_ami_clocks(info, waveform, decide, check_cancel=None):
    """Consume actual samples, keeping every completed decision even when a later step fails."""
    grid = info["grid_s"]
    waveform = np.asarray(waveform)
    if waveform.ndim != 1 or len(waveform) != len(grid) or info["use_native"]:
        info["reason"] = "invalid_consumer_input"
        raise ValueError("invalid_consumer_input")
    info["actual_branch"] = "ami"
    independent = info["producer_contract_version"] == 3
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
            if independent and (not np.isfinite(value) or not np.isfinite(decision)
                                or len(returned_bits) != 1 or returned_bits[0] not in (0, 1)):
                raise ValueError("invalid_nrz_decision")
            bits.extend(returned_bits)
            positions.append(int(tick))
            indices.append(int(index))
            samples.append(value)
            decisions.append(decision)
        loop_finished = True
    except BaseException as error:
        info.update(dict(reason="consumption_failed", error_type=type(error).__name__, error_message=str(error)))
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
        delays = actual_times - targets
        if independent:
            ready, inside = analysis_sample_mask(info, indices, positions)
            delays = info["origin_mapping"]["quantization_delay_s"][:len(indices)]
        analysis_indices = indices[inside]
        eye_indices = analysis_indices[analysis_indices + 2 * info["nspui"] <= window["stop_index"]]
        fft_start, fft_stop = window["fft_slice"]
        period_eligible = fft_stop - fft_start >= 2 and bool(np.all(known[fft_start:fft_stop]))
        full = (loop_finished and len(analysis_indices) >= window["required_decisions"]
                and len(eye_indices) >= window["required_eye_traces"] and period_eligible)
        info.update(dict(sample_indices=indices, consumed_tick_positions=positions, consumed_count=len(indices),
                    sample_grid_times_s=actual_times, sample_targets_s=targets,
                    sample_quantization_delay_s=delays, adaptation_ready=ready,
                    sample_values=np.asarray(samples), decisions=np.asarray(decisions), bits=list(bits),
                    clock_mask=clocks, period_s=period, period_known=known,
                    analysis_sample_indices=analysis_indices[-window["required_decisions"]:],
                    eye_sample_indices=eye_indices, eye_eligible_trace_count=len(eye_indices),
                    eye_trace_count=0, eye_status="not_attempted", attempted_count=attempts,
                    period_window_eligible=period_eligible, loop_finished=loop_finished,
                    full_analysis_eligible=bool(full), consumption_status="completed" if full else "partial"))
        if independent:
            info.update({"window_sample_indices": analysis_indices,
                         "ber_eligible": bool(loop_finished and len(analysis_indices) >= window["required_decisions"]),
                         "consumption_status": "completed" if loop_finished else "partial"})
        info.setdefault("model_lock_status", "unavailable")
        if len(positions) and positions[-1] == len(info["edges_s"]) - 1:
            info["last_tick_status"] = "consumed"
        elif info["deferred_reasons"][-1] is not None:
            info["last_tick_status"] = "deferred"
        else:
            info["last_tick_status"] = "not_consumed"
        if loop_finished:
            info["reason"] = None if independent or full else "insufficient_coverage"
    if not independent and not info["full_analysis_eligible"]:
        raise ValueError("insufficient_coverage")
    return info


def ami_eye_data(info, waveform, ignore_samps, height, y_max, calc_eye):
    """Draw timed traces from producer indices in this exact waveform crop, or report unavailable."""
    info.update(dict(eye_status="not_attempted", eye_trace_count=0))
    absolute = np.asarray(info["eye_sample_indices"])
    relative = absolute - ignore_samps
    width = 2 * info["nspui"]
    usable = ((relative >= 0) & (relative + width <= len(waveform))
              & (absolute + width <= info["analysis"]["stop_index"]))
    relative = relative[usable]
    info["eye_relative_indices"] = relative
    info["eye_eligible_trace_count"] = len(relative)
    complete = info["loop_finished"] if info["producer_contract_version"] == 3 else info["full_analysis_eligible"]
    if not complete or len(relative) < info["analysis"]["required_eye_traces"]:
        info.update(dict(eye_status="unavailable", eye_reason="insufficient_timed_traces"))
        return None
    try:
        image = calc_eye(info["symbol_ui_s"], info["nspui"], height, waveform, y_max, clock_indices=relative)
    except BaseException:
        info.update(dict(eye_status="partial", eye_trace_count=None, eye_reason="eye_calculation_failed"))
        raise
    info.update(dict(eye_status="completed", eye_trace_count=len(relative), eye_reason=None))
    return image


def clock_period_data(info, t_grid, ts):
    """Project known periods without filling gaps or choosing a new FFT window after observing data."""
    period = np.asarray(info.get("period_s", []), dtype=float)
    known = np.asarray(info.get("period_known", []))
    grid = np.asarray(t_grid)
    result = {"plot_t_ns": np.array([]), "plot_period_ps": np.array([]),
              "histogram_bins_ps": np.array([]), "histogram_counts": np.array([]),
              "frequency_hz": np.array([]), "spectrum": np.array([], dtype=complex),
              "spectrum_display_eligible": False, "spectrum_display_reason": "fft_unavailable"}
    if not len(period) and not len(known):
        info["period_analysis"] = {"histogram_status": "unavailable", "fft_status": "unavailable"}
        return result
    if (period.ndim != 1 or known.ndim != 1 or grid.ndim != 1 or known.dtype.kind != "b"
            or len(period) != len(known) or len(period) != len(grid)
            or np.any(~np.isfinite(period[known])) or np.any(~np.isnan(period[~known]))):
        raise ValueError("period mask must match the grid, finite known values and NaN unknown values")
    if not np.isfinite(ts) or ts <= 0:
        raise ValueError("positive sample interval required")
    period_ps = period * 1e12
    result.update(plot_t_ns=np.array(grid, copy=True) * 1e9, plot_period_ps=period_ps)
    window = info["analysis"]
    indices = np.arange(len(grid))
    inside = ((indices >= window["start_index"]) & (indices < window["stop_index"])
              & (grid >= window["start_s"]) & (grid <= window["stop_s"]))
    input_complete = (info.get("loop_finished", info.get("consumption_status") == "completed")
                      and (info.get("producer_contract_version") == 3 or info["full_analysis_eligible"]))
    hist_status = fft_status = "sampling_incomplete"
    fft_window = None
    if input_complete:
        values = period_ps[known & inside]
        hist_status = "no_known_values"
        if len(values):
            counts, edges = np.histogram(values, bins=100)
            result.update(histogram_counts=counts, histogram_bins_ps=(edges[:-1] + edges[1:]) / 2)
            hist_status = "available"
        first, stop = window["fft_slice"]
        if stop - first < 2:
            fft_status = "insufficient_period_window"
        elif not (0 <= first < stop <= len(grid)) or not bool(np.all(inside[first:stop])):
            fft_status = "outside_frozen_window"
        elif not bool(np.all(known[first:stop])):
            fft_status = "unknown_period"
        else:
            spectrum = np.fft.rfft(period_ps[first:stop])
            frequencies = np.arange(len(spectrum), dtype=float) / ((stop - first) * ts)
            result.update(spectrum=spectrum, frequency_hz=frequencies)
            fft_status, fft_window = "available", [int(first), int(stop)]
            display = len(spectrum) > 1 and abs(spectrum[1]) > 0 and bool(np.all(np.isfinite(spectrum)))
            result.update(spectrum_display_eligible=bool(display),
                          spectrum_display_reason="available" if display else "zero_fundamental")
    info["period_analysis"] = {"histogram_status": hist_status, "fft_status": fft_status,
                               "histogram_window_indices": [window["start_index"], window["stop_index"]],
                               "declared_fft_window_indices": list(window["fft_slice"]),
                               "fft_window_indices": fft_window, "sample_interval_s": ts,
                               "frozen_time_bounds_s": [window["start_s"], window["stop_s"]],
                               "fft_sample_time_bounds_s": None if fft_window is None else
                               [float(grid[fft_window[0]]), float(grid[fft_window[1] - 1])],
                               "frequency_hz": result["frequency_hz"], "spectrum": result["spectrum"],
                               "spectrum_display_reason": result["spectrum_display_reason"]}
    return result


def set_period_plot_data(plotdata, period_t_ns, period_ps):
    """Publish an independent clock-period axis and its values as one plot-data event."""
    x, y = np.array(period_t_ns, copy=True), np.array(period_ps, copy=True)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y):
        raise ValueError("period plot arrays require matching lengths")
    plotdata.update_data(period_t_ns=x, ui_ests=y)
