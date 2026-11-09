"""Motion FX pack — 17 motion-design effects for talking-head Reels, Shorts and videos.

Orbit, Couch Wall, UI World, Frame Break, Digital Zoom, Phone Mockup, Checklist,
Headline Wall, Zoom-through Cut, Chart Grow, Pull-back Reveal, Green Screen,
Paper Cut, Doodle Boil, Vertigo, Cover Story and Glass Type.

Same contract as ``reel_fx``: every builder receives validated parameters and
output-time windows and returns a fragment that consumes the current stream and
ends with an unlabeled filter. Everything is FFmpeg filter math plus the fonts
Lionstone already bundles (Poppins, SIL OFL); no stock footage, overlays or LUTs.
Geometry is relative, so one preset works on 9:16, 1:1 and 16:9.

Static artwork (gradients, rounded masks, check marks, chart lines) is drawn once
with ``geq`` on a single frame and looped, so it costs one frame, not one per frame.
Text goes through ``textfile=`` (no filtergraph escaping of user text).
"""

from __future__ import annotations

import hashlib
import math
import shutil
import tempfile
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from ....ff import has_filter
from ..easing import _f
from ..paths import filter_path
from . import ffmpeg_adapter as fa
from .ffmpeg_adapter import en, ensure_even
from .reel_fx import _hex, _prog, _rgb, _src

Win = tuple[float, float]
FONTS = Path(__file__).resolve().parents[3] / "data" / "fonts"
BOLD = FONTS / "Poppins-Bold.ttf"
MEDIUM = FONTS / "Poppins-Medium.ttf"
SERIF = FONTS / "DMSerifDisplay-Italic.ttf"


# ----------------------------------------------------------------------- helpers
def _esc_path(p: Path | str) -> str:
    return filter_path(p)


@lru_cache(maxsize=1)
def _text_dir() -> Path:
    d = Path(tempfile.gettempdir()) / "lionstone-motion-text"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _font(font: Path) -> str:
    """Escaped font path. FreeType on Windows can't open non-ASCII paths, so use a temp copy."""
    dst = _text_dir() / font.name
    if not dst.exists() or dst.stat().st_size != font.stat().st_size:
        shutil.copyfile(font, dst)
    return _esc_path(dst)


def _textfile(text: str) -> str:
    """Write `text` once (content-addressed) and return an escaped path for drawtext."""
    f = _text_dir() / (hashlib.sha1(text.encode("utf-8")).hexdigest()[:16] + ".txt")
    if not f.exists():
        f.write_text(text, encoding="utf-8")
    return _esc_path(f)


def _text(text: str, size: float, color: str, x: str, y: str, *, font: Path = BOLD,
          alpha: str = "1", enable: str = "1", extra: str = "") -> str:
    """drawtext with a bundled font; without drawtext, a placeholder bar of similar size."""
    size = max(6, int(size))
    if not has_filter("drawtext"):
        w = max(4, int(size * 0.55 * len(text)))
        bx = x.replace("tw", str(w)).replace("th", str(size))
        by = y.replace("tw", str(w)).replace("th", str(size))
        return (f"drawbox=x='{bx}':y='{by}':w={w}:h={max(2, size // 2)}:"
                f"color={color}@0.85:t=fill:enable='{enable}'")
    return (f"drawtext=fontfile={_font(font)}:textfile={_textfile(text)}:"
            f"expansion=none:fontsize={size}:fontcolor={color}:x='{x}':y='{y}':alpha='{alpha}':"
            f"enable='{enable}'" + (f":{extra}" if extra else ""))


def _items(s: str, fallback: list[str]) -> list[str]:
    out = [x.strip() for x in (s or "").split("|") if x.strip()]
    return out or fallback


def _still(c, w: int, h: int, r: str, g: str, b: str, a: str) -> str:
    """A static RGBA picture drawn once with geq and looped for the whole timeline."""
    return (f"color=c=black@0:s={w}x{h}:r={_f(c.fps)}:d={_f(2 / c.fps)},format=rgba,"
            f"geq=r='{r}':g='{g}':b='{b}':a='{a}',"
            f"trim=end_frame=1,loop=loop=-1:size=1:start=0,setpts=N/{_f(c.fps)}/TB,"
            f"trim=duration={_f(c.total + 1)}")


def _backdrop(c, ink: str, accent: str, cy: float = 0.32, glow: float = 0.35) -> str:
    """Brand backdrop: ink with a soft accent glow (static, looped)."""
    (ir, ig, ib), (ar, ag, ab) = _rgb(ink), _rgb(accent)
    s = 2 * (0.5 * max(c.W, c.H)) ** 2
    fall = f"{_f(glow)}*exp(-(pow(X-{_f(c.W / 2)},2)+pow(Y-{_f(c.H * cy)},2))/{_f(s)})"
    return _still(c, c.W, c.H, f"{ir}+({ar - ir})*{fall}", f"{ig}+({ag - ig})*{fall}",
                  f"{ib}+({ab - ib})*{fall}", "255")


def _rounded(w: float, h: float, r: float) -> str:
    """geq alpha (0-255, anti-aliased) of a rounded rectangle filling a w×h picture."""
    return (f"255*clip({_f(r)}+0.5-hypot(max(abs(X-{_f(w / 2)})-{_f(w / 2 - r)},0),"
            f"max(abs(Y-{_f(h / 2)})-{_f(h / 2 - r)},0)),0,1)")


def _swap(c, wins: list[Win], build: Callable[[str], tuple[list[str], str]]) -> str:
    """Build a full-frame layout from a copy of the stream; show it only inside `wins`."""
    a, b = c.L("wa"), c.L("wb")
    parts, out = build(b)
    return (f"split=2[{a}][{b}];" + ";".join(parts) +
            f";[{a}][{out}]overlay=0:0:shortest=1:enable='{en(wins)}'")


def _zoom(c, Z: str, fx: str = "0.5", fy: str = "0.5") -> str:
    """Scale by Z (≥ 1, time expression) and crop back to the frame around (fx, fy)."""
    W, H = c.W, c.H
    return (f"scale=w='trunc({W}*max(1,{Z})/2)*2':h='trunc({H}*max(1,{Z})/2)*2':eval=frame,"
            f"crop={W}:{H}:x='(in_w-out_w)*({fx})':y='(in_h-out_h)*({fy})'")


def _card(c, inp: str, w: int, h: int, radius: float, out: str) -> str:
    """Scale the stream to w×h (cover) with rounded corners → RGBA label `out`."""
    m, s = c.L("cm"), c.L("cs")
    return (f"[{inp}]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"format=rgba[{s}];{_still(c, w, h, '255', '255', '255', _rounded(w, h, radius))},"
            f"format=gray[{m}];[{s}][{m}]alphamerge[{out}]")


def _cutout(c, inp: str, out: str) -> str:
    """You, cut out of the shot with the person matte → RGBA label `out` (needs c.matte)."""
    return f"[{inp}]format=rgba[{out}i];[{out}i][{c.matte_label()}]alphamerge[{out}]"


def _t0(wins: list[Win], delay: float) -> str:
    """Seconds since (window start + delay), clamped to ≥ 0, for the active window."""
    return "(" + "+".join(f"if(between(t,{_f(a)},{_f(b)}),max(0,t-{_f(a + delay)}),0)"
                          for a, b in wins) + ")" if wins else "0"


def _fade(wins: list[Win], delay: float, dur: float = 0.25) -> str:
    """0→1 over `dur` after (window start + delay), held to the window end."""
    return f"min(1,{_t0(wins, delay)}/{_f(dur)})"


# ================================================================== 1 · Orbit
def orbit(p, wins, c):
    """The camera circles you: the shot turns on a card in 3D space over a brand stage."""
    amp = math.radians(p["angle"])
    sp = p["speed"]
    inset = p["inset"]
    T = f"(on/{_f(c.fps)})"
    th = f"({_f(amp)}*sin(2*PI*{_f(sp)}*{T}))"
    d = 0.18  # near side grows, far side shrinks
    hw, hh = c.W * inset / 2, c.H * inset / 2
    cx, cy = c.W / 2, c.H / 2
    xl, xr = f"{_f(cx)}-{_f(hw)}*cos({th})", f"{_f(cx)}+{_f(hw)}*cos({th})"
    yl = f"{_f(hh)}*(1+{_f(d)}*sin({th}))"
    yr = f"{_f(hh)}*(1-{_f(d)}*sin({th}))"

    def build(b):
        bg, card, out = c.L("ob"), c.L("oc"), c.L("oo")
        w, h = ensure_even(c.W * inset), ensure_even(c.H * inset)
        g = [_backdrop(c, p["bg"], p["accent"], 0.5) + f"[{bg}]",
             _card(c, b, w, h, 28 * c.k, card + "r"),
             f"[{card}r]pad={c.W}:{c.H}:{(c.W - w) // 2}:{(c.H - h) // 2}:color=black@0,"
             f"format=yuva444p,perspective=sense=destination:eval=frame:"
             f"x0='{xl}':y0='{_f(cy)}-{yl}':x1='{xr}':y1='{_f(cy)}-{yr}':"
             f"x2='{xl}':y2='{_f(cy)}+{yl}':x3='{xr}':y3='{_f(cy)}+{yr}'[{card}]",
             f"[{bg}][{card}]overlay=0:0:shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


# ============================================================= 2 · Couch Wall
def couch_wall(p, wins, c):
    """You, on every screen in the room: a 3×3 wall of monitors; the camera pulls back."""
    W, H = c.W, c.H
    cw, ch = ensure_even(W / 3), ensure_even(H / 3)
    bez = max(2, ensure_even(cw * 0.05))
    iw, ih = cw - 2 * bez, ch - 2 * bez
    P = _prog(wins, "ease-in-out", 0.0, p["pull"])
    Z = f"(3-2*{P})" if p["direction"] == "out" else f"(1+2*{P})"

    def build(b):
        r1, r2, r3, s1, s2, s3, wall, out = (c.L(x) for x in ("r1", "r2", "r3", "s1", "s2", "s3",
                                                              "cw", "co"))
        dim = ",".join(f"drawbox={x * cw}:{y * ch}:{cw}:{ch}:color=black@{_f(p['dim'])}:t=fill"
                       for y in range(3) for x in range(3) if (x, y) != (1, 1))
        g = [f"[{b}]scale={iw}:{ih}:force_original_aspect_ratio=increase,crop={iw}:{ih},"
             f"pad={cw}:{ch}:{bez}:{bez}:color={_hex(p['bezel'])},"
             f"drawbox={bez}:{bez}:{iw}:{ih}:color=white@0.06:t={max(1, int(c.k))},"
             f"split=3[{r1}][{r2}][{r3}]",
             f"[{r1}][{r2}][{r3}]hstack=3,split=3[{s1}][{s2}][{s3}]",
             f"[{s1}][{s2}][{s3}]vstack=3,crop={W}:{H}:0:0,{dim}[{wall}]",
             f"[{wall}]{_zoom(c, Z)}[{out}]"]
        return g, out
    return _swap(c, wins, build)


# =============================================================== 3 · UI World
def ui_world(p, wins, c):
    """You, inside the interface: an app window floats among drifting UI cards."""
    W, H, k = c.W, c.H, c.k
    portrait = H >= W
    s = p["scale"]
    w = ensure_even(W * (s if portrait else s * 0.62))
    h = ensure_even(w * (H / W) * (0.72 if portrait else 0.9))
    bar = ensure_even(44 * k)
    acc, ui = _hex(p["accent"]), _hex(p["panel"])
    rise = _prog(wins, "ease-out", 0.0, 0.7)

    def layer(seed: int) -> str:
        boxes = []
        rnd = [(0.05, 0.06, 0.34, 0.07), (0.62, 0.05, 0.32, 0.12), (0.06, 0.80, 0.30, 0.10),
               (0.66, 0.84, 0.28, 0.06), (0.03, 0.40, 0.12, 0.05), (0.86, 0.46, 0.11, 0.05)]
        for i, (x, y, bw, bh) in enumerate(rnd[seed::2]):
            X, Y = int(W * x), int(H * y)
            BW, BH = int(W * bw), int(H * bh)
            boxes += [f"drawbox={X}:{Y}:{BW}:{BH}:color={ui}@0.92:t=fill",
                      f"drawbox={X + BW // 12}:{Y + BH // 3}:{BW // 2}:{max(2, BH // 7)}:"
                      f"color=white@0.55:t=fill",
                      f"drawbox={X + BW - BH // 2 - BW // 12}:{Y + BH // 4}:{BH // 2}:{BH // 2}:"
                      f"color={acc}:t=fill" if i % 2 == 0 else
                      f"drawbox={X + BW // 12}:{Y + BH * 3 // 5}:{BW // 3}:{max(2, BH // 9)}:"
                      f"color=white@0.3:t=fill"]
        # drawbox does not write alpha: draw on pure black, then key the black out
        return (f"color=c=black:s={W}x{H}:r={_f(c.fps)}:d={_f(2 / c.fps)}," + ",".join(boxes) +
                f",format=rgba,colorkey=black:0.01:0,trim=end_frame=1,loop=loop=-1:size=1:start=0,"
                f"setpts=N/{_f(c.fps)}/TB,trim=duration={_f(c.total + 1)}")

    def build(b):
        bg, l1, l2, card, win, o1, o2, out = (c.L(x) for x in ("ub", "u1", "u2", "uc", "uw",
                                                             "v1", "v2", "uo"))
        x = (W - w) // 2
        y = ensure_even((H - h - bar) * 0.48)
        dots = ",".join(f"drawbox={ensure_even(18 * k + i * 26 * k)}:{bar // 2 - int(6 * k)}:"
                        f"{max(2, int(12 * k))}:{max(2, int(12 * k))}:color={col}:t=fill"
                        for i, col in enumerate(("0xFF5F57", "0xFEBC2E", "0x28C840")))
        g = [_backdrop(c, p["bg"], p["accent"], 0.45, 0.28) + f"[{bg}]",
             layer(0) + f"[{l1}]", layer(1) + f"[{l2}]",
             _card(c, b, w, h, 4 * k, card),
             f"color=c={ui}:s={w}x{h + bar}:r={_f(c.fps)}:d={_f(c.total + 1)},format=rgba,"
             f"{dots}[{win}w]",
             f"[{win}w][{card}]overlay=0:{bar}:shortest=1[{win}]",
             f"[{bg}][{l1}]overlay=x='{_f(14 * k)}*sin(t*0.9)':y='{_f(22 * k)}*cos(t*0.7)':"
             f"shortest=1[{o1}]",
             f"[{o1}][{win}]overlay=x={x}:y='{y}+{_f(H * 0.08)}*(1-{rise})+{_f(8 * k)}*sin(t*1.3)':"
             f"shortest=1[{o2}]",
             f"[{o2}][{l2}]overlay=x='{_f(-26 * k)}*sin(t*0.8+1)':y='{_f(-30 * k)}*cos(t*0.6)':"
             f"shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


# ============================================================= 4 · Frame Break
def frame_break(p, wins, c):
    """You step out of the frame: your head climbs out over the top edge of a picture frame."""
    W, H, k = c.W, c.H, c.k
    fx0, fx1 = ensure_even(W * 0.08), ensure_even(W * 0.92)
    fy0, fy1 = ensure_even(H * p["top"]), ensure_even(H * 0.94)
    bt = max(4, ensure_even(14 * k))
    colw = ensure_even(W * p["width"])
    cx = ensure_even((W - colw) / 2)
    ctop = ensure_even(H * 0.03)
    colh = fy0 - ctop
    grow = _prog(wins, "ease-out", 0.25, 0.7)
    edge = f"{fy0}-{colh}*{grow}"  # the column rises from behind the frame's top edge
    fr = _hex(p["frame"])
    sh = ensure_even(10 * k)

    def build_matte(b):
        # with the person matte: the frame is whole and you are cut out in front of its edge
        bg, f1, f2, inner, cut, col, shd, o1, o2, out = (c.L(x) for x in (
            "fb", "f1", "f2", "fi", "fk", "fc", "fs", "g1", "g2", "fo"))
        rise = f"{_f(H * 0.035)}*(1-{grow})"
        g = [_src(c, p["bg"], W, H) + f"[{bg}]",
             f"[{b}]split=2[{f1}][{f2}]",
             f"[{f1}]crop={fx1 - fx0}:{fy1 - fy0}:{fx0}:{fy0}[{inner}]",
             f"[{bg}][{inner}]overlay={fx0}:{fy0}:shortest=1,"
             f"drawbox={fx0 - bt}:{fy0 - bt}:{fx1 - fx0 + 2 * bt}:{fy1 - fy0 + 2 * bt}:"
             f"color={fr}:t={bt}[{o1}]",
             _cutout(c, f2, cut),
             f"[{cut}]crop={W}:{fy0}:0:0,split=2[{col}][{shd}a]",
             f"[{shd}a]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.3[{shd}]",
             f"[{o1}][{shd}]overlay=x={sh}:y='{rise}+{sh}':shortest=1:"
             f"enable='gt({grow},0.01)'[{o2}]",
             f"[{o2}][{col}]overlay=x=0:y='{rise}':shortest=1:enable='gt({grow},0.01)'[{out}]"]
        return g, out

    def build(b):
        bg, f1, f2, inner, col, shd, o1, o2, out = (c.L(x) for x in ("fb", "f1", "f2", "fi",
                                                                    "fc", "fs", "g1", "g2", "fo"))
        g = [_src(c, p["bg"], W, H) + f"[{bg}]",
             f"[{b}]format=rgba,split=2[{f1}][{f2}]",
             f"[{f1}]crop={fx1 - fx0}:{fy1 - fy0}:{fx0}:{fy0}[{inner}]",
             f"[{f2}]crop={colw}:{colh}:{cx}:{ctop}[{col}]",
             _src(c, "#000000", colw, colh, 0.28) + f"[{shd}]",
             f"[{bg}][{shd}]overlay=x={cx + sh}:y='{edge}+{sh}':shortest=1[{o1}]",
             f"[{o1}][{col}]overlay=x={cx}:y='{edge}':shortest=1[{o2}]",
             # the frame (drawn after the column) hides whatever is still inside it
             f"[{o2}][{inner}]overlay={fx0}:{fy0}:shortest=1,"
             f"drawbox={fx0 - bt}:{fy0}:{bt}:{fy1 - fy0 + bt}:color={fr}:t=fill,"
             f"drawbox={fx1}:{fy0}:{bt}:{fy1 - fy0 + bt}:color={fr}:t=fill,"
             f"drawbox={fx0 - bt}:{fy1}:{fx1 - fx0 + 2 * bt}:{bt}:color={fr}:t=fill,"
             f"drawbox={fx0 - bt}:{fy0 - bt}:{cx - fx0 + bt}:{bt}:color={fr}:t=fill,"
             f"drawbox={cx + colw}:{fy0 - bt}:{fx1 - cx - colw + bt}:{bt}:color={fr}:t=fill[{out}]"]
        return g, out
    return _swap(c, wins, build_matte if c.matte else build)


# ============================================================ 5 · Digital Zoom
def digital_zoom(p, wins, c):
    """Punch-ins in digital steps: each step snaps closer with a focus reticle and an RGB tick."""
    n = int(p["steps"])
    zmax = p["zoom"]
    s = f"(({_prog(wins)})*{n})"
    stepz = f"(min({n},floor({s})+min(1,({s}-floor({s}))*10)))/{n}"
    Z = f"(1+{_f(zmax - 1)}*{stepz})"
    k = c.k
    L, T = ensure_even(70 * k), max(2, ensure_even(6 * k))
    m = ensure_even(min(c.W, c.H) * 0.16)
    acc = _hex(p["accent"])
    e = en(wins)
    corners = []
    for x, y, dx, dy in ((m, m, 1, 1), (c.W - m, m, -1, 1), (m, c.H - m, 1, -1),
                         (c.W - m, c.H - m, -1, -1)):
        corners.append(f"drawbox={x if dx > 0 else x - L}:{y if dy > 0 else y - T}:{L}:{T}:"
                       f"color={acc}:t=fill:enable='{e}'")
        corners.append(f"drawbox={x if dx > 0 else x - T}:{y if dy > 0 else y - L}:{T}:{L}:"
                       f"color={acc}:t=fill:enable='{e}'")
    ticks = []
    px = max(2, int(10 * k))
    for a, b in wins:
        for i in range(1, n + 1):
            t0 = a + (b - a) * (i - 1) / n
            ticks.append(f"rgbashift=rh={px}:bh={-px}:enable='between(t,{_f(t0)},"
                         f"{_f(t0 + 2 / c.fps)})'")
    return (f"{_zoom(c, Z, p['x'], p['y'])}," + ",".join(ticks + corners) +
            f",drawgrid=w=iw:h={max(2, int(4 * k))}:t=1:color=black@{_f(0.12 * p['scanlines'])}:"
            f"enable='{e}'")


# ============================================================ 6 · Phone Mockup
def phone_mockup(p, wins, c):
    """Your clip plays on a phone that rises into the frame on your brand backdrop."""
    W, H, k = c.W, c.H, c.k
    ph = ensure_even(H * (0.78 if H >= W else 0.88) * p["size"])
    pw = ensure_even(ph * 0.49)
    bz = ensure_even(pw * 0.035)
    sw, sh = pw - 2 * bz, ph - 2 * bz
    x = (W - pw) // 2
    y = ensure_even((H - ph) / 2)
    rise = _prog(wins, "ease-out", 0.0, 0.8)
    (br, bgc, bb) = _rgb(p["body"])

    def build(b):
        bg, body, scr, o1, out = (c.L(x) for x in ("pb", "pp", "ps", "q1", "po"))
        notch_w, notch_h = ensure_even(pw * 0.28), ensure_even(ph * 0.022)
        g = [_backdrop(c, p["bg"], p["accent"], 0.4) + f"[{bg}]",
             _still(c, pw, ph, str(br), str(bgc), str(bb), _rounded(pw, ph, pw * 0.13)) +
             f"[{body}]",
             _card(c, b, sw, sh, pw * 0.11, scr),
             f"[{body}][{scr}]overlay={bz}:{bz}:shortest=1,"
             f"drawbox={(pw - notch_w) // 2}:{bz + ensure_even(ph * 0.012)}:{notch_w}:{notch_h}:"
             f"color=black:t=fill[{o1}]",
             f"[{bg}][{o1}]overlay=x={x}:y='{y}+{_f(H)}*(1-{rise})+{_f(6 * k)}*sin(t*1.4)':"
             f"shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


# =============================================================== 7 · Checklist
def _check_sprite(c, s: int, accent: str) -> str:
    """Rounded accent square with a white check mark (geq, static)."""
    ar, ag, ab = _rgb(accent)
    t = max(1.5, s * 0.085)
    # check: (0.24,0.52)→(0.43,0.70)→(0.76,0.32) in unit square
    p0, p1, p2 = (0.24 * s, 0.52 * s), (0.43 * s, 0.70 * s), (0.76 * s, 0.32 * s)

    def seg(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ll = dx * dx + dy * dy
        u = f"clip(((X-{_f(a[0])})*{_f(dx)}+(Y-{_f(a[1])})*{_f(dy)})/{_f(ll)},0,1)"
        return f"hypot(X-{_f(a[0])}-{u}*{_f(dx)},Y-{_f(a[1])}-{u}*{_f(dy)})"
    ink = f"clip({_f(t)}+0.5-min({seg(p0, p1)},{seg(p1, p2)}),0,1)"
    return _still(c, s, s, f"{ar}+(255-{ar})*{ink}", f"{ag}+(255-{ag})*{ink}",
                  f"{ab}+(255-{ab})*{ink}", _rounded(s, s, s * 0.22))


def checklist(p, wins, c):
    """Tick, tick, tick: a list card where each item checks off in turn."""
    items = _items(p["items"], ["Hook in 2 seconds", "One idea per Reel", "Clear call to action"])
    n = len(items)
    W, H, k = c.W, c.H, c.k
    portrait = H >= W
    cw = ensure_even(W * (0.84 if portrait else 0.46))
    row = ensure_even(H * (0.075 if portrait else 0.12))
    pad = ensure_even(row * 0.45)
    chh = ensure_even(pad * 2 + row * n)
    cx = ensure_even((W - cw) / 2) if portrait else ensure_even(W * 0.06)
    cy = ensure_even(H * p["y"] - chh / 2)
    box = ensure_even(row * 0.56)
    acc = _hex(p["accent"])
    e = en(wins)
    span = [(a, b) for a, b in wins]
    g = []
    base = c.L("kb")
    copies = [c.L("kc") for _ in range(n)]
    g.append(f"null[{base}]")
    g.append(_check_sprite(c, box, p["accent"]) + f",split={n}" + "".join(f"[{s}]" for s in copies))
    cur = c.L("kk")
    g.append(f"[{base}]drawbox={cx}:{cy}:{cw}:{chh}:color={_hex(p['panel'])}@{_f(p['opacity'])}:"
             f"t=fill:enable='{e}',drawbox={cx}:{cy}:{max(4, ensure_even(8 * k))}:{chh}:"
             f"color={acc}:t=fill:enable='{e}'[{cur}]")
    for i, label in enumerate(items):
        ry = cy + pad + row * i
        bx, by = cx + ensure_even(cw * 0.07), ry + (row - box) // 2
        when = [(a + (b - a) * (0.15 + 0.7 * i / max(1, n)), b) for a, b in span]
        txt = c.L("kt")
        g.append(f"[{cur}]drawbox={bx}:{by}:{box}:{box}:color=white@0.7:t={max(2, int(3 * k))}:"
                 f"enable='{e}',"
                 + _text(label, row * 0.36, "white", f"{bx + box + int(row * 0.35)}",
                         f"{ry}+({row}-th)/2", font=MEDIUM, enable=e) + f"[{txt}]")
        nxt = c.L("kk")
        last = i == n - 1
        g.append(f"[{txt}][{copies[i]}]overlay={bx}:{by}:shortest=1:enable='{en(when)}'"
                 + ("" if last else f"[{nxt}]"))
        cur = nxt
    return ";".join(g)


# =========================================================== 8 · Headline Wall
def headline_wall(p, wins, c):
    """The headlines are about you: a scrolling wall of paper headlines behind your card."""
    heads = _items(p["headlines"], ["WHO IS THIS CREATOR?", "THE EDIT EVERYONE SHARES",
                                    "NEW SERIES STARTS TODAY", "SAVE THIS FOR LATER",
                                    "THE 30-SECOND METHOD", "READ THIS BEFORE YOU POST"])
    W, H, k = c.W, c.H, c.k
    rows = 9
    rh = ensure_even(H / 6)
    big_h = rows * rh
    paper, ink = _hex(p["paper"]), _hex(p["ink"])
    s = p["scale"]
    cw, chh = ensure_even(W * s), ensure_even(H * s)

    def build(b):
        wall, card, bg, o1, out = (c.L(x) for x in ("hw", "hc", "hb", "h1", "ho"))
        draw = []
        for r in range(rows):
            y = r * rh
            off = int(W * (0.18 * (r % 3)))
            draw.append(f"drawbox=0:{y + int(rh * 0.08)}:{W}:{int(rh * 0.84)}:color={paper}:t=fill")
            draw.append(f"drawbox=0:{y + int(rh * 0.14)}:{W}:{max(2, int(3 * k))}:color={ink}:t=fill")
            draw.append(_text(heads[r % len(heads)], rh * 0.26, ink, f"{int(W * 0.04) - off}",
                              f"{y + int(rh * 0.24)}"))
            draw.append(f"drawbox={int(W * 0.04)}:{y + int(rh * 0.62)}:{int(W * 0.7)}:"
                        f"{max(2, int(rh * 0.04))}:color={ink}@0.35:t=fill")
            draw.append(f"drawbox={int(W * 0.04)}:{y + int(rh * 0.72)}:{int(W * 0.5)}:"
                        f"{max(2, int(rh * 0.04))}:color={ink}@0.35:t=fill")
        g = [f"color=c={ink}:s={W}x{big_h}:r={_f(c.fps)}:d={_f(2 / c.fps)}," + ",".join(draw) +
             f",trim=end_frame=1,loop=loop=-1:size=1:start=0,setpts=N/{_f(c.fps)}/TB,"
             f"trim=duration={_f(c.total + 1)}[{wall}]",
             _src(c, p["ink"], W, H) + f"[{bg}]",
             f"[{bg}][{wall}]overlay=x=0:y='-mod(t*{_f(H * 0.05 * p['speed'])},{big_h - H})':"
             f"shortest=1[{o1}]",
             f"[{b}]scale={cw}:{chh},pad={cw + 2 * ensure_even(8 * k)}:{chh + 2 * ensure_even(8 * k)}:"
             f"{ensure_even(8 * k)}:{ensure_even(8 * k)}:color={_hex(p['accent'])}[{card}]",
             f"[{o1}][{card}]overlay=x=(W-w)/2:y='(H-h)/2+{_f(H * 0.06)}*(1-{_prog(wins, 'ease-out', 0, 0.6)})':"
             f"shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


# ======================================================== 9 · Zoom-through Cut
def zoom_through_cut(p, wins, c):
    """Dive through the frame: a fast push in, a flash at the cut, and a settle on the next shot."""
    z = p["zoom"]
    terms = []
    for a, b in wins:
        m = (a + b) / 2
        h = max(1e-3, (b - a) / 2)
        terms.append(f"if(between(t,{_f(a)},{_f(m)}),pow((t-{_f(a)})/{_f(h)},3),"
                     f"if(between(t,{_f(m)},{_f(b)}),pow(1-(t-{_f(m)})/{_f(h)},3),0))")
    Z = f"(1+{_f(z - 1)}*(" + "+".join(terms) + "))"
    flash = [(((a + b) / 2) - 1 / c.fps, ((a + b) / 2) + 1 / c.fps) for a, b in wins]
    return (f"{_zoom(c, Z)},tmix=frames=3:weights='1 2 1':enable='{en(wins)}',"
            f"drawbox=0:0:iw:ih:color={_hex(p['flash'])}@{_f(p['flash_opacity'])}:t=fill:"
            f"enable='{en(flash)}'")


# ============================================================== 10 · Chart Grow
def chart_grow(p, wins, c):
    """Your numbers climb while you talk: a line-and-area chart draws itself on a card."""
    vals = [min(1.0, max(0.0, v)) for v in (p.get("values") or [])] or \
        [0.12, 0.22, 0.18, 0.38, 0.46, 0.64, 0.86]
    if len(vals) < 2:
        vals = [0.1, vals[0]]
    W, H, k = c.W, c.H, c.k
    cw = ensure_even(W * (0.86 if H >= W else 0.42))
    chh = ensure_even(cw * 0.52)
    x0 = ensure_even((W - cw) / 2) if H >= W else ensure_even(W * 0.05)
    y0 = ensure_even(H * p["y"])
    padx, pady = cw * 0.07, chh * 0.24
    gw, gh = cw - 2 * padx, chh - pady - chh * 0.12
    pts = [(padx + gw * i / (len(vals) - 1), pady + gh * (1 - v)) for i, v in enumerate(vals)]
    curve = "0"
    for (xa, ya), (xb, yb) in reversed(list(zip(pts, pts[1:]))):
        curve = (f"if(lte(X,{_f(xb)}),{_f(ya)}+({_f(yb - ya)})*(X-{_f(xa)})/{_f(xb - xa)},"
                 f"{curve})")
    lw = max(2.0, 5 * k)
    ar, ag, ab = _rgb(p["accent"])
    inside = f"between(X,{_f(padx)},{_f(padx + gw)})"
    line = f"{inside}*clip({_f(lw)}-abs(Y-({curve})),0,1)"
    area = f"{inside}*gte(Y,{curve})*lte(Y,{_f(pady + gh)})*0.28*(1-(Y-({curve}))/{_f(gh * 1.4)})"
    a = f"255*min(1,{line}+{area})"
    grow = _prog(wins, "ease-in-out", 0.2, p["draw"])
    acc = _hex(p["accent"])
    lbl = p["label"]
    cardc, chart, cover, card, base = (c.L(x) for x in ("gc", "gl", "gv", "gd", "gb"))
    g = [f"null[{base}]",
         f"color=c={_hex(p['panel'])}:s={cw}x{chh}:r={_f(c.fps)}:d={_f(c.total + 1)},format=rgba,"
         + ",".join(f"drawbox={int(padx)}:{int(pady + gh * f)}:{int(gw)}:{max(1, int(k))}:"
                    f"color=white@0.12:t=fill" for f in (0, 0.5, 1))
         + (("," + _text(lbl, chh * 0.13, acc, f"{int(padx)}", f"{int(chh * 0.06)}")) if lbl else "")
         + f"[{cardc}]",
         _still(c, cw, chh, str(ar), str(ag), str(ab), a) + f"[{chart}]",
         f"color=c={_hex(p['panel'])}:s={cw}x{int(gh + lw * 2 + 4)}:r={_f(c.fps)}:"
         f"d={_f(c.total + 1)},format=rgba[{cover}]",
         f"[{cardc}][{chart}]overlay=0:0:shortest=1[{card}a]",
         f"[{card}a][{cover}]overlay=x='{_f(padx)}+{_f(gw)}*{grow}':y={int(pady - lw - 2)}:"
         f"shortest=1,format=rgba,colorchannelmixer=aa={_f(p['opacity'])}[{card}]",
         f"[{base}][{card}]overlay=x={x0}:y='{y0}+{_f(H * 0.04)}*(1-{_prog(wins, 'ease-out', 0, 0.5)})':"
         f"shortest=1:enable='{en(wins)}'"]
    return ";".join(g)


# ======================================================== 11 · Pull-back Reveal
def pull_back_reveal(p, wins, c):
    """Start tight on a detail, pull back to reveal the whole scene."""
    P = _prog(wins, "ease-in-out", 0.0, p["pull"])
    Z = f"({_f(p['zoom'])}-{_f(p['zoom'] - 1)}*{P})"
    return (f"{_zoom(c, Z, p['x'], p['y'])},"
            f"vignette=angle='{_f(math.pi / 3)}*(1-{P})':eval=frame:enable='{en(wins)}'")


# ============================================================ 12 · Green Screen
def green_screen(p, wins, c):
    """Swap a green (or blue) backdrop for your brand stage — keyed, despilled, composited."""
    W = c.W
    key = _hex(p["key"])
    _, kg, kb = _rgb(p["key"])
    spill = "green" if kg >= kb else "blue"

    use_matte = c.matte and p.get("method", "auto") != "chroma"

    def build(b):
        bg, fg, out = c.L("zb"), c.L("zf"), c.L("zo")
        stage = _backdrop(c, p["bg"], p["accent"], 0.3, 0.55)
        if p["grid"]:
            stage += (f",drawgrid=w={ensure_even(W / 8)}:h={ensure_even(W / 8)}:t={max(1, int(c.k))}:"
                      f"color=white@0.06")
        key_fg = (_cutout(c, b, fg) if use_matte else
                  f"[{b}]format=yuva444p,chromakey={key}:{_f(p['similarity'])}:{_f(p['blend'])},"
                  f"despill=type={spill}:mix=0.5:expand=0.1[{fg}]")
        g = [stage + f"[{bg}]", key_fg,
             f"[{bg}][{fg}]overlay=0:0:shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


# =============================================================== 13 · Paper Cut
def _torn(c, w: int, h: int, color: str, top: bool, seed: float) -> str:
    """A paper strip with a torn edge (static geq)."""
    r, g, b = _rgb(color)
    jag = (f"({_f(h * 0.55)}+{_f(h * 0.12)}*sin(X*{_f(0.031 / c.k)}+{_f(seed)})"
           f"+{_f(h * 0.07)}*sin(X*{_f(0.097 / c.k)}+{_f(seed * 2)})"
           f"+{_f(h * 0.04)}*sin(X*{_f(0.23 / c.k)}+{_f(seed * 3)}))")
    a = f"255*clip({jag}-Y+0.5,0,1)" if top else f"255*clip(Y-({_f(h)}-{jag})+0.5,0,1)"
    grain = "(random(1)*14-7)"
    return _still(c, w, h, f"{r}+{grain}", f"{g}+{grain}", f"{b}+{grain}", a)


def paper_cut(p, wins, c):
    """You, cut out of paper: flat poster tones, paper grain and torn strips sliding in."""
    W, H = c.W, c.H
    lv = int(p["levels"])
    q = 256 / lv
    sh = ensure_even(H * p["strip"])
    P = _prog(wins, "ease-out", 0.0, 0.6)

    def build(b):
        top, bot, o1, o2, out = (c.L(x) for x in ("pt", "pq", "p1", "p2", "pc"))
        g = [f"[{b}]gblur=sigma={_f(max(1.0, 2 * c.k))},format=yuv444p,"
             f"lutyuv=y='min(235,floor(val/{_f(q)})*{_f(q)}+{_f(q / 2)})':"
             f"u='128+floor((val-128)/24)*24':v='128+floor((val-128)/24)*24',"
             f"eq=saturation={_f(1 + 0.3 * p['intensity'])},noise=alls=10:allf=u[{o1}]",
             _torn(c, W, sh, p["paper"], True, 1.3) + f"[{top}]",
             _torn(c, W, sh, p["paper2"], False, 4.1) + f"[{bot}]",
             f"[{o1}][{top}]overlay=x=0:y='-{sh}*(1-{P})':shortest=1[{o2}]",
             f"[{o2}][{bot}]overlay=x=0:y='{H - sh}+{sh}*(1-{P})':shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


# ============================================================= 14 · Doodle Boil
def doodle_boil(p, wins, c):
    """Hand-drawn lines that never sit still: a sketch outline redrawn a few times a second."""
    rate = p["boil"]
    k = c.k
    jx = f"{_f(3 * k * p['wobble'])}*sin(floor(t*{_f(rate)})*12.9898)"
    jy = f"{_f(3 * k * p['wobble'])}*sin(floor(t*{_f(rate)})*78.233)"
    lo = _f(0.06 + 0.12 * (1 - p["detail"]))
    hi = _f(0.16 + 0.2 * (1 - p["detail"]))

    def build(b):
        a1, a2, lines, base, out = (c.L(x) for x in ("da", "db", "dl", "dp", "do"))
        if p["mode"] == "sketch":
            under = _src(c, p["paper"], c.W, c.H) + f"[{base}]"
        else:
            under = f"[{a2}]eq=brightness=-0.06:saturation=0.75[{base}]"
        edges = (f"[{a1}]fps={_f(rate)},gblur=sigma={_f(max(0.8, 1.2 * k))},"
                 f"edgedetect=low={lo}:high={hi},dilation,format=gray,"
                 f"lutyuv=y='if(gt(val,100),255,0)'")
        if c.matte:  # keep your lines, drop the room's clutter, and outline your silhouette
            mt, e1, ol = c.L("dm"), c.L("de"), c.L("dw")
            draw = [edges + f"[{e1}]",
                    f"[{c.matte_label()}]fps={_f(rate)},format=gray,split=2[{mt}a][{mt}b]",
                    f"[{mt}a]edgedetect=low=0.1:high=0.3,dilation,dilation,format=gray[{ol}]",
                    f"[{mt}b]lutyuv=y='if(gt(val,90),255,0)',dilation,dilation,format=gray[{mt}]",
                    f"[{e1}][{mt}]blend=all_mode=multiply[{e1}m]",
                    f"[{e1}m][{ol}]blend=all_mode=lighten,fps={_f(c.fps)},format=gray[{lines}m]"]
        else:
            draw = [edges + f",fps={_f(c.fps)},format=gray[{lines}m]"]
        g = [f"[{b}]split=2[{a1}][{a2}]", *draw,
             f"color=c={_hex(p['color'])}:s={c.W}x{c.H}:r={_f(c.fps)}:d={_f(c.total + 1)},"
             f"format=rgba[{lines}c]",
             f"[{lines}c][{lines}m]alphamerge[{lines}]",
             under,
             f"[{base}][{lines}]overlay=x='{jx}':y='{jy}':shortest=1[{out}]"]
        if p["mode"] == "sketch":
            g.insert(1, f"[{a2}]nullsink")
        return g, out
    return _swap(c, wins, build)


# ================================================================ 15 · Vertigo
def vertigo(p, wins, c):
    """The room stretches, you stay put: a dolly-zoom on the background around a steady subject."""
    W, H = c.W, c.H
    P = _prog(wins, "ease-in-out")
    amt = p["amount"]
    Z = f"(1+{_f(amt)}*{P})" if p["direction"] == "in" else f"(1+{_f(amt)}*(1-{P}))"
    rx, ry = W * p["size"] * 0.5, H * p["size"] * 0.5 * (1.15 if H >= W else 1.4)
    cx, cy = W * p["x"], H * p["y"]
    feather = 0.35
    mask = (f"255*clip((1-hypot((X-{_f(cx)})/{_f(rx)},(Y-{_f(cy)})/{_f(ry)}))/{_f(feather)},0,1)")

    def build(b):
        a1, a2, bg, m, fg, out = (c.L(x) for x in ("va", "vb", "vg", "vm", "vf", "vo"))
        g = [f"[{b}]split=2[{a1}][{a2}]"]
        if c.matte:  # remove you from the background first, so no zoomed "ghost" peeks out
            r1, r2, hole, fill = c.L("vr"), c.L("vs"), c.L("vh"), c.L("vl")
            big = _f(max(8.0, 60 * c.k))
            inv, num, den = c.L("vi"), c.L("vn"), c.L("vd")
            # fill = blur(room without you) / blur(where the room is): colours from the room only
            g += [f"[{a1}]split=2[{r1}][{r2}]",
                  f"[{c.matte_label()}]lutyuv=y='if(gt(val,40),255,0)',"
                  + ",".join(["dilation"] * 6) + f",gblur=sigma={_f(max(2.0, 8 * c.k))}[{hole}]",
                  f"[{c.matte_label()}]lutyuv=y='if(gt(val,40),0,255)',"
                  + ",".join(["erosion"] * 6) + f",format=gbrp,split=2[{inv}a][{inv}b]",
                  f"[{r2}]format=gbrp[{r2}g];[{r2}g][{inv}a]blend=all_mode=multiply,"
                  f"gblur=sigma={big}[{num}]",
                  f"[{inv}b]gblur=sigma={big}[{den}]",
                  f"[{num}][{den}]blend=all_expr='if(gt(B,2),min(255,A*255/B),A)',"
                  f"format=rgba[{fill}c];[{fill}c][{hole}]alphamerge[{fill}]",
                  f"[{r1}][{fill}]overlay=0:0:shortest=1[{a1}c]"]
            a1 = f"{a1}c"
        g += [f"[{a1}]{_zoom(c, Z, _f(p['x']), _f(p['y']))},"
             f"gblur=sigma='{_f(2 * c.k)}':steps=1[{bg}]",
             (f"[{c.matte_label()}]gblur=sigma={_f(max(2.0, 6 * c.k))}[{m}]" if c.matte else
              _still(c, W, H, "255", "255", "255", mask) + f",format=gray[{m}]"),
             f"[{a2}]format=rgba[{a2}r];[{a2}r][{m}]alphamerge[{fg}]",
             f"[{bg}][{fg}]overlay=0:0:shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


# ============================================================ 16 · Cover Story
def cover_story(p, wins, c):
    """You, on the cover: masthead, cover lines, issue tag and barcode over a print-like grade."""
    W, H, k = c.W, c.H, c.k
    acc, ink = _hex(p["accent"]), _hex(p["ink"])
    lines = _items(p["lines"], ["The 30-second edit", "Why your hook fails", "5 habits of top creators"])
    e = en(wins)
    m = ensure_even(W * 0.06)
    mast = p["title"] or "LIONSTONE"
    size = min(W * 0.9 / max(4, len(mast)) * 1.4, H * 0.16)
    parts = [f"eq=contrast=1.08:saturation=1.12:enable='{e}'",
             f"drawbox=0:0:iw:{ensure_even(H * 0.012)}:color={acc}:t=fill:enable='{e}'",
             _text(mast, size, p["title_color"], "(w-tw)/2", f"{int(H * 0.02)}",
                   alpha=_fade(wins, 0.0, 0.35), enable=e),
             _text(p["issue"], H * 0.018, "white", f"{m}", f"{int(H * 0.02 + size * 1.02)}",
                   font=MEDIUM, alpha=_fade(wins, 0.2), enable=e)]
    ly = H * 0.62
    for i, ln in enumerate(lines):
        y = int(ly + i * H * 0.075)
        d = 0.35 + 0.18 * i
        parts.append(f"drawbox={m}:{y}:{ensure_even(W * 0.012)}:{int(H * 0.05)}:color={acc}:t=fill:"
                     f"enable='{e}*gte({_t0(wins, d)},0.001)'")
        parts.append(_text(ln.upper() if i == 0 else ln, H * (0.03 if i == 0 else 0.024),
                           "white", f"{m + ensure_even(W * 0.03)}", f"{y}+{int(H * 0.005)}",
                           font=BOLD if i == 0 else MEDIUM, alpha=_fade(wins, d), enable=e,
                           extra=f"shadowcolor={ink}@0.6:shadowx={max(1, int(2 * k))}:"
                                 f"shadowy={max(1, int(2 * k))}"))
    bw, bh = ensure_even(W * 0.16), ensure_even(H * 0.045)
    bx, by = W - m - bw, ensure_even(H * 0.93) - bh
    parts.append(f"drawbox={bx}:{by}:{bw}:{bh}:color=white:t=fill:enable='{e}'")
    xx = 0
    stripes = [2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 1, 3, 1, 2]
    unit = max(1, int(bw * 0.9 / sum(s + 1 for s in stripes)))
    for sw in stripes:
        parts.append(f"drawbox={bx + int(bw * 0.05) + xx}:{by + int(bh * 0.12)}:{sw * unit}:"
                     f"{int(bh * 0.76)}:color=black:t=fill:enable='{e}'")
        xx += (sw + 1) * unit
    return ",".join(parts)


# ============================================================== 17 · Glass Type
def glass_type(p, wins, c):
    """Big glass letters over your shot: the type refracts the picture behind it."""
    W, H, k = c.W, c.H, c.k
    text = p["text"] or "LIONSTONE"
    size = min(W * 0.92 / max(3, len(text)) * 1.4, H * (0.2 if H >= W else 0.34))
    rise = _prog(wins, "ease-out", 0.0, 0.7)
    ty = f"{_f(H * p['y'])}-th/2+{_f(H * 0.05)}*(1-{rise})"
    alpha = f"min(1,{_t0(wins, 0)}/0.45)"
    e = en(wins)

    def build(b):
        a1, a2, mk, glass, edge, o1, out = (c.L(x) for x in ("ya", "yb", "ym", "yg", "ye",
                                                             "y1", "yo"))
        sig = _f(max(2.0, 14 * k * p["frost"]))
        behind = c.matte and p.get("behind", True)
        g = [f"[{b}]split={3 if behind else 2}[{a1}][{a2}]" + (f"[{a1}k]" if behind else ""),
             f"color=c=black:s={W}x{H}:r={_f(c.fps)}:d={_f(c.total + 1)},"
             + _text(text, size, "white", "(w-tw)/2", ty, alpha=alpha, enable=e)
             + f",format=gray[{mk}]",
             f"[{a2}]gblur=sigma={sig},eq=brightness={_f(0.16 + 0.2 * p['frost'])}:"
             f"saturation=1.15,{_zoom(c, '1.04')},format=rgba[{glass}c]",
             f"[{glass}c][{mk}]alphamerge[{glass}]",
             f"[{a1}][{glass}]overlay=0:0:shortest=1[{o1}]",
             f"color=c=black@0:s={W}x{H}:r={_f(c.fps)}:d={_f(c.total + 1)},format=rgba,"
             + _text(text, size, "white@0", "(w-tw)/2", ty, alpha=alpha, enable=e,
                     extra=f"borderw={max(1, int(2 * k))}:bordercolor=white@0.7:"
                           f"shadowcolor=black@0.35:shadowx={max(2, int(6 * k))}:"
                           f"shadowy={max(2, int(8 * k))}")
             + f"[{edge}]",
             f"[{o1}][{edge}]overlay=0:0:shortest=1[{out}]"]
        if behind:  # the type sits behind you: put you back on top
            g[-1] = g[-1].replace(f"[{out}]", f"[{out}t]")
            g += [_cutout(c, f"{a1}k", f"{out}k"),
                  f"[{out}t][{out}k]overlay=0:0:shortest=1[{out}]"]
        return g, out
    return _swap(c, wins, build)


MOTION_FILTERS: dict[str, Callable] = {
    "lionstone.orbit": orbit,
    "lionstone.couch-wall": couch_wall,
    "lionstone.ui-world": ui_world,
    "lionstone.frame-break": frame_break,
    "lionstone.digital-zoom": digital_zoom,
    "lionstone.phone-mockup": phone_mockup,
    "lionstone.checklist": checklist,
    "lionstone.headline-wall": headline_wall,
    "lionstone.zoom-through-cut": zoom_through_cut,
    "lionstone.chart-grow": chart_grow,
    "lionstone.pull-back-reveal": pull_back_reveal,
    "lionstone.green-screen": green_screen,
    "lionstone.paper-cut": paper_cut,
    "lionstone.doodle-boil": doodle_boil,
    "lionstone.vertigo": vertigo,
    "lionstone.cover-story": cover_story,
    "lionstone.glass-type": glass_type,
}


def register() -> None:
    fa.FILTERS.update(MOTION_FILTERS)


register()
