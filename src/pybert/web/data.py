"""Lossless engine datasets and separate bounded display projections."""

import importlib.metadata
import json
import subprocess
import hashlib
from pathlib import Path

import numpy as np

from pybert.utility import calc_eye, safe_log10
from pybert.web import NATIVE_SHA, NATIVE_IMPORTER_SHA, PROTOTYPE_SHA, RAW_SCHEMA_VERSION, SCHEMA_VERSION

RESPONSES = ("chnl", "tx", "tx_out", "ctle", "ctle_out", "ffe", "ffe_out", "dfe", "dfe_out")
WAVEFORMS = ("ideal_signal", "chnl_out", "rx_in", "ctle_out", "ffe_out", "dfe_out")
JITTER_POINTS = ("chnl", "tx", "ctle", "dfe")
JITTER_STATS = ("isi", "dcd", "pj", "rj", "pjDD", "rjDD", "mu_pos", "mu_neg", "dj_pos", "dj_neg")
RAW_FIELDS = (
    "start_ix",
    "t",
    "f",
    "t_ns_chnl",
    "t_irfft",
    "bits",
    "symbols",
    "noise",
    "dfe_slicer_samps",
    "dfe_slicer_decisions",
    "bit_errs_dfe",
    "adaptation",
    "ui_ests",
    "clocks",
    "clock_times",
    "lockeds",
    "dfe_scalar_values",
    "chnl_H_raw",
    "chnl_trimmed_H",
) + WAVEFORMS
CATALOG = {
    "raw_fields": RAW_FIELDS,
    "response_fields": [f"{p}_{s}" for p in RESPONSES for s in ("h", "s", "p", "H")],
    "jitter_fields": [
        f"{name}_{p}"
        for p in JITTER_POINTS
        for name in ("jitter", "jitter_ext", "jitter_spectrum", "jitter_ind_spectrum", "thresh", *JITTER_STATS)
    ],
    "local_context": [
        "source.x",
        "source.ideal_signal",
        "source.ideal_xings",
        "source.ideal_xings_jit",
        "source.xing_mask",
        "source.ui/nspui/nui/eye_uis/pattern_len/rel_thresh/decision_scaler/mod_type/xing_min_t",
        "each_point.ofst/actual_xings/actual_xings_jit/t_jitter/bin_centers/spectrum_freqs/tie/tie_ind/valid",
    ],
    "eyes": ["chnl", "tx", "ctle", "ffe", "dfe", "chnl.gui_noise"],
    "analysis": ["new RxFFE native helpers", "per-point jitter and bathtub", "CDR histogram/legacy spectrum"],
    "display_only": [
        "response dB (native safe_log10)",
        "jitter /ps and ps",
        "native spectrum 10*(log10(raw)-log10(UI))",
        "last 20UI bounded waveform indices",
        "DFE/CDR adaptation",
    ],
}


def adapter_sha():
    source = Path(__file__).resolve()
    source_root = source.parents[3]
    if not (source_root / ".git").exists() or (source_root / "src/pybert/web/data.py").resolve() != source:
        return "unavailable"
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source_root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def source_identity():
    """Actual on-disk source bytes supplement Git HEAD, which can be dirty."""
    package = Path(__file__).resolve().parents[1]
    paths = [*Path(__file__).parent.glob("*.py"), *Path(__file__).parent.joinpath("static").glob("*")]
    paths += [package / name for name in ("pybert.py", "models/bert.py", "utility/sparam.py", "configuration.py", "threads/optimization.py")]
    return {str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_file()}


def collect(engine, observations, directory, identity, cancelled=lambda: False):
    """Publish only complete finite raw data, with independent axes per observation."""
    p = engine
    arrays, datasets, plots = {}, {}, {}
    window = {
        "nui": p.nui,
        "eye_uis": p.eye_uis,
        "ignore_samps": (p.nui - p.eye_uis) * p.nspui,
        "ignore_until_s": (p.nui - p.eye_uis) * p.ui,
    }

    def add(key, value, unit="1", axis=None, point=None, kind="raw", producer=None, **extra):
        arr = np.asarray(value)
        if arr.dtype.kind not in "biufc" or not np.isfinite(arr).all():
            raise ValueError(f"{key}: nonfinite or nonnumeric native dataset.")
        arrays[key] = arr
        datasets[key] = dict(
            field=key,
            producer=producer or f"PyBERT.{key}",
            point=point,
            kind=kind,
            dtype=str(arr.dtype),
            shape=list(arr.shape),
            unit=unit,
            axis=axis,
            window=window,
            clock_basis="native",
            display_noise=False,
            availability="available",
            **extra,
        )
        return key

    def line(key, x, y, label, xunit, yunit, **extra):
        if len(x) != len(y):
            raise ValueError(f"{key}: axis mismatch {len(x)} != {len(y)}")
        add(f"display.{key}.x", x, xunit, kind="display")
        add(f"display.{key}.y", y, yunit, axis=f"display.{key}.x", kind="display")
        return dict(x=f"display.{key}.x", y=f"display.{key}.y", name=label, xunit=xunit, yunit=yunit, **extra)

    for key in RAW_FIELDS:
        unit = (
            "s"
            if key in ("t", "t_irfft", "clock_times")
            else "Hz"
            if key == "f"
            else "ns"
            if key == "t_ns_chnl"
            else "ps"
            if key == "ui_ests"
            else "V"
            if key in WAVEFORMS or key in ("noise", "dfe_slicer_samps", "dfe_scalar_values")
            else "1"
        )
        add(
            key,
            getattr(p, key),
            unit,
            axis="t" if key in WAVEFORMS or key in ("noise", "ui_ests", "clocks", "lockeds") else None,
        )
    datasets["start_ix"].update(unit="sample index", producer="PyBERT.calc_chnl_h.start_ix", point="chnl")
    datasets["noise"].update(producer="my_run_simulation.noise before FEXT addition", point="noise")
    for key in WAVEFORMS + ("noise", "ui_ests", "clocks", "lockeds"):
        if arrays[key].shape != arrays["t"].shape:
            raise ValueError(f"{key}: incomplete time record")
    for point in RESPONSES:
        kind = (
            "diagnostic"
            if point == "chnl"
            else "equivalent"
            if point.startswith("dfe")
            else "cumulative"
            if point.endswith("out")
            else "single"
        )
        for suffix in ("h", "s", "p", "H"):
            key = f"{point}_{suffix}"
            value = np.asarray(getattr(p, key))
            axis = "f" if suffix == "H" else f"axis.{point}_{suffix}"
            if suffix != "H":
                time = p.t_ns_chnl if point == "chnl" or point.endswith("out") else p.t[: len(value)] * 1e9
                if len(time) != len(value):
                    raise ValueError(f"{key}: incomplete response axis")
                add(axis, time, "ns", kind="axis")
            elif len(value) != len(p.f):
                raise ValueError(f"{key}: incomplete frequency axis")
            add(
                key,
                value,
                "complex gain" if suffix == "H" else "V/sample" if suffix == "h" else "V",
                axis,
                point,
                kind,
            )
            if suffix == "H":
                traces = line(
                    key, p.f[1:] / 1e9, 20 * safe_log10(abs(value[1:])), f"{point} · {kind}", "GHz", "dB", logx=True
                )
            else:
                traces = line(key, arrays[axis], value, f"{point} · {kind}", "ns", datasets[key]["unit"])
            plots[key] = {"traces": [traces], "title": f"{key} · {kind}"}
    for key in ("chnl_H_raw", "chnl_trimmed_H"):
        if len(arrays[key]) != len(p.f):
            raise ValueError(f"{key}: incomplete frequency axis")
        datasets[key].update(axis="f", unit="complex gain", point="chnl")

    # Full arrays remain untouched. Only the plot is projected to a bounded window.
    start = max(0, len(p.t) - 20 * p.nspui)
    indices = np.unique(np.linspace(start, len(p.t) - 1, min(4096, len(p.t) - start), dtype=int))
    add("waveform_indices", indices, "sample index", kind="display")
    labels = {
        "ideal_signal": "Ideal reference",
        "chnl_out": "Channel-only diagnostic",
        "rx_in": "Native Rx input (+Tx, noise)",
        "ctle_out": "CTLE output",
        "ffe_out": "Rx FFE output",
        "dfe_out": "DFE summing-node output",
    }
    plots["waveforms"] = {"title": "Outputs · last 20 UI", "projection": "waveform_indices", "traces": []}
    for key in WAVEFORMS:
        trace = line(f"wave.{key}", p.t[indices] * 1e9, arrays[key][indices], labels[key], "ns", "V")
        plots[f"wave.{key}"] = {"title": labels[key], "traces": [trace], "projection": "waveform_indices"}
        plots["waveforms"]["traces"].append(trace)
    if cancelled():
        raise RuntimeError("Cancelled during result projection")

    for point, context in observations.items():
        for key, value in context.items():
            if value is not None:
                unit = (
                    "Hz"
                    if key == "spectrum_freqs"
                    else "V"
                    if key in ("x", "ideal_signal", "decision_scaler", "noise_total") or key.endswith("_voltage")
                    else "1"
                    if key
                    in ("xing_mask", "valid", "nspui", "nui", "eye_uis", "pattern_len", "rel_thresh", "mod_type")
                    else "s"
                )
                add(
                    f"context.{point}.{key}",
                    value,
                    unit,
                    point=point,
                    kind="context",
                    producer="my_run_simulation locals",
                )
    source = observations["source"]
    noise_traces = []
    for key in ("x", "noise_total", *(k for k in source if k.endswith("_voltage"))):
        field = f"context.source.{key}"
        if field not in arrays:
            continue
        datasets[field].update(axis="t", unit="V", point="source" if key == "x" else "noise",
                               window={"kind": "full_record", "sample_start": 0, "sample_stop_exclusive": len(p.t)},
                               producer="my_run_simulation.x" if key == "x" else "my_run_simulation FEXT injection locals")
        label = "Actual source x" if key == "x" else "Total base noise + coherent FEXT" if key == "noise_total" else key
        trace = line(f"wave.{key}", p.t[indices] * 1e9, arrays[field][indices], label, "ns", "V")
        plots[f"wave.{key}"] = {"title": label, "traces": [trace], "projection": "waveform_indices"}
        if key != "x":
            noise_traces.append(trace)
    noise_traces.insert(0, line("wave.noise_base", p.t[indices] * 1e9, arrays["noise"][indices], "Base periodic + random noise (self.noise)", "ns", "V"))
    plots["noise"] = {"title": "Base noise / coherent FEXT contributions / total injection", "traces": noise_traces,
                      "fext_availability": "active" if source.get("fext_count", 0) else "disabled"}
    for index in range(source.get("fext_count", 0)):
        prefix = f"context.source.fext_{index}"
        start_ix = int(arrays[f"{prefix}_start_ix"])
        axis = add(f"axis.fext_{index}_h", p.t[start_ix:start_ix + len(arrays[f"{prefix}_h"])] * 1e9, "ns", kind="axis")
        datasets[f"{prefix}_h"].update(axis=axis, unit="V/sample", point="noise", producer="PyBERT.calc_chnl_h FEXT trim_impulse")
        datasets[f"{prefix}_H"].update(axis="f", unit="complex gain", point="noise", producer="PyBERT.calc_chnl_h FEXT terminated s21")
        datasets[f"{prefix}_start_ix"].update(unit="sample index", producer="PyBERT.calc_chnl_h FEXT trim_impulse")
    for point in JITTER_POINTS:
        if point not in observations or not observations[point]["valid"]:
            raise ValueError(f"{point}: native jitter did not complete")
        for stat in JITTER_STATS:
            add(f"{stat}_{point}", getattr(p, f"{stat}_{point}"), "s", point=point)
        for name in ("jitter", "jitter_ext", "jitter_spectrum", "jitter_ind_spectrum", "thresh"):
            key = f"{name}_{point}"
            pdf = name in ("jitter", "jitter_ext")
            axis = f"context.{point}.{'bin_centers' if pdf else 'spectrum_freqs'}"
            add(key, getattr(p, key), "1/s" if pdf else "s", axis, point)
            if len(arrays[key]) != len(arrays[axis]):
                raise ValueError(f"{key}: local axis mismatch")
    for name in ("jitter", "jitter_ext"):
        key = f"{name}_dfe"
        trace = line(
            key,
            arrays["context.dfe.bin_centers"] * 1e12,
            arrays[key] * 1e-12,
            "Total PDF" if name == "jitter" else "Data-independent PDF",
            "ps",
            "1/ps",
        )
        plots.setdefault("jitter.dist", {"title": "DFE crossing jitter · Dist.", "traces": []})["traces"].append(trace)
    for name in ("jitter_spectrum", "jitter_ind_spectrum", "thresh"):
        key = f"{name}_dfe"
        trace = line(
            key,
            arrays["context.dfe.spectrum_freqs"][1:] * 1e-6,
            10 * (safe_log10(arrays[key][1:]) - safe_log10(p.ui)),
            name,
            "MHz",
            "10 log10(amplitude/UI)",
            logx=True,
        )
        plots.setdefault(
            "jitter.spec", {"title": "DFE jitter · Spec. (native amplitude ratio, not PSD)", "traces": []}
        )["traces"].append(trace)

    for point, field in (("rx_in", "rx_in"), ("dfe", "dfe_out")):
        ys = arrays[field][window["ignore_samps"] :]
        y_max = 1.1 * max(abs(ys))
        y_scale, y_offset = 1000 // (2 * y_max), 500
        if y_scale <= 0:
            raise ValueError(f"{point}: native eye mapping has zero scale")
        clocks = np.asarray(p.clock_times)
        clocks = clocks[clocks >= window["ignore_until_s"]] - window["ignore_until_s"]
        actual_clock = point == "dfe" and len(clocks) > 0
        counts = calc_eye(p.ui, p.nspui, 1000, ys, y_max, clocks if actual_clock else None)
        xkey = add(f"eye.{point}.x", np.linspace(-p.ui, p.ui, 2 * p.nspui) * 1e12, "ps", kind="axis")
        ykey = add(f"eye.{point}.y", (np.arange(1000) - y_offset) / y_scale, "V", kind="axis")
        zkey = add(
            f"eye.{point}.counts",
            counts,
            "count",
            point=point,
            kind="eye",
            producer="calc_eye",
            y_max=float(y_max),
            y_scale=float(y_scale),
            y_offset=y_offset,
            clock_fallback=point == "dfe" and not actual_clock,
        )
        datasets[zkey]["clock_basis"] = "recovered clock_times" if actual_clock else "nominal fold"
        plots[f"eye.{point}"] = {
            "title": f"{point} eye · {datasets[zkey]['clock_basis']}",
            "heatmap": {"x": xkey, "y": ykey, "z": zkey},
            "traces": [],
        }
        if cancelled():
            raise RuntimeError("Cancelled during native eye generation")
    plots["adaptation"] = {"title": "DFE adaptation · record index", "traces": []}
    for i, values in enumerate(np.asarray(p.adaptation).T):
        plots["adaptation"]["traces"].append(
            line(f"tap{i + 1}", np.arange(len(values)), values, f"Tap{i + 1}", "record index", "coefficient")
        )
    cdr_indices = np.unique(np.linspace(0, len(p.t) - 1, min(4096, len(p.t)), dtype=int))
    add("cdr_indices", cdr_indices, "sample index", kind="display")
    plots["cdr"] = {
        "title": "CDR UI estimates",
        "projection": "cdr_indices",
        "traces": [line("cdr", p.t[cdr_indices] * 1e9, p.ui_ests[cdr_indices], "Native UI estimates", "ns", "ps")],
    }
    stats = {key: float(getattr(p, f"{key}_dfe")) for key in JITTER_STATS}
    summary = {
        "n_errs_dfe": int(p.n_errs_dfe),
        "n_errs_viterbi": None,
        "viterbi_availability": "not run",
        "chnl_dly_s": float(p.chnl_dly),
        "rel_power": float(p.rel_power),
        "dfe_jitter_s": stats,
        "initial_level_v": identity["effective_input"]["decision_scaler"],
        "final_level_v": float(p.decision_scaler),
        "performance_Msamples_per_min": {
            k: float(getattr(p, f"{k}_perf")) * 60e-6
            for k in ("channel", "tx", "ctle", "ffe", "dfe", "jitter", "total")
        },
    }
    manifest = dict(
        schema_version=SCHEMA_VERSION,
        raw_schema_version=RAW_SCHEMA_VERSION,
        **{k: v for k, v in identity.items() if k not in ("warnings", "resources")},
        native_sha=NATIVE_SHA,
        native_importer_sha=NATIVE_IMPORTER_SHA,
        prototype_sha=PROTOTYPE_SHA,
        adapter_sha=adapter_sha(),
        actual_source_sha256=source_identity(),
        status="succeeded",
        datasets=datasets,
        plots=plots,
        summary=summary,
        window=window,
        resources=identity.get("resources", []),
        warnings=identity.get("warnings", []),
        packages={
            name: importlib.metadata.version(name)
            for name in ("pipbert", "numpy", "scipy", "traits", "pyibis-ami", "pychopmarg")
        },
    )
    directory = Path(directory)
    from pybert.web.analysis import extend_analysis

    extend_analysis(arrays, manifest, cancelled)
    from pybert.web.resource_data import annotate_interference

    annotate_interference(arrays, manifest)
    np.savez_compressed(directory / "arrays.npz", **arrays)
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False), encoding="utf-8")
    return manifest


def plot_payload(directory, plot_id):
    """Read an immutable display; changing views never runs the engine."""
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    plot = manifest["plots"][plot_id]
    if plot.get("availability") == "unavailable":
        return dict(run_id=manifest["run_id"], plot_id=plot_id, data=[], **plot)
    with np.load(directory / "arrays.npz", allow_pickle=False) as arrays:
        traces = [
            {
                "type": "scatter",
                "mode": "lines",
                "name": trace["name"],
                "x": arrays[trace["x"]].tolist(),
                "y": arrays[trace["y"]].tolist(),
            }
            for trace in plot["traces"]
        ]
        if "heatmap" in plot:
            m = plot["heatmap"]
            traces = [
                {
                    "type": "heatmap",
                    "x": arrays[m["x"]].tolist(),
                    "y": arrays[m["y"]].tolist(),
                    "z": arrays[m["z"]].tolist(),
                    "colorscale": "Viridis",
                    "colorbar": {"title": "count"},
                }
            ]
    first = plot["traces"][0] if plot["traces"] else {"xunit": "ps", "yunit": "V"}
    fields = list(plot.get("heatmap", {}).values()) or [trace[axis] for trace in plot["traces"] for axis in ("x", "y")]
    metadata = dict(plot.get("metadata", {}))
    if plot_id == "noise":
        metadata["interference"] = manifest.get("interference", {"availability": plot.get("fext_availability", "unknown")})
    if fields:
        metadata.update(window=manifest["datasets"][fields[0]]["window"],
                        datasets={key:manifest["datasets"][key] for key in fields})
    return {
        "run_id": manifest["run_id"],
        "plot_id": plot_id,
        "data": traces,
        "title": plot["title"] + (" · FEXT disabled" if plot_id == "noise" and metadata["interference"]["availability"] == "disabled" else ""),
        "xunit": first["xunit"],
        "yunit": first["yunit"],
        "logx": first.get("logx", False),
        "metadata": metadata,
        "availability": "available",
    }
