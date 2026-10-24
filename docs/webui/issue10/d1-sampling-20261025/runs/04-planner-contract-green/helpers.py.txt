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
