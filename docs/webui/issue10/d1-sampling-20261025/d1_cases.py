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
        self.assertEqual(float(direct[5, 0]), 0)
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


class ProjectionCases(unittest.TestCase):
    def test_masked_period_fft_axes_and_atomic_plot_switches(self):
        self.assertTrue(callable(functions.get("clock_period_data")), "production period projection is missing")
        self.assertTrue(callable(functions.get("set_period_plot_data")), "production plot publication is missing")

        class PlotDataStub:
            def __init__(self):
                self.data = {"t_ns": np.array([99, 100]), "other": np.array([7, 8])}
                self.events = []

            def stub_update_data(self, *args, **kwargs):
                values = dict(*args, **kwargs)
                self.data.update(values)
                if set(values) != {"period_t_ns", "ui_ests"}:
                    raise AssertionError("period x/y must be published in one event")
                if len(self.data["period_t_ns"]) != len(self.data["ui_ests"]):
                    raise AssertionError("period x/y lengths differ")
                self.events.append((len(self.data["period_t_ns"]), len(self.data["ui_ests"])))

            update_data = stub_update_data

        def input_info():
            return {"consumption_status": "completed", "full_analysis_eligible": True,
                    "period_s": np.array([np.nan, 1e-12, 2e-12, 3e-12, 4e-12, np.nan]),
                    "period_known": np.array([False, True, True, True, True, False]),
                    "analysis": {"start_s": 10, "stop_s": 11.25, "start_index": 0,
                                 "stop_index": 6, "fft_slice": [1, 5]}}

        grid = np.array([10, 10.25, 10.5, 10.75, 11, 11.25])
        plot = PlotDataStub()
        functions["set_period_plot_data"](plot, [], [])
        self.assertEqual(plot.events, [(0, 0)])
        info = input_info()
        data = functions["clock_period_data"](info, grid, 0.25)
        self.assertEqual(data["histogram_counts"].tolist(),
                         [1 if i in (0, 33, 66, 99) else 0 for i in range(100)])
        self.assertEqual(data["frequency_hz"].tolist(), [0, 1, 2])
        self.assertEqual(data["spectrum"].tolist(), [10 + 0j, -2 + 2j, -2 + 0j])
        self.assertEqual(data["plot_t_ns"].tolist(), [1e10, 1.025e10, 1.05e10, 1.075e10, 1.1e10, 1.125e10])
        self.assertEqual(data["plot_period_ps"][1:5].tolist(), [1, 2, 3, 4])
        self.assertTrue(np.isnan(data["plot_period_ps"][[0, 5]]).all())
        self.assertTrue(data["spectrum_display_eligible"])
        self.assertEqual(info["period_analysis"]["fft_window_indices"], [1, 5])
        functions["set_period_plot_data"](plot, data["plot_t_ns"], data["plot_period_ps"])

        for name in ("gap", "short", "constant", "unknown", "partial", "outside"):
            with self.subTest(period=name):
                current = input_info()
                if name == "gap":
                    current["period_known"][2] = False
                    current["period_s"][2] = np.nan
                elif name == "short":
                    current["analysis"]["fft_slice"] = [1, 2]
                elif name == "constant":
                    current["period_s"][1:5] = 1e-12
                elif name == "unknown":
                    current["period_known"][:] = False
                    current["period_s"][:] = np.nan
                elif name == "partial":
                    current["consumption_status"] = "partial"
                    current["full_analysis_eligible"] = False
                else:
                    current["analysis"]["start_s"] = 10.4
                projected = functions["clock_period_data"](current, grid, 0.25)
                if name == "constant":
                    self.assertEqual(projected["spectrum"].tolist(), [4 + 0j, 0j, 0j])
                    self.assertFalse(projected["spectrum_display_eligible"])
                    self.assertEqual(projected["spectrum_display_reason"], "zero_fundamental")
                else:
                    self.assertEqual(projected["frequency_hz"].tolist(), [])
                    self.assertEqual(projected["spectrum"].tolist(), [])
                if name in ("unknown", "partial"):
                    self.assertEqual(projected["histogram_counts"].tolist(), [])
                elif name == "gap":
                    self.assertEqual(int(projected["histogram_counts"].sum()), 3)
                    self.assertTrue(np.isnan(projected["plot_period_ps"][2]))
                elif name == "outside":
                    self.assertEqual(int(projected["histogram_counts"].sum()), 3)

        invalid = input_info()
        invalid["period_known"][2] = False  # Unknown cannot contain a fabricated finite period.
        with self.assertRaisesRegex(ValueError, "period mask"):
            functions["clock_period_data"](invalid, grid, 0.25)

        for n, stop in ((8, 1.75), (2001, 500.0)):
            with self.subTest(full_grid_length=n):
                current = {"consumption_status": "completed", "full_analysis_eligible": True,
                           "period_s": np.array([np.nan] + [1e-12] * (n - 2) + [np.nan]),
                           "period_known": np.array([False] + [True] * (n - 2) + [False]),
                           "analysis": {"start_s": 0, "stop_s": stop, "start_index": 0,
                                        "stop_index": n, "fft_slice": [1, 5]}}
                full_grid = np.array([i * 0.25 for i in range(n)])
                projected = functions["clock_period_data"](current, full_grid, 0.25)
                functions["set_period_plot_data"](plot, projected["plot_t_ns"], projected["plot_period_ps"])
                self.assertEqual(plot.events[-1], (n, n))
                self.assertEqual(float(plot.data["period_t_ns"][-1]), 1.75e9 if n == 8 else 5e11)
                self.assertTrue(np.isnan(plot.data["ui_ests"][[0, n - 1]]).all())
                functions["set_period_plot_data"](plot, [], [])
                self.assertEqual(plot.events[-1], (0, 0))

        # These are hand-given Native plot arrays; SciPy interpolation itself is not executed.
        native_x, native_y = np.array([i * 0.5 for i in range(1000)]), np.array([4.0] * 1000)
        functions["set_period_plot_data"](plot, native_x, native_y)
        self.assertEqual(plot.data["period_t_ns"].tolist(), native_x.tolist())
        self.assertEqual(plot.data["ui_ests"].tolist(), native_y.tolist())
        events_before = len(plot.events)
        with self.assertRaisesRegex(ValueError, "matching lengths"):
            functions["set_period_plot_data"](plot, np.array([1]), np.array([1, 2]))
        self.assertEqual(len(plot.events), events_before)

        produced = functions["new_clock_info"](True, "rx_getwave", "c1_fresh_main")
        original_grid = np.array([0, 0.25, 0.5, 0.75, 1, 1.25])
        window = {"start_s": 0, "stop_s": 1.25, "start_index": 0, "stop_index": 6,
                  "required_decisions": 2, "required_eye_traces": 1, "fft_slice": [1, 4]}
        functions["plan_ami_clocks"](produced, np.array([0, 0.5, 1]), original_grid, 0.5, 0, 2, window)

        def stub_decide(value):
            return 1.0, [1]

        functions["consume_ami_clocks"](produced, np.array([1] * 6), stub_decide)
        projected = functions["clock_period_data"](produced, original_grid, 0.25)
        self.assertEqual(int(projected["histogram_counts"].sum()), 4)
        functions["set_period_plot_data"](plot, projected["plot_t_ns"], projected["plot_period_ps"])
        self.assertEqual(plot.events[-1], (6, 6))
        functions["set_period_plot_data"](plot, [], [])
        self.assertEqual(plot.events[-1], (0, 0))
        self.assertEqual(plot.data["t_ns"].tolist(), [99, 100])
        self.assertEqual(plot.data["other"].tolist(), [7, 8])


class BindingCases(unittest.TestCase):
    """Static comparison of real wiring; these checks never execute Main or GUI definitions."""

    def test_producer_and_consumers_share_indices_and_native_algorithms(self):
        import ast
        from d1_under_test import root, evidence

        def read(relative):
            return ast.parse((root / relative).read_text(encoding="utf-8"))

        def original(name):
            return ast.parse((evidence / "inputs" / (name + ".baseline.py.txt")).read_text(encoding="utf-8"))

        def function(tree, name):
            return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)

        def dump(node):
            return ast.dump(node, include_attributes=False)

        def assignment(tree, name):
            return next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                        and any(ast.unparse(target) == name for target in node.targets))

        def call(tree, name):
            return [node for node in ast.walk(tree) if isinstance(node, ast.Call) and ast.unparse(node.func) == name]

        bert, old = read("src/pybert/models/bert.py"), original("bert")
        main, old_main = function(bert, "my_run_simulation"), function(old, "my_run_simulation")
        main_text = ast.unparse(main)
        self.assertLess(main_text.index("clock_info = new_clock_info"), main_text.index("if self.tx_sel"))
        self.assertIn("set_period_plot_data(self.plotdata, [], [])", main_text)
        self.assertIn("if rx_getwave_mode else 0", main_text)
        self.assertIn("['Reserved_Parameters', 'Ignore_Bits']", main_text)
        self.assertIn("consume_ami_clocks(clock_info, ffe_out, dfe.decide, _check_sim_status)", main_text)
        self.assertIn("finally:\n            self.ami_clock_info = clock_info", main_text)
        self.assertIn("main_postconditions_pending", main_text)
        self.assertLess(main_text.index("compute_com(self)"), main_text.index("run_status='completed'"))
        self.assertIn("modulation='NRZ' if mod_type == 0 else 'PAM4' if mod_type == 2 else 'unsupported'", main_text)
        self.assertNotIn("profile=", main_text)
        self.assertIn("clock_times = clock_info['sample_grid_times_s']", main_text)
        self.assertIn("selected = clock_info['analysis_sample_indices']", main_text)
        self.assertIn("_sample_times = t[selected]", main_text)
        self.assertIn("sig_samps = np.asarray(dfe_out)[selected]", main_text)
        self.assertEqual(sorted(map(dump, call(main, "run_ami_model"))),
                         sorted(map(dump, call(old_main, "run_ami_model"))))
        self.assertEqual(list(map(dump, call(main, "dfe.run_dfe"))), list(map(dump, call(old_main, "dfe.run_dfe"))))
        for name in ("clk_phase_ix", "pulse_resp_samps", "dec_lvls", "sigma"):
            self.assertEqual(dump(assignment(main, name)), dump(assignment(old_main, name)))
        for name in ("decoder.decode", "decoder_fec.decode"):
            self.assertEqual(list(map(dump, call(main, name))), list(map(dump, call(old_main, name))))
        viterbi = next(node for node in ast.walk(main) if isinstance(node, ast.If)
                       and ast.unparse(node.test) == "self.rx_use_viterbi")
        split = next(node for node in viterbi.body if isinstance(node, ast.If)
                     and ast.unparse(node.test) == "ami_getwave_clocks")
        old_viterbi = next(node for node in ast.walk(old_main) if isinstance(node, ast.If)
                           and ast.unparse(node.test) == "self.rx_use_viterbi")
        old_sampling = old_viterbi.body[1:]
        stop = next(i for i, node in enumerate(old_sampling)
                    if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "self.dbg_dict_viterbi")
        self.assertEqual(list(map(dump, split.orelse)), list(map(dump, old_sampling[:stop])))
        ber, old_ber = function(main, "calc_ber"), function(old_main, "calc_ber")
        for candidate in (ber, old_ber):
            start = candidate.body.index(assignment(candidate, "bits_tst"))
            candidate.body = candidate.body[start:]
        self.assertEqual(dump(ber), dump(old_ber))
        for name in ("getwave_parameters", "compute_com", "update_trellis", "update_eyes"):
            self.assertEqual(dump(function(bert, name)), dump(function(old, name)))

        update, old_update = function(bert, "update_results"), function(old, "update_results")
        update_text = ast.unparse(update)
        self.assertIn("clock_period_data(clock_info, t, t[1] - t[0])", update_text)
        self.assertIn("set_period_plot_data(self.plotdata, period_data['plot_t_ns'], period_data['plot_period_ps'])",
                      update_text)
        self.assertIn("set_period_plot_data(self.plotdata, t_ns_plot, ui_ests_plot)", update_text)
        for name in ("bin_centers", "clock_spec", "_f0", "spec_freqs", "ui_ests_plot"):
            old_assign = assignment(old_update, name)
            self.assertIn(dump(old_assign), [dump(node) for node in ast.walk(update)])
        native_interp = next(node for node in ast.walk(old_update) if isinstance(node, ast.If)
                             and ast.unparse(node.test) == "len_t > 1000" and "ui_ests_plot" in ast.unparse(node))
        self.assertIn(dump(native_interp), [dump(node) for node in ast.walk(update)])
        self.assertIn("ami_eye_data(clock_info, cropped, ignore_samps, height, y_max, calc_eye)", update_text)
        old_eye_start = max(i for i, node in enumerate(old_update.body) if isinstance(node, ast.Assign)
                            and ast.unparse(node.targets[0]) == "y_max")
        old_eye_stop = next(i for i, node in enumerate(old_update.body)
                           if "set_data('eye_index'" in ast.unparse(node))
        eye_branch = next(node for node in update.body if isinstance(node, ast.If)
                          and ast.unparse(node.test) == "ami_getwave_clocks" and "ami_eye_data" in ast.unparse(node))
        self.assertEqual(list(map(dump, eye_branch.orelse)),
                         list(map(dump, old_update.body[old_eye_start:old_eye_stop])))

        plot, old_plot = read("src/pybert/gui/plot.py"), original("plot")
        plot.body = [node for node in plot.body if not (isinstance(node, ast.ImportFrom)
                                                      and node.module == "utility.ami_clock")]
        plots = function(plot, "make_plots")
        plots.body = [node for node in plots.body if not (isinstance(node, ast.If)
                                                         and "period_t_ns" in ast.unparse(node.test))]
        for node in ast.walk(plot):
            if isinstance(node, ast.Constant) and node.value == "period_t_ns":
                node.value = "t_ns"
        self.assertEqual(dump(plot), dump(old_plot))
        eye = function(read("src/pybert/utility/sigproc.py"), "calc_eye")
        old_eye = function(original("sigproc"), "calc_eye")
        eye.args.kwonlyargs, eye.args.kw_defaults = [], []
        eye.body = [node for node in eye.body if not (isinstance(node, ast.If)
                                                     and ast.unparse(node.test) == "clock_indices is not None")]
        eye.body[0] = old_eye.body[0]
        self.assertEqual(dump(eye), dump(old_eye))
        self.assertNotIn("test_", (evidence / "d1_cases.py").name)
