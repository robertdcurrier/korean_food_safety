#!/usr/bin/env python3
"""Turn Korean business addresses into map coordinates.

Two deliberate simplifications keep this a demo:

* We geocode at district level (시/도 + 시/군/구), not the street. That
  is enough to see regional patterns and it keeps the number of
  lookups small (a few hundred distinct districts at most).
* We use OpenStreetMap's Nominatim, which needs no key, at one request
  per second, and cache every answer in data/geocache.json so re-runs
  cost nothing. Kakao or Naver geocoders are more accurate for Korea
  but need a key; swapping them in is a good exercise.
"""
import json
import re
import time
import urllib.parse
import urllib.request

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "korean-food-safety-demo/0.1 (github.com/robertdcurrier)"

SIDO_RE = re.compile(r"(특별자치도|특별자치시|특별시|광역시|도|시)$")
SIGUNGU_RE = re.compile(r"(시|군|구)$")

# Short province names that appear in older address strings.
SIDO_SHORT = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "세종": "세종특별자치시", "경기": "경기도",
    "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도",
    "경남": "경상남도", "제주": "제주특별자치도",
}


def split_address(address):
    """Return (sido, sigungu) from a Korean address, '' when unknown."""
    tokens = (address or "").split()
    if not tokens:
        return "", ""
    sido = SIDO_SHORT.get(tokens[0], tokens[0])
    if not SIDO_RE.search(sido):
        return "", ""
    sigungu = ""
    if len(tokens) > 1 and SIGUNGU_RE.search(tokens[1]):
        sigungu = tokens[1]
    return sido, sigungu


def load_cache(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return {}


def save_cache(path, cache):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(cache, handle, ensure_ascii=False, indent=1, sort_keys=True)


def lookup(query, timeout=30):
    """One Nominatim call. Returns [lat, lon] or None."""
    params = urllib.parse.urlencode({
        "q": query, "format": "json", "limit": 1,
        "countrycodes": "kr", "accept-language": "ko",
    })
    req = urllib.request.Request(
        f"{NOMINATIM}?{params}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        hits = json.loads(resp.read().decode("utf-8"))
    if not hits:
        return None
    return [float(hits[0]["lat"]), float(hits[0]["lon"])]


def geocode_records(records, cache_path, pause=1.1, log=print):
    """Attach sido/sigungu/lat/lon to each record, using the cache."""
    cache = load_cache(cache_path)
    misses = 0
    for rec in records:
        sido, sigungu = split_address(rec.get("address_ko", ""))
        rec["sido"] = sido
        rec["sigungu"] = sigungu
        query = f"{sido} {sigungu}".strip()
        if not query:
            rec["lat"] = rec["lon"] = None
            continue
        if query not in cache:
            try:
                cache[query] = lookup(query)
            except Exception as exc:  # network hiccup: keep going
                log(f"geocode failed for {query!r}: {exc}")
                cache[query] = None
            misses += 1
            save_cache(cache_path, cache)
            time.sleep(pause)
        point = cache.get(query)
        rec["lat"], rec["lon"] = point if point else (None, None)
    log(f"geocode: {len(cache)} cached districts, {misses} new lookups")
    return records
