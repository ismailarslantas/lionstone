"""FFmpeg builders and caption styles for the Reels looks. Original to Lionstone.

Editorial type (a high-contrast italic serif with a geometric sans), glowing keywords, translucent
notification cards, neon pills, dashed cards and a countdown. Fonts are bundled under the SIL OFL
(``data/fonts``), so these look the same on every system. Shapes are PNGs drawn with the standard
library and read through ``movie=`` with ``cwd=workdir``.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from ..captions import (
    CaptionStyle,
    Cue,
    _ass_escape,
    register_dialogue,
    register_style,
    smart_upper,
)
from ..effects.ffmpeg_fx import (
    FxContext,
    _num,
    _overlay,
    _timing,
    ease_out,
    envelope,
    filter_path,
    register_builder,
)
from ..models import GraphicEvent
from .looks import pick_keyword

FONTS = Path(__file__).resolve().parents[1] / "data" / "fonts"
SANS_BOLD = FONTS / "Poppins-Bold.ttf"
SANS = FONTS / "Poppins-Medium.ttf"
SANS_ITALIC = FONTS / "Poppins-BoldItalic.ttf"
SERIF_ITALIC = FONTS / "DMSerifDisplay-Italic.ttf"


# --- shapes ---------------------------------------------------------------------------
def rounded_png(path: Path, w: int, h: int, radius: int, fill: tuple[int, int, int, int],
                border: tuple[int, int, int] | None = None, width: int = 0, dash: int = 0) -> Path:
    """An anti-aliased rounded rectangle as RGBA PNG, standard library only."""
    rows = bytearray()
    for y in range(h):
        rows.append(0)
        for x in range(w):
            dx = max(radius - x - 0.5, x + 0.5 - (w - radius), 0.0)
            dy = max(radius - y - 0.5, y + 0.5 - (h - radius), 0.0)
            dist = (dx * dx + dy * dy) ** 0.5 - radius  # negative inside
            cover = max(0.0, min(1.0, 0.5 - dist))
            r, g, b, a = fill
            if border and width and dist > -width:
                on = not dash or ((x + y) // dash) % 2 == 0
                if on:
                    r, g, b, a = (*border, 255)
            rows += bytes((r, g, b, int(a * cover)))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(bytes(rows), 6)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def _rgb(color: str) -> tuple[int, int, int]:
    h = color.replace("0x", "").replace("#", "")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _shape(ctx: FxContext, w: int, h: int, radius: int, fill, border=None, width: int = 0,
           dash: int = 0) -> str:
    name = f"{ctx.label('shape')}.png"
    rounded_png(ctx.workdir / name, w, h, radius, fill, border, width, dash)
    return name


def _layer(ctx: FxContext, name: str, t0: float, dur: float, t_in: float, t_out: float) -> tuple[str, str]:
    lab = ctx.label("lay")
    part = (f"movie={name},loop=loop=-1:size=1:start=0,fps={_num(ctx.fps)},trim=duration={_num(dur)},"
            f"setpts=PTS-STARTPTS,format=yuva420p,fade=t=in:st=0:d={_num(t_in)}:alpha=1,"
            f"fade=t=out:st={_num(max(0, dur - t_out))}:d={_num(t_out)}:alpha=1,"
            f"setpts=PTS+{_num(t0)}/TB[{lab}]")
    return part, lab


def _text(ctx: FxContext, inp: str, out: str, text: str, font: Path, size: int, x: str, y: str,
          alpha: str, color: str = "white", extra: str = "") -> str:
    return (f"[{inp}]drawtext=fontfile={filter_path(font)}:textfile='{ctx.textfile(text)}':"
            f"expansion=none:fontsize={size}:fontcolor={color}:x='{x}':y='{y}':alpha='{alpha}'"
            f"{(':' + extra) if extra else ''}[{out}]")


SOFT = "shadowcolor=black@0.45:shadowx=0:shadowy=3"


def _lines(ev: GraphicEvent) -> list[str]:
    return [x.strip() for x in ev.text.split("/") if x.strip()]


# --- opening titles -------------------------------------------------------------------
def l01_editorial_stack(fx, ev: GraphicEvent, inp: str, ctx: FxContext):
    """Staggered lines: sans for the lead-in, a large italic serif for the last line."""
    t0, t_in, t1, t_out = _timing(fx, ev)
    W, H = ctx.width, ctx.height
    lines = _lines(ev)
    parts, cur = [], inp
    y = int(H * 0.09)
    for i, line in enumerate(lines):
        last = i == len(lines) - 1 and len(lines) > 1
        size = int(W * (0.115 if last else 0.062))
        x = "(w-tw)/2" if last else (f"{int(W * 0.12)}" if i % 2 == 0 else f"w-tw-{int(W * 0.12)}")
        a0 = t0 + i * 0.22
        out = ctx.label()
        parts.append(_text(ctx, cur, out, line, SERIF_ITALIC if last else SANS_BOLD, size, x,
                           f"{y}+{int(size * 0.35)}*(1-{ease_out(a0, t_in, 3)})",
                           envelope(a0, t_in, t1, t_out), ctx.accent if last else "white", SOFT))
        cur = out
        y += int(size * 1.12)
    return parts, cur


def l02_glow_headline(fx, ev: GraphicEvent, inp: str, ctx: FxContext):
    """Heavy capitals with a soft glow in the brand colour."""
    t0, t_in, t1, t_out = _timing(fx, ev)
    W, H = ctx.width, ctx.height
    lines = _lines(ev)
    size = int(W * 0.082)
    lh = int(size * 1.14)
    top = int(H * 0.16) - len(lines) * lh // 2
    a = envelope(t0, t_in, t1, t_out)
    glow, out = ctx.label("glow"), ctx.label()
    src = f"color=c=black@0:s={W}x{H}:r={_num(ctx.fps)}:d={_num(t1)},format=yuva420p"
    for i, line in enumerate(lines):
        cap = smart_upper(line)
        src += (f",drawtext=fontfile={filter_path(SANS_BOLD)}:textfile='{ctx.textfile(cap)}':expansion=none:"
                f"fontsize={size}:fontcolor={ctx.accent}:x='(w-tw)/2':y='{top + i * lh}':alpha='{a}'")
    parts = [f"{src},gblur=sigma={max(6, size // 7)}[{glow}]", _overlay(inp, glow, out)]
    cur = out
    for i, line in enumerate(lines):
        nxt = ctx.label()
        parts.append(_text(ctx, cur, nxt, smart_upper(line), SANS_BOLD, size, "(w-tw)/2", str(top + i * lh),
                           a, ctx.accent if i == len(lines) - 1 else "white"))
        cur = nxt
    return parts, cur


# --- moments --------------------------------------------------------------------------
def l03_glass_card(fx, ev: GraphicEvent, inp: str, ctx: FxContext):
    """A translucent notification: name in bold, message under it, sliding in above the head."""
    t0, t_in, t1, t_out = _timing(fx, ev)
    W, H = ctx.width, ctx.height
    cw, ch = int(W * 0.84), int(H * 0.086)
    x, y = (W - cw) // 2, int(H * 0.11)
    dur = t1 - t0
    parts, cur = [], inp
    lay, lab = _layer(ctx, _shape(ctx, cw, ch, ch // 3, (92, 92, 84, 205)), t0, dur, t_in, t_out)
    slide = f"{y}-{int(H * 0.03)}*(1-{ease_out(t0, t_in, 3)})"
    out = ctx.label()
    parts += [lay, _overlay(cur, lab, out, str(x), slide)]
    cur = out
    a = envelope(t0, t_in, t1, t_out)
    size_name, size_msg = int(ch * 0.27), int(ch * 0.235)
    pad = int(ch * 0.26)
    dot = int(ch * 0.62)
    lay, lab = _layer(ctx, _shape(ctx, dot, dot, dot // 2, (*_rgb(ctx.accent), 255)), t0, dur, t_in, t_out)
    out = ctx.label()
    parts += [lay, _overlay(cur, lab, out, str(x + pad), f"{slide}+{(ch - dot) // 2}")]
    cur = out
    text_x = x + pad * 2 + dot
    room = cw - (text_x - x) - pad
    message = ev.subtext
    limit = int(room / (size_msg * 0.56))
    if len(message) > limit:
        message = message[:max(1, limit - 1)].rstrip() + "…"
    for line, font, size, dy in ((ev.text, SANS_BOLD, size_name, int(ch * 0.17)),
                                 (message, SANS, size_msg, int(ch * 0.53))):
        out = ctx.label()
        parts.append(_text(ctx, cur, out, line, font, size, str(text_x), f"{slide}+{dy}", a))
        cur = out
    return parts, cur


def l04_neon_pills(fx, ev: GraphicEvent, inp: str, ctx: FxContext):
    """Black pills with a brand-coloured outline, popping in on either side of the speaker."""
    t0, t_in, t1, t_out = _timing(fx, ev)
    W, H = ctx.width, ctx.height
    parts, cur = [], inp
    size = int(W * 0.04)
    spots = (("left", int(W * 0.05), int(H * 0.42)), ("right", int(W * 0.95), int(H * 0.53)))
    for i, line in enumerate(_lines(ev)[:2]):
        side, ax, ay = spots[i]
        pw, ph = int(len(line) * size * 0.66) + size * 2, int(size * 2.2)
        px = ax if side == "left" else ax - pw
        a0 = t0 + i * 0.25
        dur = t1 - a0
        name = _shape(ctx, pw, ph, ph // 2, (8, 8, 10, 255), _rgb(ctx.accent), max(3, size // 7))
        lay, lab = _layer(ctx, name, a0, dur, t_in, t_out)
        out = ctx.label()
        parts += [lay, _overlay(cur, lab, out, str(px), str(ay))]
        cur = out
        out = ctx.label()
        parts.append(_text(ctx, cur, out, line, SANS_BOLD, size, f"{px}+({pw}-tw)/2", f"{ay}+({ph}-th)/2",
                           envelope(a0, t_in, t1, t_out)))
        cur = out
    return parts, cur


def l05_dashed_card(fx, ev: GraphicEvent, inp: str, ctx: FxContext):
    """A dark card with a dashed outline for one number or word, in the top corner."""
    t0, t_in, t1, t_out = _timing(fx, ev)
    W, H = ctx.width, ctx.height
    text = ev.text
    size = int(W * (0.1 if len(text) <= 6 else 0.06))
    cw = min(int(W * 0.8), int(len(text) * size * 0.68) + int(W * 0.08))
    ch = int(size * 2.1)
    x, y = W - cw - int(W * 0.13), int(H * 0.11)
    name = _shape(ctx, cw, ch, 18, (12, 12, 14, 215), _rgb(ctx.accent), 4, dash=14)
    lay, lab = _layer(ctx, name, t0, t1 - t0, t_in, t_out)
    out, top = ctx.label(), ctx.label()
    return ([lay, _overlay(inp, lab, out, str(x), str(y)),
             _text(ctx, out, top, text, SANS_BOLD, size, f"{x}+({cw}-tw)/2", f"{y}+({ch}-th)/2",
                   envelope(t0, t_in, t1, t_out), ctx.accent)], top)


def l06_countdown(fx, ev: GraphicEvent, inp: str, ctx: FxContext):
    """A small clock counting the Reel down to zero, above the app's UI."""
    t0, _, t1, _ = _timing(fx, ev)
    W, H = ctx.width, ctx.height
    d = int(W * 0.17)
    x, y = int(W * 0.06), int(H * 0.62)
    end = t0 + float(ev.text)
    name = _shape(ctx, d, d, d // 2, (10, 10, 12, 215), _rgb(ctx.accent), max(4, d // 26))
    lay, lab = _layer(ctx, name, t0, t1 - t0, 0.3, 0.2)
    out, top = ctx.label(), ctx.label()
    size = int(d * 0.27)
    clock = (f"[{out}]drawtext=fontfile={filter_path(SANS_BOLD)}:"
             f"text='00\\:%{{eif\\:max(0\\,ceil({_num(end)}-t))\\:d\\:2}}':"
             f"fontsize={size}:fontcolor=white:x='{x}+({d}-tw)/2':y='{y}+({d}-th)/2'[{top}]")
    return [lay, _overlay(inp, lab, out, str(x), str(y)), clock], top


# --- captions -------------------------------------------------------------------------
def _bgr(color: str) -> str:
    r, g, b = _rgb(color)
    return f"&H{b:02X}{g:02X}{r:02X}&"


def _sep(cue: Cue, i: int) -> str:
    """Keep the cue's line break: captions don't wrap on their own."""
    first = len(cue.lines[0].split()) if len(cue.lines) > 1 else len(cue.words)
    return "\\N" if i == first and i > 0 else (" " if i else "")


def editorial_dialogue(accent: str):
    """Quiet sans, with the line's key word in a large italic serif."""
    acc = _bgr(accent)

    def fn(cue: Cue, style: CaptionStyle) -> str:
        words = [w.text for w in cue.words]
        key = pick_keyword(words)
        out = []
        for i, word in enumerate(words):
            text = _ass_escape(word)
            sep = _sep(cue, i)
            out.append(f"{sep}{{\\fnDM Serif Display\\i1\\fscx165\\fscy165\\1c{acc}}}{text}"
                       f"{{\\fnPoppins Medium\\i0\\fscx100\\fscy100\\1c&HFFFFFF&}}" if i == key else f"{sep}{text}")
        return "".join(out)

    return fn


def keyword_pop_dialogue(accent: str):
    """Heavy sans, with the key word larger, in capitals and glowing in the brand colour."""
    acc = _bgr(accent)

    def fn(cue: Cue, style: CaptionStyle) -> str:
        words = [w.text for w in cue.words]
        key = pick_keyword(words)
        out = []
        for i, word in enumerate(words):
            sep = _sep(cue, i)
            if i == key:
                out.append(f"{sep}{{\\fnPoppins\\i1\\b1\\fscx118\\fscy118\\1c{acc}\\3c{acc}\\bord1\\blur4}}"
                           f"{_ass_escape(smart_upper(word))}"
                           f"{{\\i0\\fscx100\\fscy100\\1c&HFFFFFF&\\3c&H000000&\\bord3\\blur0}}")
            else:
                out.append(f"{sep}{_ass_escape(word)}")
        return "".join(out)

    return fn


def register_captions(accent: str = "#E8B04B") -> None:
    register_style(CaptionStyle("editorial", font="Poppins Medium", size_ratio=0.074, bold=False,
                                outline=0.0, shadow=2.0, margin_v_ratio=0.22))
    register_dialogue("editorial", editorial_dialogue(accent))
    register_style(CaptionStyle("keyword-pop", font="Poppins", size_ratio=0.082, outline=3.0, shadow=0.0,
                                margin_v_ratio=0.22))
    register_dialogue("keyword-pop", keyword_pop_dialogue(accent))


def register() -> None:
    for fid, fn in {"L01": l01_editorial_stack, "L02": l02_glow_headline, "L03": l03_glass_card,
                    "L04": l04_neon_pills, "L05": l05_dashed_card, "L06": l06_countdown}.items():
        register_builder(fid, fn)
    register_captions()
