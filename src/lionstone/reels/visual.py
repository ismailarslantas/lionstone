"""Cover variants and on-screen text checks for vertical video.

Instagram shows a 9:16 Reel cover cropped to 3:4 in the profile grid, and puts its
own UI over the bottom ~20 % and the right edge. Covers here keep text inside the
grid-safe centre; the text check flags graphics and captions likely to overflow.
"""

from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path

from ..effects.ffmpeg_fx import filter_path
from ..ff import font_path, has_filter, run
from ..ingest import probe
from ..models import EditPlan
from .content import tr_upper

CHAR_W = 0.56  # average glyph width / font size for sans titles (estimate)
UI_BOTTOM = 0.20  # Reels UI: caption, audio, buttons
UI_RIGHT = 0.12
UI_TOP = 0.10


def wrap(text: str, width: int = 16) -> list[str]:
    lines: list[str] = []
    for para in text.splitlines() or [""]:
        lines += textwrap.wrap(para, width=width, break_long_words=False) or [""]
    return lines


def fit_size(lines: list[str], box_w: float, box_h: float, max_size: int) -> int:
    longest = max((len(x) for x in lines), default=1) or 1
    by_w = box_w / (longest * CHAR_W)
    by_h = box_h / (len(lines) * 1.22)
    return int(max(24, min(max_size, by_w, by_h)))


def cover_frames(video: Path, n: int = 3) -> list[float]:
    d = probe(video).duration
    picks = [0.12, 0.38, 0.62, 0.85][:max(1, n)]
    return [round(d * p, 2) for p in picks]


def make_cover(video: Path, out: Path, text: str, *, at: float, colors: dict[str, str],
               font: str | None = None, size: tuple[int, int] = (1080, 1920),
               language: str = "tr") -> dict:
    W, H = size
    caps = tr_upper(text) if language == "tr" else text.upper()
    lines = wrap(caps if len(text) < 40 else text, 14 if len(text) < 40 else 18)
    # grid-safe band: centre 3:4 crop is W x (W*4/3); keep text in its middle 70 %
    band_h = W * 4 / 3
    upper = text.isupper() or len(text) < 40
    box_w, box_h = W * (0.72 if upper else 0.84), band_h * 0.42  # capitals run wider
    fs = fit_size(lines, box_w, box_h, max_size=int(W * 0.115))
    line_h = int(fs * 1.22)
    block_h = line_h * len(lines)
    y0 = int(H * 0.68 - block_h / 2)  # under a talking head's face, inside the 3:4 grid crop
    fontfile = font_path(font)
    out.parent.mkdir(parents=True, exist_ok=True)
    c_text = colors.get("text", "#FFFFFF").lstrip("#")
    c_box = colors.get("primary", "#111114").lstrip("#")
    c_acc = colors.get("accent", "#E8B04B").lstrip("#")
    vf = [f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
          "eq=brightness=-0.06:saturation=1.08"]
    notes = []
    with tempfile.TemporaryDirectory() as td:
        if has_filter("drawtext"):
            pad = int(fs * 0.35)
            vf.append(f"drawbox=x={int(W * 0.06)}:y={y0 - pad}:w={int(W * 0.88)}:"
                      f"h={block_h + 2 * pad}:color=0x{c_box}@0.72:t=fill")
            vf.append(f"drawbox=x={int(W * 0.06)}:y={y0 + block_h + pad}:w={int(W * 0.88)}:"
                      f"h={max(6, fs // 9)}:color=0x{c_acc}:t=fill")
            for i, line in enumerate(lines):
                tf = Path(td) / f"l{i}.txt"
                tf.write_text(line, encoding="utf-8")
                ff = f"fontfile={filter_path(fontfile)}:" if fontfile else ""
                vf.append(f"drawtext={ff}textfile={tf.name}:fontsize={fs}:fontcolor=0x{c_text}:"
                          f"x=(w-text_w)/2:y={y0 + i * line_h}")
        else:
            notes.append("ffmpeg has no drawtext: cover exported without text")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{at:.2f}",
             "-i", str(Path(video).resolve()), "-frames:v", "1", "-vf", ",".join(vf),
             "-q:v", "2", "-update", "1", str(out.resolve())], cwd=td)
    return {"file": str(out), "at": at, "text": text, "font_size": fs, "lines": len(lines),
            "notes": notes}


def title_lines(text: str, width: int = 18) -> str:
    """Pre-wrap a hook for vertical title effects: 'line one / line two'."""
    return " / ".join(wrap(text.replace("/", " "), width))


def _layout(effect: str, layer: str, text: str, W: int, H: int) -> tuple[list[str], float]:
    """Lines and font size the way the Lionstone builders lay this effect out."""
    if effect == "T01":  # word pop: one word at a time
        return text.split(), min(H * 0.1, W * 0.12)
    if effect == "L01":  # editorial stack: the last line is the large one
        lines = [x.strip() for x in text.split("/")]
        return lines, W * 0.115 if len(lines) == 1 else W * 0.085
    if effect == "L02":  # glow headline
        return [x.strip() for x in text.split("/")], W * 0.082
    if effect in ("L03", "L04", "L05", "L06"):  # sized and clipped by their own builders
        return [], 0.0
    if effect == "T02":  # phrase build: lines split on "/"
        lines = [x.strip() for x in text.split("/")] if "/" in text else wrap(text, 22)
        return lines, min(H * 0.065, W * 0.07)
    return text.splitlines() or [text], H * (0.075 if layer == "titles" else 0.036)


def text_findings(plan: EditPlan, width: int = 1080, height: int = 1920,
                  caption_ratio: float = 0.058) -> list[dict]:
    """Estimate overflow for graphics text and caption lines (no OCR: labelled estimate)."""
    out = []
    usable = width * (1 - UI_RIGHT) * 0.92
    for g in plan.graphics:
        for field_name, txt in (("text", g.text), ("subtext", g.subtext)):
            if not txt:
                continue
            lines, fs = _layout(g.effect if field_name == "text" else "", g.layer, txt,
                                width, height)
            if field_name == "subtext":
                fs *= 0.45
            fs = float(g.params.get("size", fs))
            for line in lines:
                need = len(line) * fs * CHAR_W
                if need > usable:
                    out.append({"check": "text_overflow", "at": g.at, "graphic": g.id,
                                "severity": "high" if need > usable * 1.15 else "medium",
                                "message": f"'{line[:40]}' ≈{need:.0f}px > {usable:.0f}px "
                                           f"safe width (estimate)"})
        y = g.params.get("y")
        if isinstance(y, (int, float)) and y > 1 - UI_BOTTOM:
            out.append({"check": "safe_zone", "at": g.at, "graphic": g.id, "severity": "medium",
                        "message": "text sits under the Reels UI (bottom 20%)"})
    cap_fs = height * caption_ratio
    max_chars = int(usable / (cap_fs * CHAR_W))
    for w in [w for w in plan.words if len(w.text) > max_chars][:5]:
        out.append({"check": "caption_overflow", "at": plan.source_to_output(w.start),
                    "severity": "medium",
                    "message": f"'{w.text}' may not fit on one line (≤{max_chars} characters)"})
    return out


def cover_source_times(plan: EditPlan, n: int = 3) -> list[float]:
    """Cover frames from the raw footage (no burned captions or titles): the middle of
    the longest kept segments, in story order."""
    n = max(1, n)
    longest = sorted(plan.segments, key=lambda s: s.duration, reverse=True)
    if not longest:
        return []
    shots = {i: 1 for i in range(min(n, len(longest)))}
    for _ in range(n - len(shots)):  # fewer segments than covers: split the longest ones
        i = max(shots, key=lambda k: longest[k].duration / shots[k])
        shots[i] += 1
    return sorted(round(longest[i].start + longest[i].duration * (k + 1) / (c + 1), 2)
                  for i, c in shots.items() for k in range(c))
