#!/usr/bin/env python3
"""Merge records, enrichment and coordinates into one local HTML file.

The template in templates/report.html is a complete page with a single
placeholder for the data. Everything is embedded, so the result opens
from the file system with no server and can be emailed or committed.
"""
import datetime as dt
import json

from kfs.mfds import SERVICES

PLACEHOLDER = "/*__DATA__*/null"
GEO_PLACEHOLDER = "/*__GEO__*/null"

DEFAULTS = {
    "product_en": "", "company_en": "", "reason_en": "",
    "summary_ko": "", "summary_en": "",
    "hazard": "unclassified", "severity": "unknown",
    "severity_why_en": "", "severity_why_ko": "",
}


def merge(record, enriched):
    """One flat dict per record with AI fields present or defaulted."""
    out = dict(record)
    out.update(DEFAULTS)
    if enriched:
        out.update({k: v for k, v in enriched.items() if k != "id"})
        out["enriched"] = True
    else:
        out["enriched"] = False
    return out


def attach_advisories(env_data, advisories):
    """Copy each bay's cached advisory onto the bay dict, if any."""
    if not env_data:
        return None
    out = dict(env_data)
    out["bays"] = [dict(b, advisory=advisories.get(b["id"]))
                   for b in env_data.get("bays", [])]
    return out


def build_payload(records, enriched, meta, env_data=None,
                  advisories=None):
    rows = [merge(r, enriched.get(r["id"])) for r in records]
    rows.sort(key=lambda r: r.get("date", ""), reverse=True)
    return {
        "generated": dt.datetime.now().astimezone().isoformat(
            timespec="minutes"),
        "services": SERVICES,
        "meta": meta,
        "records": rows,
        "env": attach_advisories(env_data, advisories or {}),
    }


def _embed(text, placeholder, obj):
    """Replace one placeholder with JSON safe inside a <script> tag."""
    if placeholder not in text:
        raise RuntimeError(f"template lacks {placeholder}")
    blob = json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")
    return text.replace(placeholder, blob)


def load_geojson(path):
    """Province outlines; None if the file is missing (map still works)."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None


def render(template_path, out_path, payload, geojson=None):
    with open(template_path, encoding="utf-8") as handle:
        template = handle.read()
    html = _embed(template, PLACEHOLDER, payload)
    html = _embed(html, GEO_PLACEHOLDER, geojson)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(html)
    return out_path
