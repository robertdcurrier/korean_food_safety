# CLAUDE.md

## Project

K-Food Safety Watch. MFDS 식품안전나라 open data (recalls I0490,
failed inspections I2620) fetched by a small Python package, enriched
by Claude (translation, hazard class, severity, bilingual summary),
rendered to one self-contained local HTML page with a map. Teaching
repo: the process matters as much as the output. Read PLAN.md first,
then docs/METHODOLOGY.md.

## Code standards

- Python 3.10+, PEP-8, max 79 chars per line
- Max 35 lines per function (excluding docstrings)
- `#!/usr/bin/env python3` shebang on every Python file
- All imports at the top of the file
- Standard library for HTTP (urllib); the only third-party
  dependencies are `anthropic` and `pydantic`
- Secrets only from the environment or `.env` (git-ignored).
  Never write a key into a file that is committed.
- Every deterministic transform (dates, addresses, normalisation)
  has a test in `tests/`. Network and API calls are not unit-tested.
- Korean strings are first-class: UTF-8 everywhere,
  `ensure_ascii=False` on every JSON dump.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
python -m kfs all            # fetch, enrich, geocode, env, build
python -m kfs env            # Open-Meteo + PSP index + advisories
python -m kfs build          # re-render from cached data
open output/index.html
```

## Working method

1. Plan before code. PLAN.md states the goal, scope, and open
   decisions. Change the plan first when the goal changes.
2. Probe before designing. Hit the real API with curl and look at a
   real row before writing a client for it.
3. Small, verifiable steps. Each pipeline stage writes a file you
   can open and read.
4. Commit results, not just code. `output/index.html` and
   `data/*.json` are in the repo so a reader sees the outcome
   without running anything.
5. Record the prompts. docs/PROMPT_LOG.md holds the prompts that
   produced this repo.

## Data notes

- The literal MFDS key `sample` returns five fixed rows per service.
  Set `MFDS_API_KEY` for the full set (see docs/MFDS_API.md).
- `data/enriched.json` is a cache keyed by record id. Delete an
  entry to have Claude redo that record.
- `data/geocache.json` caches district lookups. Delete it to
  re-geocode (about one second per district).
- AI fields are advisory. The footer of the page says so; keep it.
- `data/korea_provinces.geojson` is the embedded basemap. Keep it;
  the map must work with no tile server at all.
- The environmental tab is a conditions index, never a toxin claim.
  Keep that language in the template and in advisory.py's prompt.
  Thresholds in env.py are placeholders for the expert's rubric;
  change docs/ENVIRONMENT.md and tests/test_env.py with them.
