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
