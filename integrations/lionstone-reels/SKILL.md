---
name: lionstone-reels
description: Produce brand-specific Instagram Reels end to end with Lionstone — find a topic for the brand's sector, write hooks and a spoken script, then turn the raw footage into a captioned, sound-designed, QA-checked Reel with covers, caption and a calendar slot. Use when the user says "Reels", "reel çıkar", "konu bul", "hook yaz", "script yaz", gives raw footage for a brand, or asks for a content calendar.
---

# Lionstone Reels

You run the creative steps; Lionstone runs and measures the production steps. Work in the
brand's language (Turkish by default) and in the folder that holds `brands/` and `projects/`.

## 0 · Brand
`lionstone reels brand list`. If the brand is missing, ask for: name, @handle, sector, audience,
tone, products, results the brand can honestly claim, audience problems, banned words, CTA,
colours. Then `lionstone reels brand init …` and fill `brands/<slug>/brand.json` + `brand.md`.
`lionstone reels brand check <name>` must pass. Always read `brand.json` and `brand.md` before writing.

## 1 · Topic (per reel)
Propose 3-5 topics for the sector and audience. For each, one line on **why it will work for this
audience** (a pain from `pains`, a question they ask, a seasonal moment). Never invent statistics,
prices or legal facts; if a claim needs a source, ask the user or search. Create the folder:
`lionstone reels new "<brand>" "<topic>"`.

## 2 · Hooks
`lionstone reels hooks "<brand>" "<topic>" --angle <a> --angle <b>` gives filled templates.
Use them as raw material, not final copy. Write at least two hooks from **different angles**
(A/B), each ≤ 14 words and readable in 2 seconds, plus a second hook for second 3-6.

## 3 · Script
Spoken, not written: short sentences, the brand's tone, opens with the main hook, delivers one
idea, ends with the CTA. Fit `target_seconds` at ~2.5 words/s. Put stage directions in
[brackets]; they are ignored by timing and by the script check.

Fill `reel.json`: `why`, `angle`, `hooks`, `second_hook`, `script`, `cta`, `caption`,
`hashtags` (3-5 focused), `cover_text` (1-3 short variants), `status: "script"`.
Run `lionstone reels lint <folder>` and fix every 🔴 before showing the user.

## 4 · Production
The user puts footage into `<folder>/ham/`. Then:
`lionstone reels make <folder>` (add `--music <file>` only if the user owns the licence).
Read `<folder>/teslim/rapor.md`.
- Only say the Reel is ready if it says **TESLİME HAZIR**.
- Report every "Bak"/"Düzelt" row and every skipped check honestly.
- Script mismatch → show missing/changed words; ask whether to re-cut or accept.
- Text overflow → shorten the hook / cover text in `reel.json`, re-run `make`.
- **GÖZDEN GEÇİR** means a person must look: show the listed script differences and leftover repeats.
- Spelling of names in captions → point the user to `kurgu/room.html` (double-click a word),
  then `lionstone reels room-apply` + `lionstone reels make <folder> --keep-plan`.

## 5 · Calendar
`lionstone reels schedule <folder> "YYYY-MM-DD HH:MM"`, `lionstone reels calendar --brand <b>`,
`--ics takvim.ics` to export. Mark published reels with `lionstone reels status <folder> yayında`.

Never overwrite the user's footage. Never promise virality; promise a clean, on-brand, checked video.
