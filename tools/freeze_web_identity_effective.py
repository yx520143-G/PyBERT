"""Record native loader's dimension-dependent tuner enable state before the control run."""

import json

from freeze_web_analysis import DEST, digest
from pybert.web.config import input_hash, normalize


def main():
    parent = DEST / "frozen-manifest.json"
    requested = json.loads(parent.read_text(encoding="utf-8"))["inputs"]["F-NRZ-IDENTITY"]["config"]
    effective = normalize(dict(mode="load", config=requested))["config"]
    changes = {k: dict(requested=requested[k], effective=effective[k]) for k in requested if requested[k] != effective[k]}
    assert set(changes) == {"ffe_tap_tuners"}
    for i, (a, b) in enumerate(zip(requested["ffe_tap_tuners"], effective["ffe_tap_tuners"])):
        assert a[1:] == b[1:] and b[0] == (i == 0)
    assert input_hash(normalize(dict(mode="load",config=effective))["config"]) == input_hash(effective)
    result = dict(schema=3, parent_sha256=digest(parent), window_correction_sha256=digest(DEST / "window-correction-v2.json"),
                  frozen_before_control_simulation=True, config=effective, input_hash=input_hash(effective), changes=changes,
                  reason="Native PyBertCfg.load_from_file always enables ffe_tap_tuners by rx_n_taps. Original requested snapshot retained; only dimension-derived optimizer enabled flags change. No numerical simulation has run.")
    path = DEST / "identity-effective-v3.json"
    with path.open("x",encoding="utf-8") as stream:
        json.dump(result,stream,indent=2)
    print(digest(path))


if __name__ == "__main__":
    main()
