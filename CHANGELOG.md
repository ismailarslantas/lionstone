# Changelog

## 1.0.0 — 2026-11-09
**Lionstone 1.0: the Motion FX Pack. Seventeen motion-design effects, one command each, and a person matte that puts you in front of the frame. Free as ever.**

- **Motion FX Pack** (catalogue category `motion-fx`, 162 presets in total, 122 ready to render): `orbit`, `couch-wall`, `ui-world`, `frame-break`, `digital-zoom`, `phone-mockup`, `checklist`, `headline-wall`, `zoom-through-cut`, `chart-grow`, `pull-back-reveal`, `green-screen`, `paper-cut`, `doodle-boil`, `vertigo`, `cover-story`, `glass-type`. FFmpeg filter math plus the bundled fonts (`pro/features/renderers/motion_fx.py`), relative geometry for 9:16, 1:1 and 16:9, the same builders for preview, showcase and export. Guide: [docs/motion-fx.md](docs/motion-fx.md).
- **Person matte** (`lionstone/pro/matte.py`): Frame Break, Vertigo, Glass Type, Green Screen and Doodle Boil cut you out of the shot, so your head breaks over the frame, the type sits behind you and any background becomes a brand stage without a green screen. Built automatically when OpenCV is installed (`lionstone[all]` or `lionstone[vision]`) with U²-Net small (4.6 MB, Apache-2.0, downloaded once from GitHub, SHA-256 checked), on the CPU, cached per file. `lionstone fx matte talk.mp4` builds it ahead. Without OpenCV, or with `LIONSTONE_MATTE=0`, the plain FFmpeg versions render and the compile report says so.
- Renders, previews and showcase reels feed the matte with the same cuts as the video (`render.build_graph(matte_input=…)`).
- Text in effects is literal: `%` in a label no longer breaks the render (`expansion=none`), and bundled fonts load from Windows user folders with non-ASCII names (FreeType can't open those paths, so fonts are used from a temp copy).
- `lionstone[vision]` now also powers the person matte. Development status: Production/Stable.
- Tests: `tests/pro/test_motion_fx.py` renders every effect on 9:16 and 16:9, every matte version with a stand-in matte, a full plan render that feeds the matte through the cuts, and the fallback without OpenCV.

## 0.4.2 — 2026-11-06
**Lionstone Reels speaks English. Same features as 0.4.1, free as ever, now documented for everyone.**

- **English everywhere you operate it**: `lionstone reels` help, messages, lint, checklist, the editing room, the calendar export, the delivery report and [docs/reels.md](docs/reels.md). Hooks, captions and speech recognition still work in English and Turkish, and the catalogue page follows the brand's language.
- **Report verdicts**: READY TO DELIVER, NEEDS REVIEW, FIX NEEDED (they were TESLİME HAZIR, GÖZDEN GEÇİR, DÜZELTME GEREKİYOR).
- **Names on disk**: `raw/`, `edit/`, `delivery/`, `report.md`, `report.json`, `cover-1.jpg`, `copy-check.json`. Statuses: idea, script, shoot, edit, review, ready, published. Reel folders and `reel.json` files from 0.4.0 and 0.4.1 keep working: `ham/`, `kurgu/`, `teslim/` are found and Turkish statuses are read and accepted.
- **`lionstone reels brand init` now defaults to `--language en`** (it was `tr`). Saved brands keep their language. Turkish brands: add `--language tr`.
- **[Reel Handbook](docs/handbook/README.md)** updated from v0.3.2 for the 0.4.1 feature set, in English and Turkish.
- **[Brand setup](docs/brand-setup.md)**: an optional, by-quote setup service from Kreatif Hizmetler, with a request form. The software stays free and nothing is held back.

## 0.4.1 — 2026-11-06
**Brand onboarding for Lionstone Reels: measure your style, choose from a visual catalogue, and every later Reel remembers.**

- `lionstone reels identity "<brand>" --footage talk.mp4 --example a.mp4 …` (one talking-head take + 3-5 example Reels): measures tempo, cuts per minute, pauses, loudness, colour, palette, length, speech rate and opening lines; estimates music; writes contact sheets for the agent to look at what can't be measured. Saved in `brands/<slug>/identity/`. Anything not measured is listed with the reason.
- **Visual catalogue**: `lionstone reels catalog [--open]`. Every option has a number and a picture: hook title, captions, colour, pace, effects (Lionstone Agent styles and 11 Reel FX), music, music level, sound effects, framing, noise cleanup, covers, accent colour. Picture options are real Lionstone renders on a fictional example character; sound options are waveforms or spectrograms of real output. The character is only the example: your Reel is made from your own footage.
- `lionstone reels setup "<brand>" --pick 101 205 503 602=track.mp3`: choose by typing numbers, or click cards on the local page and copy the command. **Every group has a "decide for me from my brand identity" option** (`x00`), `0` decides everything, and each automatic choice records its reason.
- `lionstone reels make` follows the choices. The report lists them.
- **New looks in the catalogue**: hook titles Editorial Stack (L01) and Glow Headline (L02); captions `editorial` and `keyword-pop`, which stress one word chosen from each line; effects Glass Card, Neon Pills, Dashed Card and Countdown, alone or as the Editorial and Bold looks; accent colours Deep Plum and Signal Yellow. Original FFmpeg builders; all words come from your script, hooks and profile. Bundles Poppins and DM Serif Display under the SIL OFL (`data/fonts`).
- Captions now use the brand's accent colour; they were always gold.
- **Memory**: a brand made in one folder is found from any other. `lionstone reels start` and `make` offer **"produce with my saved brand identity"** or **"prepare with a new brand identity"** (`--identity same|new`). A new identity archives the old one and its choices in `identity-archive/`; nothing is deleted.
- Fixes: strong noise cleanup crashed FFmpeg 9 (`anlmdn` replaced); captions in vertical video always sit above the app UI, in every style; a failed `make` no longer leaves an old verdict behind; prompts no longer crash when there is no terminal (Windows `NUL`).

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
