"""Software clock-origin receipts, checked against integer sample coordinates."""

from copy import deepcopy

import numpy as np
import pytest
from traits.api import Dict, HasTraits

from pybert.utility import ami_clock


def receipt():
    calls, c_call = [], 0
    # Probe 2's final edge is before Main, but its half-UI target is inside Main.
    for number, sizes, ticks in [(1, [4, 1], [[0.], []]), (2, [4, 2], [[1.], [2.5]]),
                                  (3, [4, 4, 1], [[3.], [4.], [5.]])]:
        chunks = []
        for size, edges in zip(sizes, ticks):
            c_call += 1
            chunks.append({"epoch": 1, "python_call": number, "c_call": c_call, "wave_size": size,
                           "status": 1, "returned": True, "phase": "complete", "valid_clocks": tuple(edges)})
        calls.append({"python_call": number, "input_samples": sum(sizes), "completed": True, "chunks": chunks})
    return {"status": "complete", "main_entry": {"epoch_id": "instance-A/init-1", "python_calls": 2,
             "c_calls": 4, "sample_interval_s": .25},
            "history": {"epoch_id": "instance-A/init-1", "epoch": 1, "sample_interval_s": .25,
                        "python_calls": 3, "c_calls": 7, "ready": True, "invocations": calls}}


def mapped(data, grid=None):
    return ami_clock.map_same_epoch_clocks(data, np.arange(9) / 4 if grid is None else grid, 1., 1.)


def test_mapping_matches_independent_epoch_integer_grid():
    data = receipt()
    original = deepcopy(data)
    result = mapped(data)
    assert data == original
    assert result["pre_samples"] == 11 and result["pre_time_s"] == 2.75
    np.testing.assert_array_equal(result["raw_epoch_edges_s"], [0., 1., 2.5, 3., 4., 5.])
    # Compare epoch-grid integers (quarter-seconds), without using the product translation.
    targets_quarters = [2, 6, 12, 14, 18, 22]
    oracle = [next(i for i, sample in enumerate(range(11, 20)) if sample >= target)
              for target in targets_quarters if 11 <= target <= 19]
    np.testing.assert_array_equal(result["planned_indices"], oracle)
    np.testing.assert_array_equal(result["planned_tick_positions"], [2, 3, 4])
    np.testing.assert_array_equal(result["main_local_edges_s"], [-2.75, -1.75, -.25, .25, 1.25, 2.25])
    np.testing.assert_array_equal(result["planned_ready"], [False, False, True])
    assert result["deferred_reasons"] == ["before_record", "before_record", None, None, None, "future"]
    assert result["model_qualification"] == "UNKNOWN"


@pytest.mark.parametrize("change", [
    lambda d: d.update(status="incomplete"),
    lambda d: d["main_entry"].update(epoch_id="different-instance"),
    lambda d: d["main_entry"].update(sample_interval_s=.5),
    lambda d: d["main_entry"].update(c_calls=3),
    lambda d: d["history"].update(ready=False),
    lambda d: d["history"].update(python_calls=4),
    lambda d: d["history"]["invocations"][0].update(completed=False),
    lambda d: d["history"]["invocations"][1].update(input_samples=7),
    lambda d: d["history"]["invocations"][2]["chunks"][0].update(epoch=2),
    lambda d: d["history"]["invocations"][0]["chunks"][0].update(wave_size=None),
    lambda d: d["history"]["invocations"][0]["chunks"][0].update(status=0),
    lambda d: d["history"]["invocations"][1]["chunks"][1].update(valid_clocks=(float("nan"),)),
    lambda d: d["history"]["invocations"][1]["chunks"][1].update(valid_clocks=(-.25,)),
    lambda d: d["history"]["invocations"][2]["chunks"][0].update(valid_clocks=(2.5,)),
])
def test_missing_or_inconsistent_receipt_is_not_mapped(change):
    data = receipt()
    change(data)
    with pytest.raises(ValueError):
        mapped(data)


def test_all_empty_clocks_and_probe_only_boundary():
    data = receipt()
    for call in data["history"]["invocations"]:
        for chunk in call["chunks"]:
            chunk["valid_clocks"] = ()
    assert not mapped(data)["planned_indices"].size
    data["history"]["invocations"][1]["chunks"][-1]["valid_clocks"] = (2.5,)
    np.testing.assert_array_equal(mapped(data)["planned_indices"], [1])


@pytest.mark.parametrize("grid", [np.arange(8) / 4, np.arange(9) / 4 + .25,
                                  np.array([0., .25, .5, .6, 1., 1.25, 1.5, 1.75, 2.])])
def test_grid_must_match_actual_main_sample_record(grid):
    with pytest.raises(ValueError):
        mapped(receipt(), grid)


class ClockRecord(HasTraits):
    info = Dict()


@pytest.mark.parametrize("kind", ["dict", "traits"])
@pytest.mark.parametrize("clocks", ["all", "empty", "probe_only", "mismatch", "failed"])
def test_live_plan_observes_mapping_without_enabling_consumption(kind, clocks):
    data = receipt()
    if clocks in {"empty", "probe_only"}:
        for call in data["history"]["invocations"]:
            for chunk in call["chunks"]:
                chunk["valid_clocks"] = ()
    if clocks == "probe_only":
        data["history"]["invocations"][1]["chunks"][-1]["valid_clocks"] = (2.5,)
    if clocks == "failed":
        data["status"] = "incomplete"
    info = ami_clock.new_clock_info(True, "rx_getwave", "same_init_after_probes")
    info["origin_observations"] = data
    if kind == "traits":
        info = ClockRecord(info=info).info
    edges = [] if clocks in {"empty", "probe_only"} else [3., 4., 5.]
    if clocks == "mismatch":
        edges = [3.]
    window = {"start_index": 0, "stop_index": 9, "start_s": 0., "stop_s": 2.,
              "fft_slice": (1, 4), "required_decisions": 1, "required_eye_traces": 1}
    if clocks == "empty":
        ami_clock.plan_ami_clocks(info, edges, np.arange(9) / 4, 1., 1., 4, window)
        assert info["use_native"] and info["reason"] == "no_clocks"
    else:
        reason = "invalid_origin_evidence" if clocks in {"mismatch", "failed"} else "unsupported_origin_mapping"
        with pytest.raises(ValueError, match=reason):
            ami_clock.plan_ami_clocks(info, edges, np.arange(9) / 4, 1., 1., 4, window)
        assert not info["use_native"] and info["consumed_count"] == 0
    assert info["producer_contract_version"] == 2
    if clocks not in {"mismatch", "failed"}:
        assert info["origin_mapping"]["status"] == "mapped"
        np.testing.assert_array_equal(info["edges_s"], edges)


def test_first_grid_not_earlier_than_target_and_no_duplicate_samples():
    data = receipt()
    data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = (3.125,)
    result = mapped(data)
    np.testing.assert_array_equal(result["planned_indices"], [1, 4, 7])
    np.testing.assert_array_equal(result["quantization_delay_s"], [0., .125, 0.])
    data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = (2.625,)
    # Both probe edge 2.5 and Main edge 2.625 map to distinct indices 1 and 2.
    np.testing.assert_array_equal(mapped(data)["planned_indices"], [1, 2, 7])
    data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = (2.625, 2.7)
    with pytest.raises(ValueError, match="unsupported_resolution"):
        mapped(data)


@pytest.mark.parametrize("index", [0, 2, 4, 8])
def test_picosecond_grid_boundary_is_compared_in_epoch_coordinates(index):
    data, ts, ui = receipt(), 1e-12, 4e-12
    data["main_entry"]["sample_interval_s"] = ts
    data["history"]["sample_interval_s"] = ts
    for call in data["history"]["invocations"]:
        for chunk in call["chunks"]:
            chunk["valid_clocks"] = ()
    # These ABI timestamps exactly hit the corresponding absolute sample after + UI/2.
    edge = {0: 9e-12, 2: 1.1e-11, 4: 1.3e-11, 8: 1.7e-11}[index]
    data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = (edge,)
    target_epoch = edge + ui / 2
    epoch_grid = np.array([(11 + i) * ts for i in range(9)])
    assert target_epoch == epoch_grid[index]
    result = ami_clock.map_same_epoch_clocks(data, np.arange(9) * ts, ui, index / 4)
    np.testing.assert_array_equal(result["planned_indices"], [index])
    assert result["planned_ready"].tolist() == [True]
    assert result["quantization_delay_s"].tolist() == [0.]


@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("index", [0, 2, 8])
def test_nextafter_true_epoch_crossing_is_not_snapped(index, direction):
    data, ts, ui = receipt(), 1e-12, 4e-12
    data["main_entry"]["sample_interval_s"] = ts
    data["history"]["sample_interval_s"] = ts
    for call in data["history"]["invocations"]:
        for chunk in call["chunks"]:
            chunk["valid_clocks"] = ()
    epoch_grid = np.array([(11 + i) * ts for i in range(9)])
    edge = {0: 9e-12, 2: 1.1e-11, 8: 1.7e-11}[index]
    # Addition may round one nextafter back to the same target; advance until it really crosses.
    while (edge + ui / 2 - epoch_grid[index]) * direction <= 0:
        edge = np.nextafter(edge, -np.inf if direction < 0 else np.inf)
    data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = (edge,)
    result = ami_clock.map_same_epoch_clocks(data, np.arange(9) * ts, ui, index / 4)
    if index == 0 and direction < 0 or index == 8 and direction > 0:
        assert not result["planned_indices"].size
        assert result["deferred_reasons"] == ["before_record" if direction < 0 else "future"]
    else:
        np.testing.assert_array_equal(result["planned_indices"], [index if direction < 0 else index + 1])
        assert result["planned_ready"].tolist() == [direction > 0]


def test_nonbinary_last_sample_and_readiness_keep_exact_epoch_hits():
    data = receipt()
    data["main_entry"]["sample_interval_s"] = .1
    data["history"]["sample_interval_s"] = .1
    for call in data["history"]["invocations"]:
        for chunk in call["chunks"]:
            chunk["valid_clocks"] = ()
    data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = (1.3,)
    result = ami_clock.map_same_epoch_clocks(data, np.arange(9) * .1, .4, 1.)
    assert result["planned_ready"].tolist() == [True]
    # Change actual probe/Main lengths to the independently reviewed final-record counterexample.
    for call, sizes in zip(data["history"]["invocations"], [[160, 12], [160, 12], [80, 80, 6]]):
        call["input_samples"] = sum(sizes)
        for chunk, size in zip(call["chunks"], sizes):
            chunk["wave_size"] = size
    data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = (50.7,)
    result = ami_clock.map_same_epoch_clocks(data, np.arange(166) * .1, .4, 0.)
    np.testing.assert_array_equal(result["planned_indices"], [165])
    assert result["deferred_reasons"] == [None] and result["quantization_delay_s"].tolist() == [0.]
