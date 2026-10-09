# The forecast slot: contract, synthetic filler, and what replaces it

Added 2026-10-09, late afternoon. The colleague wants a predictive
model for shellfish toxin events. That is a project for his team
(see `docs/Shellfish-Prediction-Roadmap.pdf`). This session built the
**slot** the model will fill, so that the data shape, the page, and
the tests exist before the model does.

## The contract

`kfs.predict.forecast(bay, today)` returns, per bay:

```json
{
  "model": "synthetic-climatology-v0",
  "issued_at": "2026-10-09",
  "synthetic": true,
  "horizon": [
    {"date": "2026-10-10", "p10": 0.08, "p50": 0.14, "p90": 0.20, "level": "low"},
    ... 14 daily points ...
  ],
  "season_outlook": {
    "first_favourable": "2027-02-23",
    "peak": "2027-04-09",
    "peak_index": 0.80,
    "basis": "climatology only; illustrative"
  }
}
```

Rules of the contract:

- `p10`, `p50`, `p90` are quantiles of the conditions index in [0, 1].
  A real model must emit uncertainty, not a point. If it cannot, it
  emits `p10 == p50 == p90` and says so in `model`.
- `level` is derived from `p50` with the same thresholds as the
  environmental tab (0.40 moderate, 0.65 elevated).
- `synthetic` stays `true` until a model with a backtest ships.
  The page shows a SYNTHETIC badge whenever it is true.
- `model` names the exact version. The page prints it.
- Everything the page needs is in this object. The page does not know
  or care how it was produced.

## The synthetic filler

Deterministic, seeded per bay, tested in `tests/test_predict.py`:

1. Sea temperature: today's observed anomaly against a south-coast
   climatology (about 9.5 °C in late February, 24.5 °C in August)
   decays toward climatology with a ten-day e-folding time.
2. Rainfall: the observed seven-day total relaxes toward the monthly
   mean with a seven-day e-folding time.
3. Wind: persistence relaxing toward 4 m/s.
4. Each future day is scored with `kfs.env.score`, the same index as
   the tab, with the season factor of that day.
5. A widening band of plus or minus 0.05 + 0.012 × day, and a small
   seeded jitter so curves are not identical.

The season outlook scans a year of climatology-only days for the first
one that reaches moderate **while the sea is warming** and the one
that peaks. The warming requirement was added after the first run
flagged November: a cooling autumn sea passes down through the
temperature window and scored the same as a warming spring one. A
small example of why the expert must read the output, not just the
code. In October the
honest result is a low fortnight and a spring window, which is what
the page shows.

## What a real model replaces

One function: `kfs.predict.forecast`. Keep the keys. Expected inputs
for a first real model are listed in the roadmap: KHOA sea temperature
and salinity, KMA rainfall, wind and sunshine, river discharge where
available, satellite chlorophyll, and NIFS toxin and red-tide history
as labels.

## Not fed to Claude

The advisory step (`advisory.py`) deliberately does not receive the
synthetic forecast. Letting the model write prose about invented
numbers would blur the line the page draws between observed
conditions and illustration. When a real model ships, add its output
to the advisory input and update the system prompt to say how much
weight to give it.
