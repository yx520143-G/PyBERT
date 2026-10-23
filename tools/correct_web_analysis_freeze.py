"""Append the pre-computation PAM4 window correction without altering the first freeze."""

import json

import numpy as np

from freeze_web_analysis import DEST, digest


def main():
    parent = DEST / "frozen-manifest.json"
    frozen = json.loads(parent.read_text(encoding="utf-8"))
    windows = {}
    for name in ("F-NRZ-01", "F-PAM4-01"):
        source = frozen["inputs"][name]["source"]
        from pathlib import Path

        path = Path(source)
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        with np.load(path / "arrays.npz", allow_pickle=False) as arrays:
            ui, nspui = float(arrays["context.source.ui"]), int(arrays["context.source.nspui"])
            window = manifest["window"]
            assert np.isclose(window["ignore_until_s"], (window["nui"] - window["eye_uis"]) * ui, rtol=0, atol=1e-20)
            assert window["ignore_samps"] == (window["nui"] - window["eye_uis"]) * nspui
            windows[name] = dict(**window, ui_s=ui, Ts_s=ui / nspui, source_manifest_sha256=digest(path / "manifest.json"))
    result = dict(schema=2, parent_sha256=digest(parent), corrected_before_analysis=True,
                  reason="PAM4 UI is 200ps at 10Gb/s; initial supplemental window contained a bit-rate transcription error. No helper or simulation had run.",
                  windows=windows, inherited_contract="All other inputs, tolerance, display-noise and bounded scope remain in parent.")
    dest = DEST / "window-correction-v2.json"
    with dest.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(digest(dest))


if __name__ == "__main__":
    main()
