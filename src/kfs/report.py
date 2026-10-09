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


def build_payload(records, enriched, meta):
    rows = [merge(r, enriched.get(r["id"])) for r in records]
    rows.sort(key=lambda r: r.get("date", ""), reverse=True)
    return {
        "generated": dt.datetime.now().astimezone().isoformat(
            timespec="minutes"),
        "services": SERVICES,
        "meta": meta,
        "records": rows,
    }


def render(template_path, out_path, payload):
    with open(template_path, encoding="utf-8") as handle:
        template = handle.read()
    if PLACEHOLDER not in template:
        raise RuntimeError(f"{template_path} lacks {PLACEHOLDER}")
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace(PLACEHOLDER, blob)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(html)
    return out_path
