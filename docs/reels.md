# Lionstone Reels: brand-specific Instagram Reels

Give it the footage; the video comes back in your brand's style, checked and ready to post.
Every step from finding a topic to the calendar lives in plain files you can read, change and undo.

```
Topic → Hook → Script → Shoot → Cut → Graphics → Sound → QA → Cover + Caption → Calendar
 🧠      🧠      🧠       🎥      🤖      🤖       🤖     🤖      🤖 + 🧠           🤖
```

🧠 Claude writes it (reading your brand profile and the hook library) · 🎥 you shoot it · 🤖 Lionstone does it and measures it.

## What you need

| | |
|---|---|
| Claude | A paid Claude plan and **Claude Code** (the workflow runs in Claude Code on your computer, not in a normal chat) |
| Computer | Mac, Windows or Linux. Rendering happens on your computer, so speed depends on it |
| Software | Python 3.10+ and FFmpeg. No editing software needed |
| Price | Lionstone is free and open source (Apache-2.0). No monthly fee, no per-video fee, no license key, no watermark |

```bash
pip install "lionstone[whisper] @ git+https://github.com/ismailarslantas/lionstone"
lionstone doctor
lionstone reels sfx build        # a starter pack of 31 original sound effects
```

**FFmpeg on a Mac:** the plain `brew install ffmpeg` package has no `drawtext` or `subtitles` filter, so captions,
hook titles and cover text can't be drawn, and the report says NEEDS REVIEW. Install the full build:
`brew install ffmpeg-full` and `export PATH="$(brew --prefix ffmpeg-full)/bin:$PATH"`, or
`conda install -c conda-forge ffmpeg`. `lionstone doctor` should show both filters as "available".

## The short way: `lionstone reels start`

It tells you where you stand. With no brand identity it gives you the first steps; with one it asks:

1. **Produce with my saved brand identity**
2. **Prepare with a new brand identity**

`reels make` asks the same question (`--identity same` or `--identity new` skips it).
Once made, an identity is remembered and found from any folder. A new identity doesn't delete the old one: it moves it,
with its choices, to `brands/<slug>/identity-archive/`.

## 1 · Introduce the brand once

```bash
lionstone reels brand init "Acme Homes" --language en --handle @acmehomes \
  --audience "young families looking for a home in Izmir" --accent "#E8B04B"
```

`--language` sets the language of hooks, captions and speech recognition. It defaults to `en`; Turkish brands use `--language tr`.

This creates `brands/acme-homes/brand.json` and `brand.md`. The JSON holds the audience, tone of voice, products,
results you can honestly promise, the audience's problems, banned phrases, CTA, hashtags, colours, font and edit
style (`style`). `brand.md` is for free-form notes: Claude reads both when it writes topics, hooks and captions.
For a logo, lower third and end card, link an existing Lionstone brand kit with the `kit` field.

| `style` field | Default | What it does |
|---|---|---|
| `intensity` | `dynamic` | How hard it cuts: natural · balanced · dynamic |
| `caption_style` | `karaoke` | Word-by-word captions in the brand's language, with the spoken word highlighted |
| `color` | `punchy` | Colour look |
| `title_effect` | `T02` | Hook title effect (breaks lines for vertical) |
| `music`, `music_volume` | none · 0.18 | Music file; it ducks under the voice by itself |
| `sfx` | `true` | Places sound effects sparsely and with a reason |

### One talking-head take + 3-5 example Reels → brand identity

```bash
lionstone reels identity "Acme Homes" --footage talk.mp4 \
  --example example1.mp4 --example example2.mp4 --example example3.mp4
```

| Measured | From |
|---|---|
| Tempo, cuts per minute, pause ratio | Example Reels |
| Loudness, colour (brightness, contrast, saturation, warmth), palette | Example Reels |
| Typical length and range, opening lines | Example Reels (needs speech recognition) |
| Whether there is music | Example Reels (**an estimate**: does sound continue when nobody speaks?) |
| Whether it's vertical, your speech rate, your loudness | Your talking-head take |

The result is in `brands/<slug>/identity/`: `identity.md`, `identity.json`, `style.json` and a contact sheet per video
(`frames/`). Caption look and text placement can't be measured; Claude looks at those frames and completes
`brand.md`. Anything that couldn't be measured is listed with the reason.

### Choose from the visual catalogue

```bash
lionstone reels catalog "Acme Homes" --open
lionstone reels setup "Acme Homes" --pick 101 201 301 502 601 801
```

Every option has a number and a picture. On the page, click one card per group and copy the ready-made command, or
type the numbers yourself. Running just `lionstone reels setup "Acme Homes"` in a terminal asks the same numbers
one at a time. The catalogue page and these questions follow the brand's language (English or Turkish).

| Numbers | Group |
|---|---|
| 1xx | Hook title |
| 2xx | Captions |
| 3xx | Colour (including one learned from your examples) |
| 4xx | Pace |
| 5xx | Effects (Lionstone Agent styles, 11 Reel FX) |
| 6xx | Music (`602=track.mp3`, licensing is yours) |
| 7xx | Music level |
| 8xx | Sound effects |
| 9xx | Framing |
| 10xx | Noise cleanup |
| 11xx | Number of covers |
| 12xx | Accent colour |

The catalogue also has two ready-made looks, and you can pick their parts separately:

- **Editorial:** staggered title in a large italic serif (`L01`), quiet captions with one key word set large
  (`editorial`), a glass notification card, neon pills, a countdown.
- **Bold:** glowing headline (`L02`), heavy captions with a glowing key word (`keyword-pop`), a dashed card, emphasis zooms.

The words come from your script, hooks and profile; the key word is chosen from each line by rule (a number first, then
the longest meaningful word). There's no text behind the person, no object tracking, no icons and no 3D graphics.

**Each group's `x00` number means "decide for me from my brand identity"** (`100`, `200`, …). `0` decides everything,
and `--pick 0 205` lets you choose the captions and leaves the rest to Lionstone. `--auto` does the same as `0`.
Each automatic choice writes its reason to `choices.json` and the delivery report. Lionstone ships no music, so "decide
for me" can't invent any: if your examples have music, it says so and asks for your own licensed file.
The "decide for me" option doesn't pick the Editorial or Bold looks; you choose those by number.

Every picture card in the catalogue is real Lionstone output. **The fictional man in the pictures is only an example;
your Reel is always made from your own footage and reference videos.**

## 2 · Topic, hook, script (Claude)

```bash
lionstone reels new "Acme Homes" "Rent or buy"
lionstone reels hooks "Acme Homes" "rising rents" --angle mistake --angle contrarian
```

`hooks` fills 60 original templates across 10 angles (curiosity, mistake, result, contrarian, list, story, question,
demo, warning, ease) with what it knows about the brand, and also gives second-hook and CTA templates.

The library comes as two separate sets, **English and Turkish** (60 templates each). The default is the brand's
language; `--lang` changes it, and angle names work in either language:

```bash
lionstone reels hooks "Acme Homes" "rising rents" --lang tr --angle mistake
lionstone reels hooks "Acme Homes" "rising rents" --lang both --angle hata
lionstone reels brand init "Örnek Emlak" --language tr   # a Turkish brand: hooks, captions, speech recognition
```

Unknown slots stay visible as `{number}`; nothing is invented. Claude starts from these and writes `reel.json`: the
topic, **why it will work**, at least two hooks (A/B), a second hook, a script that flows like speech and ends on the
call to action, the caption, hashtags and cover text.

```bash
lionstone reels lint projects/acme-homes/2026-11-05-rent-or-buy
```

It checks hook length (≤ 14 words), unfilled template slots, A/B hooks, the second hook, script length against the
target (≈ 2.7 words/s in English, ≈ 2.5 in Turkish), the CTA ending, banned phrases, caption ≤ 2200 characters,
hashtags ≤ 30 and cover text.

## 3 · Shoot and deliver

Put the video in the reel folder's `raw/`:

```bash
lionstone reels make projects/acme-homes/2026-11-05-rent-or-buy
```

| Step | What happens |
|---|---|
| Cut | Silences, filler sounds, repeated words and sentences go; no cut lands inside a word. A repeat that can't be cut shows in the report |
| Graphics | 9:16, word-by-word captions in the brand's language, hook title, brand colours, brand kit |
| Sound | Effects, music (ducking), -14 LUFS |
| QA | The finished video is measured again (below) |
| Cover | 3 versions from the raw footage, with text placed for the 3:4 grid crop |
| Copy | `caption.txt` (caption + hashtags), copy-check results |
| Editing room | `edit/room.html` |

The result lands in `delivery/`:

```
delivery/
  acme-homes-rent-or-buy.mp4
  cover-1.jpg  cover-2.jpg  cover-3.jpg
  caption.txt
  report.md  report.json  qa.md  qa.json  copy-check.json
```

Reel folders made before 0.4.2 used `ham/`, `kurgu/`, `teslim/`. They keep working: footage is found and existing
sub-folders are used as they are.

### The delivery report

```
READY TO DELIVER ✅

| Check             | Status    |
| Repeat scan       | Clean     |
| Cut points        | Clean     |
| Script comparison | Clean     |
| Text overflow     | Clean     |
| Loudness          | Clean     |
| Picture           | Clean     |
| Covers            | 3 versions|
```

- **Script comparison:** the words actually heard in the video are aligned with the script; missing, extra and changed
  words are listed. Under 75% stops delivery.
- **Repeat scan:** repeats left after cutting, like "I think I think".
- **Cut points:** clipped words, clicks at joins, low-confidence cuts.
- **Text overflow:** every graphic is measured at the effect's real text size, allowing for the bottom 20% and right
  edge taken by the Reels UI. A clear overflow stops delivery. This is an estimate (no OCR) and the report says so.
- **Sound and picture:** loudness, true peak, black or frozen frames, A/V length, format.

A check that didn't run doesn't count as passed: the report shows it as "Skipped" with the reason.

The report gives one of three verdicts:

| Verdict | Meaning | Exit code |
|---|---|---|
| **READY TO DELIVER ✅** | Every check that ran is clean, script matches ≥ 90% | 0 |
| **NEEDS REVIEW 👀** | Script matches 75-90%, a repeat is left in, or the script couldn't be compared | 2 |
| **FIX NEEDED 🛑** | Script matches < 75%, clear text overflow, a technical fault or a copy error | 2 |

## 4 · The editing room

```bash
lionstone reels room projects/…/edit/plan.json   # make already creates it
```

One local page in your browser: the video and every word side by side. Click a word → jump to that moment.
Switch to cut mode → click a word to cut it or restore it. Double-click → fix the spelling in the captions (names,
brand, product). Preview plays back skipping what's cut. "Download changes" gives you a file to apply, then re-render:

```bash
lionstone reels room-apply projects/…/edit/plan.json ~/Downloads/room-edits.json
lionstone reels make projects/… --keep-plan
```

`--keep-plan` doesn't regenerate the plan, so your corrections stay; sound, QA and covers are made again.

The video isn't uploaded anywhere: the page plays the file from your disk.

## 5 · Calendar

```bash
lionstone reels schedule projects/…/rent-or-buy "2026-11-10 19:00"
lionstone reels calendar --brand "Acme Homes" --ics calendar.ics
```

The calendar is built from the reel folders themselves (one source of truth). The `.ics` file works with Google, Apple
and Outlook calendars. Statuses: idea · script · shoot · edit · review · ready · published.

## Sound effects and music

`lionstone reels sfx build` makes 31 original effects with FFmpeg (whoosh, pop, click, ding, riser, boom, swipe, type).
Put your own licensed packs in the same folder (`~/.config/lionstone/sfx` or `LIONSTONE_SFX_DIR`): the sub-folder name
becomes the category and they're used automatically. Placement is sparse (at most one per 1.2 s): a whoosh on the
opening, a pop on text graphics, a ding on the CTA. For manual placement, add `sfx.json` to the reel folder:

```json
[{"at": 1.2, "sound": "pop"}, {"at": 6.8, "sound": "ding/ding-02", "gain": 0.4}]
```

Commercial licensing for music is your responsibility; Lionstone ships no music.

## Checklist

`lionstone reels checklist` shows the 37-item pre-delivery list: Lionstone measures the 🤖 items, and a person looks at
the 👀 ones (is the promised result real, is the music licensed, has the client approved…).

## Who it's for

- Creators who want to finish their own videos
- Brands and agencies that publish regularly
- Teams that want to go faster with their editor
- Anyone running several brands in one setup (each brand has its own folder under `brands/`)

You still do the shooting. There's no promise of a one-click viral video: the hook and script are only as good as they
are, and Lionstone does the rest of the job carefully and quickly.

## Known limits

- The workflow has been tested with synthetic speech and a fictional AI-generated character, not yet on real camera
  footage with a human voice. Please report what you find.
- Text overflow is an estimate, not OCR. Music detection is an estimate.
- Speech recognition needs `lionstone[whisper]`; face tracking and the face-coverage check need `lionstone[vision]`.

## Want it set up for you?

The software is free and open source. If you'd rather have someone build your brand profile, identity and catalogue
choices for you, see [Brand setup for your team](brand-setup.md).
