#!/usr/bin/env python3
"""Command line: fetch -> enrich -> geocode -> build, or all at once.

    python -m kfs all            # whole pipeline
    python -m kfs fetch          # MFDS only
    python -m kfs enrich --max 40
    python -m kfs env            # weather/sea conditions + advisories
    python -m kfs build          # re-render HTML from cached data
"""
import argparse
import json
import os
import sys
from pathlib import Path

from kfs import enrich as enrich_mod
from kfs import advisory, env, geocode, mfds, predict, report

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
RECORDS = DATA / "records.json"
ENRICHED = DATA / "enriched.json"
GEOCACHE = DATA / "geocache.json"
PROVINCES = DATA / "korea_provinces.geojson"
ENV = DATA / "env.json"
ENV_ADVISORY = DATA / "env_advisory.json"
TEMPLATE = ROOT / "templates" / "report.html"
OUTPUT = ROOT / "output" / "index.html"


def load_dotenv(path=ROOT / ".env"):
    """Minimal .env loader so students need no extra package."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            print(f"warning: {path.name} line has no NAME=value form; "
                  f"expected e.g. ANTHROPIC_API_KEY=sk-ant-...")
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def cmd_fetch(args):
    RAW.mkdir(parents=True, exist_ok=True)
    key = mfds.api_key()
    mode = "sample key" if key == mfds.SAMPLE_KEY else "personal key"
    print(f"fetch: using {mode}")
    records = []
    for service in mfds.SERVICES:
        rows = mfds.fetch_all(service, key, max_rows=args.max)
        enrich_mod.save_json(RAW / f"{service}.json", rows)
        records.extend(mfds.normalize_all(service, rows))
    enrich_mod.save_json(RECORDS, records)
    print(f"fetch: {len(records)} records -> {RECORDS.relative_to(ROOT)}")


def _records():
    if not RECORDS.exists():
        sys.exit("No data/records.json yet. Run: python -m kfs fetch")
    return enrich_mod.load_json(RECORDS, [])


def cmd_enrich(args):
    if not enrich_mod.has_credentials():
        print("enrich: no Anthropic credential found "
              "(ANTHROPIC_API_KEY). Skipping; report will be "
              "Korean-only and unclassified.")
        return
    enrich_mod.enrich(_records(), ENRICHED, max_records=args.max)


def cmd_geocode(args):
    records = geocode.geocode_records(_records(), GEOCACHE)
    enrich_mod.save_json(RECORDS, records)


def cmd_env(args):
    """Fetch Open-Meteo for the eight bays, score, then ask Claude."""
    try:
        payload = env.assess_all()
    except Exception as exc:  # keep the last good file on a bad network
        print(f"env: fetch failed ({exc}); keeping previous data/env.json")
        return
    predict.add_forecasts(payload)
    enrich_mod.save_json(ENV, payload)
    print(f"env: {len(payload['bays'])} bays, synthetic forecasts "
          f"attached -> {ENV.relative_to(ROOT)}")
    if not enrich_mod.has_credentials():
        print("env: no Anthropic credential; skipping advisories")
        return
    advisory.advise(payload, _records(), ENV_ADVISORY)


def cmd_build(args):
    records = _records()
    enriched = enrich_mod.load_json(ENRICHED, {})
    env_data = enrich_mod.load_json(ENV, None)
    advisories = enrich_mod.load_json(ENV_ADVISORY, {})
    meta = {
        "key_mode": "sample" if mfds.api_key() == mfds.SAMPLE_KEY
        else "personal",
        "model": enrich_mod.MODEL if enriched else None,
        "enriched_count": sum(1 for r in records if r["id"] in enriched),
    }
    payload = report.build_payload(records, enriched, meta,
                                   env_data, advisories)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    report.render(TEMPLATE, OUTPUT, payload, report.load_geojson(PROVINCES))
    print(f"build: {len(records)} records, "
          f"{meta['enriched_count']} enriched -> {OUTPUT}")
    print(f"open {OUTPUT}")


def cmd_all(args):
    cmd_fetch(args)
    cmd_enrich(args)
    cmd_geocode(args)
    cmd_env(args)
    cmd_build(args)


def main(argv=None):
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="kfs", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, func in (("fetch", cmd_fetch), ("enrich", cmd_enrich),
                       ("geocode", cmd_geocode), ("env", cmd_env),
                       ("build", cmd_build), ("all", cmd_all)):
        cmd = sub.add_parser(name)
        cmd.add_argument("--max", type=int, default=None,
                         help="cap rows per service (fetch) or records "
                              "sent to Claude (enrich)")
        cmd.set_defaults(func=func)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
