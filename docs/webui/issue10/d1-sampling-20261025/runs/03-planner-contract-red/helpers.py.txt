"""Native Rx GetWave sampling and its producer-owned analysis coordinates."""

import numpy as np


def new_clock_info(requested=False, mode="native", origin=None):
    """Start a fresh producer record; no plan is evidence of completed consumption."""
    return {"requested": bool(requested), "mode": mode, "role": "main", "main_origin": origin,
            "format_status": "not_checked", "consumption_status": "not_attempted", "consumed_count": 0}


def plan_ami_clocks(info, edges, t_grid, symbol_ui, ignore_ui, nspui, window, *, modulation="NRZ", profile=None):
    """Map edge plus half a symbol UI to the first available absolute grid index."""
    edges = np.array(edges, dtype=float, copy=True)
    grid = np.array(t_grid, dtype=float, copy=True)
    targets = edges + symbol_ui / 2
    in_record = (targets >= grid[0]) & (targets <= grid[-1])
    info.update(format_status="valid", edges_s=edges, targets_s=targets, grid_s=grid,
                planned_tick_positions=np.flatnonzero(in_record),
                planned_indices=np.searchsorted(grid, targets[in_record], side="left"),
                symbol_ui_s=symbol_ui, ignore_ui=ignore_ui, nspui=nspui,
                analysis={**window, "fft_slice": tuple(window["fft_slice"])})
    return info
