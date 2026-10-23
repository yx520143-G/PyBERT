"""Small saved-raw perturbations test availability and cancellation without another simulation."""

import hashlib
import json
from pathlib import Path

import numpy as np

from pybert.utility import calc_eye
from pybert.web.analysis import extend_analysis

ROOT = Path(__file__).resolve().parents[1]


def main():
    frozen = json.loads((ROOT / "docs/webui/issue3/fixtures/frozen-manifest.json").read_text(encoding="utf-8"))
    source = Path(frozen["inputs"]["F-NRZ-01"]["source"])
    original = dict(np.load(source / "arrays.npz",allow_pickle=False))
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    arrays = {k:v.copy() for k,v in original.items()}
    arrays["ffe_out"] = np.ones_like(arrays["ffe_out"])
    arrays["clock_times"] = np.asarray([])
    arrays["ui_ests"] = np.zeros_like(arrays["ui_ests"])
    extend_analysis(arrays,manifest)
    window = manifest["window"]
    ys = arrays["dfe_out"][window["ignore_samps"]:]
    expected = calc_eye(float(arrays["context.source.ui"]),int(arrays["context.source.nspui"]),1000,ys,1.1*max(abs(ys)))
    checks = dict(ffe_no_crossing=manifest["ffe_analysis"]["availability"] == "unavailable",
                  ffe_eye_no_crossing=manifest["plots"]["eye.ffe"]["availability"] == "unavailable",
                  ffe_bathtub_unavailable=manifest["plots"]["jitter.ffe.bathtub"]["availability"] == "unavailable",
                  cdr_zero_unavailable=manifest["plots"]["cdr.spectrum"]["availability"] == "unavailable",
                  dfe_fallback=manifest["datasets"]["eye.dfe.counts"]["clock_fallback"],
                  dfe_fallback_counts=bool(np.array_equal(expected,arrays["eye.dfe.counts"])),
                  four_native_jitters_unchanged=all(np.array_equal(original[k],arrays[k]) for k in original if k.startswith(("jitter_","jitter_ext_","context.chnl.","context.tx.","context.ctle.","context.dfe."))),
                  json_finite=bool(json.dumps(manifest,allow_nan=False)))
    cancelled_arrays = {k:v.copy() for k,v in original.items()}
    cancelled_manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    observed = 0

    def cancel():
        nonlocal observed
        observed += 1
        return observed == 2

    try:
        extend_analysis(cancelled_arrays,cancelled_manifest,cancel)
        checks["cancel_at_group_boundary"] = False
    except RuntimeError as err:
        checks["cancel_at_group_boundary"] = "Cancelled" in str(err)
    report = dict(checks=checks,passed=all(checks.values()),
                  source_sha256=hashlib.sha256((source / "arrays.npz").read_bytes()).hexdigest(),
                  injected_fields=["ffe_out: constant", "clock_times: empty", "ui_ests: zero"],
                  scope="Function-level copies only, no main simulation, no existing run changed",
                  optional_unavailable={k:v for k,v in manifest["plots"].items() if v.get("availability") == "unavailable"})
    path = ROOT / "docs/webui/issue3/evidence/function-boundaries.json"
    with path.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2)
    print(checks)
    assert report["passed"]


if __name__ == "__main__":
    main()
