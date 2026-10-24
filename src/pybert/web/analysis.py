"""Immutable, raw-only native helper analyses; no engine execution or physical RNG."""

import warnings
from types import SimpleNamespace
import hashlib
from pathlib import Path

import numpy as np
from scipy.signal import correlate

from pybert.models.bert import MIN_BATHTUB_VAL
from pybert.utility import calc_eye, calc_jitter, find_crossings, make_bathtub, safe_log10
from pybert.web.clocks import period_projection

ANALYSIS_VERSION = 2
DISPLAY_NOISE_SEED = 34003
POINTS = {
    "chnl": ("channel_only", "chnl_out", "Channel-only diagnostic"),
    "tx": ("rx_input", "rx_in", "Native Rx input (+Tx, noise)"),
    "ctle": ("ctle_output", "ctle_out", "CTLE output"),
    "ffe": ("rx_ffe_output", "ffe_out", "Rx FFE output · new helper observation"),
    "dfe": ("dfe_output", "dfe_out", "DFE summing-node output"),
}
STATS = ("isi", "dcd", "pj", "rj", "pjDD", "rjDD", "mu_pos", "mu_neg", "dj_pos", "dj_neg")
JITTER_RETURN = ("tie", "t_jitter", "isi", "dcd", "pj", "rj", "pjDD", "rjDD", "tie_ind", "thresh",
                 "jitter_spectrum", "jitter_ind_spectrum", "spectrum_freqs", "jitter", "jitter_ext",
                 "bin_centers", "mu_pos", "mu_neg", "dj_pos", "dj_neg")


def ffe_jitter(arrays):
    """Observe ffe_out with the original four-point alignment/window/mask convention."""
    source = {k.removeprefix("context.source."): v for k, v in arrays.items() if k.startswith("context.source.")}
    t, ys, x = arrays["t"], arrays["ffe_out"], source["x"]
    offset = (np.argmax(correlate(ys, x)) - (len(x) - 1)) * (t[1] - t[0])
    crossings = find_crossings(t, ys, float(source["decision_scaler"]), mod_type=int(source["mod_type"]))
    aligned = crossings - offset
    windowed = aligned[aligned > source["xing_min_t"]] - source["xing_min_t"]
    if not len(windowed):
        raise ValueError("Rx FFE has no crossings in the frozen jitter window")
    debug = SimpleNamespace()
    values = calc_jitter(float(source["ui"]), int(source["eye_uis"]), int(source["pattern_len"]),
                         source["ideal_xings_jit"], windowed, float(source["rel_thresh"]),
                         xing_mask=source.get("xing_mask"), dbg_obj=debug)
    fits = getattr(debug, "dd_soltn", [])
    fitted = len(fits) == 3 and all(len(tail) == 3 and np.isfinite(tail[2]).all() for tail in fits[1:])
    fit_status = dict(availability="available" if fitted else "unavailable",
                      reason=None if fitted else "Native dual-Dirac tail fit missing, failed, or has nonfinite covariance; reference raw retained")
    return dict(zip(JITTER_RETURN, values)), dict(ofst=offset, actual_xings=crossings, actual_xings_jit=windowed), fit_status


def eye_data(ui, nspui, ys, clocks=None, *, clock_indices=None):
    """Return the native count matrix and its actual generation mapping."""
    if clocks is not None and clock_indices is not None:
        raise ValueError("Only one timed Eye coordinate input may be supplied")
    if clock_indices is not None and not len(clock_indices):
        raise ValueError("no_complete_timed_trace")
    ys = np.asarray(ys)
    if len(ys) < 2 * nspui or not np.isfinite(ys).all():
        raise ValueError("Insufficient or nonfinite eye waveform window")
    y_max = 1.1 * np.max(abs(ys))
    if y_max <= 0 or 1000 // (2 * y_max) <= 0:
        raise ValueError("Invalid/zero native eye voltage scale")
    if clocks is None and clock_indices is None and not np.any(np.diff(np.sign(ys))):
        raise ValueError("No waveform crossing for nominal eye alignment")
    counts = (calc_eye(ui, nspui, 1000, ys, y_max, clock_indices=clock_indices) if clock_indices is not None
              else calc_eye(ui, nspui, 1000, ys, y_max, clocks))
    if counts.sum() == 0:
        raise ValueError("Insufficient clock/crossing coverage for a complete eye fold")
    return counts, dict(y_max=float(y_max), y_scale=float(1000 // (2 * y_max)), y_offset=500)


def clock_data(t, ui_ests, ui, *, clock_contract=None):
    """Exact legacy histogram and FFT convention, with an explicit zero-denominator boundary."""
    if clock_contract is not None:
        return period_projection(clock_contract, t, ui_ests, ui)
    counts, edges = np.histogram(ui_ests, bins=100)
    spectrum = np.fft.rfft(ui_ests)
    frequency = np.arange(len(spectrum)) / (t[1] * len(t))
    return counts, edges, spectrum, frequency, frequency[1:] * ui


def clock_display(spectrum):
    """The native legacy log10 ratio requires a finite, nonzero fundamental."""
    if len(spectrum) < 2 or abs(spectrum[1]) == 0 or not np.isfinite(spectrum).all():
        raise ValueError("Zero fundamental normalization or nonfinite clock spectrum")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        ratio = abs(spectrum[1:]) / abs(spectrum[1])
        display = safe_log10(ratio)
    if not np.isfinite(ratio).all() or not np.isfinite(display).all():
        raise ValueError("Nonfinite clock normalization result; native raw spectrum retained")
    return display


def extend_analysis(arrays, manifest, cancelled=lambda: False):
    """Build all optional datasets before the caller's single atomic publication."""
    datasets, plots = manifest["datasets"], manifest["plots"]
    window = manifest["window"]
    ui = float(arrays["context.source.ui"])
    nspui = int(arrays["context.source.nspui"])
    manifest["analysis_version"] = ANALYSIS_VERSION
    manifest["analysis_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    manifest["observations"] = {}
    clock_window = dict(scope="full_record", source_field="ui_ests", time_axis="t", start_index=0,
                        stop_index=len(arrays["ui_ests"]), sample_count=len(arrays["ui_ests"]),
                        ignore_samps=0, ignore_until_s=float(arrays["t"][0]), start_s=float(arrays["t"][0]),
                        stop_s_exclusive=float(arrays["t"][-1] + arrays["t"][1] - arrays["t"][0]))

    def checkpoint():
        if cancelled():
            raise RuntimeError("Cancelled during native analysis group")

    def add(key, value, unit, point=None, axis=None, kind="analysis", producer="native helper",
            dataset_window=None, source_fields=None, **extra):
        value = np.asarray(value)
        arrays[key] = value
        finite = bool(np.isfinite(value).all())
        datasets[key] = dict(field=key, producer=producer, point=point, kind=kind, unit=unit,
                             dtype=str(value.dtype), shape=list(value.shape), axis=axis,
                             window=window if dataset_window is None else dataset_window,
                             source_fields=source_fields or [key],
                             clock_basis="native", display_noise=False,
                             availability="available" if finite else "unavailable",
                             reason=None if finite else "Native helper returned nonfinite values; raw retained",
                             nonfinite_count=int(np.count_nonzero(~np.isfinite(value))), **extra)
        return key

    def unavailable(plot_id, title, reason):
        plots[plot_id] = dict(title=title, traces=[], availability="unavailable", reason=reason)

    def line(key, x, y, name, xunit, yunit, point, xsource, ysource, dataset_window=None, **extra):
        xkey = add(f"display.{key}.x", x, xunit, point, kind="display",
                   source_fields=xsource, dataset_window=dataset_window)
        ykey = add(f"display.{key}.y", y, yunit, point, axis=xkey, kind="display",
                   source_fields=ysource, dataset_window=dataset_window)
        return dict(x=xkey, y=ykey, name=name, xunit=xunit, yunit=yunit, **extra)

    # Original four producers are consumed as-is; this call runs only after all four have finished.
    checkpoint()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            values, context, fit_status = ffe_jitter(arrays)
            for name, value in context.items():
                add(f"context.ffe.{name}", value, "s", "ffe", kind="context", producer="new find_crossings/correlate")
            for name, value in values.items():
                context_field = name in ("tie", "t_jitter", "tie_ind", "spectrum_freqs", "bin_centers")
                key = f"context.ffe.{name}" if context_field else f"{name}_ffe"
                unit = "1/s" if name in ("jitter", "jitter_ext") else "Hz" if name == "spectrum_freqs" else "s"
                axis = ("context.ffe.bin_centers" if name in ("jitter", "jitter_ext") else
                        "context.ffe.spectrum_freqs" if name in ("thresh", "jitter_spectrum", "jitter_ind_spectrum") else
                        "context.ffe.t_jitter" if name in ("tie", "tie_ind") else None)
                add(key, value, unit, "ffe", axis, producer="new calc_jitter observation")
            finite = all(np.isfinite(value).all() for value in values.values())
            manifest["ffe_analysis"] = dict(availability="available" if finite else "unavailable",
                reason=None if finite else "Native helper returned nonfinite values; raw retained", dual_dirac_fit=fit_status)
        except (ValueError, RuntimeError, IndexError, FloatingPointError, ZeroDivisionError) as err:
            manifest["ffe_analysis"] = dict(availability="unavailable", reason=f"{type(err).__name__}: {err}")
    manifest["ffe_analysis"]["warnings"] = [str(w.message) for w in caught]

    # Channel frequency triplet retains the original complex datasets and native frequency axis.
    plots["channel.frequency"] = dict(title="Channel frequency · three native sources", traces=[
        line(f"channel.{key}", arrays["f"][1:] * 1e-9, 20 * safe_log10(abs(arrays[key][1:])), label,
             "GHz", "dB", "chnl", ["f"], [key], logx=True)
        for key, label in (("chnl_H_raw", "Raw · perfect termination"), ("chnl_H", "Actual termination"),
                           ("chnl_trimmed_H", "Trimmed impulse FFT"))])
    noise = np.random.default_rng(DISPLAY_NOISE_SEED).normal(0, 1e-3, len(arrays["chnl_out"]))
    noise_key = add("display.channel_noise", noise, "V", "chnl", kind="display realization")
    datasets[noise_key].update(display_noise=True, seed=DISPLAY_NOISE_SEED, generator="PCG64", sigma_v=0.001)

    for point, (observation, waveform, label) in POINTS.items():
        checkpoint()
        context = f"context.{point}."
        jitter_keys = [f"{name}_{point}" for name in (*STATS, "jitter", "jitter_ext", "jitter_spectrum",
                                                      "jitter_ind_spectrum", "thresh")]
        valid = all(k in arrays and np.isfinite(arrays[k]).all() for k in jitter_keys)
        reason = None if valid else manifest["ffe_analysis"]["reason"] or "Nonfinite jitter result; raw retained"
        info = dict(observation_id=observation, source_waveform=waveform, label=label,
                    origin="new native helper observation" if point == "ffe" else "original native producer",
                    availability="available" if valid else "unavailable", reason=reason,
                    statistics_s={name: float(arrays[f"{name}_{point}"]) if valid else None for name in STATS},
                    crossing_boundary="PAM4: symmetric transitions about 0V; not all three voltage eyes",
                    window=window, context_prefix=context)
        info["dual_dirac_fit"] = manifest["ffe_analysis"].get("dual_dirac_fit", {}) if point == "ffe" else dict(
            availability="unknown", reason="Legacy native raw does not retain tail-fit covariance/failure details; raw reference values only")
        for metric in ("rjDD", "mu_pos", "mu_neg"):
            dataset = datasets.get(f"{metric}_{point}")
            if dataset:
                dataset["fit_availability"] = info["dual_dirac_fit"].get("availability", "unavailable")
                dataset["fit_reason"] = info["dual_dirac_fit"].get("reason")
                if point == "ffe" and dataset["fit_availability"] != "available":
                    dataset.update(availability="unavailable", reason=dataset["fit_reason"])
        info["configuration_state"] = "bypass" if point == "ctle" and not manifest["effective_input"]["ctle_enable"] else "active"
        manifest["observations"][point] = info
        for kind in ("dist", "spec", "bathtub"):
            plot_id = f"jitter.{point}.{kind}"
            if not valid:
                unavailable(plot_id, f"{label} · {kind}", reason)
                continue
            bins = arrays[context + "bin_centers"]
            if kind == "dist":
                traces = [line(f"pdf.{point}.{name}", bins * 1e12, arrays[f"{name}_{point}"] * 1e-12,
                               title, "ps", "1/ps", point, [context + "bin_centers"], [f"{name}_{point}"]) for name, title in
                          (("jitter", "Total PDF"), ("jitter_ext", "Data-independent PDF"))]
            elif kind == "spec":
                traces = [line(f"spec.{point}.{name}", arrays[context + "spectrum_freqs"][1:] * 1e-6,
                               10 * (safe_log10(arrays[f"{name}_{point}"][1:]) - safe_log10(ui)),
                               title, "MHz", "10 log10(amplitude/UI)", point, [context + "spectrum_freqs"],
                               [f"{name}_{point}", "context.source.ui"], logx=True) for name, title in
                          (("jitter_spectrum", "Total TIE amplitude"), ("jitter_ind_spectrum", "Independent TIE amplitude"),
                           ("thresh", "Pj threshold"))]
            else:
                params = dict(min_val=0.1 * MIN_BATHTUB_VAL, rj=info["statistics_s"]["rj"],
                              mu_r=info["statistics_s"]["dj_pos"], mu_l=info["statistics_s"]["dj_neg"], extrap=True)
                try:
                    probability = make_bathtub(bins, arrays[f"jitter_{point}"], **params)
                    key = add(f"bathtub.{point}.probability", probability, "probability", point,
                              context + "bin_centers", producer="make_bathtub", parameters=params,
                              source_fields=[context + "bin_centers", f"jitter_{point}", f"rj_{point}",
                                             f"dj_pos_{point}", f"dj_neg_{point}"],
                              actual_extrapolation=bool(params["rj"] > 0 and not
                                                       (arrays[f"jitter_{point}"][0] or arrays[f"jitter_{point}"][-1])))
                    if not np.isfinite(probability).all() or np.any(probability < 0):
                        raise ValueError("Nonfinite or negative native bathtub probability; raw retained")
                    traces = [line(f"bathtub.{point}", bins * 1e12, safe_log10(probability),
                                   "Crossing-jitter estimate", "ps", "log10(probability)", point,
                                   [context + "bin_centers"], [key])]
                    info["bathtub_dataset"] = key
                except (ValueError, IndexError, FloatingPointError, ZeroDivisionError) as err:
                    unavailable(plot_id, f"{label} · Bathtub", str(err))
                    continue
            plots[plot_id] = dict(title=f"{label} · {kind}", traces=traces, observation_id=observation)

        eye_variants = [(point, arrays[waveform][window["ignore_samps"]:], False)]
        if point == "chnl":
            eye_variants.append(("chnl.gui_noise", (arrays[waveform] + noise)[window["ignore_samps"]:], True))
        for eye_id, ys, display_noise in eye_variants:
            plot_id = f"eye.{eye_id}"
            clocks = arrays["clock_times"]
            clocks = clocks[clocks >= window["ignore_until_s"]] - window["ignore_until_s"]
            recovered = point == "dfe" and len(clocks) > 0
            basis = "recovered clock_times" if recovered else "nominal waveform crossing fold"
            try:
                counts, mapping = eye_data(ui, nspui, ys, clocks if recovered else None)
                xkey = add(f"{plot_id}.x", np.linspace(-ui, ui, 2 * nspui) * 1e12, "ps", point, kind="axis")
                ykey = add(f"{plot_id}.y", (np.arange(1000) - mapping["y_offset"]) / mapping["y_scale"], "V", point, kind="axis")
                zkey = add(f"{plot_id}.counts", counts, "count", point, producer="calc_eye", **mapping)
                datasets[zkey].update(clock_basis=basis, clock_fallback=point == "dfe" and not recovered,
                                     fallback_reason="No recovered clocks in window" if point == "dfe" and not recovered else None,
                                     display_noise=display_noise, display_noise_dataset=noise_key if display_noise else None,
                                     source_waveform=waveform, x_axis=xkey, y_axis=ykey)
                plots[plot_id] = dict(title=f"{label} eye · {'GUI-compatible σ=1mV' if display_noise else basis}",
                                     heatmap=dict(x=xkey, y=ykey, z=zkey), traces=[], observation_id=observation,
                                     metadata=datasets[zkey])
            except (ValueError, IndexError, FloatingPointError, ZeroDivisionError) as err:
                unavailable(plot_id, f"{label} eye", str(err))

    checkpoint()
    counts, edges, spectrum, frequency, relative = clock_data(arrays["t"], arrays["ui_ests"], ui)
    add("cdr.histogram.edges", edges, "ps", "cdr", producer="numpy.histogram(bins=100)",
        dataset_window=clock_window, source_fields=["ui_ests"])
    centers = add("cdr.histogram.centers", (edges[:-1] + edges[1:]) / 2, "ps", "cdr",
                  dataset_window=clock_window, source_fields=["cdr.histogram.edges"])
    add("cdr.histogram.counts", counts, "count", "cdr", centers,
        dataset_window=clock_window, source_fields=["ui_ests"])
    add("cdr.spectrum.raw", spectrum, "ps FFT amplitude", "cdr", "cdr.spectrum.frequency_Hz", producer="rfft(ui_ests)",
        dataset_window=clock_window, source_fields=["ui_ests"])
    add("cdr.spectrum.frequency_Hz", frequency, "Hz", "cdr",
        dataset_window=clock_window, source_fields=["ui_ests", "t"])
    add("cdr.spectrum.relative_frequency", relative, "f*UI", "cdr",
        dataset_window=clock_window, source_fields=["cdr.spectrum.frequency_Hz", "context.source.ui"])
    plots["cdr.histogram"] = dict(title="CDR clock period · 100-bin histogram", traces=[
        line("cdr.histogram", arrays[centers], counts, "Native UI estimates", "ps", "count", "cdr",
             [centers], ["cdr.histogram.counts"], dataset_window=clock_window)])
    try:
        display = clock_display(spectrum)
        plots["cdr.spectrum"] = dict(title="CDR clock period · legacy log10 ratio (no ×10/20)", traces=[
            line("cdr.spectrum", relative, display,
                 "Relative to fundamental", "f*UI", "legacy log10 ratio", "cdr",
                 ["cdr.spectrum.relative_frequency"], ["cdr.spectrum.raw"], dataset_window=clock_window, logx=True)])
    except ValueError as err:
        unavailable("cdr.spectrum", "CDR clock period · legacy log10 ratio", str(err))

    # Same scalar ratios as _get_jitter_info; source/denominator/sentinel are retained explicitly.
    manifest["jitter_rejection"] = []
    for label, before, after in (("Channel-only→Rx input", "chnl", "tx"), ("Rx input→CTLE", "tx", "ctle"),
                                  ("CTLE→DFE (includes Rx FFE)", "ctle", "dfe"), ("TOTAL", "chnl", "dfe"),
                                  ("CTLE→Rx FFE · new", "ctle", "ffe"), ("Rx FFE→DFE · new", "ffe", "dfe")):
        for metric in ("isi", "dcd", "pj", "rj"):
            start = "tx" if label == "TOTAL" and metric in ("pj", "rj") else before
            source, target = arrays.get(f"{metric}_{start}"), arrays.get(f"{metric}_{after}")
            reason = ("Tx Pj/Rj rejection is n/a" if after == "tx" and metric in ("pj", "rj") else
                      "Missing or nonfinite statistic" if source is None or target is None or not np.isfinite([source, target]).all() else
                      "Zero denominator; native sentinel is not a measurement" if target == 0 else None)
            manifest["jitter_rejection"].append(dict(segment=label, metric=metric, source=start, target=after,
                raw_ratio=1e20 if reason and target is not None and target == 0 else float(source / target) if not reason else None,
                availability="unavailable" if reason else "available", reason=reason))
    # Retained schema2 projections also enter this builder during raw-only replay.
    # Attach their direct source fields without changing or recomputing their arrays.
    def projection_sources(key, point, xsource, ysource):
        for suffix, sources in (("x", xsource), ("y", ysource)):
            dataset = datasets.get(f"display.{key}.{suffix}")
            if dataset is not None:
                dataset.update(point=point, source_fields=sources)

    for field, dataset in list(datasets.items()):
        if dataset.get("axis") and not field.startswith("display."):
            sources = [field, "context.source.ui"] if field in (
                "jitter_spectrum_dfe", "jitter_ind_spectrum_dfe", "thresh_dfe") else [field]
            projection_sources(field, dataset.get("point") or "simulation", [dataset["axis"]], sources)
    field_points = dict(ideal_signal="source", bits="source", symbols="source", noise="noise",
                        chnl_out="chnl", rx_in="tx", ctle_out="ctle", ffe_out="ffe", dfe_out="dfe",
                        adaptation="dfe", dfe_slicer_samps="dfe", dfe_slicer_decisions="dfe", bit_errs_dfe="dfe",
                        ui_ests="cdr", clocks="cdr", clock_times="cdr", lockeds="cdr", dfe_scalar_values="dfe",
                        cdr_indices="cdr")
    for field in ("ideal_signal", "chnl_out", "rx_in", "ctle_out", "ffe_out", "dfe_out"):
        projection_sources(f"wave.{field}", field_points[field], ["t", "waveform_indices"], [field, "waveform_indices"])
    for index in range(arrays.get("adaptation", np.empty((0, 0))).shape[1]):
        projection_sources(f"tap{index + 1}", "dfe", ["adaptation"], ["adaptation"])
    projection_sources("cdr", "cdr", ["t", "cdr_indices"], ["ui_ests", "cdr_indices"])
    for eye_id, point, waveform in (("rx_in", "tx", "rx_in"), ("dfe", "dfe", "dfe_out")):
        for suffix in ("x", "y", "counts"):
            dataset = datasets.get(f"eye.{eye_id}.{suffix}")
            if dataset is not None:
                dataset.update(point=point, source_fields=[waveform] + (["clock_times"] if point == "dfe" else []))
    observation_ids = {point: value[0] for point, value in POINTS.items()}
    observation_ids.update(cdr="cdr_clock", simulation="simulation_record", source="source_reference", noise="additive_noise",
                           tx_out="rx_input", ctle_out="ctle_output", ffe_out="rx_ffe_output", dfe_out="dfe_output")
    for key, dataset in datasets.items():
        dataset["point"] = dataset.get("point") or field_points.get(key, "simulation")
        if key.startswith("axis.") and key[5:] in datasets:
            dataset["point"] = datasets[key[5:]]["point"]
        if key in ("clocks", "lockeds"):
            dataset.update(window=dict(clock_window, source_field=key, stop_index=len(arrays[key]),
                                       sample_count=len(arrays[key])))
        if key == "clock_times":
            events = arrays[key]
            dataset.update(window=dict(scope="full_record", record_kind="event_times", source_field=key,
                time_axis=key, start_index=0, stop_index=len(events), sample_count=len(events), event_count=len(events),
                ignore_samps=0, ignore_until_s=0., start_s=float(events[0]) if len(events) else None,
                stop_s_inclusive=float(events[-1]) if len(events) else None))
        if key == "ui_ests" or key == "cdr_indices" or key.startswith(("cdr.", "display.cdr.")):
            dataset.update(point="cdr", window=clock_window)
        if key == "cdr_indices":
            dataset["source_fields"] = ["t"]
        dataset.setdefault("source_fields", [key])
        dataset.update(run_id=manifest["run_id"], input_hash=manifest["input_hash"], engine_sha=manifest["adapter_sha"],
                       raw_schema_version=manifest["raw_schema_version"], producer_version=ANALYSIS_VERSION,
                       observation_id=observation_ids.get(dataset["point"], dataset["point"]))
        dataset.setdefault("reason", None)
        if key.startswith("context.") and key.rsplit(".", 1)[-1] in ("tie", "tie_ind"):
            dataset["axis"] = key.rsplit(".", 1)[0] + ".t_jitter"
        if key.endswith("_h") and not key.startswith("display."):
            dataset["normalization"] = "Native discrete V/sample; no Ts rescaling"
            dataset["sample_origin"] = "native t_ns_chnl/start_ix" if key.startswith("chnl") or "_out_" in key else "native t[:N]"
    checkpoint()
