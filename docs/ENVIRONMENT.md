# The environmental tab: a PSP proof of concept

Added on 2026-10-09, afternoon, with the colleague in the room. His
team will integrate environmental data with what MFDS already
supplies; this tab shows the shape of that integration in miniature.

## What it claims, and what it does not

It computes, for eight shellfish-producing bays on the south coast,
whether the last seven days of sea temperature, rainfall, wind and
the season **favour a bloom of _Alexandrium_**, the dinoflagellate
behind paralytic shellfish poisoning (PSP) in Korea. It does **not**
measure toxin, and nothing on the page says shellfish are toxic or
safe. The official source for that is the 국립수산과학원 패류독소
속보.

## Data

Open-Meteo, free and keyless, CC BY 4.0.

| Call | Variables | Window |
|---|---|---|
| `marine-api.open-meteo.com/v1/marine` | hourly sea_surface_temperature, wave_height | 7 past days + today |
| `api.open-meteo.com/v1/forecast` | hourly wind_speed_10m (m/s); daily precipitation_sum, temperature_2m_max | 7 past days + today |

Two calls per bay, sixteen in all, about two seconds. Verified from
Seoul before design: complete hourly SST for Jinhae Bay.

## Bays

진해만, 마산만, 거제 북안, 통영, 고성 자란만, 사천만, 남해 강진만,
여수 가막만. Coordinates in `src/kfs/env.py` are approximate bay
centres and are the first thing the expert should correct.

## The index

A weighted sum in [0, 1], computed in `kfs.env.score`, tested in
`tests/test_env.py`:

| Factor | Weight | Rule |
|---|---|---|
| Sea temperature now | 0.35 | 1.0 at 12–16 °C; 0.6 at 8–12 or 16–18; 0.2 at 6–8 or 18–20; else 0 |
| Seven-day warming | 0.20 | 1.0 if > +1.0 °C; 0.6 if > +0.3; else 0.2 |
| Seven-day rainfall | 0.20 | 1.0 if > 50 mm; 0.6 if > 20; 0.3 if > 5; else 0 |
| Seven-day mean wind | 0.10 | 1.0 if < 3 m/s; 0.6 if < 5; else 0.2 |
| Season | 0.15 | 1.0 Feb–Jun; 0.5 Jan or Jul; else 0.2 |

Levels: elevated at 0.65 and above, moderate at 0.40 and above,
otherwise low. In October the honest result is low everywhere, and
the page says "outside PSP season" on every card.

These thresholds came from general knowledge in a few minutes. They
are a placeholder for the expert's rubric, exactly like the hazard
categories on the recall tab.

## Claude's one step

`src/kfs/advisory.py` sends all eight bays in one call with their
numbers, factors and any seafood-related MFDS records from the same
province, and receives a two-to-three sentence advisory per bay in
both languages plus a confidence grade with its reason. The system
prompt forbids claims of toxicity or safety and tells the model to
state the season honestly. Results are cached per bay per day in
`data/env_advisory.json`.

## What a real system replaces

| Demo | Production |
|---|---|
| Open-Meteo SST | KHOA 바다누리 coastal buoys (실시간 수온), data.go.kr key |
| Open-Meteo rainfall, wind | KMA 기상청 AWS / 단기예보, data.go.kr key |
| The heuristic index | NIFS 패류독소 발생현황 and 적조속보; a fitted model once there is labelled history |
| Province-level MFDS match | Product-level link between NIFS closures and MFDS seafood records |
| Eight hand-placed bays | The NIFS monitoring station list |

The pipeline shape does not change: one fetch module per source,
deterministic scoring with tests, one Claude step for the written
judgement, one page.

## Running it

```bash
python -m kfs env      # fetch, score, advise (advisories need an Anthropic key)
python -m kfs build
```

`python -m kfs all` includes it. If Open-Meteo is unreachable the
previous `data/env.json` is kept and the build still succeeds.
