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
