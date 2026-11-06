"""`lionstone reels make`: raw footage → branded, checked, publish-ready Reel.

plan (9:16, brand style, word captions in the brand's language) → brand kit → render → SFX + music
→ final QA on the mixed file → cover variants → caption file → editing room →
delivery report. Each step writes plain files into the reel's folder.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .. import qa as qa_mod
from ..cli import _catalog
from ..cli import main as cli_main
from ..ff import has_filter
from ..ingest import probe
from ..models import EditPlan, QAReport
from . import looks, memory, sound, visual
from .brand import Brand, home, slug
from .choices import load_choices, missing, summary_lines
from .content import DELIVERY_DIR, EDIT_DIR, LEGACY_DIRS, RAW_DIR, Reel, lint, reel_dir
from .identity import identity_dir
from .room import write_room

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
WHOLE_FX = ("brand-frame", "progress-rail")

ROWS = [  # report row → QA checks behind it
    ("Repeat scan", ["reels_repeats"]),
    ("Cut points", ["word_integrity", "join_clicks", "low_confidence_cuts"]),
    ("Script comparison", ["reels_script_match"]),
    ("Text overflow", ["reels_text_fit", "graphics_rules"]),
    ("Loudness", ["loudness", "true_peak"]),
    ("Picture", ["decode_full", "format", "plan_duration", "black_frames", "frozen_frames",
                 "av_length"]),
]


def find_footage(folder: Path, reel: Reel | None) -> Path:
    if reel and reel.footage:
        p = Path(reel.footage[0])
        return p if p.is_absolute() else folder / p
    for sub in (folder / RAW_DIR, folder / LEGACY_DIRS[RAW_DIR], folder):
        vids = sorted(p for p in sub.glob("*") if p.suffix.lower() in VIDEO_EXT)
        if vids:
            return vids[0]
    raise FileNotFoundError(f"no footage found: put the video in {folder / RAW_DIR}")


def plan_args(brand: Brand, reel: Reel | None, src: Path, out: Path, extra: list[str]) -> list[str]:
    st = brand.style
    caption = st.get("caption_style", "karaoke")
    color = st.get("color", "punchy")
    args = ["plan", str(src), "-o", str(out), "--aspect", st.get("aspect", "9:16"),
            "--intensity", st.get("intensity", "dynamic"), "--profile", "social",
            "--captions", "none" if caption == "none" else "burn",
            "--color", "natural" if color == "learned" else color, "--accent", brand.accent,
            "--denoise", st.get("denoise", "light"), "--reframe", st.get("reframe", "center")]
    if caption != "none":
        args += ["--caption-style", caption]
    learned = identity_dir(brand) / "style.json"
    if color == "learned" and learned.exists():  # measured colour, on top of a light base
        args += ["--x", f"style={learned.resolve()}", "--x", "style_apply=color"]
    if brand.language and "--language" not in extra:
        args += ["--language", brand.language]
    if brand.font:
        args += ["--font", brand.font]
    if reel and st.get("hook_title", True) and reel.hooks:
        fx = st.get("title_effect", "T02")
        width = {"L01": 15, "L02": 15}.get(fx, 18)
        hook = visual.title_lines(reel.hooks[0], width) if fx in ("T02", "L01", "L02") else reel.hooks[0]
        args += ["--title", hook, "--title-effect", fx]
    return args + extra


def _row_status(report: QAReport, names: list[str]) -> tuple[str, str]:
    checks = [c for c in report.checks if c.name in names]
    if not checks:
        return "Skipped", "the check did not run"
    ran = [c for c in checks if c.status != "skipped"]
    if not ran:
        return "Skipped", "; ".join(c.detail for c in checks)[:120]
    if any(c.status == "failed" for c in ran):
        return "Fix", "; ".join(c.detail for c in ran if c.status == "failed")[:120]
    if any(c.status == "warning" for c in ran):
        return "Review", "; ".join(c.detail for c in ran if c.status == "warning")[:120]
    return "Clean", ""


def review_reasons(report: QAReport, reel: Reel | None) -> list[str]:
    """Not broken, but a person must look before this is called ready: the video may not
    say what the script says, or the check that would tell could not run."""
    by_name = {c.name: c for c in report.checks}
    out = []
    for name, label in (("reels_script_match", "script difference"), ("reels_repeats", "repeat left in")):
        c = by_name.get(name)
        if c and c.status == "warning":
            out.append(f"{label} ({c.detail})")
    c = by_name.get("reels_script_match")
    no_words = by_name.get("reels_repeats") and by_name["reels_repeats"].status == "skipped"
    if no_words or (reel and reel.script.strip() and (c is None or c.status == "skipped")):
        out.append("no speech recognition: no captions, script not compared "
                   "(pip install \"lionstone[whisper]\")")
    return out


def report_md(brand: Brand, reel: Reel | None, report: QAReport, extras: dict) -> tuple[str, bool]:
    high = [i for i in report.issues if i.severity in ("critical", "high")]
    blocked = not report.deliverable or bool(high) or bool(extras.get("lint_errors"))
    review = [*review_reasons(report, reel), *extras.get("review", [])]
    ready = not blocked and not review
    verdict = ("FIX NEEDED 🛑" if blocked else
               "NEEDS REVIEW 👀" if review else "READY TO DELIVER ✅")
    lines = [f"# {brand.name} · {reel.topic if reel else Path(report.file).stem}", "",
             f"**{verdict}**", "",
             *([f"Look at this before delivering: {'; '.join(review)}.", ""] if review else []),
             "| Check | Status | Note |", "|---|---|---|"]
    for label, names in ROWS:
        s, note = _row_status(report, names)
        lines.append(f"| {label} | {s} | {note} |")
    lines.append(f"| Covers | {'Clean' if extras.get('covers') else 'None'} | "
                 f"{len(extras.get('covers', []))} version(s) |")
    le = extras.get("lint_errors", [])
    lines.append(f"| Copy (hook/script/caption) | {'Fix' if le else 'Clean'} | "
                 f"{'; '.join(le)[:120]} |")
    lines += ["", f"Video: `{Path(report.file).name}` · {extras.get('duration', 0):.1f} s",
              f"SFX: {len(extras.get('cues', []))} · Music: {extras.get('music') or 'none'}", ""]
    if extras.get("choices"):
        lines += ["## Brand setup", *summary_lines(extras["choices"]), ""]
    if report.issues:
        lines.append("## Findings")
        for i in report.issues:
            at = f" @ {i.at:.1f}s" if isinstance(i.at, (int, float)) else ""
            lines.append(f"- {qa_mod.SEV_ICON.get(i.severity, '')} {i.check}{at}: {i.message}")
    skipped = [c for c in report.checks if c.status == "skipped"]
    if skipped:
        lines += ["", "## Checks that did not run"]
        lines += [f"- {c.name}: {c.detail}" for c in skipped]
    return "\n".join(lines) + "\n", ready


def apply_effects(plan_path: Path, brand: Brand) -> list[str]:
    """Turn the brand's effects choice into plan instances, each with a reason. Captions and
    colour were already chosen, so the agent's own caption and look picks are left out."""
    choice = brand.style.get("effects") or "none"
    if choice == "none":
        return []
    from ..pro.commands_fx import load_catalog
    from ..pro.features import agent, timeline
    from ..pro.features.entitlements import current
    ent = current()
    cat = load_catalog(ent)
    plan = EditPlan.load(plan_path)
    notes: list[str] = []
    if choice == "look:bold":
        choice = "agent:social"  # the zooms; the card is one of the look's graphics
    elif choice.startswith("look:"):
        return []
    if choice.startswith("agent:"):
        pr = agent.propose(plan, cat, ent, content="vlog", style=choice[6:],
                           intensity="balanced", platform="reels")
        keep_look = brand.style.get("color") == "none"
        pr.decisions = [d for d in pr.decisions if "caption" not in d.preset
                        and (keep_look or "look-" not in d.preset)]
        n = agent.apply(plan, pr, cat)
        notes.append(f"{choice}: {n} decisions")
    elif choice.startswith("fx:"):
        preset = cat.get("lionstone." + choice[3:].replace("lionstone.", ""))
        if not preset.usable:
            raise ValueError(f"{preset.name} is not usable: {preset.implementationStatus}")
        params = {}
        for key, color in (("accent", brand.accent), ("color", brand.accent),
                           ("highlight", brand.accent), ("bg", brand.colors.get("primary"))):
            if key in preset.parameters and color:
                params[key] = color
        whole = choice[3:] in WHOLE_FX or not plan.segments
        anchor = ({"type": "global"} if whole else
                  {"type": "segment", "start": plan.segments[0].start, "end": plan.segments[0].end})
        timeline.add(plan, timeline.FxInstance(
            preset=preset.id, version=preset.version, anchor=anchor, params=params,
            created_by="agent", reason=f"brand choice: {choice}"))
        notes.append(f"{preset.name}: {anchor['type']}")
    else:
        raise ValueError(f"unknown effect choice: {choice}")
    plan.save(plan_path)
    return notes


def make(brand: Brand, *, folder: Path | None = None, footage: Path | None = None,
         extra: list[str] | None = None, fast: bool = False, covers: int | None = None,
         music: str | None = None, sfx: bool | None = None, keep_plan: bool = False,
         log=print) -> dict:
    reel = Reel.load(folder) if folder and (folder / "reel.json").exists() else None
    base = folder or Path(footage).parent
    src = Path(footage) if footage else find_footage(base, reel)
    out = reel_dir(folder, EDIT_DIR) if folder else src.with_name(f"{src.stem}_reels")
    deliver = reel_dir(folder, DELIVERY_DIR) if folder else out / DELIVERY_DIR
    deliver.mkdir(parents=True, exist_ok=True)
    for old in ("report.md", "report.json", "rapor.md", "rapor.json"):  # a failed run must not leave an old verdict behind
        (deliver / old).unlink(missing_ok=True)
    memory.remember(brand.slug, brand.name, home(brand), use=True)

    log(f"🎬 {brand.name} · {src.name}")
    chosen = load_choices(brand)
    if missing(chosen):
        log("🧭 Brand setup is incomplete, using defaults for what is missing: "
            f"{', '.join(missing(chosen))} → `lionstone reels setup`")
    covers = covers if covers is not None else int(brand.style.get("covers", 3))
    plan_path = out / "plan.json"
    if keep_plan and not plan_path.exists():
        raise FileNotFoundError(f"--keep-plan: no plan at {plan_path}")
    if not keep_plan:  # --keep-plan: the room's cuts and caption fixes live in plan.json
        code = cli_main(plan_args(brand, reel, src, out, list(extra or [])))
        if code != 0:
            raise RuntimeError(f"the plan step failed (code {code})")
        if brand.kit:
            code = cli_main(["brand", "apply", str(plan_path), brand.kit])
            if code != 0:
                raise RuntimeError(f"could not apply brand kit: {brand.kit}")
        for note in apply_effects(plan_path, brand):
            log(f"✨ {note}")
    plan = EditPlan.load(plan_path)
    for note in looks.apply_look(plan, brand, reel):
        log(f"✨ {note}")
    for g in plan.graphics:  # a talking head: the hook goes above the face, not over it
        if g.layer == "titles":
            g.params.setdefault("position", "top")
    plan.meta.setdefault("reels", {}).update({
        "brand": brand.name, "script": reel.script if reel else "",
        "topic": reel.topic if reel else "", "cta": (reel.cta if reel else "") or brand.cta,
        "width": 1080, "height": 1920})
    plan.save(plan_path)

    from ..pro.captions_pro import register_karaoke
    from .look_fx import register_captions
    register_karaoke(brand.accent)  # captions in this brand's colour, not the default gold
    register_captions(brand.accent)
    render_path = out / "render.mp4"
    render_path.unlink(missing_ok=True)  # never mix a stale render if this one fails
    has_fx = bool((EditPlan.load(plan_path).meta.get("lionstone_fx") or {}).get("instances"))
    cli_main([*(["fx", "render"] if has_fx else ["render"]), str(plan_path), "-o", str(render_path),
              *(["--fast"] if fast else [])])
    if not render_path.exists():
        raise RuntimeError("the render step produced no output")
    plan = EditPlan.load(plan_path)
    rv = probe(render_path).video
    if rv:  # measure text against the size that was really rendered
        plan.meta["reels"].update(width=rv.width, height=rv.height)
        plan.save(plan_path)

    stem = slug(reel.topic)[:40] if reel and reel.topic else src.stem
    final = deliver / f"{brand.slug}-{stem}.mp4"
    use_sfx = brand.style.get("sfx", True) if sfx is None else sfx
    cues: list[sound.Cue] = []
    if use_sfx:
        if not sound.library():
            log("🔊 Building the SFX starter pack")
            sound.build_pack()
        custom = (folder / "sfx.json") if folder else None
        cues = sound.load_cues(custom) if custom and custom.exists() else sound.auto_cues(
            plan, density=brand.style.get("sfx_density", "sparse"))
    music = music or brand.style.get("music") or None
    log(f"🔊 Sound: {len(cues)} effects · music: {Path(music).name if music else 'none'}")
    mixed = sound.mix(render_path, final, cues=cues, music=music,
                      music_volume=float(brand.style.get("music_volume", 0.18)))

    info = probe(final)
    # the target comes from the plan and the 9:16 promise, not from the file under test
    target = {"duration": plan.output_duration, "width": 1080, "height": 1920,
              "fps": rv.fps if rv else 30}
    if brand.style.get("aspect", "9:16") != "9:16" and rv:
        target.update(width=rv.width, height=rv.height)
    report = qa_mod.run_qa(final, plan, catalog=_catalog(), expect=target)
    qa_mod.save(report, deliver, "qa")

    cover_files = []
    texts = (reel.cover_text if reel and reel.cover_text else
             ([reel.hooks[0]] if reel and reel.hooks else []))
    for k, at in enumerate(visual.cover_source_times(plan, covers)):
        if not texts:
            break
        txt = texts[k % len(texts)]
        c = visual.make_cover(Path(plan.source), deliver / f"cover-{k + 1}.jpg", txt, at=at,
                              colors=brand.colors, font=brand.font,
                              language=brand.language)
        cover_files.append(c)

    lint_errors = []
    if reel:
        findings = lint(reel, brand)
        lint_errors = [f"{f.field}: {f.message}" for f in findings if f.level == "error"]
        tags = " ".join(t if t.startswith("#") else f"#{t}" for t in reel.hashtags)
        (deliver / "caption.txt").write_text(
            reel.caption.strip() + ("\n\n" + tags if tags else "") + "\n", encoding="utf-8")
        (deliver / "copy-check.json").write_text(
            json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=1), "utf-8")

    write_room(plan, out / "room.html", f"{brand.name} · editing room")
    absent = [f"FFmpeg has no {flt}: {what}" for flt, what, needed in (
        ("subtitles", "captions could not be burned in", bool(plan.words)),
        ("drawtext", "cover and title text could not be drawn", True)) if needed and not has_filter(flt)]
    extras = {"covers": cover_files, "cues": mixed["cues"], "music": mixed["music"],
              "duration": info.duration, "lint_errors": lint_errors, "review": absent,
              "choices": chosen}
    md, ready = report_md(brand, reel, report, extras)
    (deliver / "report.md").write_text(md, encoding="utf-8")
    (deliver / "report.json").write_text(json.dumps(
        {"ready": ready, "qa": report.to_dict(), **extras}, ensure_ascii=False, indent=1,
        default=str), "utf-8")
    if reel:
        reel.status = "ready" if ready else "review"
        reel.save(folder / "reel.json")
    log(md.split("**")[1] + f" → {deliver / 'report.md'}")
    return {"ready": ready, "video": str(final), "deliver": str(deliver),
            "room": str(out / "room.html"), "plan": str(plan_path)}
