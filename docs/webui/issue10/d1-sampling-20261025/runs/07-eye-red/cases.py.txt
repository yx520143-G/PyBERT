"""Guarded D1 software cases; intentionally outside ordinary pytest discovery."""

import unittest

from d1_under_test import functions, np, baseline_eye, candidate_eye


STUB_COUNTS = {}


class PlannerCases(unittest.TestCase):
    def test_zero_edge_and_last_grid_sample_are_planned(self):
        self.assertTrue(callable(functions.get("new_clock_info")), "production state factory is missing")
        self.assertTrue(callable(functions.get("plan_ami_clocks")), "production planner is missing")
        info = functions["new_clock_info"](True, "rx_getwave", "c1_fresh_main")
        window = {"start_s": 0.0, "stop_s": 1.25, "start_index": 0, "stop_index": 6,
                  "required_decisions": 2, "required_eye_traces": 1, "fft_slice": [1, 4]}
        functions["plan_ami_clocks"](info, np.array([0.0, 0.5, 1.0]),
                                     np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.25]),
                                     0.5, 0.0, 2, window)
        self.assertEqual(info["format_status"], "valid")
        self.assertEqual(info["targets_s"].tolist(), [0.25, 0.75, 1.25])
        self.assertEqual(info["planned_indices"].tolist(), [1, 3, 5])
        self.assertEqual(info["consumed_count"], 0)
        self.assertEqual(info["consumption_status"], "not_attempted")

    def test_planner_contract_without_claiming_consumption(self):
        grid = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25]
        window = {"start_s": 0.0, "stop_s": 1.25, "start_index": 0, "stop_index": 6,
                  "required_decisions": 2, "required_eye_traces": 1, "fft_slice": [1, 4]}
        declared = {"ignore_ui_units": "symbol_ui", "nominal_eye_offset_ui": 0,
                    "mapping": "native_pam4"}
        rows = [
            {"name": "negative", "edges": [-0.1], "error": "malformed_clocks", "format": "invalid"},
            {"name": "NaN", "edges": [float("nan")], "error": "malformed_clocks", "format": "invalid"},
            {"name": "infinite", "edges": [float("inf")], "error": "malformed_clocks", "format": "invalid"},
            {"name": "descending", "edges": [0.5, 0], "error": "malformed_clocks", "format": "invalid"},
            {"name": "duplicate", "edges": [0, 0], "error": "malformed_clocks", "format": "invalid"},
            {"name": "matrix", "edges": [[0, 0.5]], "error": "malformed_clocks", "format": "invalid"},
            {"name": "sentinel", "edges": [-1], "error": "malformed_clocks", "format": "invalid"},
            {"name": "empty grid", "edges": [0], "grid": [], "error": "invalid_grid", "format": "valid"},
            {"name": "bad grid", "edges": [0], "grid": [0, 0.25, float("nan")],
             "error": "invalid_grid", "format": "valid"},
            {"name": "repeated grid", "edges": [0], "grid": [0, 0.25, 0.25],
             "error": "invalid_grid", "format": "valid"},
            {"name": "bad UI", "edges": [0], "ui": 0, "error": "invalid_timing", "format": "valid"},
            {"name": "bad Ignore", "edges": [0], "ignore": -1,
             "error": "invalid_timing", "format": "valid"},
            {"name": "collision", "edges": [0.01, 0.05],
             "error": "unsupported_resolution", "format": "valid"},
            {"name": "unknown origin", "edges": [0], "origin": None,
             "error": "unknown_origin", "format": "valid"},
            {"name": "wrong mode", "edges": [0], "mode": "unknown",
             "error": "unsupported_mode", "format": "valid"},
            {"name": "PAM4 unknown", "edges": [0], "modulation": "PAM4",
             "error": "unsupported_profile", "format": "valid"},
            {"name": "PAM4 bit units", "edges": [0], "modulation": "PAM4",
             "profile": {**declared, "ignore_ui_units": "bits"},
             "error": "unsupported_profile", "format": "valid"},
            {"name": "PAM4 offset", "edges": [0], "modulation": "PAM4",
             "profile": {**declared, "nominal_eye_offset_ui": 0.1},
             "error": "unsupported_profile", "format": "valid"},
            {"name": "no clocks", "edges": [], "indices": [], "native": True},
            {"name": "PAM4 no clocks", "edges": [], "modulation": "PAM4", "indices": [], "native": True},
            {"name": "single tick", "edges": [0], "indices": [1], "deferred": [None]},
            {"name": "just after end", "edges": [0, 1.0000000000000002],
             "indices": [1], "deferred": [None, "future"]},
            {"name": "off-grid ceil", "edges": [0.35], "indices": [3], "deferred": [None],
             "delay": 0.15},
            {"name": "ceil cannot satisfy Ignore", "edges": [0.35], "ignore": 1.3,
             "indices": [3], "deferred": [None], "ready": [False]},
            {"name": "PAM4 uses symbol UI once", "edges": [0, 0.5, 1], "modulation": "PAM4",
             "profile": declared, "indices": [1, 3, 5], "deferred": [None, None, None]},
        ]
        for row in rows:
            with self.subTest(row["name"]):
                info = functions["new_clock_info"](True, row.get("mode", "rx_getwave"),
                                                    row.get("origin", "c1_fresh_main"))
                args = (info, np.array(row["edges"]), np.array(row.get("grid", grid)),
                        row.get("ui", 0.5), row.get("ignore", 0), 2, window)
                kwargs = {"modulation": row.get("modulation", "NRZ"), "profile": row.get("profile")}
                if "error" in row:
                    with self.assertRaisesRegex(ValueError, row["error"]):
                        functions["plan_ami_clocks"](*args, **kwargs)
                    self.assertEqual(info["format_status"], row["format"])
                    self.assertEqual(info["reason"], row["error"])
                else:
                    functions["plan_ami_clocks"](*args, **kwargs)
                    self.assertEqual(info["planned_indices"].tolist(), row["indices"])
                    self.assertEqual(info["use_native"], row.get("native", False))
                    if "deferred" in row:
                        self.assertEqual(info["deferred_reasons"], row["deferred"])
                    if "ready" in row:
                        self.assertEqual(info["planned_ready"].tolist(), row["ready"])
                    if "delay" in row:
                        self.assertAlmostEqual(info["quantization_delay_s"][0], row["delay"], places=14)
                self.assertEqual(info["consumed_count"], 0)
                self.assertEqual(info["consumption_status"], "not_attempted")


class ConsumerCases(unittest.TestCase):
    def test_actual_consumption_partial_windows_and_periods(self):
        self.assertTrue(callable(functions.get("consume_ami_clocks")), "production consumer is missing")
        grid = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25]
        window = {"start_s": 0.0, "stop_s": 1.25, "start_index": 0, "stop_index": 6,
                  "required_decisions": 2, "required_eye_traces": 1, "fft_slice": [1, 4]}
        rows = [
            {"name": "all ticks including last", "edges": [0, 0.5, 1], "indices": [1, 3, 5],
             "analysis": [3, 5], "traces": [1], "known": [False, True, True, True, True, False]},
            {"name": "decide fails second", "edges": [0, 0.5, 1], "fail_at": 2,
             "indices": [1], "error": "injected", "known": [False] * 6},
            {"name": "decide fails first", "edges": [0, 0.5, 1], "fail_at": 1,
             "indices": [], "error": "injected", "known": [False] * 6},
            {"name": "cancel before second", "edges": [0, 0.5, 1], "cancel_at": 2,
             "indices": [1], "error": "injected", "known": [False] * 6},
            {"name": "nonempty single tick is not fallback", "edges": [0], "indices": [1],
             "error": "insufficient_coverage", "known": [False] * 6},
            {"name": "sparse coverage", "edges": [0, 1], "indices": [1, 5],
             "window": {**window, "required_decisions": 3}, "error": "insufficient_coverage",
             "known": [False, True, True, True, True, False], "period": 1.0},
            {"name": "all future", "edges": [1.0000000000000002], "indices": [],
             "error": "insufficient_coverage", "known": [False] * 6},
            {"name": "actual grid above window stop", "edges": [0.35], "indices": [3],
             "window": {**window, "stop_s": 0.6, "stop_index": 3, "required_decisions": 1,
                        "fft_slice": [1, 3]}, "error": "insufficient_coverage", "analysis": [],
             "known": [False] * 6},
            {"name": "target below window start", "edges": [0.35], "indices": [3],
             "window": {**window, "start_s": 0.65, "start_index": 3, "required_decisions": 1,
                        "fft_slice": [3, 5]}, "error": "insufficient_coverage", "analysis": [],
             "known": [False] * 6},
            {"name": "ceil does not advance adaptation", "edges": [0.35], "ignore": 1.3,
             "indices": [3], "error": "insufficient_coverage", "analysis": [], "known": [False] * 6},
        ]
        for row in rows:
            with self.subTest(row["name"]):
                info = functions["new_clock_info"](True, "rx_getwave", "c1_fresh_main")
                functions["plan_ami_clocks"](info, np.array(row["edges"]), np.array(grid),
                                             0.5, row.get("ignore", 0), 2, row.get("window", window))
                calls, checks = [], []
                injected = RuntimeError("injected")

                def stub_decide(value):
                    calls.append(float(value))
                    if len(calls) == row.get("fail_at"):
                        raise injected
                    return {1.0: (1.0, [1]), -1.0: (-1.0, [0])}[float(value)]

                def stub_check():
                    checks.append(True)
                    if len(checks) == row.get("cancel_at"):
                        raise injected

                if "error" in row:
                    with self.assertRaisesRegex((RuntimeError, ValueError), row["error"]) as caught:
                        functions["consume_ami_clocks"](info, np.array([0, 1, 0, -1, 0, 1]),
                                                       stub_decide, stub_check)
                    if row["error"] == "injected":
                        self.assertIs(caught.exception, injected)
                    self.assertEqual(info["consumption_status"], "partial")
                    self.assertFalse(info["full_analysis_eligible"])
                else:
                    result = functions["consume_ami_clocks"](info, np.array([0, 1, 0, -1, 0, 1]),
                                                            stub_decide, stub_check)
                    self.assertIs(result, info)
                    self.assertEqual(info["consumption_status"], "completed")
                    self.assertTrue(info["full_analysis_eligible"])
                    self.assertEqual(info["bits"], [1, 0, 1])
                    self.assertEqual(info["sample_grid_times_s"].tolist(), [0.25, 0.75, 1.25])
                    self.assertEqual(info["clock_mask"].tolist(), [0, 1, 0, 1, 0, 1])
                    self.assertEqual(info["last_tick_status"], "consumed")
                self.assertFalse(info["use_native"])
                self.assertEqual(info["sample_indices"].tolist(), row["indices"])
                self.assertEqual(info["consumed_count"], len(row["indices"]))
                self.assertEqual(info["period_known"].tolist(), row["known"])
                for value, known in zip(info["period_s"], row["known"]):
                    if known:
                        self.assertEqual(float(value), row.get("period", 0.5))
                    else:
                        self.assertTrue(np.isnan(value))
                if "analysis" in row:
                    self.assertEqual(info["analysis_sample_indices"].tolist(), row["analysis"])
                if "traces" in row:
                    self.assertEqual(info["eye_sample_indices"].tolist(), row["traces"])
                self.assertEqual(info["model_lock_status"], "unavailable")

        # Literal W+1 counterexample from the fixed contract: keep the actual last W points.
        info = functions["new_clock_info"](True, "rx_getwave", "c1_fresh_main")
        tail_grid = np.array([0, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 2.75])
        tail_window = {"start_s": 0, "stop_s": 2.75, "start_index": 0, "stop_index": 12,
                       "required_decisions": 2, "required_eye_traces": 1, "fft_slice": [2, 6]}
        functions["plan_ami_clocks"](info, np.array([0, 1, 2]), tail_grid, 1.0, 0, 4, tail_window)

        def stub_tail_decide(value):
            return 1.0, [1]

        functions["consume_ami_clocks"](info, np.array([1] * 12), stub_tail_decide)
        self.assertEqual(info["analysis_sample_indices"].tolist(), [6, 10])
        self.assertEqual(info["sample_grid_times_s"].tolist(), [0.5, 1.5, 2.5])
        info["bits"].append(0)
        fresh = functions["new_clock_info"](True, "rx_getwave", "c1_fresh_main")
        self.assertEqual(fresh["consumed_count"], 0)
        self.assertEqual(fresh["consumption_status"], "not_attempted")
        self.assertNotIn("bits", fresh)

        for prefix in (True, False):
            with self.subTest(chunk_prefix=prefix):
                info = functions["new_clock_info"](True, "rx_getwave", "c1_fresh_main")
                part_grid = grid[:3] if prefix else grid
                part_window = ({"start_s": 0, "stop_s": 0.5, "start_index": 0, "stop_index": 3,
                                "required_decisions": 1, "required_eye_traces": 1, "fft_slice": [1, 2]}
                               if prefix else window)
                functions["plan_ami_clocks"](info, np.array([0, 0.5, 1]), np.array(part_grid),
                                             0.5, 0, 2, part_window)
                if prefix:
                    with self.assertRaisesRegex(ValueError, "insufficient_coverage"):
                        functions["consume_ami_clocks"](info, np.array([1] * 3), stub_tail_decide)
                    self.assertEqual(info["consumed_count"], 1)
                    self.assertEqual(info["deferred_reasons"], [None, "future", "future"])
                else:
                    functions["consume_ami_clocks"](info, np.array([1] * 6), stub_tail_decide)
                    self.assertEqual(info["consumed_count"], 3)
                    self.assertEqual(info["last_tick_status"], "consumed")

        info = functions["new_clock_info"](True, "rx_getwave", "c1_fresh_main")
        float_grid = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1])
        float_window = {"start_s": 0, "stop_s": 1.1, "start_index": 0, "stop_index": 12,
                        "required_decisions": 2, "required_eye_traces": 1, "fft_slice": [4, 8]}
        functions["plan_ami_clocks"](info, np.array([0.09999999999999998, 0.5, 0.9]),
                                     float_grid, 0.4, 0, 4, float_window)
        functions["consume_ami_clocks"](info, np.array([1] * 12), stub_tail_decide)
        self.assertEqual(info["sample_indices"].tolist(), [3, 7, 11])
        self.assertEqual(info["sample_grid_times_s"].tolist(), [0.3, 0.7, 1.1])
        self.assertEqual(int(info["sample_grid_times_s"][0] // 0.1), 2)  # Never round-trip this way in consumers.


class EyeCases(unittest.TestCase):
    def test_producer_indices_and_native_eye_compatibility(self):
        self.assertTrue(callable(functions.get("ami_eye_data")), "production timed Eye projection is missing")
        waveforms = [[-1, -1, 1, 1] * 4, [-0.5, 0.5] * 8]
        for values in waveforms:
            for clocks in (None, np.array([0, 0.25, 0.75, 1])):
                with self.subTest(native=values[:4], clocks=None if clocks is None else clocks.tolist()):
                    old = baseline_eye(0.5, 2, 16, np.array(values), 2.0, clocks)
                    current = candidate_eye(0.5, 2, 16, np.array(values), 2.0, clocks)
                    self.assertEqual(current.tolist(), old.tolist())

        values = np.array([-1, 1] * 9)
        # At ts=0.1, canonical grid time 0.3 // ts is 2; the producer's actual index is 3.
        direct = candidate_eye(0.4, 4, 16, values, 2.0, clock_indices=np.array([3, 7]))
        self.assertEqual(float(direct[12, 0]), 2)
        self.assertEqual(float(direct[4, 0]), 0)
        self.assertEqual(float(direct.sum()), 16)
        for bad in ([-1], [12], [1.5]):
            with self.subTest(invalid_indices=bad):
                with self.assertRaisesRegex(ValueError, "clock_indices"):
                    candidate_eye(0.4, 4, 16, values, 2.0, clock_indices=bad)
        empty = candidate_eye(0.4, 4, 16, values, 2.0, clock_indices=[])
        self.assertEqual(float(empty.sum()), 0)

        rows = [
            {"indices": [5, 9], "stop": 20, "length": 18, "relative": [3, 7], "traces": 2},
            {"indices": [1, 5, 9, 15], "stop": 20, "length": 18, "relative": [3, 7], "traces": 2},
            {"indices": [0, 15], "stop": 20, "length": 10, "relative": [], "traces": 0},
            {"indices": [5, 9], "stop": 14, "length": 18, "relative": [3], "traces": 0},
        ]
        for row in rows:
            with self.subTest(crop=row):
                info = {"full_analysis_eligible": True, "symbol_ui_s": 0.4, "nspui": 4,
                        "eye_sample_indices": np.array(row["indices"]),
                        "analysis": {"stop_index": row["stop"], "required_eye_traces": 2}}
                image = functions["ami_eye_data"](info, values[:row["length"]], 2, 16, 2.0, candidate_eye)
                self.assertEqual(info["eye_relative_indices"].tolist(), row["relative"])
                self.assertEqual(info["eye_trace_count"], row["traces"])
                if row["traces"]:
                    self.assertEqual(info["eye_status"], "completed")
                    self.assertEqual(float(image.sum()), 16)
                else:
                    self.assertIsNone(image)
                    self.assertEqual(info["eye_status"], "unavailable")
