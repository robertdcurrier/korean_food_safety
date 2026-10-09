#!/usr/bin/env python3
"""Environmental conditions for shellfish bays: a PSP proof of concept.

Paralytic shellfish poisoning in Korea comes from spring blooms of
Alexandrium along the south coast as the sea warms through roughly
8–18 °C, helped by rainfall runoff and calm, stratified water. Weather
cannot say shellfish are toxic. It can say conditions favour a bloom.
This module computes exactly that, as a deterministic, tested index,
from Open-Meteo (free, keyless, CC BY 4.0). It is a stand-in for the
KHOA buoys, KMA rainfall and NIFS bulletins a real system would use.
"""
import datetime as dt
import json
import urllib.parse
import urllib.request

MARINE = "https://marine-api.open-meteo.com/v1/marine"
FORECAST = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "korean-food-safety-demo/0.1"
PAST_DAYS = 7

# Approximate bay centres on the south coast. Corrected by the expert.
BAYS = [
    {"id": "jinhae", "name_ko": "진해만", "name_en": "Jinhae Bay",
     "sido": "경상남도", "lat": 35.08, "lon": 128.62},
    {"id": "masan", "name_ko": "마산만", "name_en": "Masan Bay",
     "sido": "경상남도", "lat": 35.17, "lon": 128.58},
    {"id": "geoje", "name_ko": "거제 북안", "name_en": "Geoje (north)",
     "sido": "경상남도", "lat": 34.95, "lon": 128.60},
    {"id": "tongyeong", "name_ko": "통영", "name_en": "Tongyeong",
     "sido": "경상남도", "lat": 34.80, "lon": 128.42},
    {"id": "goseong", "name_ko": "고성 자란만", "name_en": "Jaran Bay",
     "sido": "경상남도", "lat": 34.93, "lon": 128.30},
    {"id": "sacheon", "name_ko": "사천만", "name_en": "Sacheon Bay",
     "sido": "경상남도", "lat": 34.93, "lon": 128.05},
    {"id": "namhae", "name_ko": "남해 강진만", "name_en": "Gangjin Bay",
     "sido": "경상남도", "lat": 34.83, "lon": 127.95},
    {"id": "yeosu", "name_ko": "여수 가막만", "name_en": "Gamak Bay",
     "sido": "전라남도", "lat": 34.68, "lon": 127.68},
]

WEIGHTS = {"sst": 0.35, "trend": 0.20, "rain": 0.20, "calm": 0.10,
           "season": 0.15}


def _get(url, params, timeout=30):
    req = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_bay(bay):
    """Two Open-Meteo calls for one bay. Returns raw hourly/daily dicts."""
    common = {"latitude": bay["lat"], "longitude": bay["lon"],
              "timezone": "Asia/Seoul", "past_days": PAST_DAYS,
              "forecast_days": 1}
    marine = _get(MARINE, dict(
        common, hourly="sea_surface_temperature,wave_height"))
    weather = _get(FORECAST, dict(
        common, hourly="wind_speed_10m", wind_speed_unit="ms",
        daily="precipitation_sum,temperature_2m_max"))
    return marine, weather


def daily_means(times, values):
    """Hourly series -> ordered list of (date, mean) ignoring nulls."""
    buckets = {}
    for stamp, value in zip(times, values):
        if value is None:
            continue
        buckets.setdefault(stamp[:10], []).append(value)
    return [(day, sum(v) / len(v)) for day, v in sorted(buckets.items())]


def summarize(marine, weather, today):
    """Reduce raw series to the handful of numbers the index uses."""
    hourly = marine["hourly"]
    sst_days = daily_means(hourly["time"], hourly["sea_surface_temperature"])
    past = [d for d in sst_days if d[0] < today] or sst_days
    sst_now = next((v for v in reversed(hourly["sea_surface_temperature"])
                    if v is not None), None)
    wave = next((v for v in reversed(hourly["wave_height"])
                 if v is not None), None)
    wind = [v for v in weather["hourly"]["wind_speed_10m"]
            if v is not None]
    daily = weather["daily"]
    rain = [r or 0.0 for r, d in zip(daily["precipitation_sum"],
                                      daily["time"]) if d < today]
    return {
        "sst_now": round(sst_now, 1) if sst_now is not None else None,
        "sst_delta_7d": round(past[-1][1] - past[0][1], 1)
        if len(past) > 1 else 0.0,
        "sst_daily": [[d, round(v, 1)] for d, v in sst_days],
        "wave_now": wave,
        "rain_7d": round(sum(rain), 1),
        "rain_daily": [[d, r or 0.0] for d, r in
                       zip(daily["time"], daily["precipitation_sum"])],
        "wind_7d_mean": round(sum(wind) / len(wind), 1) if wind else None,
        "air_tmax": daily["temperature_2m_max"][-1],
    }


def factor_sst(temp):
    if temp is None:
        return 0.0
    if 12 <= temp <= 16:
        return 1.0
    if 8 <= temp < 12 or 16 < temp <= 18:
        return 0.6
    if 6 <= temp < 8 or 18 < temp <= 20:
        return 0.2
    return 0.0


def factor_trend(delta):
    if delta > 1.0:
        return 1.0
    if delta > 0.3:
        return 0.6
    return 0.2


def factor_rain(total):
    if total > 50:
        return 1.0
    if total > 20:
        return 0.6
    if total > 5:
        return 0.3
    return 0.0


def factor_calm(wind):
    if wind is None:
        return 0.5
    if wind < 3:
        return 1.0
    if wind < 5:
        return 0.6
    return 0.2


def factor_season(month):
    if 2 <= month <= 6:
        return 1.0
    if month in (1, 7):
        return 0.5
    return 0.2


def score(summary, month):
    """Weighted 0–1 index and its factors. A POC heuristic, not a model."""
    factors = {
        "sst": factor_sst(summary["sst_now"]),
        "trend": factor_trend(summary["sst_delta_7d"]),
        "rain": factor_rain(summary["rain_7d"]),
        "calm": factor_calm(summary["wind_7d_mean"]),
        "season": factor_season(month),
    }
    total = sum(WEIGHTS[k] * v for k, v in factors.items())
    if total >= 0.65:
        level = "elevated"
    elif total >= 0.40:
        level = "moderate"
    else:
        level = "low"
    return round(total, 2), level, factors


def assess_all(log=print, today=None):
    """Fetch and score every bay. Returns the env payload."""
    today = today or dt.date.today().isoformat()
    month = int(today[5:7])
    bays = []
    for bay in BAYS:
        marine, weather = fetch_bay(bay)
        summary = summarize(marine, weather, today)
        total, level, factors = score(summary, month)
        bays.append(dict(bay, **summary, score=total, level=level,
                         factors=factors))
        log(f"env: {bay['name_ko']} sst={summary['sst_now']} "
            f"rain7={summary['rain_7d']} -> {level} ({total})")
    return {
        "fetched_at": dt.datetime.now().astimezone().isoformat(
            timespec="minutes"),
        "today": today,
        "in_season": 2 <= month <= 6,
        "source": "Open-Meteo (open-meteo.com), CC BY 4.0",
        "weights": WEIGHTS,
        "bays": bays,
    }
