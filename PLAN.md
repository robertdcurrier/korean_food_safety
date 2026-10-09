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
- [x] Basemap: embedded KOSTAT province outlines, Esri tiles on
      top with automatic fallback. OSM tiles returned 403 from a
      file:// page; CARTO now needs a key.
- [x] Model: claude-opus-5-5 by default, overridable with KFS_MODEL.
- [x] Anthropic key on the demo machine (seven-day key, 2026-10-09).
- [ ] Personal MFDS key: needed for the full dataset in the
      committed example output.

## Phase 2 (2026-10-09, afternoon): environmental layer, PSP proof of concept

Asked for by the colleague, who will lead a team integrating
environmental data with what MFDS already supplies. Decisions made
with him in the room: no new keys, eight south-coast bays, the
paralytic shellfish poisoning (PSP) spring window only.

What it is: a second tab, "환경 조건 / Environmental conditions", that
shows for eight shellfish-producing bays whether current weather and
sea conditions are favourable for an Alexandrium bloom. It is a
conditions index, not a toxicity measurement, and every label says so.

Source for the demo: Open-Meteo (free, keyless, CC BY 4.0). Hourly
sea-surface temperature and wave height from its marine API; rainfall,
wind and air temperature from its forecast API; seven days of history.
Verified live from Seoul before design: complete data for Jinhae Bay.

Bays: 진해만, 마산만, 거제, 통영, 고성 자란만, 사천만, 남해 강진만,
여수 가막만. Coordinates are approximate bay centres; the colleague
corrects them.

Index (deterministic, in code, tested; a heuristic for a POC):
- sea temperature in the Alexandrium window (8–18 °C, best 12–16)
- seven-day warming trend
- seven-day rainfall (runoff, nutrients)
- seven-day mean wind (calm water stratifies)
- month (PSP season February–June)
Weighted to 0–1; levels low / moderate / elevated. In October the
honest answer is "low, out of season", and the page says that.

Claude's one step: for each bay, a short bilingual advisory that
combines the index with any seafood records from MFDS in the same
province, with an explicit confidence and why. Cached per bay per day.

What the real system replaces: Open-Meteo with KHOA buoys and KMA
rainfall; the heuristic with NIFS 패류독소 and 적조 bulletins; the
advisory rubric with the team's own thresholds. Architecture unchanged.

## Phase 3 (2026-10-09, late afternoon): a slot for a predictive model

The colleague wants to build a predictive model for shellfish toxin
events. That is a project, not a session. What this session adds is
the **interface**: a fixed data contract for a forecast per bay, a
synthetic forecast that fills it, and the place on the page where a
forecast is shown. When the real model exists it replaces one
function and nothing else moves.

Contract (per bay, see docs/PREDICTION.md):
- `model`, `issued_at`, `synthetic` (true until a real model ships)
- `horizon`: 14 daily points of `date`, `p10`, `p50`, `p90`, `level`
- `season_outlook`: illustrative first date and peak date of the next
  favourable window from climatology alone

Synthetic generator: deterministic, seeded per bay, blends today's
observed conditions toward a south-coast sea-temperature climatology
and scores each day with the same index as the environmental tab.
It is honest about being synthetic in the data, on the card, and in
the popup.

Second training document: docs/Shellfish-Prediction-Roadmap.pdf, for
the colleague and the team he will lead. Distinct from the primary
guide: what the target is, what data and labels exist, the modelling
ladder from climatology to gradient boosting, evaluation as the
expert's job, and where Claude helps and where it does not.
