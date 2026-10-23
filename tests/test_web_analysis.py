"""Function-level availability boundaries for the native analysis adapter."""

import numpy as np
import pytest

from pybert.utility import calc_eye
from pybert.web.analysis import clock_data, clock_display, eye_data, ffe_jitter


@pytest.fixture
def metadata_analysis(monkeypatch):
    from pybert.web import analysis

    t = np.arange(256) * 1e-12
    window = dict(nui=32, eye_uis=16, ignore_samps=128, ignore_until_s=128e-12)
    arrays = dict(t=t, f=np.arange(5) * 1e9, ui_ests=np.r_[np.full(128, 8.), np.tile([8., 8.1], 64)],
                  clocks=np.zeros(256), lockeds=np.ones(256), clock_times=np.r_[0., np.arange(136, 273, 16) * 1e-12])
    arrays.update({"context.source.ui":np.asarray(8e-12), "context.source.nspui":np.asarray(8)})
    for key in ("chnl_H_raw", "chnl_H", "chnl_trimmed_H"):
        arrays[key] = np.ones(5, dtype=complex)
    for point, (_, waveform, _) in analysis.POINTS.items():
        arrays[waveform] = np.tile(np.r_[-np.ones(8), np.ones(8)], 16)
        arrays[f"context.{point}.bin_centers"] = np.linspace(-4e-12, 4e-12, 9)
        arrays[f"context.{point}.spectrum_freqs"] = np.arange(5) * 1e9
        for name in analysis.STATS:
            arrays[f"{name}_{point}"] = np.asarray(1e-13)
        for name in ("jitter", "jitter_ext"):
            arrays[f"{name}_{point}"] = np.full(9, 1e11)
        for name in ("jitter_spectrum", "jitter_ind_spectrum", "thresh"):
            arrays[f"{name}_{point}"] = np.linspace(1e-14, 5e-14, 5)
    # Only the unrelated physical FFE calculation is replaced; the metadata/plot path is real.
    monkeypatch.setattr(analysis, "ffe_jitter", lambda _: ({}, {}, dict(availability="available", reason=None)))
    datasets = {key:dict(point=None, field=key, window=window) for key in ("ui_ests", "clocks", "clock_times", "lockeds")}
    manifest = dict(datasets=datasets, plots={}, window=window, run_id="metadata-test", input_hash="input",
                    adapter_sha="engine", raw_schema_version=3, effective_input=dict(ctle_enable=True))
    analysis.extend_analysis(arrays, manifest)
    return arrays, manifest


def test_display_metadata_has_concrete_observation_and_sources(metadata_analysis):
    _, manifest = metadata_analysis
    datasets = manifest["datasets"]
    for point, observation in (("chnl", "channel_only"), ("tx", "rx_input"), ("ctle", "ctle_output"),
                               ("ffe", "rx_ffe_output"), ("dfe", "dfe_output")):
        for key, xsource, ysource in ((f"pdf.{point}.jitter", f"context.{point}.bin_centers", f"jitter_{point}"),
                                      (f"spec.{point}.thresh", f"context.{point}.spectrum_freqs", f"thresh_{point}"),
                                      (f"bathtub.{point}", f"context.{point}.bin_centers", f"bathtub.{point}.probability")):
            for suffix, source in (("x", xsource), ("y", ysource)):
                dataset = datasets[f"display.{key}.{suffix}"]
                assert dataset["point"] == point
                assert dataset["observation_id"] == observation
                assert source in dataset["source_fields"]
    assert datasets["display.channel.chnl_H_raw.y"]["observation_id"] == "channel_only"
    assert datasets["display.channel.chnl_H_raw.y"]["source_fields"] == ["chnl_H_raw"]
    assert datasets["display.cdr.histogram.y"]["observation_id"] == "cdr_clock"
    assert datasets["display.cdr.histogram.y"]["source_fields"] == ["cdr.histogram.counts"]


def test_cdr_metadata_uses_complete_record_not_eye_window(metadata_analysis, tmp_path):
    import json
    from pybert.web.data import plot_payload

    arrays, manifest = metadata_analysis
    assert arrays["cdr.histogram.counts"].sum() == len(arrays["ui_ests"]) == 256
    for key, dataset in manifest["datasets"].items():
        if key in ("ui_ests", "clocks", "clock_times", "lockeds"):
            assert dataset["window"]["source_field"] == key
            assert dataset["window"]["sample_count"] == len(arrays[key])
            assert dataset["window"]["ignore_samps"] == 0
            assert dataset["observation_id"] == "cdr_clock"
            if key == "clock_times":
                assert dataset["window"]["record_kind"] == "event_times"
                assert dataset["window"]["time_axis"] == "clock_times"
                assert dataset["window"]["stop_s_inclusive"] == arrays[key][-1] > arrays["t"][-1]
                assert "stop_s_exclusive" not in dataset["window"]
        if key.startswith(("cdr.", "display.cdr.")):
            window = dataset["window"]
            assert window["scope"] == "full_record"
            assert window["source_field"] == "ui_ests"
            assert window["start_index"] == 0 and window["stop_index"] == 256
            assert window["sample_count"] == 256 and window["ignore_samps"] == 0
            assert window["ignore_until_s"] == 0
            assert dataset["observation_id"] == "cdr_clock"
    assert manifest["datasets"]["display.pdf.ffe.jitter.y"]["window"] == manifest["window"]
    np.savez_compressed(tmp_path / "arrays.npz", **arrays)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    payload = plot_payload(tmp_path, "cdr.histogram")
    assert payload["metadata"]["window"]["sample_count"] == 256
    assert payload["metadata"]["datasets"]["display.cdr.histogram.y"]["observation_id"] == "cdr_clock"


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
