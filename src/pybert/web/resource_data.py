"""Source identity/windows for the raw interference collection and its display."""


def annotate_interference(arrays, manifest):
    datasets = manifest["datasets"]
    t, indices = arrays["t"], arrays["waveform_indices"]
    raw = {"noise": "noise", "context.source.x": "source", "context.source.noise_total": "noise"}
    raw.update({key: "noise" for key in arrays if key.startswith("context.source.fext_") and key.endswith("_voltage")})
    for field, point in raw.items():
        if field not in datasets:
            continue
        window = dict(scope="full_record", source_field=field, time_axis="t", start_index=0, stop_index=len(t),
                      sample_count=len(t), ignore_samps=0, ignore_until_s=float(t[0]), start_s=float(t[0]),
                      stop_s_exclusive=float(t[-1] + t[1] - t[0]))
        datasets[field].update(point=point, observation_id="source_reference" if point == "source" else "additive_noise",
                               source_fields=[field], axis="t", unit="V", window=window)
        name = "noise_base" if field == "noise" else field.rsplit(".",1)[-1]
        projected = dict(scope="display_projection", source_field=field, time_axis="t",
                         start_index=int(indices[0]), stop_index=int(indices[-1])+1, sample_count=len(indices),
                         projection_index_field="waveform_indices", start_s=float(t[indices[0]]),
                         stop_s_inclusive=float(t[indices[-1]]))
        for suffix, sources in (("x", ["t", "waveform_indices"]), ("y", [field, "waveform_indices"])):
            key = f"display.wave.{name}.{suffix}"
            if key in datasets:
                datasets[key].update(point=point, observation_id="source_reference" if point == "source" else "additive_noise",
                                     source_fields=sources, window=projected, producer="bounded integer-index waveform projection")
    if "context.source.fext_count" in datasets:
        datasets["context.source.fext_count"].update(unit="1", producer="my_run_simulation actual FEXT path count")
    for key, dataset in datasets.items():
        if key.startswith("context.source.fext_") and key.endswith("_h"):
            dataset["sample_origin"] = "native FEXT trim_impulse start_ix, captured at producer"
    manifest["interference"] = {"base": "noise", "total": "context.source.noise_total",
        "coherent_source": "context.source.x", "fext_count": int(arrays.get("context.source.fext_count", 0)),
        "availability": "active" if int(arrays.get("context.source.fext_count", 0)) else "disabled",
        "victim_policy": "native package when enabled, otherwise ordinary Rs/Cout/Rin/Cin",
        "aggressor_policy": "native separate Rs/Rin renormalized termination; no victim package propagation",
        "native_mapping_boundary": "see resource port_mapping and source applicability; native multi-lane pair-order defect requires separate resolution"}
