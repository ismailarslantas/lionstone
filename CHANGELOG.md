# Changelog

## 0.4.0 — 2026-11-06
Lionstone 0.4.0 is the whole Lionstone package — speech-aware editing, Creative Suite (145 presets incl. Reel FX), multicam, style learning, Shorts/Reels clips, brand kits, team tools, NLE export, Styles, MCP and QA — plus **Lionstone Reels**.

- **Lionstone Reels** (`lionstone reels …`, `src/lionstone/reels/`, standard library + FFmpeg): a brand-specific Instagram Reels workflow from topic to calendar.
  - `brand init|show|list|check`: brand profiles in `brands/<slug>/brand.json` + `brand.md` (audience, tone, products, promises, pains, banned words, CTA, colours, font, edit style, optional brand kit).
  - `new`, `hooks`, `lint`: reel briefs (`reel.json`), a hook library in English and Turkish, 60 original templates each in the same 10 angles plus second hooks and CTAs (`data/reels/hooks.en.json`, `hooks.json`; `hooks --lang en|tr|both`, `brand init --language`), and checks for hook length, A/B hooks, second hook, script length (~2.5 words/s in Turkish, ~2.7 in English), CTA ending, banned words, caption ≤ 2200, hashtags ≤ 30, cover text.
  - `make`: raw footage → 9:16 plan in the brand's style (karaoke word captions, T02 hook title pre-wrapped for vertical) → brand kit → render → SFX + ducked music + loudnorm → QA on the final file → 3 covers from the raw footage, cropped for the 3:4 grid → `caption.txt` → `rapor.md` with a TESLİME HAZIR / DÜZELTME GEREKİYOR verdict.
  - New QA checks for reels plans: `reels_script_match` (script vs. heard words, difflib alignment), `reels_repeats` (repeats left after cutting), `reels_text_fit` (effect-aware text size vs. the Reels UI safe area; a clear overflow blocks delivery). Estimates are labelled as estimates; checks that can't run are `skipped`.
  - `sfx build|list`, `mix`: an original 31-sound SFX starter pack synthesised with FFmpeg (whoosh, pop, click, ding, riser, boom, swipe, type), user packs picked up from the same folder, sparse automatic cues or `sfx.json`, music bed with sidechain ducking.
  - `room`, `room-apply`: a local editing-room page — click a word to seek, cut or restore it, double-click to fix caption spelling — exported as `room-edits.json` and applied to the plan.
  - `schedule`, `status`, `calendar [--ics]`: a content calendar built from the reel folders.
  - `cover`, `checklist` (37-item delivery checklist, auto vs. manual).
  - Three report verdicts: TESLİME HAZIR, GÖZDEN GEÇİR (script match under 90 %, a repeat left, no transcript, or FFmpeg lacks `subtitles`/`drawtext`) and DÜZELTME GEREKİYOR. `make` exits 0 only on the first.
  - `make --keep-plan` re-delivers after editing-room changes without re-planning.
- Editing core (all videos):
  - Whisper's invented lines over silence are dropped (`is_phantom_segment`), so captions don't show words nobody said.
  - A sentence said twice (3-8 words, up to a 3 s pause) loses its first take.
  - Karaoke captions moved up to 22 % from the bottom, above the Reels/Shorts UI.
- Claude skill `integrations/lionstone-reels` and Turkish guide `docs/reels.md`.
- Tests: `tests/test_reels.py`, including an end-to-end make that must report TESLİME HAZIR, room edits through `--keep-plan`, and measured music ducking.

## 0.3.2 — 2026-11-01
- **Reel FX Pack**: 12 original one-command effects for vertical Reels & Shorts (catalog category `reel-fx`, 145 presets in total). Creative: `stage-light`, `press-mono`, `frost-panels`, `duotone-pop`, `scan-line`, `afterimage`, `halo-orbit`, `neon-outline`. Brand-aware (colours as parameters, set by brand kits): `insight-split`, `brand-frame`, `progress-rail`, `pixel-resolve`. Pure FFmpeg (`pro/features/renderers/reel_fx.py`), relative geometry for 9:16 / 1:1 / 16:9, same builders for preview and export.
- **`lionstone fx showcase <effect> clip.mp4`** renders a 6.4 s 1080×1920 "one command" reel: the command types itself, a card shows the effect's promise, the clip dissolves through a gold/ink pixel dither and the real render fills the screen with an "Edited with Lionstone" pill.
- Guide `docs/reel-fx.md` with real renders and new docs visuals; `tools/gen_reel_presets.py` regenerates `presets/reelfx.json`.
- Tests: every Reel FX effect renders on 9:16 and 16:9, compiles into a plan, and the showcase renders 1080×1920.

## 0.3.1 — 2026-11-01
- **Fix: audio/video stay in sync when the source audio ends before the video.** A kept segment that ran past the end of the audio produced a shorter audio piece, so the render drifted (QA reported it as `av_length`, and blocked delivery above 0.5 s). Each segment's audio is now padded with silence to the segment length.
- The many-features render test prints the QA report when it fails and now requires `av_length` to pass.

## 0.3.0 — 2026-11-01
- **Everything is free.** The commercial Lionstone Pro/Studio plugin (0.2.3) is merged into the open core as `lionstone.pro`: Creative Suite (133 looks, effects, transitions, motion and text presets, previews, keyframes, agent), multicam, style learning, Shorts/Reels clips, FCPXML/EDL export, vision QA, brand kits, roles, team presets and batch apply. License keys, activation, renewal and watermarks are gone; the old tier names stay as catalog labels.
- `lionstone pro whoami` is now `lionstone whoami`. Uninstall `lionstone-pro` if you had it.
- **Lionstone Styles**: `lionstone styles [--open] [--list] [--group O] [--cmd O4 W3 A3]`, original style recipes (Opening, Words, Aspect, Grade, Sound, Pace, Labels), a visual guide and a Claude skill in `integrations/lionstone-styles`. Source: `src/lionstone/data/styles/styles.json`; run `python tools/build_styles.py` after editing.
- New extras: `lionstone[extras]` (NumPy) and `lionstone[vision]` (NumPy + OpenCV).
