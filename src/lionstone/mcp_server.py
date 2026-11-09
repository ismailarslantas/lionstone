"""Lionstone as an MCP server — let Claude, Cursor or any MCP client edit video.

    pip install "lionstone[mcp]"
    lionstone mcp            # stdio transport

Claude Desktop / Claude Code config::

    {"mcpServers": {"lionstone": {"command": "lionstone", "args": ["mcp"]}}}

Tools return compact JSON so an agent can read the plan, reason about cuts,
restore or remove material, render and inspect the QA report — the same loop a
human editor runs.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from . import qa as qa_mod
from . import textedit
from .effects import Catalog
from .ingest import probe
from .models import EditPlan
from .pipeline import ASROptions, make_plan, options_from_meta, render_and_verify, replan_graphics
from .planner import EditOptions, parse_chapter, parse_speaker
from .plugins import registry
from .render import RenderOptions
from .speech import segments_from_cuts

INSTRUCTIONS = (
    "Lionstone edits spoken-word video (podcasts, interviews, talks). Typical loop: "
    "plan_edit → review cuts/transcript → restore_cuts or edit_transcript → render_plan → "
    "read the QA result. For a whole production (brief → checked video) use editing_init "
    "and editing_run. Never claim a video is ready unless render_plan or editing_run returned "
    "deliverable=true."
)


def _server():
    try:  # MCP Python SDK 2.x
        from mcp.server.mcpserver import MCPServer
        return MCPServer("lionstone", instructions=INSTRUCTIONS)
    except ImportError:
        try:  # 1.x
            from mcp.server.fastmcp import FastMCP
            return FastMCP("lionstone", instructions=INSTRUCTIONS)
        except ImportError as e:  # pragma: no cover
            raise SystemExit('MCP support needs: pip install "lionstone[mcp]"') from e


def _quiet(fn, *args, **kwargs):
    """Pipeline logs go to stdout; keep the stdio transport clean."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def _summary(plan: EditPlan) -> dict:
    return {
        "source_seconds": round(plan.duration, 2),
        "output_seconds": round(plan.output_duration, 2),
        "intensity": plan.intensity,
        "cuts": [{"id": c.id, "start": c.start, "end": c.end, "kind": c.kind,
                  "reason": c.reason, "confidence": c.confidence, "enabled": c.enabled}
                 for c in plan.cuts],
        "graphics": [{"id": g.id, "effect": g.effect, "at": g.at, "text": g.text}
                     for g in plan.graphics],
        "has_transcript": bool(plan.words),
    }


def build():
    app = _server()

    @app.tool()
    def inspect_media(path: str) -> str:
        """Read codec, resolution, frame rate, duration and validation warnings of a media file."""
        info = probe(path)
        return json.dumps(info.__dict__, default=lambda o: o.__dict__)

    @app.tool()
    def plan_edit(path: str, out_dir: str = "", intensity: str = "balanced",
                  profile: str = "youtube", title: str = "", speakers: list[str] | None = None,
                  chapters: list[str] | None = None, language: str = "",
                  no_asr: bool = False) -> str:
        """Analyze a recording and create an edit plan (no render).

        intensity: natural | balanced | dynamic. speakers: ["Name|Title"]. chapters:
        ["00:05:10 Title"]. Returns the plan summary with every cut and its reason."""
        src = Path(path)
        outdir = Path(out_dir or f"{src.stem}_lionstone")
        outdir.mkdir(parents=True, exist_ok=True)
        opts = EditOptions(intensity=intensity, profile=profile, title=title,
                           speakers=[parse_speaker(s) for s in speakers or []],
                           chapters=[parse_chapter(c) for c in chapters or []])
        catalog = Catalog(registry().effect_dirs)
        plan, log = _quiet(make_plan, src, outdir, opts,
                           ASROptions(mode="none" if no_asr else "auto",
                                      language=language or None), catalog=catalog)
        return json.dumps({"plan_path": str(outdir / "plan.json"), "log": log[-1500:],
                           **_summary(plan)}, ensure_ascii=False)

    @app.tool()
    def get_transcript(plan_path: str) -> str:
        """Return the editable transcript (one tagged sentence per line)."""
        plan = EditPlan.load(plan_path)
        text = textedit.export(plan)
        plan.save(plan_path)
        return text

    @app.tool()
    def edit_transcript(plan_path: str, transcript_markdown: str) -> str:
        """Apply an edited transcript: deleted lines are cut, moved lines reordered."""
        plan = EditPlan.load(plan_path)
        stats = textedit.apply(plan, transcript_markdown)
        replan_graphics(plan, Catalog(registry().effect_dirs))
        plan.save(plan_path)
        return json.dumps({**stats, "output_seconds": round(plan.output_duration, 2)})

    @app.tool()
    def restore_cuts(plan_path: str, cut_ids: list[str], restore: bool = True) -> str:
        """Restore (undo) cuts by id, or re-enable them with restore=false."""
        plan = EditPlan.load(plan_path)
        for c in plan.cuts:
            if c.id in cut_ids:
                c.enabled = not restore
        plan.segments = segments_from_cuts(plan.cuts, plan.duration, plan.words)
        replan_graphics(plan, Catalog(registry().effect_dirs))
        plan.save(plan_path)
        return json.dumps(_summary(plan), ensure_ascii=False)

    @app.tool()
    def render_plan(plan_path: str, captions: str = "burn", aspect: str = "") -> str:
        """Render the plan with FFmpeg and run QA. Returns output paths and QA verdict."""
        plan = EditPlan.load(plan_path)
        outdir = Path(plan_path).parent
        opts = options_from_meta(plan)
        ropts = RenderOptions(aspect=aspect or opts.aspect, captions=captions,
                              caption_style=opts.caption_style, denoise=opts.denoise,
                              accent=opts.accent, font=opts.font)
        (res, report), log = _quiet(render_and_verify, plan, outdir,
                                    Path(plan.source).stem + ".edit.mp4", ropts,
                                    catalog=Catalog(registry().effect_dirs))
        return json.dumps({"video": str(res.output), "captions": res.captions,
                           "deliverable": report.deliverable,
                           "qa_markdown": qa_mod.to_markdown(report)}, ensure_ascii=False)

    @app.tool()
    def list_effects(category: str = "", style: str = "", tier: str = "all") -> str:
        """List title / lower-third effects with tier and timing."""
        cat = Catalog(registry().effect_dirs)
        unlocked = registry().tiers
        return json.dumps([{"id": e.id, "name": e.name, "tier": e.tier, "category": e.category,
                            "style": e.style, "seconds": e.total, "locked": e.tier not in unlocked,
                            "description": e.description}
                           for e in cat.filter(category=category or None, style=style or None,
                                               tier=tier)])

    @app.tool()
    def editing_init(folder: str, footage: str = "", brief: dict | None = None) -> str:
        """Lionstone Editing: write or update brief.json in a production folder.

        brief keys: goal, platform (reels|shorts|tiktok|youtube|podcast), language, asr,
        intensity, content, style, title, subtitle, speakers, chapters, captions, look,
        review, fx ([{"effect", "start", "end", "params"}]). Write all copy yourself."""
        from . import editing
        path = editing.init(folder, footage, **(brief or {}))
        return json.dumps({"brief_path": str(path),
                           "problems": editing.validate(editing.load_brief(folder), folder)},
                          ensure_ascii=False)

    @app.tool()
    def editing_run(folder: str, from_stage: str = "") -> str:
        """Lionstone Editing: run brief → plan → review → look → render → fx → qa → report.

        Stops at review when the brief asks for it (run again to continue). Returns each
        stage's status, the next stage and deliverable."""
        from . import editing
        try:
            st, log = _quiet(editing.run, folder, from_stage or None, log=print)
        except Exception as e:  # the failed stage is recorded in production.json
            return json.dumps({"error": f"{type(e).__name__}: {e}",
                               **editing.status(folder)}, ensure_ascii=False)
        return json.dumps({**st, "log": log[-1500:]}, ensure_ascii=False)

    @app.tool()
    def editing_status(folder: str) -> str:
        """Lionstone Editing: read the stages of a production (production.json)."""
        from . import editing
        return json.dumps(editing.status(folder), ensure_ascii=False)

    return app


def main() -> None:
    build().run()
