#!/usr/bin/env python3
"""Claude's one step for the environmental tab: a bilingual advisory
per bay that combines the conditions index with any seafood records
from MFDS in the same province, with an explicit confidence.

Cached per bay per day in data/env_advisory.json.
"""
import json
import re
from typing import Literal

import anthropic
from pydantic import BaseModel

from kfs.enrich import MODEL, load_json, save_json

SEAFOOD = re.compile(
    r"수산|패류|어패|굴|홍합|바지락|조개|가리비|피조개|멍게|미더덕|젓갈|해산|"
    r"shellfish|oyster|mussel|clam|seafood", re.I)


class Advisory(BaseModel):
    id: str
    advisory_ko: str
    advisory_en: str
    confidence: Literal["low", "medium", "high"]
    confidence_why_ko: str
    confidence_why_en: str


class AdvisoryBatch(BaseModel):
    items: list[Advisory]


SYSTEM = """You are a bilingual (Korean/English) shellfish-safety
analyst writing short public advisories for a proof-of-concept tool.

Input: for each bay, a conditions index for paralytic shellfish
poisoning (PSP) computed from weather and sea-surface temperature,
with its factors, plus any recent MFDS seafood enforcement records
from the same province.

Rules:
- The index measures whether conditions favour an Alexandrium bloom.
  It is NOT a toxin measurement. Never state or imply that shellfish
  are toxic or safe. Say "conditions", "favourable", "monitor".
- Two or three sentences per language, plain, for a shopper or a
  fisheries officer. Name the bay. Mention the season honestly: the
  Korean PSP season is February to June; outside it say so.
- Mention an MFDS record only if it is seafood-related and relevant;
  otherwise say there are no related MFDS records.
- confidence reflects the evidence, not the risk: a weather proxy
  alone is low; corroborating MFDS records raise it.
- Do not invent data. Use only the numbers given."""


def seafood_records(records, sido):
    """MFDS records in this province that look seafood-related."""
    hits = []
    for rec in records:
        if rec.get("sido") != sido:
            continue
        text = " ".join([rec.get("product_ko", ""),
                         rec.get("category_ko", ""),
                         rec.get("reason_ko", ""),
                         rec.get("product_en", "")])
        if SEAFOOD.search(text):
            hits.append({k: rec.get(k, "") for k in (
                "id", "source", "product_ko", "product_en",
                "reason_ko", "reason_en", "date", "severity")})
    return hits[:5]


def _bay_input(bay, records):
    keys = ("id", "name_ko", "name_en", "sido", "sst_now", "sst_delta_7d",
            "rain_7d", "wind_7d_mean", "score", "level", "factors")
    item = {k: bay.get(k) for k in keys}
    item["mfds_seafood_records"] = seafood_records(records, bay["sido"])
    return item


def advise(env, records, cache_path, log=print):
    """Return {bay_id: advisory}. One call for all bays not yet cached."""
    cache = load_json(cache_path, {})
    day = env["today"]
    todo = [b for b in env["bays"]
            if cache.get(b["id"], {}).get("day") != day]
    log(f"advisory: {len(env['bays']) - len(todo)} cached for {day}, "
        f"{len(todo)} to send")
    if not todo:
        return cache
    payload = json.dumps(
        {"today": day, "in_season": env["in_season"],
         "bays": [_bay_input(b, records) for b in todo]},
        ensure_ascii=False)
    response = anthropic.Anthropic().messages.parse(
        model=MODEL, max_tokens=16000, system=SYSTEM,
        messages=[{"role": "user", "content": payload}],
        output_format=AdvisoryBatch)
    parsed = response.parsed_output
    if response.stop_reason == "refusal" or parsed is None:
        raise RuntimeError(f"no advisory (stop_reason="
                           f"{response.stop_reason})")
    for item in parsed.items:
        cache[item.id] = dict(item.model_dump(), day=day)
    save_json(cache_path, cache)
    log(f"advisory: tokens in {response.usage.input_tokens}, "
        f"out {response.usage.output_tokens}")
    return cache
