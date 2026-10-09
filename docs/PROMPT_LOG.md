# Prompt log

The human prompts that produced this repository, in order, lightly
trimmed. Claude Code's intermediate tool use (web searches, curl
probes, file writes) is omitted; what each prompt produced is noted.

## 1. Briefing

> Greetings. So I'm in Hongdae, Seoul right now. I'm meeting a new
> colleague in a few hours to teach him my working methodology for
> Claude Code. His SME is as a food safety scientist. He is interested
> in building something related to Korean food safety that both uses
> AI to write the code (so he can learn good prompting) and uses AI
> in the back-end. To get him started, I thought we could build a
> demonstration app that uses a local HTML output. I'll need a public
> repo created in https://github.com/robertdcurrier so I can have him
> clone the repo later and get all of the doc, code, and results.
> Read this, and then report back and I'll give you some ideas I've
> had.

Produced: a status report (empty folder, nested in another git repo,
GitHub CLI authenticated), a restatement of the goal, a proposed repo
layout, and three open questions: data source, what Claude should do,
language.

## 2. Decisions and delegation

> Let's go with the Korean MFDS open data portal, as he mentioned that
> as a source, and it will show him how to connect and use an API.
> What Claude does: I'm not sure of the format of the MFDS, so I'll
> rely on your judgement to create a simple, yet useful demonstration
> that is not replicated on the MFDS site. Perhaps a simplified search
> tool, or something along that line? Maybe even with an integrated
> map of events/problems/etc? And yes, Hangul and English easily
> switchable, please.

Produced, in order:

1. Web research on the 식품안전나라 open API: URL anatomy, the
   `sample` key, service ids.
2. Live `curl` probes of I0490 and I2620 (and I2630, I2810, I0030,
   C005) to see real fields, paging behaviour, filter whitelist, and
   a Nominatim test on a Korean district.
3. Environment checks: Python 3.14, no SDK installed, no Anthropic
   key, Chrome available for headless screenshots.
4. PLAN.md, then the code: `mfds.py`, `geocode.py`, `enrich.py`,
   `report.py`, `cli.py`, the HTML template, tests.
5. A first full run with no keys, a headless Chrome render, docs,
   and the public repo.

## Prompts used inside the app

The system prompt Claude receives for each batch of records is in
`src/kfs/enrich.py` (`SYSTEM`). It is deliberately plain: the job,
the output fields, the ten hazard categories with examples, the
severity rubric, and two guardrails (do not invent facts; when in
doubt pick the more cautious severity and say why).
