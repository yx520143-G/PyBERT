"""Guarded D1 software cases; intentionally outside ordinary pytest discovery."""

import unittest

from d1_under_test import functions, np


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
