"""D2 bounded software contracts, outside default pytest discovery."""

import unittest

from d2_under_test import modules, np


class MaskCases(unittest.TestCase):
    def test_dense_bytes_and_exact_known_compact(self):
        validate = getattr(modules["pybert.web.clocks"], "validate_period", None)
        self.assertTrue(callable(validate), "production masked-period validation is missing")
        grid = np.array([i * 0.25 for i in range(9)])
        # Distinct quiet-NaN payloads must survive; validation cannot normalize them.
        bits = np.array([0x7FF8000000000042, 0x7FF8000000000011, 0x7FF8000000000022,
                         0x3FF0000000000000, 0x4000000000000000, 0x7FF8000000000033,
                         0x4008000000000000, 0x4010000000000000, 0x7FF8000000000044], dtype=np.uint64)
        periods = bits.view(np.float64)
        known = np.array([False, False, False, True, True, False, True, True, False])
        raw = periods.tobytes()
        indices, times, values = validate(grid, periods, known)
        self.assertEqual(indices.tolist(), [3, 4, 6, 7])
        self.assertEqual(times.tolist(), [0.75, 1.0, 1.5, 1.75])
        self.assertEqual(values.tolist(), [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(periods.tobytes(), raw)
        for case in ("mask_type", "mask_shape", "period_type", "known_nan", "known_zero", "known_negative",
                     "unknown_finite", "unknown_inf", "grid_shape", "period_shape"):
            with self.subTest(case=case):
                current, mask, t = periods.copy(), known.copy(), grid
                if case == "mask_type":
                    mask = mask.astype(np.int8)
                elif case == "mask_shape":
                    mask = mask[:-1]
                elif case == "period_type":
                    current = np.array([1] * 9)
                elif case.startswith("known_"):
                    current[3] = {"known_nan": np.nan, "known_zero": 0, "known_negative": -1}[case]
                elif case.startswith("unknown_"):
                    current[0] = np.inf if case == "unknown_inf" else 1
                elif case == "grid_shape":
                    t = grid.reshape((3, 3))
                else:
                    current = current[:-1]
                with self.assertRaises(ValueError):
                    validate(t, current, mask)
        indices, times, values = validate(grid, np.array([np.nan] * 9), np.array([False] * 9))
        self.assertEqual((indices.tolist(), times.tolist(), values.tolist()), ([], [], []))


class ProducerCases(unittest.TestCase):
    def test_fresh_host_producer_and_each_actual_eye_crop(self):
        from types import SimpleNamespace
        clocks = modules["pybert.web.clocks"]
        self.assertTrue(callable(getattr(clocks, "snapshot_producer", None)), "host producer snapshot is missing")
        factory = modules["pybert.utility.ami_clock"].new_clock_info
        info = factory(True, "rx_getwave", "c1_fresh_main")
        next_info = factory(True, "rx_getwave", "c1_fresh_main")
        self.assertEqual(info["producer_contract_version"], 2)
        self.assertNotEqual(info["invocation_id"], next_info["invocation_id"])
        grid = np.array([i * 0.25 for i in range(16)])
        samples = np.array([2, 6, 10, 14])
        period = np.array([np.nan] * 2 + [1e12] * 12 + [np.nan] * 2)
        known = np.array([False] * 2 + [True] * 12 + [False] * 2)
        info.update(actual_branch="ami", consumption_status="completed", consumed_count=4, run_status="completed",
                    format_status="valid", eligible=True, full_analysis_eligible=True,
                    grid_s=grid, edges_s=np.array([0., 1., 2., 3.]), targets_s=np.array([0.5, 1.5, 2.5, 3.5]),
                    sample_indices=samples, consumed_tick_positions=np.array([0, 1, 2, 3]),
                    sample_targets_s=grid[samples], sample_grid_times_s=grid[samples],
                    sample_quantization_delay_s=np.array([0.] * 4), analysis_sample_indices=np.array([10, 14]),
                    period_s=period / 1e12, period_known=known, nspui=4, symbol_ui_s=1., ignore_ui=0.,
                    analysis={"start_s": 1., "stop_s": 3.75, "start_index": 4, "stop_index": 16,
                              "required_decisions": 2, "required_eye_traces": 1, "fft_slice": [6, 10]},
                    profile={"ignore_ui_units": "symbol_ui", "nominal_eye_offset_ui": 0, "mapping": "native_nrz"},
                    profile_source="nrz_ui_contract", model_qualification="UNKNOWN")
        engine = SimpleNamespace(ami_clock_info=info, t=grid, ui_ests=period, ami_period_known=known,
                                 clock_times=grid[samples], dfe_out=np.array([1.] * 16))
        snapshot = clocks.snapshot_producer(engine, previous_invocation="earlier-main", phase="post_main")
        self.assertTrue(snapshot["fresh"])
        self.assertEqual(snapshot["phase"], "post_main")
        self.assertIsNot(snapshot["info"]["sample_indices"], samples)
        context = clocks.clock_context(engine, snapshot)
        self.assertEqual(context["version"], 2)
        self.assertEqual(context["info"]["invocation_id"], info["invocation_id"])
        relative, meta = clocks.eye_selection(context, 4, 14)
        self.assertEqual(relative.tolist(), [2])
        self.assertEqual(meta["absolute_indices"], [6])
        self.assertEqual(meta["slice_start"], 4)
        self.assertEqual(meta["slice_stop"], 14)
        self.assertEqual(meta["width"], 8)
        self.assertEqual(meta["consumed_count"], 4)
        self.assertEqual(meta["window_sample_count"], 3)
        self.assertEqual(meta["eligible_trace_count"], 1)
        relative, meta = clocks.eye_selection(context, 7, 16)
        self.assertEqual(relative.tolist(), [])
        self.assertEqual(meta["reason"], "no_complete_timed_trace")
        self.assertEqual(meta["eligible_trace_count"], 0)
        engine.ui_ests[0] = 99.
        self.assertTrue(np.isnan(snapshot["raw"]["ui_ests"][0]))
        with self.assertRaises(ValueError):
            clocks.clock_context(engine, snapshot)
        engine.ui_ests[0] = np.nan
        for case in ("no_snapshot", "same_invocation", "other_invocation", "old_contract", "partial", "bad_indices"):
            with self.subTest(case=case):
                current = clocks.snapshot_producer(engine, phase="post_main")
                if case == "no_snapshot":
                    current = None
                elif case == "same_invocation":
                    current["fresh"] = False
                elif case == "other_invocation":
                    current["info"]["invocation_id"] = "not-this-main"
                elif case == "old_contract":
                    current["info"].pop("producer_contract_version")
                elif case == "partial":
                    current["info"]["run_status"] = "not_completed"
                else:
                    current["info"]["sample_indices"] = np.array([2, 6, 6, 14])
                with self.assertRaises(ValueError):
                    clocks.clock_context(engine, current)
        native = factory(True, "rx_getwave", "c1_fresh_main")
        native.update(actual_branch="native", native_returned=True, format_status="no_clocks", use_native=True,
                      edges_s=np.array([]), consumption_status="completed", run_status="completed")
        engine.ami_clock_info = native
        self.assertIsNone(clocks.clock_context(engine, clocks.snapshot_producer(engine)))
        native["native_returned"] = False
        with self.assertRaises(ValueError):
            clocks.clock_context(engine, clocks.snapshot_producer(engine))


class ProjectionCases(unittest.TestCase):
    def test_actual_eye_indices_masked_histogram_fft_and_segments(self):
        clocks = modules["pybert.web.clocks"]
        analysis = modules["pybert.web.analysis"]
        self.assertTrue(callable(getattr(clocks, "period_projection", None)), "masked period projection is missing")
        grid = np.array([10, 10.25, 10.5, 10.75, 11, 11.25])
        periods = np.array([np.nan, 1., 2., 3., 4., np.nan])
        known = np.array([False, True, True, True, True, False])

        def context():
            return {"version": 2, "info": {"period_known": known.copy(),
                    "analysis": {"start_index": 0, "stop_index": 6, "start_s": 10., "stop_s": 11.25,
                                 "fft_slice": [1, 5]}}, "raw": {"t": grid, "ui_ests": periods}}

        projected = analysis.clock_data(grid, periods, 0.5, clock_contract=context())
        hist, spectrum = projected["histogram"], projected["spectrum"]
        self.assertEqual(hist["indices"].tolist(), [1, 2, 3, 4])
        self.assertEqual(hist["values_ps"].tolist(), [1, 2, 3, 4])
        self.assertEqual(hist["counts"].tolist(), [1 if i in (0, 33, 66, 99) else 0 for i in range(100)])
        self.assertEqual(spectrum["raw"].tolist(), [10 + 0j, -2 + 2j, -2 + 0j])
        self.assertEqual(spectrum["frequency_hz"].tolist(), [0, 1, 2])
        self.assertEqual(spectrum["relative_frequency"].tolist(), [0.5, 1.0])
        self.assertEqual(spectrum["sample_interval_s"], 0.25)
        self.assertEqual(spectrum["origin_s"], 10.25)
        display = analysis.clock_display(spectrum["raw"])
        self.assertEqual(len(display), 2)
        for case, reason in (("gap", "unknown_period"), ("short", "insufficient_fft_window"),
                             ("bounds", "invalid_fft_bounds"), ("outside", "outside_analysis_window"),
                             ("nonuniform", "nonuniform_grid"), ("unknown", "unknown_period"),
                             ("zero_ts", "unknown_or_nonpositive_sample_interval")):
            with self.subTest(fft=case):
                current, values, times = context(), periods.copy(), grid.copy()
                if case == "gap":
                    current["info"]["period_known"][2] = False
                    values[2] = np.nan
                elif case == "short":
                    current["info"]["analysis"]["fft_slice"] = [1, 2]
                elif case == "bounds":
                    current["info"]["analysis"]["fft_slice"] = [-1, 4]
                elif case == "outside":
                    current["info"]["analysis"]["start_s"] = 10.4
                elif case == "nonuniform":
                    times[3] = 10.8
                elif case == "unknown":
                    current["info"]["period_known"][:] = False
                    values[:] = np.nan
                else:
                    times[1] = times[0]
                actual = analysis.clock_data(times, values, 0.5, clock_contract=current)
                self.assertEqual(actual["spectrum"]["availability"], "unavailable")
                self.assertEqual(actual["spectrum"]["reason"], reason)
                self.assertEqual(actual["spectrum"]["raw"].tolist(), [])
                if case == "unknown":
                    self.assertEqual(actual["histogram"]["availability"], "unavailable")
        constant = analysis.clock_data(grid, np.array([np.nan, 1., 1., 1., 1., np.nan]), 0.5,
                                      clock_contract=context())
        self.assertEqual(constant["spectrum"]["raw"].tolist(), [4 + 0j, 0j, 0j])
        self.assertEqual(constant["histogram"]["availability"], "available")
        with self.assertRaisesRegex(ValueError, "fundamental"):
            analysis.clock_display(constant["spectrum"]["raw"])
        # Legacy defaults remain actual, on the same nonzero-origin input: old t[1] convention retained.
        legacy = analysis.clock_data(grid, np.array([1.] * 6), 0.5)
        self.assertEqual(legacy[3].tolist(), [0., 1 / 61.5, 2 / 61.5, 3 / 61.5])

        t = np.array([i * 0.25 for i in range(9)])
        mask = np.array([False, False, False, True, True, False, True, True, False])
        ps = np.array([np.nan, np.nan, np.nan, 1., 2., np.nan, 3., 4., np.nan])
        segments, meta = clocks.period_segments(t, ps, mask)
        self.assertEqual([part.tolist() for part in segments], [[3, 4], [6, 7]])
        segments, meta = clocks.period_segments(t, ps, mask, limit=3)
        self.assertEqual([part.tolist() for part in segments], [[3, 4], [7]])
        self.assertEqual(meta["selected_points"], 3)
        segments, meta = clocks.period_segments(t, np.array([np.nan] * 9), np.array([False] * 9))
        self.assertEqual(segments, [])
        self.assertEqual(meta["availability"], "unavailable")

        native = np.array([1., -1.] * 8)
        before, old_mapping = modules["baseline.analysis"].eye_data(1., 2, native)
        after, mapping = analysis.eye_data(1., 2, native)
        self.assertTrue(np.array_equal(before, after))
        self.assertEqual(mapping, old_mapping)
        native_clocks = np.array([0.5, 1.5, 2.5])
        before, old_mapping = modules["baseline.analysis"].eye_data(1., 2, native, native_clocks)
        after, mapping = analysis.eye_data(1., 2, native, native_clocks)
        self.assertTrue(np.array_equal(before, after))
        self.assertEqual(mapping, old_mapping)
        # Timed indices bypass nominal crossing preflight, even on a constant waveform.
        counts, mapping = analysis.eye_data(1., 2, np.array([1.] * 12), clock_indices=np.array([0, 8]))
        self.assertEqual(float(counts.sum()), 8.)
        self.assertEqual(counts[954].tolist(), [2., 2., 2., 2.])
        with self.assertRaisesRegex(ValueError, "no_complete_timed_trace"):
            analysis.eye_data(1., 2, np.array([1.] * 12), clock_indices=np.array([], dtype=int))
        with self.assertRaises(ValueError):
            analysis.eye_data(1., 2, native, clocks=np.array([0.]), clock_indices=np.array([0]))
        with self.assertRaisesRegex(ValueError, "crossing"):
            analysis.eye_data(1., 2, np.array([1.] * 12))


class ArchiveCases(unittest.TestCase):
    def test_masked_archive_features_and_lossless_original_files(self):
        import io
        import zipfile
        from types import SimpleNamespace
        from d2_under_test import destination
        clocks = modules["pybert.web.clocks"]
        self.assertTrue(callable(getattr(clocks, "store_clock_context", None)), "stored clock contract is missing")
        archive, viterbi = modules["pybert.web.archive"], modules["pybert.web.viterbi"]
        factory = modules["pybert.utility.ami_clock"].new_clock_info
        t = np.array([i * 0.25 for i in range(16)])
        indices = np.array([2, 6, 10, 14])
        ps = np.array([np.nan] * 2 + [1e12] * 12 + [np.nan] * 2)
        ps.view(np.uint64)[0] = 0x7FF8000000000042
        ps.view(np.uint64)[15] = 0x7FF8000000000021
        mask = np.array([False] * 2 + [True] * 12 + [False] * 2)
        info = factory(True, "rx_getwave", "c1_fresh_main")
        info.update(actual_branch="ami", format_status="valid", eligible=True, full_analysis_eligible=True,
                    run_status="completed", consumption_status="completed", consumed_count=4,
                    grid_s=t, edges_s=np.array([0., 1., 2., 3.]), targets_s=t[indices],
                    sample_indices=indices, sample_targets_s=t[indices], sample_grid_times_s=t[indices],
                    consumed_tick_positions=np.array([0, 1, 2, 3]), sample_quantization_delay_s=np.array([0.] * 4),
                    analysis_sample_indices=np.array([10, 14]), period_s=ps / 1e12, period_known=mask,
                    nspui=4, symbol_ui_s=1., ignore_ui=0.,
                    analysis={"start_index": 4, "stop_index": 16, "start_s": 1., "stop_s": 3.75,
                              "fft_slice": [6, 10], "required_decisions": 2, "required_eye_traces": 1},
                    profile={"ignore_ui_units": "symbol_ui", "nominal_eye_offset_ui": 0, "mapping": "native_nrz"},
                    profile_source="nrz_ui_contract", model_qualification="UNKNOWN")
        engine = SimpleNamespace(ami_clock_info=info, t=t, ui_ests=ps, ami_period_known=mask,
                                 clock_times=t[indices], dfe_out=np.array([1.] * 16), n_errs_viterbi=-1)
        context = clocks.clock_context(engine, clocks.snapshot_producer(engine))
        arrays, datasets = {}, {}
        contract = clocks.store_clock_context(context, arrays, datasets)
        config = dict(nbits=4, eye_bits=2, nspui=4, rx_use_viterbi=False, rx_viterbi_fec=False,
                      rx_viterbi_symbols=2, mod_type="NRZ")
        run = dict(run_id="manual-masked-record", schema_version=1, raw_schema_version=6, draft_revision=0,
                   status="succeeded", input_hash="1" * 64, native_sha="2" * 40, prototype_sha="3" * 40,
                   adapter_sha="4" * 40, requested_input=config, effective_input=config, datasets=datasets, plots={},
                   summary={"n_errs_dfe": 0, "n_errs_viterbi": -1}, window={}, packages={}, resources=[], warnings=[],
                   input_identity_hash="5" * 64, resource_hash="6" * 64, resource_bindings={}, runtime_extensions={},
                   execution_strategy={}, ami={"schema_version": 1, "clock_contract": contract},
                   required_features=["ami-clock-grid-v2"], actual_source_sha256={
                       "models/bert.py": "a" * 64, "models/viterbi.py": "b" * 64, "web/viterbi.py": "c" * 64})
        def add(key, value):
            arrays[key] = value
            datasets[key] = dict(dtype=str(value.dtype), shape=list(value.shape), producer="manual frozen input",
                                 unit="1", window={}, clock_basis="manual", availability="available")
        add("t", t)
        add("clock_times", t[indices])
        add("bits", np.array([0, 1, 0, 1]))
        add("bit_errs_dfe", np.array([], dtype=int))
        captured = {"dfe": dict(bits_out=np.array([0, 1, 0, 1]), bits_test=np.array([0, 1]),
                               bits_reference=np.array([0, 1]), auto_corr=np.array([1.]),
                               errors=np.array([], dtype=int),
                               count=0, bit_delay=0, test_start_bit=2, test_stop_bit=4,
                               reference_start_bit=2, reference_stop_bit=4)}
        viterbi.extend(engine, captured, arrays, run)
        directory = destination / "manual-run"
        directory.mkdir()
        np.savez_compressed(directory / "arrays.npz", **arrays)
        original_manifest = archive.json_bytes(run)
        (directory / "manifest.json").write_bytes(original_manifest)
        original_npz = (directory / "arrays.npz").read_bytes()
        saved = archive.save_archive(directory, directory / "record.pybert_run")
        self.assertEqual(saved["required_features"], ["ami-clock-grid-v2"])
        opened = destination / "opened"
        opened.mkdir()
        result, size = archive.load_archive((directory / "record.pybert_run").read_bytes(), opened)
        self.assertEqual((opened / "manifest.json").read_bytes(), original_manifest)
        self.assertEqual((opened / "arrays.npz").read_bytes(), original_npz)
        self.assertEqual(result, run)
        read = archive.read_arrays(original_npz, run=run)
        self.assertEqual(read["ui_ests"].tobytes(), ps.tobytes())
        self.assertEqual(size, sum(value.nbytes for value in arrays.values()))
        with self.assertRaises(ValueError):
            archive.read_arrays(original_npz)  # ordinary finite gate is still closed
        for feature in ([], ["unsupported-feature"]):
            with self.subTest(archive_features=feature):
                with zipfile.ZipFile(io.BytesIO((directory / "record.pybert_run").read_bytes())) as source:
                    envelope = archive.read_json(source.read("manifest.json"))
                envelope["required_features"] = feature
                broken = io.BytesIO()
                with zipfile.ZipFile(broken, "w", compression=zipfile.ZIP_STORED) as output:
                    output.writestr("manifest.json", archive.json_bytes(envelope))
                    output.writestr("arrays.npz", original_npz)
                with self.assertRaises(ValueError):
                    archive.load_archive(broken.getvalue(), opened)
                self.assertEqual((opened / "arrays.npz").read_bytes(), original_npz)
        for case in ("missing_feature", "unknown_feature", "downgrade", "missing_contract", "native_label"):
            with self.subTest(version=case):
                current = archive.read_json(original_manifest)
                if case == "missing_feature":
                    current.pop("required_features")
                elif case == "unknown_feature":
                    current["required_features"].append("unsupported-feature")
                elif case == "downgrade":
                    current["raw_schema_version"] = 5
                elif case == "missing_contract":
                    current["ami"].pop("clock_contract")
                else:
                    current["ami"]["clock_contract"]["actual_branch"] = "native"
                with self.assertRaises(ValueError):
                    archive.read_arrays(original_npz, run=current)
        tampered = {key: value.copy() for key, value in arrays.items()}
        tampered["ami.cdr.known_period_ps"][0] = 99.
        with self.assertRaises(ValueError):
            archive.validate_run(run, tampered)
        for key, value in (("other", np.array([np.nan])), ("ui_ests", np.array(["blocked"], dtype=object))):
            with self.subTest(npy_gate=key):
                buffer = io.BytesIO()
                np.savez_compressed(buffer, **{key: value})
                with self.assertRaises(ValueError):
                    archive.read_arrays(buffer.getvalue(), run=run)
        # Native and historical records keep their own finite/raw2-5 rules and original bytes.
        for raw_version in (2, 3, 4, 5):
            current = archive.read_json(original_manifest)
            current.pop("ami")
            current.pop("required_features")
            current["raw_schema_version"] = raw_version
            values = {key: value for key, value in arrays.items() if not key.startswith("ami.")}
            values["ui_ests"] = np.array([1e12] * 16)
            if raw_version < 5:
                current.pop("decoding")
                values = {key: value for key, value in values.items() if not key.startswith("ber.")}
            current["datasets"] = {key: dict(datasets[key], dtype=str(value.dtype), shape=list(value.shape))
                                   for key, value in values.items()}
            for dataset in current["datasets"].values():
                dataset.update(axis=None, clock_basis="native", availability="available")
            buffer = io.BytesIO()
            np.savez_compressed(buffer, **values)
            original = buffer.getvalue()
            reread = archive.read_arrays(original, run=current)
            archive.validate_run(current, reread)
            self.assertEqual(reread["ui_ests"].tobytes(), values["ui_ests"].tobytes())


class LifecycleCases(unittest.TestCase):
    def test_partial_raw_phase_errors_cancellation_and_actual_annotation(self):
        from types import SimpleNamespace
        from d2_under_test import destination
        clocks, ami, archive = (modules[name] for name in
                               ("pybert.web.clocks", "pybert.web.ami", "pybert.web.archive"))
        self.assertTrue(callable(getattr(clocks, "write_partial", None)), "partial diagnostic output is missing")
        execution = ami.Execution()
        with execution.phase("prepare"):
            pass  # An ordinary software caller; no engine construction or Main is executed.
        failure = ami.AMICancelled("software post-Main checkpoint cancellation")
        with self.assertRaises(ami.AMICancelled):
            with execution.phase("collect"):
                raise failure
        self.assertEqual([row["status"] for row in execution.phases], ["completed", "failed"])
        self.assertEqual(execution.phases[-1]["error_type"], "AMICancelled")
        raw = np.array([np.nan, 0.5, np.nan])
        raw.view(np.uint64)[0] = 0x7FF8000000000042
        info = dict(producer_contract_version=2, invocation_id="software-partial-main", actual_branch="ami",
                    consumption_status="partial", run_status="not_completed", consumed_count=1,
                    sample_indices=np.array([1]), period_known=np.array([False, True, False]),
                    reason="consumption_failed")
        engine = SimpleNamespace(ami_clock_info=info, t=np.array([0., 0.25, 0.5]), ui_ests=raw)
        snapshot = clocks.snapshot_producer(engine, phase="Main_exception")
        folder = destination / "cancelled-diagnostic"
        folder.mkdir()
        (folder / "arrays.npz").write_bytes(b"prior-success-bytes")
        (folder / "manifest.json").write_bytes(b"prior-success-manifest")
        record = clocks.write_partial(folder, snapshot, execution.phases,
                                      {"status": "cancelled", "error": str(failure), "error_type": "AMICancelled"})
        self.assertEqual(record["status"], "cancelled")
        self.assertEqual(record["evidence_type"], "diagnostic_partial_only")
        self.assertEqual(record["producer"]["consumed_count"], 1)
        self.assertEqual((folder / "arrays.npz").read_bytes(), b"prior-success-bytes")
        self.assertEqual((folder / "manifest.json").read_bytes(), b"prior-success-manifest")
        with np.load(folder / "partial-arrays.npz", allow_pickle=False) as values:
            self.assertEqual(values["raw.ui_ests"].tobytes(), raw.tobytes())
            self.assertEqual(values["producer.sample_indices"].tolist(), [1])
        with self.assertRaises(FileExistsError):
            clocks.write_partial(folder, snapshot, execution.phases, {"status": "failed", "error": "new"})

        class Unstarted:
            @property
            def t(self):
                raise AssertionError("snapshot must not evaluate a missing engine property")

        absent = clocks.snapshot_producer(Unstarted(), phase="prepare_failed")
        empty = destination / "pre-main-diagnostic"
        empty.mkdir()
        record = clocks.write_partial(empty, absent, [], {"status": "failed", "error": "prepare failed"})
        self.assertIsNone(record["producer"])
        self.assertEqual(record["raw"], {})
        self.assertEqual(record["run_qualification"], "not evaluated")
        # A metadata write failure keeps the already written diagnostic NPZ and the original exception.
        save_error = OSError("software metadata write failure")
        original_write = archive.atomic_write
        def stub_fail_write(path, content):
            if str(path).endswith(".json"):
                raise save_error
            return original_write(path, content)
        failed = destination / "save-failed-diagnostic"
        failed.mkdir()
        archive.atomic_write = stub_fail_write
        try:
            with self.assertRaises(OSError) as caught:
                clocks.write_partial(failed, snapshot, [], {"status": "failed", "error": "original Main failure"})
            self.assertIs(caught.exception, save_error)
            self.assertTrue((failed / "partial-arrays.npz").is_file())
            self.assertFalse((failed / "partial-manifest.json").exists())
        finally:
            archive.atomic_write = original_write
        execution.arrays["ami.call0.clocks"] = np.array([0., 0.5])
        execution.write(empty)
        saved = archive.read_json((empty / "ami-execution.json").read_bytes())
        self.assertEqual(saved["phases"], execution.phases)
        self.assertEqual(saved["clock_buffer_scope"],
                 "helper valid prefix only; full ABI buffers are separate B diagnostics")

        names = ("ctle_h", "ctle_s", "ctle_p", "ctle_H", "ctle_out_h", "ctle_out_s", "ctle_out_p", "ctle_out_H",
                 "ffe_out", "rx_in", "ctle_out")
        p = SimpleNamespace(rx_dll_file="no-model", tx_use_ami=False, tx_use_getwave=False,
                            rx_use_ami=True, rx_use_getwave=True, rx_use_clocks=True, ami_clock_info=info)
        def manifest():
            return {"datasets": {name: {} for name in names}, "plots": {}, "warnings": []}
        first = manifest()
        ami.annotate(p, execution, {}, {}, first)
        branch = first["ami"]["actual_branch"]
        self.assertEqual(branch["consumption_status"], "partial")
        self.assertEqual(branch["consumed_count"], 1)
        self.assertNotIn("Ignore_Bits", branch["native_DFE_CDR_AGC"])
        p.ami_clock_info = {}
        second = manifest()
        ami.annotate(p, execution, {}, {}, second)
        self.assertEqual(second["ami"]["actual_branch"]["clock_source"], "unavailable")
        self.assertIsNone(second["ami"]["actual_branch"]["consumed_count"])


class CoordinatorCases(unittest.TestCase):
    def test_actual_collect_analysis_masked_bytes_and_decoder_provenance(self):
        import copy
        import sys
        import types
        from types import SimpleNamespace
        from d2_under_test import destination
        data, analysis, clocks, ami, archive, viterbi = (modules[name] for name in (
            "pybert.web.data", "pybert.web.analysis", "pybert.web.clocks", "pybert.web.ami",
            "pybert.web.archive", "pybert.web.viterbi"))
        crop = {"info": {"nspui": 2, "consumed_count": 2, "invocation_id": "software-time-stop",
                         "analysis": {"stop_index": 16, "stop_s": 2.25}},
                "raw": {"t": np.array([i * 0.25 for i in range(16)])}, "window_indices": np.array([2, 6])}
        relative, meta = clocks.eye_selection(crop, 4, 16)
        self.assertEqual(relative.tolist(), [2])
        self.assertEqual(meta["slice_stop"], 10)  # last trace sample t[9]=2.25, never cross the time stop

        def stub_ffe_jitter(arrays):
            raise ValueError("unrelated FFE jitter deliberately stubbed; not qualified")

        def stub_bathtub(bins, values, **kwargs):
            return np.array([0., 0.1, 0.5, 0.1, 0.])

        def stub_package_version(name):
            return np.__version__ if name == "numpy" else "not installed; software metadata stub"

        class NoiseStub:
            def stub_normal(self, mean, sigma, count):
                return np.array([0.] * count)
            normal = stub_normal

        def stub_default_rng(seed):
            return NoiseStub()

        def stub_interference(arrays, manifest):
            manifest["interference_test_scope"] = "ordinary metadata stub; resource behavior not qualified"

        analysis.ffe_jitter, analysis.make_bathtub = stub_ffe_jitter, stub_bathtub
        np.random.default_rng = stub_default_rng
        data.importlib = SimpleNamespace(metadata=SimpleNamespace(version=stub_package_version))
        resource = types.ModuleType("pybert.web.resource_data")
        resource.annotate_interference = stub_interference
        sys.modules[resource.__name__] = resource

        t = np.array([i * 0.25 for i in range(32)])
        samples = np.array([2, 6, 10, 14, 18, 22, 26, 30])
        ps = np.array([np.nan] * 2 + [1e12] * 28 + [np.nan] * 2)
        ps.view(np.uint64)[0] = 0x7FF8000000000042
        known = np.array([False] * 2 + [True] * 28 + [False] * 2)
        source = modules["pybert.utility.ami_clock"].new_clock_info(True, "rx_getwave", "c1_fresh_main")
        source.update(actual_branch="ami", format_status="valid", eligible=True, consumption_status="completed",
            consumed_count=8, run_status="completed", full_analysis_eligible=True, grid_s=t,
            edges_s=np.array([0., 1., 2., 3., 4., 5., 6., 7.]), targets_s=t[samples],
            sample_indices=samples, consumed_tick_positions=np.array([0, 1, 2, 3, 4, 5, 6, 7]),
            sample_targets_s=t[samples], sample_grid_times_s=t[samples],
            sample_quantization_delay_s=np.array([0.] * 8),
            analysis_sample_indices=np.array([10, 14, 18, 22, 26, 30]), period_s=ps / 1e12, period_known=known,
            nspui=4, symbol_ui_s=1., ignore_ui=0., model_lock_status="unavailable",
            analysis={"start_index": 8, "stop_index": 32, "start_s": 2., "stop_s": 7.75,
                      "fft_slice": [12, 28], "required_decisions": 6, "required_eye_traces": 4},
            profile={"ignore_ui_units": "symbol_ui", "nominal_eye_offset_ui": 0, "mapping": "native_nrz"},
            profile_source="nrz_ui_contract", model_qualification="UNKNOWN")
        wave = np.array([-1., -1., 1., 1.] * 8)
        config = dict(nbits=8, eye_bits=6, nspui=4, rx_use_viterbi=False, rx_viterbi_fec=False,
                      rx_viterbi_symbols=2, mod_type="NRZ", decision_scaler=1., ctle_enable=True)
        engine = SimpleNamespace(ami_clock_info=source, ami_period_known=known, t=t,
            f=np.array([i / 8 for i in range(17)]), nui=8, eye_uis=6, nspui=4, ui=1., start_ix=0,
            t_ns_chnl=t[:8] * 1e9, t_irfft=t, bits=np.array([1] * 8), symbols=np.array([1.] * 8),
            noise=np.array([0.] * 32), ui_ests=ps, clock_times=t[samples], clocks=np.array([0.] * 32),
            lockeds=np.array([False] * 32), adaptation=np.empty((1, 0)), dfe_scalar_values=np.array([]),
            dfe_slicer_samps=np.array([1.] * 6), dfe_slicer_decisions=np.array([1.] * 6),
            bit_errs_dfe=np.array([], dtype=int), n_errs_dfe=0, n_errs_viterbi=-1, chnl_dly=0., rel_power=0.5,
            decision_scaler=1., rx_dll_file="no-model", tx_use_ami=False, tx_use_getwave=False,
            rx_use_ami=True, rx_use_getwave=True, rx_use_clocks=True, mod_type="NRZ", L=2, rx_viterbi_symbols=2)
        engine.clocks[samples] = 1.
        for name in data.WAVEFORMS:
            setattr(engine, name, wave.copy())
        for point in data.RESPONSES:
            for suffix in ("h", "s", "p", "H"):
                setattr(engine, f"{point}_{suffix}", np.array([1. + 0j] * 17) if suffix == "H" else np.array([1.] * 8))
        engine.chnl_H_raw, engine.chnl_trimmed_H = np.array([1. + 0j] * 17), np.array([1. + 0j] * 17)
        for name in ("channel", "tx", "ctle", "ffe", "dfe", "jitter", "total"):
            setattr(engine, name + "_perf", 1.)
        observations = {"source": dict(x=wave, ideal_signal=wave, ideal_xings=t[samples],
            ideal_xings_jit=np.array([0.5, 1.5, 2.5, 3.5, 4.5, 5.5]), xing_mask=None,
            ui=1., nspui=4, nui=8, eye_uis=6, pattern_len=2, rel_thresh=0.01,
            decision_scaler=1., mod_type=0, xing_min_t=2., noise_total=engine.noise, fext_count=0)}
        for point in data.JITTER_POINTS:
            observations[point] = dict(valid=True, ofst=0., actual_xings=t[samples], actual_xings_jit=t[samples],
                t_jitter=np.array([0., 1., 2.]), bin_centers=np.array([-0.5, -0.25, 0., 0.25, 0.5]),
                spectrum_freqs=np.array([0., 0.25, 0.5]), tie=np.array([0.] * 3), tie_ind=np.array([0.] * 3))
            for stat in data.JITTER_STATS:
                setattr(engine, f"{stat}_{point}", 0.01)
            for name in ("jitter", "jitter_ext", "jitter_spectrum", "jitter_ind_spectrum", "thresh"):
                setattr(engine, f"{name}_{point}", np.array([0., 1., 2., 1., 0.])
                        if name in ("jitter", "jitter_ext") else np.array([1.] * 3))
        captured = {"dfe": dict(bits_out=np.array([1] * 8), bits_test=np.array([1] * 6),
            bits_reference=np.array([1] * 6), auto_corr=np.array([1.] * 3), errors=np.array([], dtype=int),
            count=0, bit_delay=0, test_start_bit=2, test_stop_bit=8, reference_start_bit=2, reference_stop_bit=8)}
        identity = dict(run_id="d2-software-coordinator", input_hash="1" * 64, input_identity_hash="2" * 64,
            resource_hash="3" * 64, requested_input=config, effective_input=config, draft_revision=0,
            resource_bindings={}, runtime_extensions={}, execution_strategy={}, resources=[], warnings=[],
            test_scope="hand arrays/ordinary stubs only; no Main/model/decoder/trellis/noise algorithm qualification")
        folder = destination / "coordinator-run"
        folder.mkdir()
        execution = ami.Execution()
        snapshot = clocks.snapshot_producer(engine, previous_invocation="earlier", phase="software post-Main state")
        with execution.phase("collect"):
            run = data.collect(engine, observations, folder, identity, decoding=captured,
                               ami=(execution, {"rx": {"status": "software fixture; no binary loaded"}}),
                               producer_snapshot=snapshot, phase=execution.phase)
        self.assertEqual(run["raw_schema_version"], 6)
        self.assertEqual(run["required_features"], ["ami-clock-grid-v2"])
        raw = (folder / "arrays.npz").read_bytes()
        arrays = archive.read_arrays(raw, run=run)
        archive.validate_run(run, arrays)
        self.assertEqual(arrays["ui_ests"].tobytes(), ps.tobytes())
        self.assertEqual(arrays["ami.cdr.known_grid_indices"].tolist(), list(range(2, 30)))
        self.assertEqual(int(arrays["cdr.histogram.counts"].sum()), 22)
        self.assertEqual(arrays["cdr.spectrum.raw"].tolist(), [16e12 + 0j] + [0j] * 8)
        self.assertEqual(arrays["cdr.spectrum.frequency_Hz"].tolist(), [i * 0.25 for i in range(9)])
        self.assertEqual(run["ami"]["clock_contract"]["period_analysis"]["spectrum"]["origin_s"], 3.)
        self.assertEqual(run["datasets"]["cdr.spectrum.raw"]["window"], {"start_index": 12, "stop_index": 28})
        self.assertEqual(run["datasets"]["ui_ests"]["numerical_availability"], "masked")
        self.assertEqual(run["plots"]["cdr.spectrum"]["availability"], "unavailable")
        consumers = run["ami"]["clock_contract"]["eye_consumers"]
        for name in ("collect.eye.dfe", "analysis.eye.dfe"):
            self.assertEqual(consumers[name]["consumed_count"], 8)
            self.assertEqual(consumers[name]["window_sample_count"], 6)
            self.assertEqual(consumers[name]["trace_count"], 4)
            self.assertEqual(consumers[name]["absolute_indices"], [10, 14, 18, 22])
            self.assertEqual(consumers[name]["relative_indices"], [2, 6, 10, 14])
        self.assertEqual(float(arrays["eye.dfe.counts"].sum()), 32.)
        self.assertEqual(arrays["eye.dfe.counts"][954].tolist(), [4., 4., 0., 0., 4., 4., 0., 0.])
        payload = data.plot_payload(folder, "cdr")
        archive.json_bytes(payload)  # strict JSON finite check on the actual read-only projection
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(len(payload["data"][0]["x"]), 28)
        self.assertEqual(run["decoding"]["availability"], "disabled")
        self.assertEqual(run["summary"]["n_errs_viterbi"], -1)

        class PlotDataStub:
            def __init__(self):
                self.values = {}
            def stub_set_data(self, name, value):
                self.values[name] = np.asarray(value)
            def stub_get_data(self, name):
                return self.values[name]
            set_data, get_data = stub_set_data, stub_get_data

        def stub_trellis(sink):
            count = 6
            values = {"trellis_x": np.array([], dtype=int), "trellis_y": np.array([], dtype=int),
                      "trellis_path_xs": np.array([0, 1, 2, 3, 4, 5]), "trellis_path_ys": np.array([3] * count),
                      "trellis_err_xs": np.array([], dtype=int), "trellis_err_ys": np.array([])}
            for rank in (1, 2, 3):
                values[f"trellis_state{rank}_ys"] = np.array([rank - 1] * count)
                values[f"trellis_state{rank}_probs"] = np.array([0.25] * count)
            for name, value in values.items():
                sink.plotdata.set_data(name, value)

        sys.modules["chaco.api"].ArrayPlotData = PlotDataStub
        sys.modules["pybert.models.bert"].update_trellis = stub_trellis
        run = copy.deepcopy(run)
        arrays = {key: value.copy() for key, value in arrays.items()}
        run["effective_input"] = dict(config, rx_use_viterbi=True)
        engine.n_errs_viterbi = 0
        engine.bit_errs_viterbi = np.array([], dtype=int)
        engine.dbg_dict_viterbi = dict(
            decoder=SimpleNamespace(states=np.array([[-1., -1.], [-1., 1.], [1., -1.], [1., 1.]]),
                                    trans=np.array([[0.25] * 4] * 4)),
            sig_samps=np.array([1.] * 6), pulse_resp_samps=np.array([1., 1.]), probs=np.array([[0.25] * 4] * 6),
            prevs=np.array([[0] * 4] * 6), path=np.array([3] * 6), symbols_viterbi=np.array([1.] * 6),
            symbols_dfe=np.array([1.] * 8))
        captured["viterbi"] = dict(captured["dfe"], bits_out=np.array([1] * 6))
        captured["isi"] = dict(sample_times=t[[10, 14, 18, 22, 26, 30]],
            sample_indices=np.array([10, 14, 18, 22, 26, 30]), sigma=0.1, decision_scaler=1., ui=1., ts=0.25,
            nspui=4, N=2, L=2, clk_phase_ix=2, pulse_resp_curs_ix=2, pulse_peak_ix=0,
            decided_levels=np.array([1.] * 6))
        viterbi.extend(engine, captured, arrays, run)
        self.assertEqual(arrays["viterbi.sample_indices"].tolist(), [10, 14, 18, 22, 26, 30])
        self.assertIn("last W producer indices", run["decoding"]["clock_source"]["sample_selection"])
        original = arrays["viterbi.sample_indices"]
        arrays["viterbi.sample_indices"] = np.array([6, 10, 14, 18, 22, 26])  # old W+1 counterexample
        with self.assertRaisesRegex(ValueError, "final W"):
            viterbi.validate(run, arrays)
        arrays["viterbi.sample_indices"] = original


class BindingCases(unittest.TestCase):
    def test_real_wiring_native_math_discovery_and_failure_boundaries(self):
        import ast
        import subprocess
        from d2_under_test import root, evidence

        def source(path):
            return (root / path).read_text(encoding="utf-8")

        def function(text, name):
            return next(node for node in ast.parse(text).body
                        if isinstance(node, ast.FunctionDef) and node.name == name)

        def dump(node):
            return ast.dump(node, include_attributes=False)

        data = source("src/pybert/web/data.py")
        collect = function(data, "collect")
        old_data = (evidence / "inputs/data.baseline.py.txt").read_text(encoding="utf-8")
        old_collect = function(old_data, "collect")
        def nested_add(node):
            return next(item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == "add")
        self.assertEqual(dump(nested_add(collect)), dump(nested_add(old_collect)))
        text = ast.unparse(collect)
        self.assertLess(text.index("clock = clock_context"), text.index("for key in RAW_FIELDS"))
        self.assertIn("clock_indices=relative", text)
        self.assertIn("producer_snapshot", ast.unparse(collect.args))
        self.assertIn("clock_contract=clock", text)
        self.assertIn("Incomplete required AMI timed Eye", text)
        self.assertIn("Incomplete required AMI period analysis", text)
        current = function(source("src/pybert/web/analysis.py"), "clock_data")
        old = function((evidence / "inputs/analysis.baseline.py.txt").read_text(encoding="utf-8"), "clock_data")
        self.assertEqual([dump(node) for node in current.body[2:]], [dump(node) for node in old.body[1:]])
        analysis = ast.unparse(function(source("src/pybert/web/analysis.py"), "extend_analysis"))
        self.assertIn("clock_indices=relative", analysis)
        self.assertIn("clock_contract is None and", analysis)
        self.assertIn("clock_contract['eye_consumers']['analysis.eye.dfe']", analysis)
        worker = ast.unparse(function(source("src/pybert/web/worker.py"), "run_worker"))
        for phase in ("prepare", "Main", "collect", "finally"):
            self.assertIn("execution.phase('" + phase + "')", worker)
        self.assertLess(worker.index("snapshot_producer(p, previous_invocation, 'post_Main')"),
                        worker.index("if p.status != 'Ready.'"))
        self.assertIn("producer_snapshot=producer_snapshot, phase=execution.phase", worker)
        self.assertIn("write_partial(directory, partial_snapshot, execution.phases, terminal)", worker)
        self.assertIn("evidence_errors", worker)
        old_worker = function((evidence / "inputs/worker.baseline.py.txt").read_text(encoding="utf-8"), "run_worker")
        calls = lambda node: [dump(item) for item in ast.walk(node) if isinstance(item, ast.Call)
                              and ast.unparse(item.func) == "my_run_simulation"]
        self.assertEqual(calls(function(source("src/pybert/web/worker.py"), "run_worker")), calls(old_worker))
        annotation = ast.unparse(function(source("src/pybert/web/ami.py"), "annotate"))
        self.assertNotIn("raw_clocks", annotation)
        self.assertNotIn("Ignore_Bits", annotation)
        self.assertIn("copy.deepcopy(execution.phases)", annotation)
        for path in ("src/pybert/utility/sigproc.py", "src/pybert/utility/math.py", "src/pybert/web/config.py",
                     "pyproject.toml", "uv.lock", ".gitmodules", "tests"):
            result = subprocess.run(["git", "--no-optional-locks", "diff", "--quiet",
                                     "0f04562c50a12fae637fece04da100c44c86617e", "--", path], cwd=root)
            self.assertEqual(result.returncode, 0, path)
        for name in ("d2_cases.py", "guard_cases.py"):
            self.assertFalse(name.startswith("test_"))
            self.assertFalse(name.endswith("_test.py"))
        guard = (evidence / "run_guarded.py").read_text(encoding="utf-8")
        self.assertIn("os._exit(86)", guard)
        self.assertIn("except BaseException as error:", ast.unparse(function(guard, "main")))


class ReviewFixCases(unittest.TestCase):
    def test_worker_imported_config_snapshot_keeps_global_scope(self):
        import ast
        import json
        import symtable
        from d2_under_test import root, evidence, destination

        paths = {"base": evidence / "inputs/worker.baseline.py.txt",
                 "reviewed": evidence / "inputs/worker.review-broken.py.txt",
                 "current": root / "src/pybert/web/worker.py"}
        report = {}
        functions = {}
        for label, path in paths.items():
            text = path.read_text(encoding="utf-8")
            table = next(item for item in symtable.symtable(text, str(path), "exec").get_children()
                         if item.get_name() == "run_worker")
            symbol = table.lookup("snapshot")
            function = next(item for item in ast.parse(text).body
                            if isinstance(item, ast.FunctionDef) and item.name == "run_worker")
            functions[label] = function
            report[label] = {"global": symbol.is_global(), "local": symbol.is_local(),
                             "referenced": symbol.is_referenced(), "assigned": symbol.is_assigned()}
        (destination / "worker-scope.json").write_text(json.dumps(report, indent=2) + "\n",
                                                       encoding="utf-8")
        self.assertTrue(report["base"]["global"])
        self.assertTrue(report["reviewed"]["local"])
        self.assertTrue(report["reviewed"]["assigned"])
        self.assertTrue(report["current"]["global"], "config snapshot was shadowed by a worker local")
        self.assertFalse(report["current"]["assigned"])
        self.assertFalse(any(isinstance(item, ast.Name) and item.id == "snapshot" and isinstance(item.ctx, ast.Store)
                             for item in ast.walk(functions["current"])))
        calls = lambda node: [ast.dump(item, include_attributes=False) for item in ast.walk(node)
                              if isinstance(item, ast.Call) and ast.unparse(item.func) == "my_run_simulation"]
        self.assertEqual(calls(functions["base"]), calls(functions["current"]))
        analysis = ast.unparse(ast.parse((root / "src/pybert/web/analysis.py").read_text(encoding="utf-8")))
        self.assertIn("'uniform_grid_validation'", analysis)

    def test_high_origin_roundoff_and_real_nonuniform_period_inputs(self):
        import json
        from d2_under_test import evidence

        fixture = json.loads((evidence / "review-fixtures.json").read_text(encoding="utf-8"))
        t = np.array([float.fromhex(value) for value in fixture["grid_hex"]])
        periods = np.array(fixture["period_ps"])
        original_t, original_periods = t.tobytes(), periods.tobytes()
        projection = modules["pybert.web.clocks"].period_projection

        def context(grid):
            return {"info": {"period_known": np.array([True] * 16), "analysis": {
                "start_index": 0, "stop_index": 16, "start_s": float(grid[0]), "stop_s": float(grid[-1]),
                "fft_slice": [2, 10]}}}

        product = projection(context(t), t, periods, 1e-10)
        spectrum = product["spectrum"]
        self.assertEqual(spectrum["availability"], "available", spectrum["reason"])
        self.assertEqual(spectrum["indices"].tolist(), [2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(spectrum["window"], {"start_index": 2, "stop_index": 10})
        self.assertEqual(spectrum["origin_s"], float.fromhex(fixture["grid_hex"][2]))
        self.assertEqual(spectrum["sample_interval_s"], float.fromhex(fixture["actual_first_interval_hex"]))
        self.assertEqual(spectrum["frequency_hz"].tolist(),
                         [float.fromhex(value) for value in fixture["expected_frequency_hex"]])
        self.assertEqual(spectrum["raw"].real.tolist(), fixture["expected_fft_real"])
        self.assertEqual(spectrum["raw"].imag.tolist(), [0.] * 5)
        self.assertEqual(int(product["histogram"]["counts"].sum()), 16)
        validation = spectrum["uniform_grid_validation"]
        self.assertEqual(validation["max_interval_error_s"], fixture["max_abs_interval_error_s"])
        self.assertEqual(validation["max_bound_s"], fixture["expected_roundoff_bound_s"])
        self.assertEqual(validation["timestamp_dtype"], t.dtype.str)
        self.assertTrue(validation["strictly_increasing"])
        self.assertEqual(t.tobytes(), original_t)
        self.assertEqual(periods.tobytes(), original_periods)

        for kind in ("perturbed", "duplicate", "reversed", "initial_zero"):
            grid = t.copy()
            if kind == "perturbed":
                grid[8] += float.fromhex(fixture["nominal_ts_hex"]) / 16
            elif kind == "duplicate":
                grid[8] = grid[7]
            elif kind == "reversed":
                grid[8] = grid[6]
            else:
                grid[1] = grid[0]
            with self.subTest(kind=kind):
                result = projection(context(grid), grid, periods, 1e-10)
                self.assertEqual(result["spectrum"]["availability"], "unavailable")
                self.assertEqual(result["spectrum"]["reason"], "unknown_or_nonpositive_sample_interval"
                                 if kind == "initial_zero" else "nonuniform_grid")
                self.assertEqual(result["spectrum"]["raw"].size, 0)
                self.assertEqual(int(result["histogram"]["counts"].sum()), 16)
        for bad in (float("nan"), float("inf")):
            grid = t.copy()
            grid[8] = bad
            with self.subTest(nonfinite=str(bad)), self.assertRaises(ValueError):
                projection(context(grid), grid, periods, 1e-10)
        # Exactly representable zero-origin control must retain the old raw FFT/frequency convention.
        grid = np.array([i * 0.25 for i in range(16)])
        result = projection(context(grid), grid, periods, 1.)["spectrum"]
        self.assertEqual(result["raw"].tolist(), [40. + 0j, 0j, 0j, 0j, 0j])
        self.assertEqual(result["frequency_hz"].tolist(), [0., 0.5, 1., 1.5, 2.])


class IntegerReviewCases(unittest.TestCase):
    def fixture(self, item):
        from d2_under_test import destination
        grid = np.array(item["t"], dtype=item["dtype"])
        periods = np.array([5., 5., 5.])
        (destination / (item["name"] + ".t.bin")).write_bytes(grid.tobytes())
        (destination / (item["name"] + ".period.bin")).write_bytes(periods.tobytes())
        context = {"info": {"period_known": np.array([True, True, True]), "analysis": {
            "start_index": 0, "stop_index": 3, "start_s": int(min(grid)), "stop_s": int(max(grid)),
            "fft_slice": [0, 3]}}}
        return grid, periods, context

    def test_exact_integer_nonuniform_and_unsigned_reverse_rejected(self):
        import json
        from d2_under_test import evidence
        cases = json.loads((evidence / "integer-review-followup-plan.json").read_text(encoding="utf-8"))["fixtures"]
        for item in cases:
            if item["expected"] == "available":
                continue
            with self.subTest(name=item["name"]):
                grid, periods, context = self.fixture(item)
                before = grid.tobytes()
                spectrum = modules["pybert.web.clocks"].period_projection(context, grid, periods, 1.)["spectrum"]
                self.assertEqual(spectrum["availability"], "unavailable", item["name"])
                self.assertEqual(spectrum["reason"], "nonuniform_grid")
                self.assertEqual(spectrum["raw"].size, 0)
                self.assertEqual(grid.tobytes(), before)

    def test_exact_integer_uniform_preserves_original_bytes_and_frequency(self):
        import json
        from d2_under_test import evidence
        cases = json.loads((evidence / "integer-review-followup-plan.json").read_text(encoding="utf-8"))["fixtures"]
        for item in cases:
            if item["expected"] != "available":
                continue
            with self.subTest(name=item["name"]):
                grid, periods, context = self.fixture(item)
                original_grid, original_periods = grid.tobytes(), periods.tobytes()
                result = modules["pybert.web.clocks"].period_projection(context, grid, periods, 1.)
                spectrum = result["spectrum"]
                self.assertEqual(spectrum["availability"], "available")
                self.assertEqual(spectrum["sample_interval_s"], 1024.)
                self.assertEqual(spectrum["window"], {"start_index": 0, "stop_index": 3})
                self.assertEqual(spectrum["indices"].tolist(), [0, 1, 2])
                self.assertEqual(spectrum["raw"].tolist(), [15. + 0j, 0j])
                self.assertEqual(spectrum["frequency_hz"].tolist(), [0., float.fromhex("0x1.5555555555555p-12")])
                self.assertEqual(int(result["histogram"]["counts"].sum()), 3)
                metadata = spectrum["uniform_grid_validation"]
                self.assertEqual(metadata["rule"], "exact integer intervals; zero floating timestamp tolerance")
                self.assertEqual(metadata["max_bound_s"], 0.)
                self.assertTrue(metadata["integer_intervals_equal"])
                self.assertEqual(metadata["timestamp_dtype"], grid.dtype.str)
                self.assertEqual(grid.tobytes(), original_grid)
                self.assertEqual(periods.tobytes(), original_periods)
