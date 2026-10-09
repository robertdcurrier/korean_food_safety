#!/usr/bin/env python3
"""Thin client for the MFDS 식품안전나라 open API.

URL anatomy. One GET, no headers, the key rides in the path:

    https://openapi.foodsafetykorea.go.kr/api/
        {key}/{service}/json/{start}/{end}

The literal key ``sample`` works without registration but returns the
same five rows whatever range you ask for. A free personal key returns
up to 1000 rows per call. Details and field dictionary: docs/MFDS_API.md
"""
import json
import os
import re
import time
import urllib.request

BASE = "https://openapi.foodsafetykorea.go.kr/api"
SAMPLE_KEY = "sample"
PAGE_SIZE = 1000
USER_AGENT = "korean-food-safety-demo/0.1"

SERVICES = {
    "I0490": {
        "kind": "recall",
        "name_ko": "회수·판매중지 정보",
        "name_en": "Recalls and sales suspensions",
    },
    "I2620": {
        "kind": "inspection",
        "name_ko": "검사부적합(국내)",
        "name_en": "Domestic inspection non-conformities",
    },
}

_DATE = re.compile(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})")


class MfdsError(RuntimeError):
    """Raised when the API answers with an error code."""


def api_key():
    """Personal key from the environment, else the public sample key."""
    return os.environ.get("MFDS_API_KEY") or SAMPLE_KEY


def build_url(service, start, end, key=None):
    """Compose the request URL for one page of one service."""
    key = key or api_key()
    return f"{BASE}/{key}/{service}/json/{start}/{end}"


def _get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_page(service, start, end, key=None):
    """Return the body dict for one page: total_count, RESULT, row."""
    data = _get_json(build_url(service, start, end, key))
    body = data.get(service)
    if body is None:
        # Error answers are not wrapped in the service id.
        raise MfdsError(f"{service}: {data.get('RESULT', data)}")
    code = body.get("RESULT", {}).get("CODE", "")
    if code == "INFO-200":
        return {"total_count": "0", "row": [], "RESULT": body["RESULT"]}
    if not code.startswith("INFO-000"):
        raise MfdsError(f"{service}: {body.get('RESULT')}")
    return body


def fetch_all(service, key=None, max_rows=None, pause=0.5, log=print):
    """Page through a service until total_count (or max_rows) rows."""
    key = key or api_key()
    first = fetch_page(service, 1, PAGE_SIZE, key)
    total = int(first.get("total_count") or 0)
    rows = list(first.get("row") or [])
    log(f"{service}: total_count={total}, received {len(rows)}")
    if key == SAMPLE_KEY:
        log(f"{service}: sample key returns a fixed page; stopping")
        return rows[:max_rows] if max_rows else rows
    limit = min(total, max_rows) if max_rows else total
    while len(rows) < limit:
        start = len(rows) + 1
        end = min(start + PAGE_SIZE - 1, limit)
        time.sleep(pause)
        got = fetch_page(service, start, end, key).get("row") or []
        if not got:
            break
        rows.extend(got)
        log(f"{service}: {len(rows)}/{limit}")
    return rows[:limit]


def clean_date(text):
    """'2026.3.5', '2026-03-05 17:52:53', '(소비기한) 2031.8.13' -> ISO."""
    match = _DATE.search(text or "")
    if not match:
        return ""
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def _text(row, field):
    return (row.get(field) or "").strip()


def normalize(service, row, index=0):
    """Map one raw MFDS row onto the unified record schema."""
    kind = SERVICES[service]["kind"]
    seq = _text(row, "RTRVLDSUSE_SEQ")
    if not seq:
        seq = f"{_text(row, 'PRDLST_REPORT_NO')}-{index}"
    record = {
        "id": f"{service}-{seq}",
        "source": kind,
        "service": service,
        "product_ko": _text(row, "PRDTNM"),
        "company_ko": _text(row, "BSSHNM"),
        "address_ko": _text(row, "ADDR"),
        "category_ko": _text(row, "PRDLST_CD_NM"),
        "date": clean_date(row.get("CRET_DTM")),
        "mfg_date": clean_date(row.get("MNFDT")),
        "expiry": clean_date(row.get("DISTBTMLMT")),
        "license_no": _text(row, "LCNS_NO"),
        "report_no": _text(row, "PRDLST_REPORT_NO"),
        "barcode": _text(row, "BRCDNO"),
        "unit": _text(row, "FRMLCUNIT"),
        "grade": "",
        "method_ko": "",
        "image": "",
        "test_item_ko": "",
        "test_result": "",
        "standard": "",
        "agency_ko": "",
    }
    if kind == "recall":
        record["reason_ko"] = _text(row, "RTRVLPRVNS")
        record["grade"] = _text(row, "RTRVL_GRDCD_NM")
        record["method_ko"] = _text(row, "RTRVLPLANDOC_RTRVLMTHD")
        record["image"] = _text(row, "IMG_FILE_PATH")
    else:
        item = _text(row, "TEST_ITMNM")
        result = _text(row, "TESTANALS_RSLT")
        standard = _text(row, "STDR_STND")
        record["reason_ko"] = f"{item}: {result} (기준 {standard})"
        record["test_item_ko"] = item
        record["test_result"] = result
        record["standard"] = standard
        record["agency_ko"] = _text(row, "INSTT_NM")
    return record


def normalize_all(service, rows):
    """Normalize a list of raw rows, dropping exact duplicate ids."""
    seen = set()
    out = []
    for i, row in enumerate(rows):
        rec = normalize(service, row, i)
        if rec["id"] in seen:
            continue
        seen.add(rec["id"])
        out.append(rec)
    return out
