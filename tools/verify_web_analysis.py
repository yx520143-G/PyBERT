"""Bounded #3 raw/helper/display checks, independent of adapter builders for expectations."""

import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from scipy import signal

from pybert.models.bert import MIN_BATHTUB_VAL
from pybert.utility import calc_eye, calc_jitter, find_crossings, make_bathtub, safe_log10
from pybert.web.analysis import extend_analysis
from pybert.web.tasks import Tasks

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "docs/webui/issue3/fixtures"
OUT = ROOT / "docs/webui/issue3/evidence" / time.strftime("numeric-%Y%m%d-%H%M%S")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(arrays, manifest, old_arrays=None):
    raw_checks, display_checks = [], []
    ui = float(arrays["context.source.ui"])

    def check(name, actual, expected, rtol=1e-10, atol=1e-18, display=False):
        a, b = np.asarray(actual), np.asarray(expected)
        shape = a.shape == b.shape
        masks = shape and np.array_equal(np.isfinite(a), np.isfinite(b))
        finite = shape and np.isfinite(a).all() and np.isfinite(b).all()
        good = np.isclose(a, b, rtol=rtol, atol=atol) if shape else np.asarray(False)
        difference = abs(a.astype(int) - b.astype(int)) if shape and a.dtype.kind == "b" else abs(a - b) if shape else np.asarray([])
        relative = np.divide(difference, abs(b), out=np.zeros_like(difference, dtype=float), where=abs(b) > 0) if shape else difference
        record = dict(check=name, passed=bool(shape and finite and good.all()), shape=list(a.shape), rtol=rtol, atol=atol,
                      validity_masks_equal=bool(masks), max_abs=float(difference.max()) if finite and a.size else None,
                      max_rel=float(relative.max()) if finite and a.size else None,
                      first_bad=np.argwhere(~good)[0].tolist() if shape and not good.all() else None)
        (display_checks if display else raw_checks).append(record)

    if old_arrays is not None:
        for key, value in old_arrays.items():
            check(f"original unchanged: {key}", arrays[key], value, 0, 0)
    source = {k.split("context.source.")[1]: v for k, v in arrays.items() if k.startswith("context.source.")}
    # Direct existing helpers with the frozen full waveform and local reference, no adapter helper/builder.
    t, reference = arrays["t"], source["x"]
    shift = (signal.correlate(arrays["ffe_out"], reference).argmax() - (len(reference) - 1)) * ui / int(source["nspui"])
    crossings = find_crossings(t, arrays["ffe_out"], float(source["decision_scaler"]), mod_type=int(source["mod_type"]))
    aligned = crossings - shift
    chosen = aligned[aligned > source["xing_min_t"]] - source["xing_min_t"]
    expected = calc_jitter(ui, int(source["eye_uis"]), int(source["pattern_len"]), source["ideal_xings_jit"],
                           chosen, float(source["rel_thresh"]), xing_mask=source.get("xing_mask"))
    return_names = ("tie", "t_jitter", "isi", "dcd", "pj", "rj", "pjDD", "rjDD", "tie_ind", "thresh", "jitter_spectrum",
                    "jitter_ind_spectrum", "spectrum_freqs", "jitter", "jitter_ext", "bin_centers", "mu_pos", "mu_neg", "dj_pos", "dj_neg")
    context_names = {"tie", "t_jitter", "tie_ind", "spectrum_freqs", "bin_centers"}
    for name, value in zip(return_names, expected):
        key = f"context.ffe.{name}" if name in context_names else f"{name}_ffe"
        rtol, atol = (1e-12, 1e-6) if name == "spectrum_freqs" else (1e-10, 1e-12 / ui) if name in ("jitter", "jitter_ext") else (1e-10, 1e-18)
        check(f"direct helper: {key}", arrays[key], value, rtol, atol)
    for name, value in (("ofst", shift), ("actual_xings", crossings), ("actual_xings_jit", chosen)):
        check(f"direct context: {name}", arrays[f"context.ffe.{name}"], value)
    if int(source["mod_type"]) == 2:
        ideal = arrays["context.source.ideal_xings"]
        before = np.interp(ideal-ui/2, t, source["ideal_signal"])
        after = np.interp(ideal+ui/2, t, source["ideal_signal"])
        symmetric = abs(before+after) < .1*max(abs(source["ideal_signal"]))
        check("PAM4 symmetric mask", source["xing_mask"], symmetric[ideal>source["xing_min_t"]], 0, 0)
    noise = np.random.default_rng(34003).normal(0, 1e-3, len(t))
    check("separate frozen display noise", arrays["display.channel_noise"], noise, 0, 0)
    for point, field in (("chnl", "chnl_out"), ("tx", "rx_in"), ("ctle", "ctle_out"), ("ffe", "ffe_out"), ("dfe", "dfe_out"), ("chnl.gui_noise", "chnl_out")):
        ys = (arrays[field] + noise if point == "chnl.gui_noise" else arrays[field])[manifest["window"]["ignore_samps"]:]
        clocks = arrays["clock_times"][arrays["clock_times"] >= manifest["window"]["ignore_until_s"]] - manifest["window"]["ignore_until_s"]
        use_clocks = point == "dfe" and len(clocks) > 0
        maximum = 1.1 * max(abs(ys))
        expected_eye = calc_eye(ui, int(source["nspui"]), 1000, ys, maximum, clocks if use_clocks else None)
        check(f"direct eye counts {point}", arrays[f"eye.{point}.counts"], expected_eye, 0, 0)
        mapping = manifest["datasets"][f"eye.{point}.counts"]
        check(f"eye y_max {point}", mapping["y_max"], maximum, 0, 0)
        check(f"eye y_scale {point}", mapping["y_scale"], 1000//(2*maximum), 0, 0)
        check(f"eye x {point}", arrays[f"eye.{point}.x"], np.linspace(-ui,ui,2*int(source["nspui"]))*1e12, 1e-10, 1e-10, True)
        check(f"eye y {point}", arrays[f"eye.{point}.y"], (np.arange(1000)-500)/(1000//(2*maximum)), 1e-10, 1e-10, True)
    for point in ("chnl", "tx", "ctle", "ffe", "dfe"):
        bins = arrays[f"context.{point}.bin_centers"]
        probability = make_bathtub(bins, arrays[f"jitter_{point}"], min_val=.1*MIN_BATHTUB_VAL,
                                   rj=float(arrays[f"rj_{point}"]), mu_r=float(arrays[f"dj_pos_{point}"]),
                                   mu_l=float(arrays[f"dj_neg_{point}"]), extrap=True)
        check(f"direct bathtub {point}", arrays[f"bathtub.{point}.probability"], probability, 1e-8, 0)
        check(f"bathtub floor mask {point}", arrays[f"bathtub.{point}.probability"] == .1*MIN_BATHTUB_VAL, probability == .1*MIN_BATHTUB_VAL, 0, 0)
        for name in ("jitter", "jitter_ext"):
            check(f"display PDF {point} {name}", arrays[f"display.pdf.{point}.{name}.y"], arrays[f"{name}_{point}"]*1e-12, 1e-10, 1e-10, True)
            check(f"display PDF bins {point} {name}", arrays[f"display.pdf.{point}.{name}.x"], bins*1e12, 1e-10, 1e-10, True)
        for name in ("jitter_spectrum", "jitter_ind_spectrum", "thresh"):
            check(f"display spectrum {point} {name}", arrays[f"display.spec.{point}.{name}.y"], 10*(safe_log10(arrays[f"{name}_{point}"][1:])-safe_log10(ui)), 1e-10, 1e-10, True)
            check(f"display spectrum axis {point} {name}", arrays[f"display.spec.{point}.{name}.x"], arrays[f"context.{point}.spectrum_freqs"][1:]*1e-6, 1e-10, 1e-10, True)
        check(f"display bathtub {point}", arrays[f"display.bathtub.{point}.y"], safe_log10(probability), 1e-10, 1e-10, True)
    counts, edges = np.histogram(arrays["ui_ests"], bins=100)
    check("clock histogram counts", arrays["cdr.histogram.counts"], counts, 0, 0)
    check("clock histogram edges ps", arrays["cdr.histogram.edges"], edges, 1e-10, 1e-6)
    fft = np.fft.rfft(arrays["ui_ests"])
    f_clock = np.arange(len(fft)) / (t[1] * len(t))
    check("clock raw complex FFT real", arrays["cdr.spectrum.raw"].real, fft.real, 1e-10, 1e-6)
    check("clock raw complex FFT imag", arrays["cdr.spectrum.raw"].imag, fft.imag, 1e-10, 1e-6)
    check("clock frequency Hz", arrays["cdr.spectrum.frequency_Hz"], f_clock, 1e-12, 1e-6)
    check("clock frequency f*UI", arrays["cdr.spectrum.relative_frequency"], f_clock[1:]*ui, 1e-12, 1e-6*ui)
    check("clock legacy log10 display", arrays["display.cdr.spectrum.y"], safe_log10(abs(fft[1:])/abs(fft[1])), 1e-10, 1e-10, True)
    for key in ("chnl_H_raw", "chnl_H", "chnl_trimmed_H"):
        check(f"channel frequency {key}", arrays[f"display.channel.{key}.y"], 20*safe_log10(abs(arrays[key][1:])), 1e-10, 1e-10, True)
    for key, dataset in manifest["datasets"].items():
        raw_checks.append(dict(check=f"typed identity {key}",passed=dataset["shape"] == list(arrays[key].shape)
            and dataset["dtype"] == str(arrays[key].dtype) and dataset["run_id"] == manifest["run_id"]
            and dataset["input_hash"] == manifest["input_hash"] and dataset["window"] == manifest["window"]
            and "reason" in dataset and "unit" in dataset and "producer_version" in dataset))
    for row in manifest["jitter_rejection"]:
        before, after = arrays[f"{row['metric']}_{row['source']}"], arrays[f"{row['metric']}_{row['target']}"]
        na = row["target"] == "tx" and row["metric"] in ("pj","rj")
        if na or after == 0:
            raw_checks.append(dict(check=f"rejection unavailable {row['segment']} {row['metric']}",passed=row["availability"] == "unavailable" and bool(row["reason"])))
        else:
            check(f"rejection source/ratio {row['segment']} {row['metric']}",row["raw_ratio"],before/after,0,0)
    return dict(raw_checks=raw_checks, display_checks=display_checks,
                passed=all(c["passed"] for c in raw_checks+display_checks))


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    frozen = json.loads((FIX / "frozen-manifest.json").read_text(encoding="utf-8"))
    correction = json.loads((FIX / "window-correction-v2.json").read_text(encoding="utf-8"))
    assert correction["parent_sha256"] == digest(FIX / "frozen-manifest.json")
    report = dict(parent_freeze_sha256=correction["parent_sha256"], window_correction_sha256=digest(FIX / "window-correction-v2.json"),
                  method="Saved full raw; independent direct native helper expectations, no shared analysis builder for expected values", fixtures=[],
                  execution_sources={str(p.relative_to(ROOT)):digest(p) for p in [*sorted((ROOT / "src/pybert/web").glob("*.py")), Path(__file__)]})
    try:
        for name in ("F-NRZ-01", "F-PAM4-01"):
            item = frozen["inputs"][name]
            source = Path(item["source"])
            assert digest(source / "arrays.npz") == item["source_raw_sha256"]
            assert digest(source / "manifest.json") == item["source_manifest_sha256"]
            original = dict(np.load(source / "arrays.npz", allow_pickle=False))
            manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
            assert manifest["window"] == {k:v for k,v in correction["windows"][name].items() if k in manifest["window"]}
            manifest["run_id"] = name
            manifest["raw_schema_version"] = 3
            arrays = {key:value.copy() for key,value in original.items()}
            rng = np.random.get_state()
            extend_analysis(arrays, manifest)
            assert all(np.array_equal(a,b) for a,b in zip(rng,np.random.get_state()))
            dest = OUT / name
            dest.mkdir()
            np.savez_compressed(dest / "arrays.npz", **arrays)
            (dest / "manifest.json").write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding="utf-8")
            result = verify(arrays, manifest, original)
            report["fixtures"].append(dict(fixture=name, **result))
            print(name, result["passed"], len(result["raw_checks"]),len(result["display_checks"]),flush=True)
        if "--identity" in sys.argv or "--identity-source" in sys.argv:
            item = json.loads((FIX / "identity-effective-v3.json").read_text(encoding="utf-8"))
            report["identity_effective_freeze_sha256"] = digest(FIX / "identity-effective-v3.json")
            if "--identity-source" in sys.argv:
                dest = Path(sys.argv[sys.argv.index("--identity-source")+1])
                report["identity_reused_source"] = dict(path=str(dest),raw_sha256=digest(dest / "arrays.npz"),manifest_sha256=digest(dest / "manifest.json"))
            else:
                manager = Tasks(OUT / "local/control")
                normalized = manager.normalize(dict(mode="load",config=item["config"]))
                assert normalized["input_hash"] == item["input_hash"]
                task = manager.start("run",dict(config=normalized["config"],input_hash=item["input_hash"]))
                assert manager.tasks[task["task_id"]]["done"].wait(180)
                task = manager.get(task["task_id"])
                report["identity_task"] = task
                assert task["state"] == "succeeded", task
                dest = manager.directory(task["task_id"])
            arrays = dict(np.load(dest / "arrays.npz",allow_pickle=False))
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            if "--identity-source" in sys.argv:
                extend_analysis(arrays, manifest)
                output = OUT / "F-NRZ-IDENTITY"
                output.mkdir()
                np.savez_compressed(output / "arrays.npz",**arrays)
                (output / "manifest.json").write_text(json.dumps(manifest,indent=2,allow_nan=False),encoding="utf-8")
            result = verify(arrays,manifest)
            equality = {key: bool(np.array_equal(arrays[key+"_ctle"], arrays[key+"_ffe"])) for key in
                        ("jitter","jitter_ext","jitter_spectrum","jitter_ind_spectrum","thresh","isi","dcd","pj","rj","pjDD","rjDD","mu_pos","mu_neg","dj_pos","dj_neg")}
            equality.update({"context_"+key:bool(np.array_equal(arrays["context.ctle."+key],arrays["context.ffe."+key]))
                             for key in ("ofst","actual_xings","actual_xings_jit","t_jitter","bin_centers","spectrum_freqs","tie","tie_ind")})
            equality.update(waveform=bool(np.array_equal(arrays["ctle_out"],arrays["ffe_out"])),
                            eye=bool(np.array_equal(arrays["eye.ctle.counts"], arrays["eye.ffe.counts"])),
                            bathtub=bool(np.array_equal(arrays["bathtub.ctle.probability"],arrays["bathtub.ffe.probability"])))
            original = dict(np.load(Path(frozen["inputs"]["F-NRZ-01"]["source"]) / "arrays.npz"))
            equality.update({key+"_unchanged": bool(np.array_equal(arrays[key],original[key])) for key in ("bits","noise")})
            report["fixtures"].append(dict(fixture="F-NRZ-IDENTITY", **result, identity_equalities=equality))
            print("identity",result["passed"],equality,flush=True)
        report["passed"] = all(item["passed"] and all(item.get("identity_equalities",{}).values()) for item in report["fixtures"])
    except Exception:
        report["passed"] = False
        report["exception"] = traceback.format_exc()
        raise
    finally:
        (OUT / "report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
        print(OUT,flush=True)
    assert report["passed"]


if __name__ == "__main__":
    main()
