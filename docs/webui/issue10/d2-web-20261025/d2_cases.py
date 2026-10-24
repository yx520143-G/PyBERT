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
