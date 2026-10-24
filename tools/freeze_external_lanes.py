"""Materialize #16 input/provenance/budget before any acceptance computation."""

import json
from datetime import datetime, timezone
from pathlib import Path

from external_lane_reference import ISSUE, ROOT, REFS, read_touchstone, sha, write_reordered
from verify_external_lanes import write

SI_COMMIT = "1922a1591100700aa8bd635964cd688012b8668d"
SI_PATH = "Test/TestSignalIntegrity/TestWElement/TestWElementTest_testWElement3Pairs.s12p"


def main():
    target = ISSUE / "freeze-v1.json"
    assert not target.exists(), "Never overwrite an existing freeze"
    resource_root = ISSUE / "local/resources"
    definitions = [
        {"id": "LL8", "original": resource_root / "LinkLab/backplane_25g_xtalk.s8p",
         "author": "Rune Bæverrud / SI-Forum (site author; model header credits SI-forum make_samples.mjs)",
         "url": "https://www.si-forum.no/siforum-static/eye/samples/backplane_25g_xtalk.s8p?v=1791651621",
         "version": "LinkLab manual v0.17.0; download query v=1791651621, acquired bytes fixed by SHA256",
         "permission": "Public author-provided sample for local importing/evaluation (manual 11.6); no explicit redistribution license found. Original and derived files local only; no relicensing claimed.",
         "port_evidence": "Original header lines 1-5 explicitly name victim TX+/TX-/RX+/RX- = 1/2/5/6, aggressor 3/4 -> 7/8; analysis lane1 + at3/7, - at4/8 follows same neighbouring-pair notation.",
         "lanes": [{"tx": [0, 1], "rx": [4, 5]}, {"tx": [2, 3], "rx": [6, 7]}]},
        {"id": "SI12", "original": resource_root / "SignalIntegrity" / SI_PATH,
         "author": "SignalIntegrity / Teledyne LeCroy / Nubis Communications; repository maintainer Pete Pupalaikis",
         "url": f"https://github.com/Nubis-Communications/SignalIntegrity/blob/{SI_COMMIT}/{SI_PATH}",
         "version": SI_COMMIT + "; file header SignalIntegrity v1.1.13",
         "permission": "GPL-3.0-or-later, repository LICENSE.txt and file/source copyright headers. Original bytes and source evidence retained locally; no external files added to PyBERT licensing scope.",
         "port_evidence": "WElement.py circuit declares wire j: port j -> j+6 (1based). WireBond3Pairs.net couples (1,2)/(7,8), (3,4)/(9,10), (5,6)/(11,12) to MixedModeConverter ports1=+,2=-. Tx=left/Rx=right are declared analysis-direction labels, not measurement labels.",
         "lanes": [{"tx": [0, 1], "rx": [6, 7]}, {"tx": [2, 3], "rx": [8, 9]}, {"tx": [4, 5], "rx": [10, 11]}]},
    ]
    resources, importer_cases = [], []
    derived = resource_root / "derived"
    derived.mkdir(exist_ok=True)
    for definition in definitions:
        f, s, z0, metadata = read_touchstone(definition["original"])
        original = definition["original"]
        row = {k: v for k, v in definition.items() if k != "original"}
        row.update(original=str(original.relative_to(ROOT)), original_name=original.name,
                   sha256=sha(original), bytes=original.stat().st_size, format=metadata,
                   frequency_hz={"first": float(f[0]), "last": float(f[-1]), "count": len(f)},
                   z0_single_ended_ohm=z0, classification="external simulation/model, not measured hardware",
                   retrieved_utc=datetime.now(timezone.utc).isoformat(), original_plain_lane_input="UNSUPPORTED_PORT_LAYOUT; requires documented permutation")
        variants = []
        for numbering in ("interleaved", "grouped"):
            mapping = []
            for lane in definition["lanes"]:
                tx, rx = lane["tx"], lane["rx"]
                mapping.extend([tx[0], rx[0], tx[1], rx[1]] if numbering == "interleaved" else tx + rx)
            path = derived / (definition["id"] + "-" + numbering + original.suffix)
            write_reordered(original, path, mapping)
            variants.append({"numbering": numbering, "path": str(path.relative_to(ROOT)),
                             "new_to_original_0based": mapping,
                             "original_to_new_0based": [mapping.index(i) for i in range(len(mapping))],
                             "sha256": sha(path), "bytes": path.stat().st_size,
                             "operation": "Snew[f,a,b]=Soriginal[f,new_to_original[a],new_to_original[b]]; all ports retained; DB/MA to complex RI 17 digits; frequency and real 50-ohm Z0 retained"})
            for renumber in ((False, True) if numbering == "interleaved" else (True,)):
                for victim in range(len(definition["lanes"])):
                    importer_cases.append({"id": f"{definition['id']}-{numbering}-r{int(renumber)}-v{victim}",
                        "original": row["original"], "input": str(path.relative_to(ROOT)), "numbering": numbering,
                        "renumber": renumber, "victim": victim,
                        "aggressors": [j for j in range(len(definition["lanes"])) if j != victim],
                        "physical_lanes": definition["lanes"], "frequency_grid": "all original frequencies, no subsampling",
                        "s_unit": "dimensionless complex power-wave Sdd", "z0_diff_ohm": 2 * z0})
        row["variants"] = variants
        resources.append(row)
    write(ISSUE / "resources.json", resources)
    downstream = []
    for identifier, fixture, resource, victim in (
        ("D-LL8-NRZ", "F4-L0-ON", resources[0], 0),
        ("D-SI12-PAM4", "F4-SINGLE-PAM4", resources[1], 1),
    ):
        config = json.loads((ROOT / f"docs/webui/issue4/fixtures/{fixture}.json").read_text(encoding="utf-8"))
        config.update(ch_file=str(ROOT / resource["variants"][0]["path"]), ch_files=[], inter_sel="single",
                      renumber=False, lane_sel=victim, include_fext=True, enable_com=False, pkg_enable=False,
                      use_window=False)
        path = ISSUE / "fixtures" / (identifier + ".json")
        write(path, config)
        downstream.append({"id": identifier, "config": str(path.relative_to(ROOT)), "parent_fixture": fixture,
                           "fext_count": len(resource["lanes"]) - 1, "resource": resource["id"], "victim": victim,
                           "versions_direct": ["pre", "post", "final"], "versions_worker": ["final"],
                           "native_grid": "f=arange(0,f_max*1e9+f_step*1e6/2,f_step*1e6), from actual trait",
                           "package": "disabled; native Rs/RL=100 ohm, Cout/Cin=0.5 pF; no IBIS/AMI",
                           "window": "inherit exact #2/#3/#4 full input and eye_uis/ignore convention; no extra ignore clipping"})
    inherited = [ROOT / "docs/webui/issue2/fixtures/tolerances.json", ROOT / "docs/webui/issue3/fixtures/frozen-manifest.json"]
    files = [ROOT / "tools/external_lane_reference.py", ROOT / "tools/verify_external_lanes.py", Path(__file__),
             *ISSUE.glob("environment-*.json"), ISSUE / "resources.json", ISSUE / "live-contract.json",
             ISSUE / "source-research.md", ISSUE / "preparation-attempt-1.json",
             *[ROOT / c["config"] for c in downstream], *inherited,
             *[p for p in resource_root.rglob("*") if p.is_file()]]
    local_sources = {str(p.relative_to(ISSUE)): sha(p) for p in (ISSUE / "local/sources").rglob("*") if p.is_file()}
    freeze = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "status": "FROZEN / NOT_EXECUTED",
        "versions": REFS, "source_export": "git archive src/pyproject.toml/.gitmodules at each fixed commit; separate source export of both pinned gitlinks; all imports assert selected snapshot paths",
        "versions_importer": ["pre", "post", "final"], "importer_cases": importer_cases, "downstream_cases": downstream,
        "reference": "external_lane_reference.py reads full original single-ended matrix independently; B rows (+1,-1)/sqrt(2), Sdd=B*S*B.T, equal real Zse=50 -> Zdiff=100 ohm. Unselected SE incident waves zero (matched); no unequal/complex-Z0 generalization. FEXT two-port includes aggressor-input/victim-output reflections and both transfer directions.",
        "reference_interpolation": "independent scipy magnitude/unwrap-phase linear interpolation; outside original band transfer=0, reflections extrapolated/capped at1 per native convention. Original-grid importer avoids extrapolation. LL8 has no DC: downstream native transfer at0=0, explicitly not measured or supplied DC.",
        "phase_magnitude_floor": 1e-8, "phase_atol_rad": 1e-8,
        "tolerances": {"complex_real_and_imag_separately": {"rtol": 1e-10, "atol": 1e-12},
                       "z0_ohm": {"rtol": 1e-10, "atol": 1e-12}, "frequency_hz": {"rtol": 1e-12, "atol": 1e-6},
                       "native_direct_worker": "inherit docs/webui/issue2/fixtures/tolerances.json exactly; no requirement that pre equals physical expected"},
        "budget": {"importer": {"top_import_freq_calls": 45, "top_import_fext_calls": 45,
                                "independent_skrf_reader_checks": 45, "wall_timeout_per_version_s": 180},
                   "Main_direct": {"calls": 6, "max_per_case_s": 120, "constructors": 6},
                   "Main_final_worker": {"calls": 2, "max_per_case_s": 180, "single_active_worker": True},
                   "worker_timeout_s": 180, "total_Main_cap": 8, "COM": 0, "coopt": 0,
                   "AMI_Init": 0, "AMI_GetWave": 0, "binary_loads": 0, "raw_disk_cap_bytes": 2 * 1024**3,
                   "peak_policy": "UNKNOWN unless actually measured; no invented peak; observe elapsed and preserve failures",
                   "overrun": "stop new calls, retain original outputs/costs and report minimum scope to PM before extending"},
        "preexisting_saved_evidence": "#13/native13 only old TwoLaneModel/constructed networks; #4 saved downstream only its original resources. Source hashes show corrected importer same as final, but none answers these new resources; do not relabel/recompute them.",
        "remaining_gaps": {"measured_S8P": "SOURCE_BLOCKED / NOT_EXECUTED", "measured_S12P": "SOURCE_BLOCKED / NOT_EXECUTED",
                           "original_arbitrary_port_layout_direct_support": "OUTSIDE_PLAIN_SUPPORT; frozen documented permutation used, no product fix",
                           "IEEE_COM_correlation": "NOT_IN_SCOPE", "default_COM": "BLOCKED_BUDGET / NOT_EXECUTED", "valid_AMI_clocks": "BLOCKED, separate #10"},
        "files": {str(p.relative_to(ROOT)): sha(p) for p in files}, "local_source_files": local_sources,
    }
    write(target, freeze)
    print(json.dumps({"freeze": str(target), "sha256": sha(target), "importer_cases_per_version": len(importer_cases),
                      "resources": [{k: r[k] for k in ("id", "sha256", "bytes", "frequency_hz")} for r in resources]}, indent=2))


if __name__ == "__main__":
    main()
