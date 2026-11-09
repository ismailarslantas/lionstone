# Lionstone Editing: brief in, checked video out

Lionstone Editing is Lionstone's own production loop for an AI assistant (Claude Code, Claude
Desktop, Cursor or any MCP client) or for you. You write a short brief; Lionstone plans the
edit, applies a look and effects, renders, checks the result and writes a report. Every step
lives in plain files in one folder, so a person or an assistant can read, change and re-run it.

It is an original design built only from Lionstone's own parts. It does not use, copy or adapt
code, prompts or skill files from any other video agent.

## The loop

```
brief → plan → review → look → render → fx → qa → report
 🧠      🤖      🧠       🤖      🤖      🤖     🤖     🤖
```

🧠 the assistant (or you) decides · 🤖 Lionstone does it and measures it.

| Stage | What happens | Built from |
|---|---|---|
| brief | Check `brief.json`: footage exists, every value is known | `editing.validate` |
| plan | Silence, filler and retake cuts, transcript, titles, chapter cards, lower thirds | `pipeline.make_plan` |
| review | Optional stop so the cuts and transcript can be checked and changed | `lionstone cuts`, `apply-transcript`, MCP review tools |
| look | One grade, emphasis zooms, transitions on topic changes, each with a reason | Studio agent (`pro/features/agent.py`) |
| render | FFmpeg render with captions, aspect and loudness, then QA with auto-fix | `pipeline.render_and_verify` |
| fx | The Motion FX / Reel FX in the brief, each on its own time window | `fx clip` (`clipfx.apply_to_clip`) |
| qa | Technical and editorial QA of the final file → `out/qa.md` | `qa.py` |
| report | `report.md`: stages, every cut and decision with its reason, QA verdict | `editing.report_markdown` |

Each stage ends as one of:

* `done`
* `skipped`, with the reason (for example `review is off in brief.json`, `no effects in brief.json`)
* `partial`, when only some of the effects could be applied (the note says which and why)
* `waiting`, at the review stop
* `failed`, with the error; the run stops there

The video is ready only when the QA stage says `deliverable: yes`. QA checks that could not run
are listed as skipped, never as passed.

## Quick start

```bash
lionstone editing init my-video --footage take1.mp4 --platform reels --language en
# write the goal, title and effects into my-video/brief.json
lionstone editing run my-video
lionstone editing status my-video          # add --json for scripts
lionstone editing run my-video --from look # redo from a stage after a change
```

`run` skips stages that are already finished, so after fixing a problem you can simply run it
again. `--from STAGE` clears that stage and every stage after it. The exit code is `0` when the
video is deliverable (or the run is waiting for review) and `2` when QA blocks it.

## One folder per production

```
my-video/
  brief.json         ← written by the assistant (or you)
  production.json    ← written by Lionstone: each stage's status, note and time
  edit/plan.json     ← the edit plan (cuts, segments, graphics, effect instances)
  edit/transcript.md ← the transcript (when speech recognition ran)
  edit/<name>.edit.mp4, edit/qa.md ← the render and its QA
  out/<name>.mp4     ← the final video, with the brief's effects
  out/qa.md          ← QA of the final video
  report.md          ← the production summary
```

The source footage is never changed.

## brief.json

```json
{
  "footage": "take1.mp4",
  "goal": "60-second Reel: the three mistakes first-time buyers make",
  "platform": "reels",
  "language": "en",
  "asr": "auto",
  "intensity": "dynamic",
  "content": "talk",
  "style": "social",
  "title": "3 mistakes first-time buyers make",
  "subtitle": "",
  "speakers": ["Ada Lane|Agent, Acme Homes"],
  "chapters": [],
  "captions": "burn",
  "look": true,
  "review": true,
  "fx": [
    {"effect": "frame-break", "start": 0, "end": 3},
    {"effect": "glass-type", "start": 12, "end": 15, "params": {"text": "FOCUS"}}
  ]
}
```

| Field | Values | Default |
|---|---|---|
| `footage` | path, relative to the folder or absolute | (required) |
| `goal`, `title`, `subtitle` | your copy | empty |
| `platform` | `reels` · `shorts` · `tiktok` (9:16, social loudness and captions) · `youtube` · `podcast` | `youtube` |
| `language` | speech language, e.g. `en`, `tr`; empty detects it | empty |
| `asr` | `auto` (speech recognition when installed) · `none` | `auto` |
| `intensity` | `natural` · `balanced` · `dynamic` | `balanced` |
| `content` | `podcast` · `interview` · `talk` · `lecture` · `real-estate` · `product` · `vlog` · `music` · `corporate` | `talk` |
| `style` | `cinematic` · `minimal` · `energetic` · `documentary` · `social` | `minimal` |
| `speakers` | `["Name\|Role"]` lower thirds | `[]` |
| `chapters` | `["00:05:10 Title"]` chapter cards | `[]` |
| `captions` | `burn` · `file` · `none` | `burn` |
| `look` | run the look stage | `true` |
| `review` | stop after the plan for review | `false` |
| `fx` | effects: `effect` id (`lionstone fx list`), `start`/`end` in seconds of the **edited** video (omit for the whole video), optional `params` | `[]` |

Creative copy (goal, title, chapter names, any on-screen text in `fx` params) is written by the
assistant or by you. Lionstone never invents copy: `editing init` leaves those fields empty and
`editing run` does not fill them.

## Review

With `"review": true` the run stops after the plan:

```bash
lionstone cuts my-video/edit/plan.json                 # every cut with its reason and confidence
lionstone cuts my-video/edit/plan.json --restore c3    # bring a cut back
lionstone apply-transcript my-video/edit/plan.json my-video/edit/transcript.md
lionstone editing run my-video                         # continues from the look stage
```

Through MCP, use `get_transcript`, `edit_transcript` and `restore_cuts` on `edit/plan.json`.

## Effects

Effects in `fx` are applied one after another on the rendered video, with the same builders as
`lionstone fx clip`. An effect that cannot be applied (unknown id, bad parameter, render error)
is skipped and the note says why; the others still run. Frame Break, Vertigo, Glass Type,
Green Screen and Doodle Boil use the person matte when `lionstone[vision]` is installed;
without it the plain version renders and the note says so.

## MCP tools

Part of `lionstone mcp` ([mcp.md](mcp.md)):

| Tool | Purpose |
|---|---|
| `editing_init(folder, footage, brief)` | write or update `brief.json`; returns any problems in it |
| `editing_run(folder, from_stage)` | run the loop; returns each stage, the next stage and `deliverable` |
| `editing_status(folder)` | read `production.json` |

## Skill

[`integrations/lionstone-editing/SKILL.md`](../integrations/lionstone-editing/SKILL.md) tells an
assistant how to run a production: ask for the footage and goal, write the brief (all copy is
its own), choose a few effects, review, run, read `report.md` and report every skipped stage
or check.

## Not included

Lionstone Editing edits real footage. It does not generate footage, images, voice-over or
music, and does not search stock libraries. One footage file per production; for brand Reels
with hooks, covers and a calendar, use [Lionstone Reels](reels.md). Programs under other
licences are only ever called as separate processes, never bundled.
