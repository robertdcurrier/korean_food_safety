# PLAN.md — K-Food Safety Watch

Written before any code, 2026-10-09, Hongdae. This file is the
contract between the person and Claude Code: what we are building,
what we are not, and the decisions still open. Update it when a
decision changes. Code follows the plan, not the other way round.

## Goal

A demonstration app a food safety scientist can clone, run, and
extend, that:

1. Pulls live records from the MFDS 식품안전나라 open API
   (teaches: connecting to and paging a public API).
2. Uses Claude in the back end for work a rule cannot do
   (teaches: when and how to put an LLM behind a pipeline).
3. Produces a single local HTML file, no server
   (teaches: a complete result with nothing to deploy).
4. Is bilingual, Hangul and English, with one-click switching.
5. Is not a copy of what the MFDS site already shows.

## Why these two services

| Service | Korean | What it is | Rows (2026-10-09) |
|---|---|---|---|
| I0490 | 회수·판매중지 정보 | Recalls and sales suspensions | 383 |
| I2620 | 검사부적합(국내) | Domestic lab inspections that failed a standard | 544 |

Both carry a business address (map), a product, a reason, and a date.
Together they show the two ends of enforcement: a lab finding and a
market action. The MFDS site lists each separately, Korean only, with
no map, no hazard taxonomy and no severity view. That is the gap the
demo fills.

Probed before deciding (see docs/MFDS_API.md): the public key
`sample` returns a fixed five rows per service, no paging, no
filtering. A free personal key returns 1000 rows per call.

## What Claude does, and does not do

Does (one structured-output call per 20 records):
- translate product, company, reason into natural English
- classify the hazard into ten fixed categories
- judge consumer-health severity high / medium / low with a reason
- write a one-sentence plain-language summary in both languages

Does not:
- parse dates or addresses (regex, deterministic, tested)
- geocode (Nominatim, cached)
- render the page (template + JSON)

Rule of thumb taught here: give the model the judgement work, keep
the mechanical work in code where it is testable and free.

## Pipeline

```
fetch   MFDS API  -> data/raw/{service}.json -> data/records.json
enrich  Claude    -> data/enriched.json      (cache by record id)
geocode Nominatim -> data/geocache.json      (cache by district)
build   template  -> output/index.html       (self-contained)
```

Every step is re-runnable and skips work it has already done. The
pipeline runs with no keys at all (sample rows, no AI, Korean only)
so the first `python -m kfs all` works within minutes of cloning.

## Page design

- Header with language toggle (KO/EN) and theme toggle.
- Five stat tiles: total, recalls, inspections, high severity,
  provinces.
- One filter row: free text, source, hazard, severity, province.
- Leaflet map, markers at district centroids coloured by severity,
  bilingual popups.
- Horizontal bar chart of hazard categories, clickable as a filter.
- Case list with AI summary, severity rationale, and full details.
- Footer stating source, generation time, model, and that AI output
  is advisory.

## Out of scope for the demo

- Street-level geocoding (needs Kakao/Naver key).
- Imported-food recalls, administrative dispositions (I2630), HACCP.
- Scheduling, hosting, a database. All are natural next exercises.

## Open decisions (resolved as we go)

- [x] Services: I0490 + I2620.
- [x] Geocoder: Nominatim at district level, cached.
- [x] Model: claude-opus-5-5 by default, overridable with KFS_MODEL.
- [ ] Personal MFDS key: needed for the full dataset in the
      committed example output.
- [ ] Anthropic key on the demo machine: needed for the committed
      enrichment.
