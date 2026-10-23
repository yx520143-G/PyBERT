"""Read-only native port-boundary diagnostic; no time-domain/COM execution."""

import json
from pathlib import Path

import numpy as np
from skrf import Network

from pybert.utility.sparam import sdd_21, import_freq
from freeze_web_resource_execution import ROOT, FIX, OUT, sha


def main():
    path = OUT / "native-port-boundary-v2.json"
    if path.exists():
        raise FileExistsError(path)
    resources = json.loads((FIX / "resources.json").read_text(encoding="utf-8"))
    net = Network(resources["M"]["path"])
    rows = []
    for victim in (0, 1):
        aggressor = 1 - victim
        ports = [4*aggressor, 4*aggressor+2, 4*victim+1, 4*victim+3]
        actual = sdd_21(net.subnetwork(ports)).s[:,1,0]
        # Independently specified differential excitation: input (+A,-A), output (+B,-B).
        ap, an, vp, vn = ports
        expected_physical = .5 * (net.s[:,vp,ap] - net.s[:,vp,an] - net.s[:,vn,ap] + net.s[:,vn,an])
        disconnected = net.copy()
        disconnected.s[:,:4,4:] = 0
        disconnected.s[:,4:,:4] = 0
        native_disconnected = sdd_21(disconnected.subnetwork(ports)).s[:,1,0]
        lane_ports = [4*victim,4*victim+2,4*victim+1,4*victim+3]
        lane = import_freq(resources["M"]["path"], renumber=False, lane=victim)
        p, n, q, r = 4*victim,4*victim+2,4*victim+1,4*victim+3
        physical_thru = .5 * (net.s[:,q,p] - net.s[:,q,n] - net.s[:,r,p] + net.s[:,r,n])
        rows.append({"victim": victim, "aggressor": aggressor, "fext_subnetwork": ports,
            "native_sdd_input_pair_0based": [ports[0],ports[2]], "native_sdd_output_pair_0based": [ports[1],ports[3]],
            "physical_input_pair_0based": [ap,an], "physical_output_pair_0based": [vp,vn],
            "native_fext_max_abs": float(abs(actual).max()), "physical_differential_fext_max_abs": float(abs(expected_physical).max()),
            "native_fext_after_zeroing_all_crosslane_s_max_abs": float(abs(native_disconnected).max()),
            "nonzero_native_fext_without_crosslane_coupling": bool((abs(native_disconnected) > 1e-12).any()),
            "native_victim_subnetwork": lane_ports, "native_victim_max_abs_s21": float(abs(lane.s[:,1,0]).max()),
            "physical_victim_max_abs_sdd21": float(abs(physical_thru).max()),
            "precheck_v1_through_pair_label_correction": [[lane_ports[0],lane_ports[1]],[lane_ports[2],lane_ports[3]]]})
    result = {"parent_precheck_sha256": sha(OUT / "native-resource-precheck-v1.json"),
       "frozen_manifest_sha256": sha(FIX / "frozen-manifest.json"), "resource_sha256": resources["M"]["sha256"],
       "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / "src/pybert/utility/sparam.py")},
       "native_source_matches_semantic_baseline": (ROOT / "src/pybert/utility/sparam.py").read_text(encoding="utf-8").replace("\r\n","\n") == (OUT / "native-src_pybert_utility_sparam.py.txt").read_text(encoding="utf-8").replace("\r\n","\n"),
       "native_formula": "0.5*(sub_S21-sub_S23-sub_S41+sub_S43), input subports0&2, output subports1&3",
       "convention_source": "native import_freq/import_fext docs and frozen SignalIntegrity model: lane (+A,+B,-A,-B)",
       "diagnostic_only": True, "main_simulation_performed": False,
       "limitation": "multilane reorder passes grouped [input+,input-,output+,output-] into helper expecting interleaved [input+,output+,input-,output-]; FEXT renumber is intentionally omitted; real physical mapping is not qualified",
       "tests_boundary": "existing test_multilane_sparam deliberately puts -2*T in S[-B,+A] to fit this formula; it does not validate physical pair mapping",
       "status": "NATIVE_PORT_MAPPING_BLOCKER_PENDING_PM", "cases_unchanged": True, "rows": rows}
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(path), "sha256": sha(path), "rows": rows}))


if __name__ == "__main__":
    main()
