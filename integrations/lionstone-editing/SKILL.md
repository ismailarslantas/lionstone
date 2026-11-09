---
name: lionstone-editing
description: Produce a finished talking-head video with Lionstone Editing, from a short brief to a checked file with a report. Use when the user gives footage and a goal ("make a Reel from this take", "edit this talk for YouTube with a title and an effect on the hook").
---

# Lionstone Editing

One folder per production. You write `brief.json`; Lionstone plans, renders, checks and reports.
Full guide: `docs/editing.md`. With the MCP server, the same steps are `editing_init`,
`editing_run`, `editing_status`, plus `get_transcript`, `edit_transcript` and `restore_cuts` for
the review.

## Steps

1. Ask for the footage file and the goal if either is missing. Ask the platform (reels, shorts,
   tiktok, youtube, podcast) only when the goal does not make it clear.
2. `lionstone editing init <folder> --footage <file> --platform <p> --language <en|tr>`.
3. Edit `<folder>/brief.json`. You write all copy: `goal`, `title`, `subtitle`, chapter names,
   any on-screen text in effect params. Never leave copy for Lionstone to invent; it will not.
   Set `"review": true` when the user wants to see the cuts first.
4. Effects: list them with `lionstone fx list` (or `list_effects`) and add at most a few to
   `fx`, each with `start`/`end` in seconds of the **edited** video. More is not better.
5. `lionstone editing run <folder>`. If it stops at review, show the user the uncertain cuts
   (`lionstone cuts <folder>/edit/plan.json`) and the transcript, apply their changes, then run
   again.
6. Read `<folder>/report.md`. Tell the user the video path, what was decided and why, and every
   stage or QA check that was `skipped` or `partial`, with its reason.
7. Only call the video ready when the report says **Deliverable: yes**. If a stage failed, fix
   the cause and run `lionstone editing run <folder> --from <stage>`.

## Do not

* Overwrite the source footage (outputs go to `<folder>/edit/` and `<folder>/out/`).
* Report a skipped check or skipped effect as done.
* Promise generated footage, voice-over, music or stock clips: Lionstone Editing works with the
  user's own footage.
