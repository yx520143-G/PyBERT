"""F6 software contracts; synthetic receipts do not qualify a real AMI model."""

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from pybert.utility import ami_clock
from pybert.web import clocks


def receipt(edges, probe_edges=()):
    calls, c_call = [], 0
    for number, sizes in ((1, (3, 1)), (2, (3, 1)), (3, (7, 7, 2))):
        chunks = []
        for index, size in enumerate(sizes):
            c_call += 1
            ticks = edges if number == 3 and index == 0 else probe_edges if number == 2 and index == 1 else ()
            chunks.append({"epoch": 1, "python_call": number, "c_call": c_call, "wave_size": size,
                               "status": 1, "returned": True, "phase": "complete", "valid_clocks": list(ticks)})
        calls.append({"python_call": number, "input_samples": sum(sizes), "completed": True, "chunks": chunks})
    return {"status": "complete", "main_entry": {"epoch_id": "software-fixture/init-1", "python_calls": 2,
                "c_calls": 4, "sample_interval_s": .25},
                "history": {"epoch_id": "software-fixture/init-1", "epoch": 1, "sample_interval_s": .25,
                             "python_calls": 3, "c_calls": 7, "ready": True, "invocations": calls}}


def planned(edges=(2., 3., 4., 5.), *, required=2, eye_traces=1, fft=(6, 10), probe_edges=(), ignore=0.):
    info = ami_clock.new_clock_info(True, "rx_getwave", "same_init_after_probes", contract_version=3)
    info["origin_observations"] = receipt(edges, probe_edges)
    window = {"start_index": 0, "stop_index": 16, "start_s": 0., "stop_s": 3.75,
                  "required_decisions": required, "required_eye_traces": eye_traces, "fft_slice": fft}
    ami_clock.plan_ami_clocks(info, edges, np.arange(16) / 4, 1., ignore, 4, window)
    return info


def consumed(edges=(2., 3., 4., 5.), **kwargs):
    info = planned(edges, **kwargs)
    wave = np.tile([-1., -1., 1., 1.], 4)
    ami_clock.consume_ami_clocks(info, wave, lambda value: (np.sign(value), [int(value > 0)]))
    return info, wave


@pytest.mark.parametrize("edges,required,fft,indices,ber,hist,spectrum", [
    ((2., 3., 4., 5.), 2, (6, 10), [2, 6, 10, 14], True, True, True),
    ((2., 3.), 4, (6, 10), [2, 6], False, True, False),
    ((2., 3., 4., 5.), 2, (12, 16), [2, 6, 10, 14], True, True, False),
    ((2.,), 2, (6, 10), [2], False, False, False),
    ((8.,), 2, (6, 10), [], False, False, False),
])
def test_independent_coverage(edges, required, fft, indices, ber, hist, spectrum):
    info, wave = consumed(edges, required=required, fft=fft)
    assert info["consumption_status"] == "completed" and info["loop_finished"]
    assert info["run_status"] == "not_completed"  # A sampler cannot complete the Main pipeline.
    assert not info["use_native"]
    assert info["model_qualification"] == "UNKNOWN"
    np.testing.assert_array_equal(info["sample_indices"], indices)
    np.testing.assert_array_equal(info["sample_values"], wave[indices])
    assert info["ber_eligible"] is ber
    products = ami_clock.clock_period_data(info, info["grid_s"], .25)
    assert bool(products["histogram_counts"].size) is hist
    assert bool(products["spectrum"].size) is spectrum


def test_eye_uses_own_coverage_and_retains_declared_trace_requirement():
    info, wave = consumed((2., 3.), required=4, eye_traces=1)
    calls = []
    image = ami_clock.ami_eye_data(info, wave, 0, 10, 1., lambda *a, **k: calls.append(k) or np.ones((10, 8)))
    assert image.shape == (10, 8) and calls[0]["clock_indices"].tolist() == [2, 6]
    info["analysis"]["required_eye_traces"] = 3
    assert ami_clock.ami_eye_data(info, wave, 0, 10, 1., lambda *a, **k: pytest.fail("insufficient traces")) is None
    assert info["eye_status"] == "unavailable"


@pytest.mark.parametrize("failure", ["decide", "cancel"])
def test_actual_failure_is_partial_and_retains_completed_samples(failure):
    info, wave, calls = planned(), np.ones(16), []
    def decide(value):
        calls.append(value)
        if failure == "decide" and len(calls) == 2:
            raise RuntimeError("actual failure")
        return 1., [1]
    def cancel():
        if failure == "cancel" and len(calls) == 1:
            raise RuntimeError("actual failure")
    with pytest.raises(RuntimeError, match="actual failure"):
        ami_clock.consume_ami_clocks(info, wave, decide, cancel)
    assert info["sample_indices"].tolist() == [2]
    assert info["consumption_status"] == "partial" and not info["loop_finished"]
    assert info["reason"] == "consumption_failed"


def test_probe_boundary_and_empty_fallback_are_distinct():
    info, _ = consumed((), probe_edges=(1.5,))
    assert info["sample_indices"].tolist() == [0] and not info["use_native"]
    info = planned(())
    assert info["use_native"] and info["format_status"] == "no_clocks"


def test_version_two_still_rejects_insufficient_coverage():
    info = ami_clock.new_clock_info(True, "rx_getwave", "c1_fresh_main")
    window = {"start_index": 0, "stop_index": 16, "start_s": 0., "stop_s": 3.75,
                  "required_decisions": 2, "required_eye_traces": 1, "fft_slice": (6, 10)}
    ami_clock.plan_ami_clocks(info, [0.], np.arange(16) / 4, 1., 0., 4, window)
    with pytest.raises(ValueError, match="insufficient_coverage"):
        ami_clock.consume_ami_clocks(info, np.ones(16), lambda value: (1., [1]))


def completed_engine(edges=(2., 3., 4., 5.), **kwargs):
    info, wave = consumed(edges, **kwargs)
    info.update(run_status="completed", ber_status={"availability": "available" if info["ber_eligible"] else "unavailable",
                "reason": None if info["ber_eligible"] else "insufficient_frozen_ber_decisions"})
    engine = SimpleNamespace(ami_clock_info=info, t=info["grid_s"], ui_ests=info["period_s"] * 1e12,
                             ami_period_known=info["period_known"], clock_times=info["sample_grid_times_s"],
                             clocks=info["clock_mask"], dfe_out=wave, ffe_out=wave.copy())
    return engine


@pytest.mark.parametrize("edges", [(2.,), (8.,), (2., 3., 4., 5.)])
def test_live_v3_accepts_independent_analysis_and_rejects_stale_or_partial(edges):
    engine = completed_engine(edges)
    snapshot = clocks.snapshot_producer(engine, phase="post_main")
    context = clocks.clock_context(engine, snapshot)
    assert context["version"] == 3
    for field, value in (("run_status", "not_completed"), ("consumption_status", "partial")):
        bad = deepcopy(snapshot)
        bad["info"][field] = value
        with pytest.raises(ValueError):
            clocks.clock_context(engine, bad)
    snapshot["fresh"] = False
    with pytest.raises(ValueError):
        clocks.clock_context(engine, snapshot)


@pytest.mark.parametrize("boundary", ["first", "last", "readiness"])
def test_epoch_boundary_survives_consumption_and_saved_coordinates(boundary):
    from test_ami_clock_origin import receipt as origin_receipt
    info = ami_clock.new_clock_info(True, "rx_getwave", "same_init_after_probes", contract_version=3)
    receipt_data = origin_receipt()
    receipt_data["main_entry"]["sample_interval_s"] = .1
    receipt_data["history"]["sample_interval_s"] = .1
    for call in receipt_data["history"]["invocations"]:
        for chunk in call["chunks"]:
            chunk["valid_clocks"] = ()
    if boundary == "last":
        for call, sizes in zip(receipt_data["history"]["invocations"], [[160, 12], [160, 12], [80, 80, 6]]):
            call["input_samples"] = sum(sizes)
            for chunk, size in zip(call["chunks"], sizes):
                chunk["wave_size"] = size
        edges, count, index, ignore = [50.7], 166, 165, 0.
    else:
        edges, count, index, ignore = [1.3], 9, 4, 1. if boundary == "readiness" else 0.
    receipt_data["history"]["invocations"][2]["chunks"][0]["valid_clocks"] = edges
    info["origin_observations"] = receipt_data
    grid = np.arange(count) * .1
    window = {"start_index": index if boundary == "first" else 0, "stop_index": count,
                  "start_s": float(grid[index]) if boundary == "first" else 0., "stop_s": float(grid[-1]),
                  "required_decisions": 1, "required_eye_traces": 1, "fft_slice": (index, count)}
    ami_clock.plan_ami_clocks(info, edges, grid, .4, ignore, 4, window)
    wave = np.ones(count)
    ami_clock.consume_ami_clocks(info, wave, lambda value: (1., [1]))
    assert info["analysis_sample_indices"].tolist() == [index]
    assert info["sample_quantization_delay_s"].tolist() == [0.]
    info.update(run_status="completed", ber_status={"availability": "available", "reason": None})
    engine = SimpleNamespace(ami_clock_info=info, t=grid, ui_ests=info["period_s"] * 1e12,
        ami_period_known=info["period_known"], clock_times=info["sample_grid_times_s"], dfe_out=wave, ffe_out=wave.copy())
    context = clocks.clock_context(engine, clocks.snapshot_producer(engine))
    arrays, datasets = {"t": grid, "dfe_out": wave, "clock_times": engine.clock_times}, {}
    contract = clocks.store_clock_context(context, arrays, datasets)
    run = {"raw_schema_version": 7, "required_features": ["ami-clock-independent-v3"], "ami": {"clock_contract": contract}}
    stored = clocks.stored_clock_context(run, arrays)
    assert stored["info"]["analysis_sample_indices"].tolist() == [index]
    assert stored["info"]["sample_quantization_delay_s"].tolist() == [0.]
