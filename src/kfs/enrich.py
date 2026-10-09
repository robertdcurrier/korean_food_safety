#!/usr/bin/env python3
"""Enrich MFDS records with Claude.

This is the one place the back end uses AI, and it is used only for
what a rule cannot do: translating Korean product names and reasons
into natural English, classifying the hazard, judging severity, and
writing a one-sentence plain-language summary in both languages.

Design choices worth copying:

* Structured output. Claude fills a Pydantic schema, so the report
  code never parses prose.
* Batches of records per call, not one call per record.
* A cache keyed by record id in data/enriched.json. Re-running only
  sends records Claude has not seen, so the run is idempotent and
  cheap.
* Refusals and errors are handled, never silently dropped.
"""
import json
import os
from typing import Literal

import anthropic
from pydantic import BaseModel

MODEL = os.environ.get("KFS_MODEL", "claude-opus-5-5")
BATCH_SIZE = 20

Hazard = Literal[
    "microbiological", "chemical_residue", "heavy_metal", "foreign_matter",
    "allergen_labeling", "unapproved_ingredient", "additive_violation",
    "quality_spec", "labeling_other", "other",
]
Severity = Literal["high", "medium", "low"]


class Enriched(BaseModel):
    id: str
    product_en: str
    company_en: str
    reason_en: str
    summary_ko: str
    summary_en: str
    hazard: Hazard
    severity: Severity
    severity_why_en: str
    severity_why_ko: str


class EnrichedBatch(BaseModel):
    items: list[Enriched]


SYSTEM = """You are a bilingual (Korean/English) food-safety analyst
helping make public MFDS (식품의약품안전처) enforcement records readable.

For each input record produce one output item with the same id.

Translation: product_en, company_en and reason_en are natural English.
Keep company names as romanized proper nouns, with a short English
gloss only when it helps (e.g. "Saengsaeng Dream Co., Ltd.").

hazard: choose the single best category.
  microbiological      pathogens, coliforms, total bacterial count
  chemical_residue     pesticide or veterinary drug residues
  heavy_metal          lead, cadmium, mercury, arsenic, tin
  foreign_matter       metal, glass, plastic, insects, other 이물
  allergen_labeling    undeclared or mislabelled allergens
  unapproved_ingredient  parts or substances not allowed as food
                       (e.g. aloe skin/latex, unregistered raw materials)
  additive_violation   preservatives, sweeteners, colours over limits
                       or not permitted for that food type
  quality_spec         composition or quality limits (moisture, acid
                       value, peroxide value, net weight)
  labeling_other       labelling or date-marking faults, no direct hazard
  other                anything else

severity: a consumer-health judgement, not a legal one.
  high    pathogens, toxins, undeclared allergens, sharp or hard
          foreign matter, banned substances, large heavy-metal
          exceedances, recall grade 1등급
  medium  residue or additive limits exceeded, moderate heavy-metal
          exceedances, soft foreign matter, recall grade 2등급
  low     quality or labelling faults, recall grade 3등급

summary_ko and summary_en: one sentence a shopper would understand,
naming the product and the problem. Do not invent facts. If the
reason text is ambiguous, say so in severity_why and pick the more
cautious severity."""


def has_credentials():
    """True if the SDK is likely to find an Anthropic credential."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get(
            "ANTHROPIC_AUTH_TOKEN"):
        return True
    profile_dir = os.path.expanduser("~/.config/anthropic")
    return os.path.isdir(profile_dir)


def _slim(rec):
    """Only the fields Claude needs, to keep prompts short."""
    keys = ("id", "source", "product_ko", "company_ko", "category_ko",
            "reason_ko", "grade", "test_item_ko", "test_result",
            "standard")
    return {k: rec.get(k, "") for k in keys if rec.get(k)}


def enrich_batch(client, records):
    """One API call for up to BATCH_SIZE records. Returns dicts by id."""
    payload = json.dumps([_slim(r) for r in records], ensure_ascii=False)
    response = client.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Records (JSON):\n{payload}",
        }],
        output_format=EnrichedBatch,
    )
    parsed = response.parsed_output
    if response.stop_reason == "refusal" or parsed is None:
        raise RuntimeError(
            f"Claude did not return structured output "
            f"(stop_reason={response.stop_reason})")
    usage = response.usage
    out = {item.id: item.model_dump() for item in parsed.items}
    return out, usage.input_tokens, usage.output_tokens


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)


def enrich(records, cache_path, max_records=None, log=print):
    """Enrich every record not already in the cache. Returns the cache."""
    cache = load_json(cache_path, {})
    todo = [r for r in records if r["id"] not in cache]
    if max_records is not None:
        todo = todo[:max_records]
    log(f"enrich: {len(cache)} cached, {len(todo)} to send, model {MODEL}")
    if not todo:
        return cache
    client = anthropic.Anthropic()
    tokens_in = tokens_out = 0
    for start in range(0, len(todo), BATCH_SIZE):
        chunk = todo[start:start + BATCH_SIZE]
        got, t_in, t_out = enrich_batch(client, chunk)
        tokens_in += t_in
        tokens_out += t_out
        missing = [r["id"] for r in chunk if r["id"] not in got]
        if missing:
            log(f"enrich: {len(missing)} ids missing from reply: {missing}")
        cache.update(got)
        save_json(cache_path, cache)
        log(f"enrich: {min(start + BATCH_SIZE, len(todo))}/{len(todo)} "
            f"(tokens in {tokens_in}, out {tokens_out})")
    return cache
