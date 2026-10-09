# LinkedIn post

Written 2026-10-09 to announce this repository. LinkedIn does not
render Markdown, so the body below is plain text with line breaks.
Post the links as the first comment, and attach
`docs/screenshots/report_ko.png`.

## Body

People keep asking me, "Bob, how do you get such good results from Claude Code?"

This morning in a café in Hongdae, Seoul, I answered it by building something, and the whole process is now public.

A colleague I'm meeting today is a food safety scientist. Smart, deeply expert, not a programmer. He wants to build tools for his field using AI, and he wants to learn how to prompt well. So I built him a demonstration, start to finish, before lunch.

The app pulls live recall and failed-inspection records from Korea's MFDS open-data API, sends them to Claude to translate into English, classify the hazard, grade the severity with a stated reason, and summarise each case in Korean and English. Then it writes a single HTML file: a searchable, bilingual map of what is being pulled off Korean shelves and why. No server. Open it from your desktop.

Claude Code wrote every line. My two prompts contained no technical vocabulary at all.

That is the real answer to the question. The results come from the method, not from clever wording:

Brief it like a colleague. Where we are, who this is for, what done looks like. Then "read this and report back" before any code.

Decide only what a human must decide, and say explicitly what you are delegating.

Make it probe reality first. Real API, real rows, before any design. Three things we learned in five minutes changed the whole architecture.

Plan in the repo. Standards in the repo. Prompts in the repo. Results in the repo.

Use AI only for judgement. Everything a regular expression can do, code does, with tests.

Look at the output with your own eyes. The first map broke in a real browser for a policy reason, not a code reason. We removed the dependency instead of swapping it.

And the lesson I most want my colleague to take away: own the question, not the keyboard. His scarce contribution is knowing that aloe latex contains laxative anthraquinones, not knowing git. Find a Gen MZ partner for the terminal. Spend your own time on the rubric and the evaluation.

The repo includes a 26-page guide for non-developers: what the two Claudes each do (the builder on your laptop versus the worker behind the API), setup on Mac and Windows, how to get both keys, and a chapter on applying the same recipe to botany, marine biology, epidemiology, chemistry, agronomy. Nothing in the method is about food.

Links in the first comment. Clone it, read PLAN.md first, and tell me what you build.

#ClaudeCode #AI #FoodSafety #OpenData #Korea

## First comment

Repo: https://github.com/robertdcurrier/korean_food_safety
The guide: https://github.com/robertdcurrier/korean_food_safety/blob/main/docs/K-Food-Safety-Watch-Guide.pdf
Start with PLAN.md and docs/METHODOLOGY.md. The prompts that built it are in docs/PROMPT_LOG.md.
