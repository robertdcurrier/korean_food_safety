# How this repo was built: a working method for Claude Code

This repository was built in one sitting in Hongdae, Seoul, on
2026-10-09, as a teaching example. The method below is the one that
produced it. The prompts are in PROMPT_LOG.md; read the two together.

## 1. Start with a briefing, not a task

The first message to Claude Code was not "build an app". It said where
we were, who the colleague is, what he knows (food safety science),
what he wants to learn (prompting and AI in a back end), and what the
deliverable looks like (local HTML, public repo he can clone). It
ended with "read this, and then report back".

That one line matters. It asks the model to show its understanding
before it does anything, which is cheap to correct. The report came
back with the current state, a restatement of the goal, a proposed
file layout, and three open questions. Only then did the human make
decisions.

## 2. Decide the things only you can decide, delegate the rest

The second message made three decisions (data source: MFDS; language:
Hangul and English, switchable; shape: a search tool, maybe a map) and
explicitly delegated one ("I'm not sure of the format of the MFDS, so
I'll rely on your judgement").

Explicit delegation beats vague delegation. The model knows which
choices are yours and which are its own to make and defend.

## 3. Probe reality before designing

Before any design, the model searched for the API documentation, then
hit the live endpoint with `curl` and looked at real rows. That is
how we learned, in minutes, that:

- the public `sample` key returns a fixed five rows and ignores paging,
- field names are Korean abbreviations (`RTRVLPRVNS` = recall reason),
- the inspection service often carries only a district-level address,
- Nominatim resolves Korean districts well enough for a map.

Each of those changed the design. None could have been guessed.
A good prompt here is simply: "Before you design anything, fetch a
real record and show me the fields."

## 4. Write the plan down, in the repo

PLAN.md was written before the code and committed with it. It holds
the goal, the two services and why, what Claude does and does not do,
the pipeline, the page design, what is out of scope, and a checklist
of open decisions. When you clone this repo you can read how it was
meant to work before you read how it works.

## 5. Put the standards where the model will see them every time

CLAUDE.md is read at the start of every session. Ours holds the code
standards (79 columns, 35-line functions, imports at top, no secrets
in files), the commands, and the working method. A standard that is
only in your head is a standard the model cannot follow.

## 6. Use the model where judgement lives, code where rules live

The only place Claude runs in the back end is `src/kfs/enrich.py`:
translation, hazard classification, severity, plain-language summary.
Date parsing, address splitting, geocoding and rendering are plain
Python with unit tests. Ask of every step: could a regex do this?
If yes, do not spend tokens on it, and do test it.

## 7. Make the output structured, batched and cached

- Structured output (a Pydantic schema) means no prose parsing.
- Twenty records per call, not one call per record.
- A cache keyed by record id means re-running costs nothing and a
  single bad record can be redone by deleting one entry.

## 8. Make the first run work with no keys

`python -m kfs all` runs with no Anthropic key and no MFDS key. It
fetches the sample rows, skips enrichment with a clear message,
geocodes, and builds the page. A learner sees a result in five
minutes, then adds keys to see the result improve. Design for the
empty-wallet path first.

## 9. Verify with your eyes, then commit the evidence

The page was rendered in headless Chrome and inspected before the
first commit. The rendered `output/index.html` and the data files are
committed, so the repo shows its result without being run.

## 10. Keep the prompts

PROMPT_LOG.md records what was asked, in order, and what each ask
produced. Six months from now that log explains the repo better than
the git history does.

## Prompting patterns that worked today

| Pattern | Example |
|---|---|
| Context, audience, deliverable, then "report back" | First message |
| Decide what is yours, delegate what is not, say which is which | "I'll rely on your judgement" |
| Ask for a probe before a design | "I'm not sure of the format" |
| Name the constraint that shapes everything | "Hangul and English easily switchable" |
| Request a specific artefact the student will hold | "a public repo so I can have him clone it" |

## Exercises for the next session

1. Add service I2630 (행정처분). Same address field, so the map works.
2. Replace Nominatim with the Kakao local API for street-level points.
3. Add a date-range filter. The API supports `CRET_DTM`.
4. Ask Claude for a weekly bilingual digest paragraph at the top of
   the page, built from the enriched records.
5. Write an eval: twenty records with a scientist's own hazard and
   severity labels, and measure agreement with the model.
