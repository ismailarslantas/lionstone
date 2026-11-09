"""Lionstone Editing: a brief in, a checked video out.

One folder per production. The assistant (or a person) writes ``brief.json``; Lionstone runs
the stages below, records each one in ``production.json`` and writes ``report.md``.

    brief → plan → review → look → render → fx → qa → report

Creative copy (goal, title, chapter names, on-screen text) only ever comes from the brief:
nothing here invents it. A stage that cannot run is recorded as ``skipped`` with a reason.
See docs/editing.md.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from pathlib import Path

STAGES = ("brief", "plan", "review", "look", "render", "fx", "qa", "report")
SOCIAL = ("reels", "shorts", "tiktok")
PLATFORMS = (*SOCIAL, "youtube", "podcast")
LOOK_INTENSITY = {"natural": "subtle", "balanced": "balanced", "dynamic": "bold"}
FINISHED = ("done", "skipped", "partial")

BRIEF_DEFAULTS: dict = {
    "footage": "",
    "goal": "",          # copy: written by the assistant
    "platform": "youtube",
    "language": "",      # empty = detect
    "asr": "auto",       # auto | none
    "intensity": "balanced",
    "content": "talk",
    "style": "minimal",
    "title": "",         # copy
    "subtitle": "",      # copy
    "speakers": [],      # ["Name|Role"]
    "chapters": [],      # ["00:05:10 Title"]
    "captions": "burn",
    "look": True,
    "review": False,
    "fx": [],            # [{"effect": id, "start": s, "end": s, "params": {}}]
}

Log = Callable[[str], None]


class Production:
    def __init__(self, folder: str | Path):
        self.dir = Path(folder)
        self.edit = self.dir / "edit"
        self.out = self.dir / "out"
        self.state_path = self.dir / "production.json"
        self.state: dict = (json.loads(self.state_path.read_text(encoding="utf-8"))
                            if self.state_path.exists() else {"stages": {}})

    @property
    def plan_path(self) -> Path:
        return self.edit / "plan.json"

    def footage(self, brief: dict) -> Path:
        p = Path(brief["footage"])
        return p if p.is_absolute() else self.dir / p

    def final(self, brief: dict) -> Path:
        return self.out / f"{self.footage(brief).stem}.mp4"

    def mark(self, stage: str, status: str, note: str = "") -> None:
        self.state["stages"][stage] = {"status": status, "note": note,
                                       "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.save()

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2, ensure_ascii=False),
                                   encoding="utf-8")


# --- brief -----------------------------------------------------------------------------
def init(folder: str | Path, footage: str = "", **fields) -> Path:
    """Write brief.json, or update the given fields of an existing one."""
    path = Path(folder) / "brief.json"
    brief = (json.loads(path.read_text(encoding="utf-8")) if path.exists()
             else dict(BRIEF_DEFAULTS))
    unknown = set(fields) - set(BRIEF_DEFAULTS)
    if unknown:
        raise ValueError(f"unknown brief fields: {', '.join(sorted(unknown))}")
    if footage:
        brief["footage"] = footage
    brief.update(fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_brief(folder: str | Path) -> dict:
    path = Path(folder) / "brief.json"
    if not path.exists():
        raise FileNotFoundError(f"no brief.json in {folder}: run `lionstone editing init` first")
    return {**BRIEF_DEFAULTS, **json.loads(path.read_text(encoding="utf-8"))}


def validate(brief: dict, folder: str | Path) -> list[str]:
    from .planner import parse_chapter
    from .presets import INTENSITIES
    from .pro.features.agent import CONTENT, STYLES
    errs = []
    if not brief["footage"]:
        errs.append("footage is empty")
    elif not Production(folder).footage(brief).exists():
        errs.append(f"footage not found: {brief['footage']}")
    for key, allowed in (("platform", PLATFORMS), ("intensity", tuple(INTENSITIES)),
                         ("content", CONTENT), ("style", STYLES), ("asr", ("auto", "none")),
                         ("captions", ("burn", "file", "none"))):
        if brief[key] not in allowed:
            errs.append(f"{key} must be one of {', '.join(allowed)} (got {brief[key]!r})")
    for c in brief["chapters"]:
        try:
            parse_chapter(c)
        except ValueError:
            errs.append(f"chapter needs 'HH:MM:SS Title': {c!r}")
    for i, f in enumerate(brief["fx"]):
        if not isinstance(f, dict) or not f.get("effect"):
            errs.append(f"fx[{i}] needs an 'effect' id")
        elif f.get("start") is not None and f.get("end") is not None and f["end"] <= f["start"]:
            errs.append(f"fx[{i}] ({f['effect']}): end must be after start")
    return errs


# --- stages: each returns (status, note) -------------------------------------------------
def _brief(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    errs = validate(brief, prod.dir)
    if errs:
        raise ValueError("brief.json: " + "; ".join(errs))
    return "done", brief["goal"] or "no goal written"


def _plan(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    from .effects import Catalog
    from .pipeline import ASROptions, make_plan
    from .planner import EditOptions, parse_chapter, parse_speaker
    from .plugins import registry
    social = brief["platform"] in SOCIAL
    opts = EditOptions(intensity=brief["intensity"],
                       profile="social" if social else brief["platform"],
                       aspect="9:16" if social else None, title=brief["title"],
                       subtitle=brief["subtitle"], captions=brief["captions"],
                       caption_style="social" if social else "clean",
                       speakers=[parse_speaker(s) for s in brief["speakers"]],
                       chapters=[parse_chapter(c) for c in brief["chapters"]])
    prod.edit.mkdir(parents=True, exist_ok=True)
    plan = make_plan(prod.footage(brief), prod.edit, opts,
                     ASROptions(mode=brief["asr"], language=brief["language"] or None),
                     catalog=Catalog(registry().effect_dirs), log=log)
    n = sum(1 for c in plan.cuts if c.enabled)
    return "done", f"{plan.duration:.1f}s → {plan.output_duration:.1f}s, {n} cuts"


def _review(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    if not brief["review"]:
        return "skipped", "review is off in brief.json"
    if prod.state["stages"].get("review", {}).get("status") == "waiting":
        return "done", "reviewed"
    return "waiting", (f"review the cuts (`lionstone cuts {prod.plan_path}`) and "
                       f"{prod.edit / 'transcript.md'} (apply edits with `lionstone "
                       f"apply-transcript`), then run again")


def _look(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    if not brief["look"]:
        return "skipped", "look is off in brief.json"
    from .models import EditPlan
    from .pro.commands_fx import load_catalog
    from .pro.features import agent
    from .pro.features.entitlements import current
    ent = current()
    cat = load_catalog(ent)
    plan = EditPlan.load(prod.plan_path)
    pr = agent.propose(plan, cat, ent, content=brief["content"], style=brief["style"],
                       intensity=LOOK_INTENSITY[brief["intensity"]],
                       platform=brief["platform"])
    # the render stage burns the captions already
    pr.decisions = [d for d in pr.decisions if "caption" not in d.preset]
    n = agent.apply(plan, pr, cat)
    if any("look-" in d.preset for d in pr.decisions):
        plan.color["preset"] = "none"  # one grade, not two
    plan.save(prod.plan_path)
    if not n:
        return "skipped", "no look or effect fits this plan" + "".join(f"; {x}" for x in pr.notes)
    return "done", f"{n} decisions" + "".join(f"; {x}" for x in pr.notes)


def _render(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    from .effects import Catalog
    from .models import EditPlan
    from .pipeline import options_from_meta, render_and_verify
    from .plugins import registry
    from .pro.commands_fx import load_catalog
    from .pro.features import timeline
    from .pro.features.compile import compile_plan
    from .pro.features.entitlements import current
    from .render import RenderOptions
    plan = EditPlan.load(prod.plan_path)
    notes = []
    if timeline.instances(plan):
        ent = current()
        rep = compile_plan(plan, load_catalog(ent), ent)
        notes += [f"{x['preset']} not compiled: {x['reason']}" for x in rep.skipped]
        plan.save(prod.plan_path)
    o = options_from_meta(plan)
    ro = RenderOptions(aspect=o.aspect, captions=o.captions, caption_style=o.caption_style,
                       denoise=o.denoise, accent=o.accent, font=o.font)
    res, report = render_and_verify(plan, prod.edit, prod.footage(brief).stem + ".edit.mp4", ro,
                                    catalog=Catalog(registry().effect_dirs), log=log)
    notes.insert(0, f"{res.width}x{res.height}, {res.duration:.1f}s")
    return "done", "; ".join(notes)


def _fx(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    rendered = prod.edit / (prod.footage(brief).stem + ".edit.mp4")
    final = prod.final(brief)
    prod.out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(rendered, final)
    if not brief["fx"]:
        return "skipped", "no effects in brief.json"
    from .ff import FFmpegError
    from .pro.features.clipfx import apply_to_clip
    from .pro.features.entitlements import EntitlementError
    from .pro.matte import available, wants
    done, notes = 0, []
    for i, f in enumerate(brief["fx"]):
        tmp = prod.out / f".fx{i}.mp4"
        try:
            apply_to_clip(f["effect"], final, tmp, params=f.get("params") or {},
                          start=f.get("start"), end=f.get("end"))
        except (FFmpegError, EntitlementError, KeyError, ValueError, RuntimeError) as e:
            tmp.unlink(missing_ok=True)
            notes.append(f"{f['effect']} skipped: {e}")
            continue
        shutil.move(tmp, final)
        done += 1
        pid = f["effect"] if "." in f["effect"] else f"lionstone.{f['effect']}"
        if wants([pid]) and not available():
            notes.append(f"{f['effect']}: person matte unavailable (pip install "
                         "\"lionstone[vision]\"), plain version used")
        log(f"   fx {f['effect']} applied")
    status = "done" if done == len(brief["fx"]) else "partial" if done else "skipped"
    return status, "; ".join([f"{done}/{len(brief['fx'])} effects applied", *notes])


def _qa(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    from . import qa as qa_mod
    from .effects import Catalog
    from .models import EditPlan
    from .plugins import registry
    report = qa_mod.run_qa(prod.final(brief), EditPlan.load(prod.plan_path),
                           catalog=Catalog(registry().effect_dirs))
    qa_mod.save(report, prod.out)
    prod.state["deliverable"] = report.deliverable
    skipped = [c.name for c in report.checks if c.status == "skipped"]
    return "done", (f"deliverable: {'yes' if report.deliverable else 'NO'}"
                    + (f"; skipped checks: {', '.join(skipped)}" if skipped else ""))


def _report(prod: Production, brief: dict, log: Log) -> tuple[str, str]:
    path = prod.dir / "report.md"
    prod.mark("report", "done", str(path))  # so the report lists itself as done
    path.write_text(report_markdown(prod, brief), encoding="utf-8")
    return "done", str(path)


STAGE_FNS: dict[str, Callable[[Production, dict, Log], tuple[str, str]]] = {
    "brief": _brief, "plan": _plan, "review": _review, "look": _look, "render": _render,
    "fx": _fx, "qa": _qa, "report": _report,
}


def report_markdown(prod: Production, brief: dict) -> str:
    from .models import EditPlan
    st = prod.state["stages"]
    ok = prod.state.get("deliverable")
    lines = [f"# Production report: {brief['title'] or prod.dir.name}", "",
             f"**Goal:** {brief['goal'] or '(none written)'}  ",
             f"**Video:** `{prod.final(brief)}`  ",
             f"**Deliverable:** {'yes' if ok else 'NO' if ok is False else 'not checked'}", "",
             "## Stages", "", "| Stage | Status | Note |", "|---|---|---|"]
    lines += [f"| {s} | {st.get(s, {}).get('status', 'pending')} | "
              f"{st.get(s, {}).get('note', '')} |" for s in STAGES]
    if prod.plan_path.exists():
        from .pro.features import timeline
        plan = EditPlan.load(prod.plan_path)
        lines += ["", "## Decisions", ""]
        lines += [f"* cut {c.start:.2f}-{c.end:.2f}s ({c.kind}): {c.reason}"
                  for c in plan.cuts if c.enabled]
        lines += [f"* {i.preset.replace('lionstone.', '')}: {i.reason}"
                  for i in timeline.instances(plan) if i.created_by == "agent"]
        lines += [f"* effect {f['effect']} from {f.get('start') or 0}s to "
                  f"{f.get('end') if f.get('end') is not None else 'the end'}"
                  for f in brief["fx"]]
    if (prod.out / "qa.md").exists():
        lines += ["", f"Full QA report: `{prod.out / 'qa.md'}` (skipped checks did not run)."]
    return "\n".join(lines) + "\n"


# --- runner ----------------------------------------------------------------------------
def status(folder: str | Path) -> dict:
    prod = Production(folder)
    st = prod.state["stages"]
    nxt = next((s for s in STAGES if st.get(s, {}).get("status") not in FINISHED), None)
    return {"folder": str(prod.dir), "stages": {s: st.get(s, {"status": "pending"})
                                                 for s in STAGES},
            "next": nxt, "deliverable": prod.state.get("deliverable")}


def run(folder: str | Path, from_stage: str | None = None, log: Log = print) -> dict:
    """Run every stage that is not finished; stop at a review wait or a failure."""
    if from_stage and from_stage not in STAGES:
        raise ValueError(f"--from must be one of {', '.join(STAGES)}")
    prod = Production(folder)
    brief = load_brief(folder)
    if from_stage:
        for s in STAGES[STAGES.index(from_stage):]:
            prod.state["stages"].pop(s, None)
        prod.state.pop("deliverable", None)
    for s in STAGES:
        if prod.state["stages"].get(s, {}).get("status") in FINISHED:
            continue
        log(f"▶ {s}")
        try:
            result, note = STAGE_FNS[s](prod, brief, log)
        except Exception as e:  # recorded, then re-raised so the caller sees the error
            prod.mark(s, "failed", f"{type(e).__name__}: {e}")
            raise
        prod.mark(s, result, note)
        log(f"   {result}: {note}")
        if result == "waiting":
            break
    return status(folder)
