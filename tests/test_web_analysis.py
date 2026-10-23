"""Function-level availability boundaries for the native analysis adapter."""

import numpy as np
import pytest

from pybert.utility import calc_eye
from pybert.web.analysis import clock_data, clock_display, eye_data, ffe_jitter


@pytest.mark.parametrize("ys,reason", [(np.ones(100), "No waveform crossing"), (np.ones(4), "Insufficient"),
                                      (np.full(100,np.nan), "nonfinite"), (np.zeros(100), "voltage scale")])
def test_invalid_eye_is_unavailable(ys, reason):
    with pytest.raises(ValueError, match=reason):
        eye_data(1e-10, 8, ys)


def test_nominal_eye_fallback_uses_native_helper():
    ys = np.tile(np.r_[-np.ones(8),np.ones(8)],30)
    counts, mapping = eye_data(1e-10,8,ys)
    assert np.array_equal(counts,calc_eye(1e-10,8,1000,ys,mapping["y_max"]))
    assert counts.sum() > 0


def test_no_ffe_crossings_is_explicit():
    arrays = {"t":np.arange(128)*1e-12,"ffe_out":np.ones(128),"context.source.x":np.ones(128),
              "context.source.decision_scaler":np.asarray(.5),"context.source.mod_type":np.asarray(0),
              "context.source.xing_min_t":np.asarray(0.)}
    with pytest.raises(ValueError,match="no crossings"):
        ffe_jitter(arrays)


@pytest.mark.parametrize("spectrum", [np.zeros(10),np.array([1,np.nan]),np.array([1,np.inf]),np.array([0,1e-320,1])])
def test_zero_or_nonfinite_clock_normalization(spectrum):
    with pytest.raises(ValueError,match="normalization"):
        clock_display(spectrum)


def test_clock_histogram_preserves_complete_record_and_legacy_scale():
    values = np.tile(np.array([100.,101.,99.,100.]),32)
    t = np.arange(len(values))*1e-12
    counts, edges, spectrum, frequency, relative = clock_data(t,values,1e-10)
    assert counts.sum() == len(values)
    assert len(edges) == 101
    assert np.array_equal(spectrum,np.fft.rfft(values))
    assert np.array_equal(relative,frequency[1:]*1e-10)
    s = np.array([100.,10.,100.,1.])
    assert np.array_equal(clock_display(s),[0.,1.,-1.])
