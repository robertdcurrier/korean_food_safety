#!/usr/bin/env python3
"""Offline tests for the PSP conditions index. No network."""
import unittest

from kfs import env

SPRING = {"sst_now": 14.2, "sst_delta_7d": 1.4, "rain_7d": 62.0,
          "wind_7d_mean": 2.4}
OCTOBER = {"sst_now": 23.9, "sst_delta_7d": -0.3, "rain_7d": 17.9,
           "wind_7d_mean": 4.1}


class BayTests(unittest.TestCase):
    def test_eight_bays_in_korea(self):
        self.assertEqual(len(env.BAYS), 8)
        for bay in env.BAYS:
            self.assertTrue(33.0 < bay["lat"] < 38.7, bay)
            self.assertTrue(125.0 < bay["lon"] < 130.0, bay)
        self.assertEqual(len({b["id"] for b in env.BAYS}), 8)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(env.WEIGHTS.values()), 1.0)


class ScoreTests(unittest.TestCase):
    def test_spring_bloom_conditions_are_elevated(self):
        total, level, factors = env.score(SPRING, month=4)
        self.assertEqual(level, "elevated")
        self.assertEqual(factors["sst"], 1.0)
        self.assertEqual(factors["season"], 1.0)
        self.assertGreaterEqual(total, 0.65)

    def test_warm_october_is_low(self):
        total, level, factors = env.score(OCTOBER, month=10)
        self.assertEqual(level, "low")
        self.assertEqual(factors["sst"], 0.0)
        self.assertLess(total, 0.40)

    def test_missing_sst_does_not_crash(self):
        total, level, _ = env.score(dict(SPRING, sst_now=None), month=4)
        self.assertIn(level, ("low", "moderate", "elevated"))

    def test_daily_means_skip_nulls(self):
        times = ["2026-04-01T00:00", "2026-04-01T01:00",
                 "2026-04-02T00:00"]
        means = env.daily_means(times, [10.0, None, 12.0])
        self.assertEqual(means, [("2026-04-01", 10.0),
                                 ("2026-04-02", 12.0)])


if __name__ == "__main__":
    unittest.main()
