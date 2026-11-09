"""Motion FX 2 — eight more motion-design effects for talking-head video (Lionstone 1.1).

Split-flap Board, Count-up Stat, Beat Type, Day Grid, Particle Reveal, Receipt,
Notification Stack and Before/After.

Same contract and helpers as ``motion_fx``: every builder gets validated parameters and
output-time windows and returns a fragment that ends with an unlabeled filter. FFmpeg
filter math plus the bundled fonts; geometry is relative, so one preset works on 9:16,
1:1 and 16:9. Anything that moves is an overlay (or crop) with a per-frame x/y
expression: drawbox can't animate its position.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable

from ..easing import _f
from . import ffmpeg_adapter as fa
from . import motion_fx as mfx
from .ffmpeg_adapter import en, ensure_even
from .motion_fx import MEDIUM, _items, _rounded, _still, _swap, _t0, _text, _zoom
from .reel_fx import _hex, _prog, _rgb

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


# ----------------------------------------------------------------------- helpers
def _rr(x: float, y: float, w: float, h: float, r: float) -> str:
    """geq coverage (0-1, anti-aliased) of a rounded rectangle at (x, y)."""
    return (f"clip({_f(r)}+0.5-hypot(max(abs(X-{_f(x + w / 2)})-{_f(w / 2 - r)},0),"
            f"max(abs(Y-{_f(y + h / 2)})-{_f(h / 2 - r)},0)),0,1)")


def _panel(c, w: int, h: int, r: float, color: str, opacity: float = 1.0, draw: str = "") -> str:
    """Rounded panel sprite (static, RGBA), optionally with text/boxes drawn on it once."""
    pr, pg, pb = _rgb(color)
    return _still(c, w, h, str(pr), str(pg), str(pb), f"{_f(opacity)}*{_rounded(w, h, r)}", draw)


def _cap_y(cy: float, size: float) -> str:
    """drawtext y that centres capitals on `cy` (Poppins: ascent ≈ 1.05 em, caps ≈ 0.7 em)."""
    return _f(cy - 0.7 * size)


def _live(wins, delay: float) -> str:
    """1 once (window start + delay) has passed, inside the windows."""
    return f"gt({_t0(wins, delay)},0)"


def _lit(s: str) -> str:
    """Literal text inside an expansion=normal drawtext file."""
    return s.replace("\\", "\\\\").replace("%", "\\%")


# ========================================================== 18 · Split-flap Board
def split_flap(p, wins, c):
    """A departures board spells your word: every tile flips through letters, then lands."""
    W, H, k = c.W, c.H, c.k
    text = (p["text"] or "LIONSTONE").upper()
    n = len(text)
    tile_w = ensure_even(min(W * 0.82 / (n + (n - 1) * 0.1), H * 0.1))
    gap = max(2, int(tile_w * 0.1))
    tile_h = ensure_even(tile_w * 1.42)
    total_w = n * tile_w + (n - 1) * gap
    x0, y0 = (W - total_w) // 2, ensure_even(H * p["y"] - tile_h / 2)
    size = tile_h * 0.64
    pad, hinge = ensure_even(tile_w * 0.25), max(2, int(3 * k))
    flips, rate, stag = int(p["flips"]), p["rate"], p["stagger"]
    ink, e = _hex(p["ink"]), en(wins)
    ty = _cap_y(y0 + tile_h / 2, size)
    parts = [f"drawbox={x0 - pad}:{y0 - pad}:{total_w + 2 * pad}:{tile_h + 2 * pad}:"
             f"color=black@0.62:t=fill:enable='{e}'",
             f"drawbox={x0 - pad}:{y0 + tile_h + pad}:{total_w + 2 * pad}:{max(2, int(5 * k))}:"
             f"color={_hex(p['accent'])}:t=fill:enable='{e}'"]
    for i, ch in enumerate(text):
        tx = x0 + i * (tile_w + gap)
        cx = f"{tx}+({tile_w}-tw)/2"
        parts += [f"drawbox={tx}:{y0}:{tile_w}:{tile_h}:color={_hex(p['tile'])}:t=fill:enable='{e}'",
                  f"drawbox={tx}:{y0 + tile_h // 2}:{tile_w}:{tile_h - tile_h // 2}:"
                  f"color=white@0.05:t=fill:enable='{e}'"]
        if ch != " ":
            rng = random.Random(i * 7919 + ord(ch))  # same flips on every render
            for a, b in wins:
                land = min(b, a + 0.15 + i * stag + flips / rate)
                for j in range(flips):
                    t0, t1 = land - (flips - j) / rate, land - (flips - j - 1) / rate
                    if t0 >= a:
                        parts.append(_text(rng.choice(CHARS.replace(ch, "")), size, ink, cx, ty,
                                           enable=f"gte(t,{_f(t0)})*lt(t,{_f(t1)})"))
                parts.append(_text(ch, size, ink, cx, ty, enable=f"between(t,{_f(land)},{_f(b)})"))
        parts.append(f"drawbox={tx}:{y0 + tile_h // 2 - hinge // 2}:{tile_w}:{hinge}:"
                     f"color=black@0.75:t=fill:enable='{e}'")
    return ",".join(parts)


# ============================================================== 19 · Count-up Stat
def count_up(p, wins, c):
    """Your number counts up on a brand card, with a bar that fills as it climbs."""
    W, H, k = c.W, c.H, c.k
    portrait = H >= W
    cw = ensure_even(W * (0.8 if portrait else 0.42))
    ch = ensure_even(cw * 0.56)
    x0 = (W - cw) // 2 if portrait else ensure_even(W * 0.05)
    y0 = H * p["y"]
    P = _prog(wins, "ease-out", 0.25, p["draw"])
    dy = f"{_f(H * 0.03)}*(1-{_prog(wins, 'ease-out', 0, 0.5)})"
    dec = int(p["decimals"])
    v = f"({_f(p['value'])}*{P})"
    if dec:
        m = 10 ** dec
        num = (f"%{{eif:floor({v}+0.000001):d}}.%{{eif:mod(floor({v}*{m}+0.000001),{m}):d:{dec}}}")
    else:
        num = f"%{{eif:floor({v}+0.000001):d}}"
    pre, suf = p["prefix"], p["suffix"]
    if mfx.has_filter("drawtext"):
        number, expansion = _lit(pre) + num + _lit(suf), "normal"
    else:  # placeholder bar of the final number's width
        number, expansion = f"{pre}{p['value']:.{dec}f}{suf}", "none"
    bx = ensure_even(cw * 0.08)
    bw, bh, by = cw - 2 * bx, max(2, ensure_even(ch * 0.04)), ensure_even(ch * 0.82)
    pr, pg, pb = _rgb(p["panel"])
    groove = "#{:02X}{:02X}{:02X}".format(*(int(q * 0.8 + 255 * 0.2) for q in (pr, pg, pb)))
    ar, ag, ab = _rgb(p["accent"])
    e = en(wins)
    base, card, bar, track = (c.L(x) for x in ("nb", "nc", "nr", "nt"))
    nsize = ch * 0.4
    return ";".join([
        f"null[{base}]",
        _panel(c, cw, ch, 26 * k, p["panel"], p["opacity"]) + f"[{card}]",
        _still(c, bw, bh, str(ar), str(ag), str(ab), "255") + f"[{bar}]",
        f"color=c={_hex(groove)}:s={bw}x{bh}:r={_f(c.fps)}:d={_f(c.total + 1)}[{track}g]",
        f"[{track}g][{bar}]overlay=x='-{bw}*(1-{P})':y=0:shortest=1[{track}]",
        f"[{base}][{card}]overlay=x={x0}:y='{_f(y0)}+{dy}':shortest=1:enable='{e}'[{base}1]",
        f"[{base}1][{track}]overlay=x={x0 + bx}:y='{_f(y0 + by)}+{dy}':shortest=1:enable='{e}',"
        + _text(number, nsize, "white", f"{x0}+({cw}-tw)/2", f"{_f(y0 + ch * 0.1)}+{dy}",
                enable=e, expansion=expansion) + ","
        + _text(p["label"].upper(), ch * 0.1, _hex(p["accent"]), f"{x0}+({cw}-tw)/2",
                f"{_f(y0 + ch * 0.6)}+{dy}", font=MEDIUM, enable=e),
    ])


# ================================================================== 20 · Beat Type
def beat_type(p, wins, c):
    """Words land on the beat: one word per beat, the frame pulses on every hit."""
    W, H = c.W, c.H
    words = [w.upper() for w in (p["text"] or "").replace("|", " ").split()] or ["ON", "THE", "BEAT"]
    spb = 60 / p["bpm"]
    size = min(W * 0.9 / max(3, max(len(w) for w in words)) * 1.55, H * 0.13)
    shadow = f"shadowcolor=black@0.55:shadowx={max(1, int(4 * c.k))}:shadowy={max(1, int(5 * c.k))}"
    parts, pulse = [], []
    for a, b in wins:
        t0 = a + p["offset"]
        for i in range(64):  # 64 beats per window is plenty for a Reel
            s = t0 + i * spb
            if s >= b:
                break
            pop = f"max(0,1-(t-{_f(s)})/{_f(min(0.16, spb / 2))})"
            parts.append(_text(words[i % len(words)], size * (1.15 if i % 4 == 0 else 1.0),
                               _hex(p["accent"] if i % 2 else p["ink"]), "(w-tw)/2",
                               f"{_f(H * p['y'])}-th/2+{_f(H * 0.04)}*{pop}*{pop}",
                               alpha=f"min(1,(t-{_f(s)})/0.05)",
                               enable=f"gte(t,{_f(s)})*lt(t,{_f(min(b, s + spb))})", extra=shadow))
        pulse.append(f"if(between(t,{_f(t0)},{_f(b)}),exp(-7*mod(t-{_f(t0)},{_f(spb)})/{_f(spb)}),0)")
    Z = f"(1+{_f(p['pulse'])}*({'+'.join(pulse) or '0'}))"
    return ",".join([_zoom(c, Z), *parts])


# =================================================================== 21 · Day Grid
def day_grid(p, wins, c):
    """Day 17 of 30: a challenge grid fills up to today, and today's square blinks."""
    W, H, k = c.W, c.H, c.k
    total = int(p["total"])
    day = min(int(p["day"]), total)
    cols = 7 if total <= 35 else 10
    rows = math.ceil(total / cols)
    portrait = H >= W
    cw = ensure_even(W * (0.78 if portrait else 0.4))
    pad = cw * 0.07
    pitch = (cw - 2 * pad) / cols
    cell = ensure_even(pitch * 0.8)
    head = cw * 0.24
    ch = ensure_even(head + rows * pitch + pad * 0.7)
    x0 = (W - cw) // 2 if portrait else ensure_even(W * 0.05)
    y0 = ensure_even(H * p["y"] - ch / 2)
    acc, e = _hex(p["accent"]), en(wins)
    base, card = c.L("db"), c.L("dc")
    line = max(1, int(2 * k))
    draw = [_text(f"DAY {day}", head * 0.4, "white", f"{_f(x0 + pad)}", f"{_f(y0 + pad * 0.7)}",
                  alpha=mfx._fade(wins, 0.0, 0.3), enable=e),
            _text(f"{round(100 * day / total)}%", head * 0.3, acc, f"{_f(x0 + cw - pad)}-tw",
                  f"{_f(y0 + pad * 0.85)}", alpha=mfx._fade(wins, 0.2, 0.3), enable=e),
            _text(f"{p['label'].upper()}  ·  {day}/{total}", head * 0.12, "white@0.7",
                  f"{_f(x0 + pad)}", f"{_f(y0 + pad * 0.7 + head * 0.48)}", font=MEDIUM, enable=e)]
    for i in range(total):
        r, col = divmod(i, cols)
        cx = int(x0 + pad + col * pitch + (pitch - cell) / 2)
        cy = int(y0 + head + r * pitch + (pitch - cell) / 2)
        when = 0.3 + p["fill"] * i / max(1, day)
        draw.append(f"drawbox={cx}:{cy}:{cell}:{cell}:color=white@0.22:t={line}:enable='{e}'")
        if i < day - 1:
            draw.append(f"drawbox={cx}:{cy}:{cell}:{cell}:color={acc}@0.9:t=fill:"
                        f"enable='{e}*{_live(wins, when)}'")
        elif i == day - 1:  # today: white, blinking once it has landed
            draw.append(f"drawbox={cx}:{cy}:{cell}:{cell}:color=white:t=fill:"
                        f"enable='{e}*{_live(wins, when)}*lt(mod(t,0.9),0.6)'")
            draw.append(f"drawbox={cx - 2 * line}:{cy - 2 * line}:{cell + 4 * line}:"
                        f"{cell + 4 * line}:color={acc}:t={2 * line}:enable='{e}*{_live(wins, when)}'")
    return ";".join([
        f"null[{base}]",
        _panel(c, cw, ch, 26 * k, p["panel"], p["opacity"]) + f"[{card}]",
        f"[{base}][{card}]overlay=x={x0}:y={y0}:shortest=1:enable='{e}'," + ",".join(draw),
    ])


# ============================================================ 22 · Particle Reveal
def particle_reveal(p, wins, c):
    """Sparks swirl in, lock into a ring, flash, then burst out as your title appears."""
    W, H, k = c.W, c.H, c.k
    portrait = H >= W
    n = int(p["count"])
    cx, cy = W / 2, H * p["y"]
    rx = W * (0.42 if portrait else 0.26)
    ry = min(W, H) * (0.26 if portrait else 0.34)
    conv = p["converge"]
    # one short time prelude per expression: ld(0) = gather (smoothstep), ld(1) = burst (ease-out)
    g0, g1 = ("+".join(f"if(between(t,{_f(a)},{_f(b)}),clip((t-{_f(a + d)})/{_f(dur)},0,1),0)"
                       for a, b in wins) or "0" for d, dur in ((0.0, conv), (conv, 1.2)))
    pre = f"st(0,{g0});st(1,{g1});st(0,ld(0)*ld(0)*(3-2*ld(0)));st(1,1-pow(1-ld(1),3));"
    ar, ag, ab = _rgb(p["color"])
    rng = random.Random(11)  # the same constellation on every render
    sizes = [max(4, ensure_even(s * k * p["size"])) for s in (44, 24)]

    def dot(s: int) -> str:
        d = f"hypot(X-{_f(s / 2 - 0.5)},Y-{_f(s / 2 - 0.5)})/{_f(s / 2)}"
        core = f"pow(clip(1-2*{d},0,1),2)"
        return _still(c, s, s, f"{ar}+{255 - ar}*{core}", f"{ag}+{255 - ag}*{core}",
                      f"{ab}+{255 - ab}*{core}", f"255*pow(clip(1-{d},0,1),1.5)")

    e = en(wins)
    base = c.L("pb")
    big = [c.L("pd") for _ in range(n // 3)]
    small = [c.L("pd") for _ in range(n - n // 3)]
    g = [f"null,drawbox=0:0:iw:ih:color=black@{_f(p['dim'])}:t=fill:enable='{e}'[{base}]",
         dot(sizes[0]) + f",split={len(big)}" + "".join(f"[{x}]" for x in big),
         dot(sizes[1]) + f",split={len(small)}" + "".join(f"[{x}]" for x in small)]
    cur = base
    for i, spr in enumerate(big + small):
        s = sizes[0] if i < len(big) else sizes[1]
        th = 2 * math.pi * i / n + rng.uniform(-0.12, 0.12)
        m = (f"(1+{_f(rng.uniform(1.8, 3.2))}*(1-ld(0))+{_f(rng.uniform(1.6, 4.0))}*ld(1))"
             f"*{_f(rng.uniform(0.93, 1.07))}")
        phi = f"({_f(th)}+{_f(rng.uniform(1.2, 2.4))}*(1-ld(0))+0.35*ld(1))"
        nxt = c.L("pp")
        g.append(f"[{cur}][{spr}]overlay=x='{pre}{_f(cx - s / 2)}+{_f(rx)}*{m}*cos({phi})':"
                 f"y='{pre}{_f(cy - s / 2)}+{_f(ry)}*{m}*sin({phi})':shortest=1:enable='{e}'[{nxt}]")
        cur = nxt
    flash = [(a + conv - 1 / c.fps, a + conv + 1 / c.fps) for a, _ in wins]
    title = p["title"] or "LIONSTONE"
    size = min(W * 0.78 / max(4, len(title)) * 1.5, H * 0.09)
    g.append(f"[{cur}]drawbox=0:0:iw:ih:color=white@0.35:t=fill:enable='{en(flash)}',"
             + _text(title, size, "white", "(w-tw)/2", _cap_y(cy, size),
                     alpha=mfx._fade(wins, conv, 0.35), enable=e) + ","
             + _text(p["subtitle"].upper(), size * 0.32, _hex(p["color"]), "(w-tw)/2",
                     f"{_f(cy + size * 0.75)}", font=MEDIUM, alpha=mfx._fade(wins, conv + 0.25, 0.35),
                     enable=e))
    return ";".join(g)


# ==================================================================== 23 · Receipt
def receipt(p, wins, c):
    """The receipt for your result prints out line by line from a slot at the top."""
    W, H, k = c.W, c.H, c.k
    rows = [(lab.strip(), val.strip()) for lab, _, val in
            (it.partition("=") for it in _items(p["items"], ["Hook=2 s", "Cuts=14"]))][:8]
    tl, _, tv = (p["total"] or "TOTAL=FREE").partition("=")
    portrait = H >= W
    rw = ensure_even(W * (0.58 if portrait else 0.3))
    lh, pad = rw * 0.085, rw * 0.08
    head = lh * 2.5
    zig = lh * 0.35
    rh = ensure_even(head + lh * (len(rows) + 0.7) + lh * 1.6 + lh * 1.7 + zig)
    ink, acc = _hex(p["ink"]), _hex(p["accent"])
    t = max(1, int(1.5 * k))

    def dashes(y: float) -> list[str]:
        d = max(2, int(rw / 60))
        return [f"drawbox={int(pad + x)}:{int(y)}:{d}:{t}:color={ink}@0.6:t=fill"
                for x in range(0, int(rw - 2 * pad), 2 * d)]
    draw = [_text(p["title"].upper(), lh * 0.62, ink, "(w-tw)/2", f"{_f(pad * 0.9)}"),
            _text(p["subtitle"], lh * 0.4, f"{ink}@0.7", "(w-tw)/2", f"{_f(pad * 0.9 + lh * 0.9)}",
                  font=MEDIUM), *dashes(head - lh * 0.3)]
    for i, (lab, val) in enumerate(rows):
        y = _f(head + i * lh)
        draw += [_text(lab, lh * 0.44, ink, f"{_f(pad)}", y, font=MEDIUM),
                 _text(val, lh * 0.44, ink, f"w-{_f(pad)}-tw", y, font=MEDIUM)]
    ty = head + (len(rows) + 0.4) * lh
    draw += dashes(ty)
    draw += [_text(tl.strip().upper(), lh * 0.62, ink, f"{_f(pad)}", f"{_f(ty + lh * 0.4)}"),
             _text(tv.strip(), lh * 0.62, acc, f"w-{_f(pad)}-tw", f"{_f(ty + lh * 0.4)}")]
    bw, bh = rw * 0.6, lh * 0.9
    bx0, by0 = (rw - bw) / 2, ty + lh * 1.7
    stripes = [2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 1, 3, 1, 2, 2, 1]
    unit = max(1, int(bw / sum(s + 1 for s in stripes)))
    xx = 0
    for sw in stripes:
        draw.append(f"drawbox={int(bx0 + xx)}:{int(by0)}:{sw * unit}:{int(bh)}:color={ink}:t=fill")
        xx += (sw + 1) * unit
    pr, pg, pb = _rgb(p["paper"])
    pz = rw / 22
    edge = f"({_f(rh - zig)}+{_f(zig)}*abs(2*mod(X,{_f(pz)})/{_f(pz)}-1))"
    grain = "(random(1)*8-4)"
    sprite = _still(c, rw, rh, f"{pr}+{grain}", f"{pg}+{grain}", f"{pb}+{grain}",
                    f"255*clip({edge}-Y,0,1)", ",".join(draw))
    steps = max(8, int(p["print"] * 14))
    P = f"floor({_prog(wins, 'linear', 0.25, p['print'])}*{steps})/{steps}"  # printer stutter
    rx = int(min(W - rw, max(0, W * p["x"] - rw / 2)))
    sw_, sh_ = ensure_even(rw * 1.16), ensure_even(lh * 0.9)
    sx, sy = rx - (sw_ - rw) // 2, ensure_even(H * p["y"])
    e = en(wins)
    base, rc = c.L("rb"), c.L("rc")
    return ";".join([
        f"null[{base}]",
        sprite + f",pad={rw}:{2 * rh}:0:0:color=black@0,crop={rw}:{rh}:0:'{rh}*(1-{P})'[{rc}]",
        f"[{base}][{rc}]overlay=x={rx}:y={sy + sh_ // 2}:shortest=1:enable='{e}',"
        f"drawbox={sx}:{sy}:{sw_}:{sh_}:color=0x0E0F13:t=fill:enable='{e}',"
        f"drawbox={sx + sh_ // 3}:{sy + sh_ // 2 - t}:{sw_ - 2 * (sh_ // 3)}:{2 * t}:"
        f"color=black:t=fill:enable='{e}',"
        f"drawbox={sx + sw_ - sh_ // 2 - max(4, sh_ // 6)}:{sy + sh_ // 4}:{max(4, sh_ // 6)}:"
        f"{max(4, sh_ // 6)}:color={acc}:t=fill:enable='{e}'",
    ])


# ======================================================== 24 · Notification Stack
def notification_stack(p, wins, c):
    """Your phone lights up: notification cards drop in and stack, newest on top."""
    W, H = c.W, c.H
    items = _items(p["items"], ["Lionstone: Your Reel is ready"])[:4]
    portrait = H >= W
    cw = ensure_even(W * (0.88 if portrait else 0.42))
    ch = ensure_even(cw * 0.19)
    gap = ensure_even(ch * 0.12)
    x0 = (W - cw) // 2 if portrait else ensure_even(W * 0.96 - cw)
    top = ensure_even(H * p["y"])
    icon = ensure_even(ch * 0.56)
    ix, iy = ensure_even(ch * 0.22), (ch - icon) // 2
    (pr, pg, pb), (ar, ag, ab) = _rgb(p["panel"]), _rgb(p["accent"])
    cov = _rr(ix, iy, icon, icon, icon * 0.24)
    tx = ix + icon + ch * 0.2
    ts, bs = ch * 0.2, ch * 0.18
    room = int((cw - tx - ch * 0.25) / (bs * 0.52))
    e = en(wins)
    base = c.L("nb")
    g = [f"null[{base}]"]
    cur = base
    delays = [0.15 + i * p["interval"] for i in range(len(items))]
    for i, it in enumerate(items):
        title, _, body = it.partition(":")
        title, body = title.strip(), body.strip()
        body = body if len(body) <= room else body[:max(1, room - 3)].rstrip() + "..."
        draw = [_text(title[:1].upper() or "L", icon * 0.55, _hex(p["panel"]),
                      f"{ix}+({icon}-tw)/2", _cap_y(iy + icon / 2, icon * 0.55)),
                _text(title, ts, "white", _f(tx), _f(ch * 0.16)),
                _text(body, bs, "white@0.78", _f(tx), _f(ch * 0.52), font=MEDIUM),
                _text("now", ch * 0.14, "white@0.5", f"w-{_f(ch * 0.25)}-tw", _f(ch * 0.2),
                      font=MEDIUM)]
        spr, nxt = c.L("ns"), c.L("nn")
        g.append(_still(c, cw, ch, f"{pr}+({ar - pr})*{cov}", f"{pg}+({ag - pg})*{cov}",
                        f"{pb}+({ab - pb})*{cov}", f"{_f(p['opacity'])}*{_rounded(cw, ch, ch * 0.28)}",
                        ",".join(draw)) + f"[{spr}]")
        push = "+".join(f"{ch + gap}*{_prog(wins, 'ease-out', d, 0.35)}" for d in delays[i + 1:]) or "0"
        drop = f"{top + ch + 10}*(1-{_prog(wins, 'spring', delays[i], 0.55)})"
        g.append(f"[{cur}][{spr}]overlay=x={x0}:y='{top}+{push}-{drop}':shortest=1:"
                 f"enable='{e}*{_live(wins, delays[i])}'" + ("" if i == len(items) - 1 else f"[{nxt}]"))
        cur = nxt
    return ";".join(g)


# ============================================================ 25 · Before / After
def before_after(p, wins, c):
    """A slider wipes between the flat 'before' and your graded 'after', labels included."""
    W, H, k = c.W, c.H, c.k
    look = {"flat": "eq=contrast=0.8:saturation=0.45:gamma=1.12:brightness=0.02",
            "mono": "hue=s=0,eq=contrast=0.9",
            "soft": f"gblur=sigma={_f(max(2.0, 6 * k))},eq=saturation=0.7"}[p["look"]]
    sweeps = p["sweeps"]
    pos = "(" + "+".join(
        f"if(between(t,{_f(a)},{_f(b)}),0.5+0.38*cos(2*PI*{_f(sweeps)}*(t-{_f(a)})/{_f(max(1e-3, b - a))}),0)"
        for a, b in wins) + ")"
    lw = max(2, ensure_even(4 * k))
    ks = max(8, ensure_even(110 * k))
    ar, ag, ab = _rgb(p["accent"])
    r_in = f"lt(hypot(X-{_f(ks / 2)},Y-{_f(ks / 2)}),{_f(ks * 0.34)})"
    lab = H * 0.026
    m = ensure_even(W * 0.06)
    box = f"box=1:boxcolor=black@0.55:boxborderw={max(2, int(lab * 0.5))}"

    def build(b):
        a1, a2, bef, msk, wht, ln, kn, o1, o2, out = (c.L(x) for x in (
            "ba", "bb", "bf", "bm", "bw", "bl", "bk", "b1", "b2", "bo"))
        d = f"r={_f(c.fps)}:d={_f(c.total + 1)}"
        g = [f"[{b}]split=2[{a1}][{a2}]",
             f"[{a1}]{look},format=rgba[{bef}c]",
             f"color=c=black:s={W}x{H}:{d}[{msk}b]",
             f"color=c=white:s={W}x{H}:{d}[{wht}]",
             f"[{msk}b][{wht}]overlay=x='-{W}+{W}*{pos}':y=0:shortest=1,format=gray[{msk}]",
             f"[{bef}c][{msk}]alphamerge[{bef}]",
             f"[{a2}]eq=contrast=1.06:saturation=1.18[{a2}e]",
             f"[{a2}e][{bef}]overlay=0:0:shortest=1[{o1}]",
             f"color=c={_hex(p['line'])}:s={lw}x{H}:{d}[{ln}]",
             f"[{o1}][{ln}]overlay=x='{W}*{pos}-{lw // 2}':y=0:shortest=1[{o2}]",
             _still(c, ks, ks, f"if({r_in},20,{ar})", f"if({r_in},22,{ag})", f"if({r_in},28,{ab})",
                    f"255*clip({_f(ks / 2)}+0.5-hypot(X-{_f(ks / 2)},Y-{_f(ks / 2)}),0,1)",
                    _text("< >", ks * 0.34, "white", "(w-tw)/2", _cap_y(ks / 2, ks * 0.3)))
             + f"[{kn}]",
             f"[{o2}][{kn}]overlay=x='{W}*{pos}-{ks // 2}':y={(H - ks) // 2}:shortest=1,"
             + _text(p["before"].upper(), lab, "white", f"{m}", f"{_f(H * 0.07)}", extra=box) + ","
             + _text(p["after"].upper(), lab, "white", f"w-{m}-tw", f"{_f(H * 0.07)}",
                     extra=box.replace("black@0.55", f"{_hex(p['accent'])}@0.9")) + f"[{out}]"]
        return g, out
    return _swap(c, wins, build)


MOTION_FILTERS_2: dict[str, Callable] = {
    "lionstone.split-flap": split_flap,
    "lionstone.count-up": count_up,
    "lionstone.beat-type": beat_type,
    "lionstone.day-grid": day_grid,
    "lionstone.particle-reveal": particle_reveal,
    "lionstone.receipt": receipt,
    "lionstone.notification-stack": notification_stack,
    "lionstone.before-after": before_after,
}


def register() -> None:
    fa.FILTERS.update(MOTION_FILTERS_2)


register()
