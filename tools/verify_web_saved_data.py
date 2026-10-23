"""独立复核已保存数组：原生GUI helper、summary、complex real/imag、hash规范映射。"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

from pybert.utility import safe_log10
from pybert.web.config import input_hash, load_config, new_engine, snapshot

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs/webui/issue2/evidence/numeric-20261024-043542"
FIXTURES = ROOT / "docs/webui/issue2/fixtures"


def main():
    spec = importlib.util.spec_from_file_location("pybert.models.independent_native", BASE / "F-NRZ-01/native_bert.py")
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    report = {
        "method": "Rehydrate saved raw data; call exact native update_results, no simulation.",
        "hash_schema": "v1 canonical JSON: sorted keys, integral float represented as integer; booleans remain boolean",
        "previous_hash_schema": "legacy JSON distinguished 40 from 40.0; old frozen files retained unchanged",
        "fixtures": [],
    }
    source_report = json.loads((BASE / "report.json").read_text(encoding="utf-8"))
    for item in source_report["fixtures"]:
        name = item["fixture"]
        path = BASE / "workers" / item["task"]["task_id"]
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        reference = json.loads((BASE / name / "manifest.json").read_text(encoding="utf-8"))
        config = manifest["effective_input"]
        p = new_engine()
        load_config(p, config, snapshot(p))
        checks = []

        def check(label, actual, expected, rtol=1e-10, atol=1e-10, checks=checks):
            a, b = np.asarray(actual), np.asarray(expected)
            same_shape = a.shape == b.shape
            finite = np.isfinite(a).all() and np.isfinite(b).all()
            good = np.isclose(a, b, rtol=rtol, atol=atol) if same_shape else np.array(False)
            checks.append(
                {
                    "check": label,
                    "passed": bool(same_shape and finite and good.all()),
                    "rtol": rtol,
                    "atol": atol,
                    "max_abs": float(np.max(np.abs(a - b))) if same_shape and a.size else 0,
                    "shape": list(a.shape),
                    "first_bad": np.argwhere(~good)[0].tolist() if same_shape and not good.all() else None,
                }
            )

        with np.load(path / "arrays.npz") as arrays, np.load(BASE / name / "arrays.npz") as original:
            if "start_ix" in arrays:
                check("native start_ix integer", arrays["start_ix"], original["start_ix"], 0, 0)
                checks.append(
                    {
                        "check": "start_ix scalar integer metadata",
                        "passed": arrays["start_ix"].ndim == 0
                        and arrays["start_ix"].dtype.kind in "iu"
                        and manifest["datasets"]["start_ix"]["unit"] == "sample index",
                    }
                )
            for key in arrays.files:
                if np.iscomplexobj(arrays[key]):
                    check(f"{key}.real", arrays[key].real, original[key].real, 1e-10, 1e-12)
                    check(f"{key}.imag", arrays[key].imag, original[key].imag, 1e-10, 1e-12)
                if (
                    key in ("t", "f", "symbols", "bits", "t_irfft")
                    or key.startswith(("display.", "context.", "axis.", "eye."))
                    or key == "waveform_indices"
                ):
                    continue
                setattr(p, key, arrays[key].item() if arrays[key].ndim == 0 else arrays[key])
            p.jitter_bins = arrays["context.chnl.bin_centers"]
            p.f_MHz = arrays["context.chnl.spectrum_freqs"] * 1e-6
            p.f_MHz_dfe = arrays["context.dfe.spectrum_freqs"] * 1e-6
            # Exact native initialization at bert.py:1017; S1 does not display this placeholder.
            p.jitter_rejection_ratio = np.zeros(len(p.jitter_spectrum_dfe))
            # This is the original GUI producer, independent of web collect/metadata.
            native.update_results(p)
            for point in ("chnl", "tx", "tx_out", "ctle", "ctle_out", "dfe", "dfe_out"):
                for suffix in ("h", "s", "p", "H"):
                    key = f"{point}_{suffix}"
                    if key not in p.plotdata.list_data():
                        continue
                    check(f"native GUI display {key}", arrays[f"display.{key}.y"], p.plotdata.get_data(key))
            for point in ("ffe", "ffe_out"):
                check(
                    f"native helper display {point}_H",
                    arrays[f"display.{point}_H.y"],
                    20 * safe_log10(abs(arrays[f"{point}_H"][1:])),
                )
            for key in (
                "jitter_dfe",
                "jitter_ext_dfe",
                "jitter_spectrum_dfe",
                "jitter_ind_spectrum_dfe",
                "thresh_dfe",
            ):
                check(f"native GUI display {key}", arrays[f"display.{key}.y"], p.plotdata.get_data(key))
            check("native GUI PDF axis ps", arrays["display.jitter_dfe.x"], p.plotdata.get_data("jitter_bins"))
            check("native GUI spec axis MHz", arrays["display.thresh_dfe.x"], p.plotdata.get_data("f_MHz_dfe"))
            for point, key in (("rx_in", "eye_tx"), ("dfe", "eye_dfe")):
                check(f"native GUI {point} eye counts", arrays[f"eye.{point}.counts"], p.plotdata.get_data(key), 0, 0)
                ymax = 1.1 * np.max(
                    abs(arrays["rx_in" if point == "rx_in" else "dfe_out"][manifest["window"]["ignore_samps"] :])
                )
                scale = 1000 // (2 * ymax)
                check(f"{point} pixel to voltage mapping", arrays[f"eye.{point}.y"], (np.arange(1000) - 500) / scale)
                check(f"{point} native GUI eye x ps", arrays[f"eye.{point}.x"], p.plotdata.get_data("eye_index"))
            for point in ("chnl", "tx", "ctle", "dfe"):
                for key in ("bin_centers", "spectrum_freqs", "t_jitter"):
                    check(
                        f"{point} own {key}",
                        arrays[f"context.{point}.{key}"],
                        original[f"context.{point}.{key}"],
                        0,
                        0,
                    )
            for point in ("chnl", "tx_out", "ctle_out", "ffe_out", "dfe_out"):
                check(f"{point} cumulative native ns axis", arrays[f"display.{point}_h.x"], arrays["t_ns_chnl"], 0, 0)
            for point in ("tx", "ctle", "ffe", "dfe"):
                check(
                    f"{point} single native ns axis",
                    arrays[f"display.{point}_h.x"],
                    arrays["t"][: len(arrays[f"{point}_h"])] * 1e9,
                    0,
                    0,
                )
            ix = arrays["waveform_indices"]
            for field in ("ideal_signal", "chnl_out", "rx_in", "ctle_out", "ffe_out", "dfe_out"):
                check(f"{field} projection x ns", arrays[f"display.wave.{field}.x"], arrays["t"][ix] * 1e9, 0, 0)
                check(f"{field} projection values", arrays[f"display.wave.{field}.y"], arrays[field][ix], 0, 0)
            if "cdr_indices" in arrays:
                check(
                    "CDR recorded time projection",
                    arrays["display.cdr.x"],
                    arrays["t"][arrays["cdr_indices"]] * 1e9,
                    0,
                    0,
                )
                check(
                    "CDR estimates projection", arrays["display.cdr.y"], arrays["ui_ests"][arrays["cdr_indices"]], 0, 0
                )
                checks.append(
                    {
                        "check": "context voltage units",
                        "passed": all(
                            manifest["datasets"][f"context.source.{k}"]["unit"] == "V"
                            for k in ("x", "ideal_signal", "decision_scaler")
                        ),
                    }
                )
        for key in ("n_errs_dfe", "chnl_dly_s", "rel_power", "initial_level_v", "final_level_v"):
            check(
                f"summary {key}",
                manifest["summary"][key],
                reference["summary"][key],
                0 if key == "n_errs_dfe" else 1e-10,
                0 if key == "n_errs_dfe" else 1e-18 if key == "chnl_dly_s" else 1e-12,
            )
        for key, value in manifest["summary"]["dfe_jitter_s"].items():
            check(f"summary jitter {key}", value, reference["summary"]["dfe_jitter_s"][key], 1e-10, 1e-18)
        checks.append(
            {
                "check": "Viterbi unavailable; not numeric zero",
                "passed": manifest["summary"]["n_errs_viterbi"] is None
                and manifest["summary"]["viterbi_availability"] == "not run",
            }
        )
        extension = json.loads((FIXTURES / f"{name}.extensions.json").read_text(encoding="utf-8"))
        entry = {
            "fixture": name,
            "legacy_frozen_input_hash": extension["input_hash"],
            "canonical_input_hash": input_hash(config),
            "yaml_sha256": hashlib.sha256((FIXTURES / f"{name}.yaml").read_bytes()).hexdigest(),
            "checks": checks,
            "passed": all(c["passed"] for c in checks),
        }
        report["fixtures"].append(entry)
    out = ROOT / f"docs/webui/issue2/evidence/independent-saved-data-{BASE.name}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print([(f["fixture"], f["passed"], len(f["checks"])) for f in report["fixtures"]])
    assert all(f["passed"] for f in report["fixtures"])


if __name__ == "__main__":
    main()
