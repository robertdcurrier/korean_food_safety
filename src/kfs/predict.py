#!/usr/bin/env python3
"""A forecast slot for each bay, filled for now by a synthetic model.

The point of this module is the shape of its output, not its skill.
``forecast(bay, today)`` returns the contract a real model must meet:

    {
      "model": "synthetic-climatology-v0",
      "issued_at": "2026-10-09",
      "synthetic": true,
      "horizon": [{"date", "p10", "p50", "p90", "level"} x 14],
      "season_outlook": {"first_favourable", "peak", "basis"}
    }

The synthetic model blends today's observed sea temperature toward a
south-coast climatology, lets rainfall relax toward its monthly mean,
assumes persistence for wind, and scores every future day with the
same index the environmental tab uses. It is deterministic (seeded
per bay) and tested. Replace this function with a fitted model and
nothing else in the pipeline changes.
"""
import datetime as dt
import math
import random

from kfs import env

MODEL_NAME = "synthetic-climatology-v0"
HORIZON_DAYS = 14

# Approximate south-coast monthly mean rainfall, mm per day.
CLIM_RAIN = {1: 1.2, 2: 1.5, 3: 2.5, 4: 3.5, 5: 3.5, 6: 6.0,
             7: 9.0, 8: 9.0, 9: 5.0, 10: 2.0, 11: 1.5, 12: 1.0}
CLIM_WIND = 4.0


def clim_sst(day_of_year):
    """South-coast sea-surface climatology: ~9.5 °C late Feb, ~24.5 Aug."""
    return 17.0 - 7.5 * math.cos(2 * math.pi * (day_of_year - 50) / 365)


def _date(today, offset):
    return dt.date.fromisoformat(today) + dt.timedelta(days=offset)


def project(bay, today, day):
    """Conditions summary expected `day` days ahead (synthetic)."""
    start = _date(today, 0)
    doy0 = start.timetuple().tm_yday
    anomaly = (bay.get("sst_now") or clim_sst(doy0)) - clim_sst(doy0)
    decay = math.exp(-day / 10.0)
    target = _date(today, day)
    sst = clim_sst(target.timetuple().tm_yday) + anomaly * decay
    week_ago = clim_sst(_date(today, day - 7).timetuple().tm_yday)
    week_ago += anomaly * math.exp(-max(day - 7, 0) / 10.0)
    relax = math.exp(-day / 7.0)
    rain = (bay.get("rain_7d") or 0.0) * relax
    rain += CLIM_RAIN[target.month] * 7 * (1 - relax)
    wind = (bay.get("wind_7d_mean") or CLIM_WIND) * relax
    wind += CLIM_WIND * (1 - relax)
    return {"sst_now": round(sst, 1), "sst_delta_7d": round(sst - week_ago, 1),
            "rain_7d": round(rain, 1), "wind_7d_mean": round(wind, 1)}


def _level(value):
    if value >= 0.65:
        return "elevated"
    if value >= 0.40:
        return "moderate"
    return "low"


def horizon(bay, today):
    """Fourteen daily points with a widening uncertainty band."""
    rng = random.Random(bay["id"])
    points = []
    for day in range(1, HORIZON_DAYS + 1):
        summary = project(bay, today, day)
        month = _date(today, day).month
        p50, _, _ = env.score(summary, month)
        p50 = min(1.0, max(0.0, p50 + rng.uniform(-0.02, 0.02)))
        spread = 0.05 + 0.012 * day
        points.append({
            "date": _date(today, day).isoformat(),
            "p10": round(max(0.0, p50 - spread), 2),
            "p50": round(p50, 2),
            "p90": round(min(1.0, p50 + spread), 2),
            "level": _level(p50),
        })
    return points


def season_outlook(today):
    """From climatology alone: next day the index reaches 'moderate'
    while the sea is warming, and the day it peaks, within a year.
    Illustrative, not a forecast. The warming requirement keeps a
    cooling autumn sea passing down through the temperature window
    from counting as a bloom window."""
    best = (0.0, None)
    first = None
    for day in range(1, 366):
        target = _date(today, day)
        doy = target.timetuple().tm_yday
        summary = {"sst_now": clim_sst(doy),
                   "sst_delta_7d": clim_sst(doy) - clim_sst(doy - 7),
                   "rain_7d": CLIM_RAIN[target.month] * 7,
                   "wind_7d_mean": CLIM_WIND}
        value, _, _ = env.score(summary, target.month)
        warming = summary["sst_delta_7d"] > 0
        if first is None and value >= 0.40 and warming:
            first = target.isoformat()
        if value > best[0]:
            best = (value, target.isoformat())
    return {"first_favourable": first, "peak": best[1],
            "peak_index": round(best[0], 2),
            "basis": "climatology only; illustrative"}


def forecast(bay, today):
    """The contract. Swap the body for a real model; keep the keys."""
    return {
        "model": MODEL_NAME,
        "issued_at": today,
        "synthetic": True,
        "horizon": horizon(bay, today),
        "season_outlook": season_outlook(today),
    }


def add_forecasts(env_payload):
    """Attach a forecast to every bay in an env payload (in place)."""
    today = env_payload["today"]
    for bay in env_payload["bays"]:
        bay["forecast"] = forecast(bay, today)
    return env_payload
