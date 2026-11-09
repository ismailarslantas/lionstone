"""Apply one effect to a whole clip at its own size: `lionstone fx clip glass-type in.mp4 -o out.mp4`.

The same builders as the export, preview and showcase (and the person matte when
the effect uses it). Audio is copied. Used by the OpenMontage integration.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


def apply_to_clip(preset: str, clip: str | Path, out: str | Path, *, params: dict | None = None,
                  start: float | None = None, end: float | None = None) -> Path:
    """Render `preset` over `clip` (window start..end seconds, default: the whole clip)."""
    from lionstone.ff import run
    from lionstone.ingest import probe
    from lionstone.render import _script_flag

    from .. import matte as _matte
    from .catalog import Catalog
    from .params import resolve
    from .renderers import ffmpeg_adapter as fa

    p = Catalog().get(preset)
    if p.pipeline != "filter" or p.renderer_id not in fa.FILTERS:
        raise ValueError(f"{p.name} has no filter renderer; use a plan for it")
    src = Path(clip).resolve()
    info = probe(src)
    v = info.video
    if v is None or not v.width or not v.height:
        raise ValueError(f"{src.name} has no video stream")
    W, H = v.width // 2 * 2, v.height // 2 * 2
    fps = round(v.avg_fps or v.fps or 30.0, 3)
    a = max(0.0, start or 0.0)
    b = min(info.duration, end) if end else info.duration
    if b <= a:
        raise ValueError("the effect window is empty")
    mf = _matte.ensure(src) if _matte.wants([p.id]) else None
    ctx = fa.RCtx(W, H, fps, info.duration, matte=mf is not None)
    frag = fa.FILTERS[p.renderer_id](resolve(p.parameters, params), [(a, b)], ctx)
    graph = (f"[0:v]scale={W}:{H},fps={fps},setsar=1,format=yuv420p[s];"
             f"[s]{frag},format=yuv420p[o]")
    inputs = ["-i", str(src)]
    if ctx.mattes:
        inputs += ["-i", str(mf)]
        graph = _matte.graph_inputs(1, ctx.mattes, W, H, fps) + ";" + graph
    wd = Path(tempfile.mkdtemp(prefix="lsclip-"))
    try:
        (wd / "g.txt").write_text(graph, encoding="utf-8")
        dst = Path(out).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        audio = ["-map", "0:a?", "-c:a", "copy"]
        run(["ffmpeg", "-hide_banner", "-y", "-loglevel", "error", *inputs, _script_flag(), "g.txt",
             "-map", "[o]", *audio, "-c:v", "libx264", "-crf", "18", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", f"{info.duration:.3f}",
             str(dst)], cwd=wd)
        return dst
    finally:
        shutil.rmtree(wd, ignore_errors=True)
