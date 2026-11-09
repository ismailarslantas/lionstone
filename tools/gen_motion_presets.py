"""Generate the Motion FX pack catalog (src/lionstone/pro/features/presets/motionfx.json).

Run after editing: python tools/gen_motion_presets.py

Seventeen motion-design effects for talking-head Reels, Shorts and videos, new in
Lionstone 1.0. Every name, look and parameter set is original to Lionstone; the
renderers are FFmpeg filter math in ``features/renderers/motion_fx.py`` plus the
bundled Poppins / DM Serif Display fonts (SIL OFL). No stock assets are bundled.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_reel_presets import ACCENT, INK, color, enum, integer, num  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "lionstone" / "pro" / "features" / "presets" / "motionfx.json"
LIC = {"source": "lionstone-original", "verified": True}
CAT = "motion-fx"
PAPER = "#F2EAD8"


def text(default, max_len=200):
    return {"type": "string", "default": default, "maxLength": max_len}


def boolean(default):
    return {"type": "bool", "default": default}


def fx(slug, name, tier, line, desc, params, cost="medium", tags=(), limitations=(),
       styles=("social",), duration=None, text_fx=False, matte=False):
    lim = list(limitations)
    if matte:
        tags = (*tags, "matte")
    if text_fx:
        lim.append("Text needs an FFmpeg build with drawtext; without it, bars stand in for text.")
    return {
        "id": f"lionstone.{slug}", "name": name, "kind": "effect", "category": CAT,
        "tier": tier, "implementationStatus": "ready", "version": 1,
        "parameters": params, "performanceCost": cost, "license": LIC,
        "description": f"{line} — {desc}", "tags": ["motion", "reel", *tags],
        "styles": list(styles), "supportedRenderers": ["ffmpeg"],
        "compatibleMedia": ["video", "image"],
        "duration": duration or {"default": 4.0, "min": 1.0, "max": 60.0},
        "intensityRange": [0.0, 1.0], "fallbackEffectId": None,
        "limitations": lim, "pipeline": "filter",
    }


MOTION_FX = [
    fx("orbit", "Orbit", "pro", "the camera circles you",
       "Your shot becomes a rounded card that swings left and right in 3D perspective over a "
       "brand-lit stage, as if the camera were orbiting you.",
       {"angle": num(28, 5, 60, "deg"), "speed": num(0.25, 0.05, 1.0, "swings/s"),
        "inset": num(0.8, 0.6, 0.95), "bg": color(INK), "accent": color(ACCENT)},
       tags=["3d", "camera"]),
    fx("couch-wall", "Couch Wall", "pro", "you, on every screen in the room",
       "A 3x3 wall of monitors all playing your clip. The camera starts on the centre screen and "
       "pulls back to reveal the wall (or pushes in with direction=in).",
       {"direction": enum("out", ["out", "in"]), "pull": num(1.6, 0.4, 5, "s"),
        "dim": num(0.35, 0, 0.8), "bezel": color("#0B0C10")},
       cost="high", tags=["wall", "screens", "reveal"]),
    fx("ui-world", "UI World", "studio", "you, inside the interface",
       "Your clip plays in an app window that floats up among drifting interface cards, toggles "
       "and buttons in your brand colours. Made for tech, SaaS and tutorial creators.",
       {"scale": num(0.78, 0.5, 0.9), "bg": color(INK), "panel": color("#23262F"),
        "accent": color(ACCENT)},
       tags=["ui", "app", "brand"]),
    fx("frame-break", "Frame Break", "pro", "you step out of the frame",
       "You sit inside a picture frame on a flat backdrop, then your head breaks out over the top "
       "edge with a soft drop shadow.",
       {"top": num(0.46, 0.25, 0.6), "width": num(0.5, 0.3, 0.8), "bg": color(PAPER),
        "frame": color(INK)},
       tags=["frame", "pop-out"],
       limitations=["Without the person matte (OpenCV) the break-out is a centred column: "
                    "keep your head centred above the frame line."], matte=True),
    fx("digital-zoom", "Digital Zoom", "pro", "punch in, step by step",
       "Stepped punch-ins towards a point you choose. Every step snaps in with an RGB tick, a "
       "focus reticle frames the shot and faint scan lines sell the digital look.",
       {"steps": integer(3, 1, 6), "zoom": num(1.6, 1.1, 3.0), "x": num(0.5), "y": num(0.35),
        "scanlines": num(0.5), "accent": color(ACCENT)},
       cost="low", tags=["zoom", "punch-in"]),
    fx("phone-mockup", "Phone Mockup", "studio", "your clip, on a phone",
       "A clean phone with a rounded screen and notch rises into the frame and plays your clip, "
       "floating gently over a brand backdrop.",
       {"size": num(1.0, 0.7, 1.1), "body": color("#0E0F13"), "bg": color(INK),
        "accent": color(ACCENT)},
       tags=["mockup", "phone", "brand"]),
    fx("checklist", "Checklist", "studio", "tick, tick, tick",
       "A list card with your items; each one checks off in turn across the window. Separate "
       "items with '|'.",
       {"items": text("Hook in 2 seconds|One idea per Reel|Clear call to action"),
        "y": num(0.7, 0.2, 0.85), "panel": color(INK), "opacity": num(0.85),
        "accent": color(ACCENT)},
       cost="low", tags=["list", "steps", "text"], text_fx=True),
    fx("headline-wall", "Headline Wall", "pro", "the headlines are about you",
       "A wall of paper headlines scrolls behind you while your clip sits in an accent-bordered "
       "card in front. Separate headlines with '|'.",
       {"headlines": text("WHO IS THIS CREATOR?|THE EDIT EVERYONE SHARES|NEW SERIES STARTS TODAY|"
                          "SAVE THIS FOR LATER|THE 30-SECOND METHOD|READ THIS BEFORE YOU POST", 600),
        "scale": num(0.62, 0.4, 0.8), "speed": num(1.0, 0.2, 3.0),
        "paper": color(PAPER), "ink": color("#1B1B1B"), "accent": color(ACCENT)},
       tags=["news", "text", "wall"], text_fx=True),
    fx("zoom-through-cut", "Zoom-through Cut", "pro", "dive through the frame into the next shot",
       "A fast push in with motion blur, a one-frame flash at the cut and a settle out on the next "
       "shot. Centre the window on a cut; 0.6 to 1 s works best.",
       {"zoom": num(3.0, 1.5, 6.0), "flash": color("#FFFFFF"), "flash_opacity": num(0.6)},
       cost="low", tags=["transition", "zoom"],
       duration={"default": 0.8, "min": 0.3, "max": 3.0}),
    fx("chart-grow", "Chart Grow", "studio", "your numbers climb while you talk",
       "A line-and-area chart draws itself left to right on a brand card, with an optional label "
       "such as '+240%'. Give your own values (0 to 1) or use the rising default.",
       {"values": {"type": "list", "items": {"type": "number", "min": 0, "max": 1}, "default": []},
        "label": text("+240%", 24), "y": num(0.1, 0.02, 0.7), "draw": num(1.6, 0.4, 6, "s"),
        "panel": color(INK), "opacity": num(0.9), "accent": color(ACCENT)},
       tags=["chart", "data", "brand"], text_fx=True),
    fx("pull-back-reveal", "Pull-back Reveal", "pro", "start tight, then show the whole scene",
       "Opens tight on a detail you choose and eases back to the full shot while a vignette "
       "lifts.",
       {"zoom": num(2.2, 1.2, 4.0), "x": num(0.5), "y": num(0.32), "pull": num(1.8, 0.4, 6, "s")},
       cost="low", tags=["zoom", "reveal"]),
    fx("green-screen", "Green Screen", "studio", "swap your backdrop for your brand",
       "Keys out a green (or blue) backdrop, removes the colour spill and puts you on a brand "
       "stage with an optional grid.",
       {"method": enum("auto", ["auto", "chroma", "matte"]),
        "key": color("#00B140"), "similarity": num(0.12, 0.01, 0.4), "blend": num(0.08, 0, 0.3),
        "grid": boolean(True), "bg": color(INK), "accent": color(ACCENT)},
       tags=["chroma", "key", "brand"],
       limitations=["Without the person matte (OpenCV) it needs footage shot on an evenly lit "
                    "green or blue backdrop."], matte=True),
    fx("paper-cut", "Paper Cut", "pro", "you, cut out of paper",
       "Flattens the shot into a few poster tones with paper grain while two torn paper strips "
       "slide in at the top and bottom.",
       {"levels": integer(5, 3, 8), "intensity": num(0.6), "strip": num(0.14, 0.06, 0.25),
        "paper": color(PAPER), "paper2": color(ACCENT)},
       tags=["paper", "craft"]),
    fx("doodle-boil", "Doodle Boil", "pro", "hand-drawn lines that never sit still",
       "Traces the shot as ink lines redrawn a few times a second, with a small wobble on every "
       "redraw: the boiling-line look of hand-drawn animation. Sketch mode puts the lines on "
       "paper.",
       {"mode": enum("overlay", ["overlay", "sketch"]), "boil": num(8, 4, 15, "fps"),
        "wobble": num(0.6), "detail": num(0.5), "color": color("#FFFFFF"),
        "paper": color(PAPER)},
       tags=["sketch", "hand-drawn"], matte=True),
    fx("vertigo", "Vertigo", "pro", "the room stretches, you stay put",
       "A dolly-zoom illusion: the background zooms around you while a soft oval around the "
       "subject keeps its size.",
       {"direction": enum("in", ["in", "out"]), "amount": num(0.35, 0.1, 1.0), "x": num(0.5),
        "y": num(0.4), "size": num(0.55, 0.3, 0.9)},
       tags=["dolly", "zoom", "cinematic"], styles=("social", "cinematic"),
       limitations=["Without the person matte (OpenCV) the subject is a soft oval; keep the "
                    "subject inside it."], matte=True),
    fx("cover-story", "Cover Story", "studio", "you, on the cover",
       "Turns the shot into a magazine cover: masthead, issue line, staggered cover lines with "
       "accent bars and a barcode, over a print-like grade. Separate cover lines with '|'.",
       {"title": text("LIONSTONE", 24), "issue": text("ISSUE 01 · THE CREATOR EDITION", 60),
        "lines": text("The 30-second edit|Why your hook fails|5 habits of top creators"),
        "title_color": color("#FFFFFF"), "ink": color(INK), "accent": color(ACCENT)},
       tags=["magazine", "text", "brand"], text_fx=True),
    fx("glass-type", "Glass Type", "pro", "big glass letters over your shot",
       "Large frosted-glass type rises over the shot: the letters refract a blurred, brighter "
       "copy of the picture and carry a thin light edge.",
       {"text": text("LIONSTONE", 16), "y": num(0.42, 0.1, 0.9), "frost": num(0.6),
        "behind": boolean(True)},
       tags=["text", "glass", "title"], text_fx=True, matte=True),
]


def main() -> int:
    ids = [d["id"] for d in MOTION_FX]
    assert len(ids) == 17 and len(ids) == len(set(ids)), "expected 17 unique ids"
    OUT.write_text(json.dumps(MOTION_FX, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(ids)} motion presets -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
