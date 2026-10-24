"""Source identity/windows for the raw interference collection and its display."""


def annotate_interference(arrays, manifest):
    datasets = manifest["datasets"]
    t, indices = arrays["t"], arrays["waveform_indices"]
    config = manifest.get("effective_input", {})
    channel = next(
        (row for row in manifest.get("resources", []) if row.get("field") == "ch_file"),
        {},
    )
    for index, aggressor in enumerate(
        channel.get("aggressors", [])[: int(arrays.get("context.source.fext_count", 0))]
    ):
        prefix = f"context.source.fext_{index}"
        path = dict(
            victim_lane=channel.get("victim_lane"),
            aggressor_lane=aggressor["lane"],
            port_mapping_0based=aggressor["port_mapping_0based"],
            renumber=config.get("renumber"),
            use_window=config.get("use_window"),
            coherent_source="context.source.x",
            termination="native independent Rs/Rin renormalization",
            rs_ohm=config.get("rs"),
            rin_ohm=config.get("rin"),
            victim_package_active=config.get("pkg_enable", False),
            package_propagated_to_aggressor=False,
        )
        for suffix in ("_h", "_H", "_start_ix", "_voltage"):
            if prefix + suffix in datasets:
                datasets[prefix + suffix]["fext_path"] = path
    raw = {
        "noise": "noise",
        "context.source.x": "source",
        "context.source.noise_total": "noise",
    }
    raw.update(
        {
            key: "noise"
            for key in arrays
            if key.startswith("context.source.fext_") and key.endswith("_voltage")
        }
    )
    for field, point in raw.items():
        if field not in datasets:
            continue
        window = dict(
            scope="full_record",
            source_field=field,
            time_axis="t",
            start_index=0,
            stop_index=len(t),
            sample_count=len(t),
            ignore_samps=0,
            ignore_until_s=float(t[0]),
            start_s=float(t[0]),
            stop_s_exclusive=float(t[-1] + t[1] - t[0]),
        )
        datasets[field].update(
            point=point,
            observation_id="source_drive" if point == "source" else "additive_noise",
            source_fields=[field],
            axis="t",
            unit="V",
            window=window,
            clock_basis="native uniform source sample grid",
        )
        name = "noise_base" if field == "noise" else field.rsplit(".", 1)[-1]
        projected = dict(
            scope="display_projection",
            source_field=field,
            time_axis="t",
            start_index=int(indices[0]),
            stop_index=int(indices[-1]) + 1,
            sample_count=len(indices),
            projection_index_field="waveform_indices",
            start_s=float(t[indices[0]]),
            stop_s_inclusive=float(t[indices[-1]]),
        )
        for suffix, sources in (
            ("x", ["t", "waveform_indices"]),
            ("y", [field, "waveform_indices"]),
        ):
            key = f"display.wave.{name}.{suffix}"
            if key in datasets:
                datasets[key].update(
                    point=point,
                    observation_id="source_drive"
                    if point == "source"
                    else "additive_noise",
                    source_fields=sources,
                    window=projected,
                    producer="bounded integer-index waveform projection",
                )
    if "context.source.fext_count" in datasets:
        datasets["context.source.fext_count"].update(
            unit="1",
            producer="my_run_simulation actual FEXT path count",
            window={"scope": "scalar", "source_field": "context.source.fext_count"},
        )
    for key, dataset in datasets.items():
        if key.startswith("context.source.fext_") and key.endswith("_h"):
            dataset["sample_origin"] = (
                "native FEXT trim_impulse start_ix, captured at producer"
            )
            prefix = key[:-2]
            start = int(arrays[prefix + "_start_ix"])
            dataset.update(
                window=dict(
                    scope="trimmed_response",
                    source_field=key,
                    axis=dataset["axis"],
                    start_index=start,
                    stop_index=start + len(arrays[key]),
                    sample_count=len(arrays[key]),
                    start_s=float(t[start]),
                    stop_s_exclusive=float(
                        t[start + len(arrays[key]) - 1] + t[1] - t[0]
                    ),
                )
            )
            datasets[dataset["axis"]].update(
                point="noise",
                observation_id="additive_noise",
                source_fields=["t", prefix + "_start_ix"],
                window=dict(dataset["window"], source_field=dataset["axis"]),
                producer="native FEXT trimmed response time axis",
            )
        if key.startswith("context.source.fext_") and key.endswith("_H"):
            dataset.update(
                window=dict(
                    scope="frequency_grid",
                    source_field=key,
                    axis="f",
                    start_index=0,
                    stop_index=len(arrays["f"]),
                    frequency_start_hz=float(arrays["f"][0]),
                    frequency_stop_hz=float(arrays["f"][-1]),
                )
            )
        if key.startswith("context.source.fext_") and key.endswith("_start_ix"):
            dataset.update(window={"scope": "scalar", "source_field": key})
    manifest["interference"] = {
        "base": "noise",
        "total": "context.source.noise_total",
        "coherent_source": "context.source.x",
        "fext_count": int(arrays.get("context.source.fext_count", 0)),
        "availability": "active"
        if int(arrays.get("context.source.fext_count", 0))
        else "disabled",
        "victim_policy": "native package when enabled, otherwise ordinary Rs/Cout/Rin/Cin",
        "aggressor_policy": "native separate Rs/Rin renormalized termination; no victim package propagation",
        "convolution_policy": "native trimmed h convolved with the same x from discrete index zero, cropped to record length; no adapter delay compensation",
        "native_mapping_boundary": "corrected #13 interleaved 8/12-port caller; source-lane through detection only, no cross-path heuristic",
    }
