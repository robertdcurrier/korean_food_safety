#!/usr/bin/env python3
"""Offline tests for the synthetic forecast and its contract."""
import unittest

from kfs import predict

BAY = {"id": "jinhae", "sst_now": 23.8, "sst_delta_7d": -0.8,
       "rain_7d": 1.0, "wind_7d_mean": 4.7}
KEYS = {"model", "issued_at", "synthetic", "horizon", "season_outlook"}


class ContractTests(unittest.TestCase):
    def test_shape(self):
        fc = predict.forecast(BAY, "2026-10-09")
        self.assertEqual(set(fc), KEYS)
        self.assertTrue(fc["synthetic"])
        self.assertEqual(len(fc["horizon"]), 14)
        for pt in fc["horizon"]:
            self.assertEqual(set(pt), {"date", "p10", "p50", "p90", "level"})
            self.assertLessEqual(pt["p10"], pt["p50"])
            self.assertLessEqual(pt["p50"], pt["p90"])
            self.assertIn(pt["level"], ("low", "moderate", "elevated"))
        self.assertEqual(fc["horizon"][0]["date"], "2026-10-10")

    def test_deterministic(self):
        a = predict.forecast(BAY, "2026-10-09")
        b = predict.forecast(dict(BAY), "2026-10-09")
        self.assertEqual(a, b)

    def test_october_stays_low(self):
        fc = predict.forecast(BAY, "2026-10-09")
        self.assertTrue(all(p["level"] == "low" for p in fc["horizon"]))

    def test_spring_rises(self):
        spring = dict(BAY, sst_now=11.5, sst_delta_7d=0.9, rain_7d=30.0,
                      wind_7d_mean=2.5)
        fc = predict.forecast(spring, "2026-04-01")
        self.assertTrue(any(p["level"] != "low" for p in fc["horizon"]))

    def test_season_outlook_is_in_spring(self):
        out = predict.season_outlook("2026-10-09")
        self.assertIsNotNone(out["first_favourable"])
        first_month = int(out["first_favourable"][5:7])
        self.assertTrue(2 <= first_month <= 6, out)
        month = int(out["peak"][5:7])
        self.assertTrue(2 <= month <= 6, out)

    def test_climatology_bounds(self):
        vals = [predict.clim_sst(d) for d in range(1, 366)]
        self.assertAlmostEqual(min(vals), 9.5, places=1)
        self.assertAlmostEqual(max(vals), 24.5, places=1)


if __name__ == "__main__":
    unittest.main()
