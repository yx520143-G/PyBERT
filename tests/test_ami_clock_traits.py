"""Clock provenance must work with the actual Traits Dict storage used by PyBERT."""

import numpy as np
import pytest
from traits.api import Dict, HasTraits

from pybert.utility.ami_clock import ami_eye_data, consume_ami_clocks, new_clock_info, plan_ami_clocks
from pybert.utility.sigproc import calc_eye


class ClockRecord(HasTraits):
    info = Dict()


@pytest.fixture(params=[False, True], ids=["dict", "traits-dict"])
def info(request):
    value = new_clock_info(True, "rx_getwave", "c1_fresh_main")
    return ClockRecord(info=value).info if request.param else value


def plan(info, edges):
    grid = np.arange(32) / 4
    window = dict(start_index=0, stop_index=32, start_s=0., stop_s=grid[-1],
                  required_decisions=4, required_eye_traces=1, fft_slice=(2, 10))
    return plan_ami_clocks(info, edges, grid, 1., 0., 4, window)


def test_clock_record_no_clock_fallback(info):
    plan(info, [])
    assert info["use_native"] and info["reason"] == "no_clocks"
    assert info["planned_indices"].size == 0


@pytest.mark.parametrize("origin", ["same_init_after_probes", None])
def test_empty_clocks_do_not_require_an_origin_mapping(info, origin):
    info["main_origin"] = origin
    plan(info, [])
    assert info["use_native"] and info["reason"] == "no_clocks"


def test_same_epoch_nonempty_clocks_require_explicit_mapping(info):
    info["main_origin"] = "same_init_after_probes"
    with pytest.raises(ValueError, match="unsupported_origin_mapping"):
        plan(info, [12.])
    assert info["format_status"] == "valid"
    assert info["consumed_count"] == 0
    assert not info["use_native"]
    assert "not the model Init epoch" in info["epoch_basis"]
    assert "fresh" not in info["epoch_basis"]


def test_clock_record_invalid_input_keeps_reason(info):
    with pytest.raises(ValueError, match="malformed_clocks"):
        plan(info, [1., 0.])
    assert info["format_status"] == "invalid"
    assert info["reason"] == "malformed_clocks"


def test_clock_record_sampling_and_eye(info):
    plan(info, np.arange(6))
    waveform = np.tile([-.5, -.5, .5, .5], 8)
    consume_ami_clocks(info, waveform, lambda value: (value, [int(value > 0)]))
    assert info["consumption_status"] == "completed"
    np.testing.assert_array_equal(info["sample_indices"], [2, 6, 10, 14, 18, 22])
    np.testing.assert_array_equal(info["sample_values"], waveform[info["sample_indices"]])
    image = ami_eye_data(info, waveform, 0, 1000, .55, calc_eye)
    assert info["eye_status"] == "completed"
    assert image.sum() == info["eye_trace_count"] * 8


def test_clock_record_partial_failure_preserves_first_decision(info):
    plan(info, np.arange(6))
    calls = 0

    def decide(value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("slicer failed")
        return value, [1]

    with pytest.raises(RuntimeError, match="slicer failed"):
        consume_ami_clocks(info, np.ones(32), decide)
    assert info["reason"] == "consumption_failed"
    assert info["consumption_status"] == "partial"
    assert info["consumed_count"] == 1
    np.testing.assert_array_equal(info["sample_indices"], [2])
