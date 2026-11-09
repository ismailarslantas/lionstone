"""Build the Motion FX launch visuals from REAL Lionstone renders.

    python scripts/build_motionfx_visuals.py portrait.png cover.png --out build/motionfx

portrait.png: a fictional demo character (9:16 or 3:4). cover.png: a slide in the brand
design (its top bar, the lion logo + "LIONSTONE | v1.0.0", is reused on every slide).
Every effect picture is a frame from `lionstone fx clip`, the same code as the export.
Writes carousel slides (1080x1350) and docs images (docs/img/motionfx-*.jpg).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
FONTS = ROOT / "src" / "lionstone" / "data" / "fonts"
BOLD, MED = str(FONTS / "Poppins-Bold.ttf"), str(FONTS / "Poppins-Medium.ttf")
MONO = next((p for p in ("C:/Windows/Fonts/consolab.ttf",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                         "/System/Library/Fonts/Menlo.ttc") if Path(p).exists()), BOLD)
GOLD, GOLD2, GREY, INK = (245, 197, 24), (232, 163, 61), (178, 178, 186), (10, 10, 12)

# effect id, name, promise, (window start, end), frame time, params
FX = [
    ("orbit", "Orbit", "The camera circles you.", (0, 8), 1.2, {}),
    ("couch-wall", "Couch Wall", "You, on every screen in the room.", (0, 8), 2.4, {}),
    ("ui-world", "UI World", "You, inside the interface.", (0, 8), 2.0, {}),
    ("frame-break", "Frame Break", "You step out of the frame.", (0, 8), 2.0, {}),
    ("digital-zoom", "Digital Zoom", "Punch in, step by step.", (0, 6), 4.3, {}),
    ("phone-mockup", "Phone Mockup", "Your clip, on a phone.", (0, 8), 2.0, {}),
    ("checklist", "Checklist", "Tick, tick, tick.", (0, 6), 4.2, {}),
    ("headline-wall", "Headline Wall", "The headlines are about you.", (0, 8), 2.0, {}),
    ("zoom-through-cut", "Zoom-through Cut", "Dive through the frame into the next shot.",
     (1.0, 2.0), 1.36, {}),
    ("chart-grow", "Chart Grow", "Your numbers climb while you talk.", (0, 8), 2.6, {}),
    ("pull-back-reveal", "Pull-back Reveal", "Start tight, then show the whole scene.", (0, 8),
     0.9, {}),
    ("green-screen", "Green Screen", "Swap your backdrop for your brand.", (0, 8), 2.0,
     {"method": "matte"}),
    ("paper-cut", "Paper Cut", "You, cut out of paper.", (0, 8), 2.0, {}),
    ("doodle-boil", "Doodle Boil", "Hand-drawn lines that never sit still.", (0, 8), 2.0, {}),
    ("vertigo", "Vertigo", "The room stretches, you stay put.", (0, 6), 5.0, {}),
    ("cover-story", "Cover Story", "You, on the cover.", (0, 8), 2.5, {}),
    ("glass-type", "Glass Type", "Big glass letters behind you.", (0, 8), 2.0, {"text": "FOCUS"}),
]


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def demo_clip(portrait: Path, wd: Path) -> Path:
    """8 s 1080x1920 clip with a small hand-held sway, so motion effects have motion."""
    out = wd / "demo.mp4"
    sway = "x='60+40*sin(t*1.7)':y='70+30*sin(t*1.1)'"
    ff("-loop", "1", "-r", "30", "-i", str(portrait), "-f", "lavfi", "-i",
       "anullsrc=r=48000:cl=stereo", "-t", "8", "-vf",
       f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1080:1920:{sway}",
       "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac",
       "-shortest", str(out))
    return out


def renders(clip: Path, wd: Path) -> dict[str, Image.Image]:
    from lionstone.pro.features.clipfx import apply_to_clip
    frames = {}
    for slug, *_, (a, b), t, prm in FX:
        mp4 = wd / f"{slug}.mp4"
        if not mp4.exists():
            apply_to_clip(slug, clip, mp4, params=prm, start=a, end=b)
        png = wd / f"{slug}.png"
        ff("-ss", f"{t:.3f}", "-i", str(mp4), "-frames:v", "1", str(png))
        frames[slug] = Image.open(png).convert("RGB")
        print("rendered", slug)
    ff("-ss", "2", "-i", str(clip), "-frames:v", "1", str(wd / "original.png"))
    frames["original"] = Image.open(wd / "original.png").convert("RGB")
    from lionstone.pro import matte
    ff("-ss", "2", "-i", str(matte.ensure(clip)), "-frames:v", "1", "-vf",
       "scale=1080:1920", str(wd / "matte.png"))
    frames["matte"] = Image.open(wd / "matte.png").convert("RGB")
    return frames


def background(w: int, h: int) -> Image.Image:
    """Black with a soft gold light arc, like the brand slides."""
    bg = Image.new("RGB", (w, h), INK)
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.arc((int(w * 0.55), int(-h * 0.62), int(w * 1.9), int(h * 0.1)), 100, 170, fill=GOLD2,
          width=6)
    soft = glow.filter(ImageFilter.GaussianBlur(18))
    sharp = glow.filter(ImageFilter.GaussianBlur(1.2))
    bg = Image.blend(bg, soft, 0.9)
    return Image.composite(sharp, bg, sharp.convert("L").point(lambda v: 255 if v > 60 else 0))


def header(cover: Path, w: int) -> Image.Image:
    c = Image.open(cover).convert("RGB")
    c = c.resize((w, round(c.height * w / c.width)), Image.LANCZOS)
    hd = c.crop((0, 30, int(w * 0.72), 150)).convert("RGBA")
    # keep the logo and the type, drop the cover's own background
    hd.putalpha(hd.convert("L").point(lambda v: max(0, min(255, (v - 28) * 4))))
    return hd


def rounded(img: Image.Image, r: int) -> Image.Image:
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, *img.size), r, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0, 0), m)
    return out


def text_w(d: ImageDraw.ImageDraw, s: str, f) -> int:
    return int(d.textlength(s, font=f))


def wrap(d, s: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        t = (cur + " " + word).strip()
        if text_w(d, t, f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def footer(d, w: int, h: int, page: str, note: str) -> None:
    d.line((60, h - 110, w - 280, h - 110), fill=GOLD2, width=2)
    d.text((60, h - 88), note, font=font(MED, 24), fill=(220, 220, 225))
    f = font(BOLD, 30)
    pw = text_w(d, page, f) + 44
    d.rounded_rectangle((w - 60 - pw, h - 98, w - 60, h - 46), 26, outline=GOLD, width=3)
    d.text((w - 60 - pw + 22, h - 94), page, font=f, fill="white")


def title(d, y: int, white: str, gold: str, size: int = 92) -> None:
    f = font(BOLD, size)
    d.text((60, y), white, font=f, fill="white")
    d.text((60 + text_w(d, white + " ", f), y), gold, font=f, fill=GOLD)


def effect_slide(cover: Path, frames, group, first: int, page: str) -> Image.Image:
    W, H = 1080, 1350
    im = background(W, H)
    hd = header(cover, W)
    im.paste(hd, (0, 20), hd)
    d = ImageDraw.Draw(im)
    last = first + len(group) - 1
    title(d, 150, "Motion FX", f"{first:02d}-{last:02d}")
    n = len(group)
    fw = 316 if n == 3 else 400
    gap = (W - 120 - n * fw) // max(1, n - 1) if n > 1 else 0
    fh = int(fw * 16 / 9)
    top = 290 + max(0, (1225 - 290 - fh - 175) // 2)  # centre the block above the footer
    for i, (slug, name, promise) in enumerate(group):
        x = 60 + i * (fw + gap) if n == 3 else (W - n * fw - (n - 1) * 40) // 2 + i * (fw + 40)
        pic = rounded(frames[slug].resize((fw, fh), Image.LANCZOS), 22)
        d.rounded_rectangle((x - 3, top - 3, x + fw + 3, top + fh + 3), 25, outline=GOLD2, width=2)
        im.paste(pic, (x, top), pic)
        y = top + fh + 22
        num = f"{first + i:02d}"
        fb = font(BOLD, 30)
        d.rounded_rectangle((x, y, x + 58, y + 46), 10, fill=GOLD)
        d.text((x + 29 - text_w(d, num, fb) // 2, y + 2), num, font=fb, fill=INK)
        fn = font(BOLD, 36 if text_w(d, name, font(BOLD, 36)) < fw - 70 else 28)
        d.text((x + 70, y + 2), name, font=fn, fill="white")
        fp = font(MED, 23)
        for j, line in enumerate(wrap(d, promise, fp, fw)[:2]):
            d.text((x, y + 58 + j * 31), line, font=fp, fill=GREY)
        cmd = f"fx clip {slug}"
        fm = font(MONO, 19 if n == 3 else 22)
        d.rounded_rectangle((x, y + 128, x + fw, y + 166), 10, fill=(22, 22, 26),
                            outline=(60, 60, 66))
        d.text((x + 12, y + 136), cmd, font=fm, fill=GOLD)
    footer(d, W, H, page, "Real Lionstone renders · fictional demo character")
    return im


def matte_slide(cover: Path, frames, page: str) -> Image.Image:
    W, H = 1080, 1350
    im = background(W, H)
    hd = header(cover, W)
    im.paste(hd, (0, 20), hd)
    d = ImageDraw.Draw(im)
    title(d, 150, "The AI", "person matte", 84)
    d.text((60, 262), "Lionstone cuts you out of every frame, on your CPU.", font=font(MED, 30),
           fill=(225, 225, 230))
    fw, fh, top = 300, 533, 340
    for i, (key, cap) in enumerate((("original", "Your shot"), ("matte", "The matte"),
                                    ("frame-break", "Frame Break"))):
        x = 60 + i * (fw + 30)
        pic = rounded(frames[key].resize((fw, fh), Image.LANCZOS), 20)
        d.rounded_rectangle((x - 3, top - 3, x + fw + 3, top + fh + 3), 23, outline=GOLD2, width=2)
        im.paste(pic, (x, top), pic)
        d.text((x, top + fh + 12), cap, font=font(BOLD, 28), fill="white")
        if i < 2:
            d.text((x + fw + 6, top + fh // 2 - 30), "›", font=font(BOLD, 52), fill=GOLD)
    y = top + fh + 80
    for i, line in enumerate(("Your head breaks out of the frame",
                              "Big type sits behind you",
                              "Any room becomes a brand stage, no green screen")):
        d.rounded_rectangle((60, y + i * 74, 104, y + i * 74 + 44), 10, outline=GOLD, width=3)
        d.text((72, y + i * 74 + 2), "✓" if False else str(i + 1), font=font(BOLD, 28), fill=GOLD)
        d.text((124, y + i * 74 + 2), line, font=font(BOLD, 32), fill="white")
    footer(d, W, H, page, "Automatic with lionstone[all] · 4.6 MB model · cached")
    return im


def command_slide(cover: Path, page: str) -> Image.Image:
    W, H = 1080, 1350
    im = background(W, H)
    hd = header(cover, W)
    im.paste(hd, (0, 20), hd)
    d = ImageDraw.Draw(im)
    title(d, 150, "One", "command each", 92)
    x0, y0, x1 = 60, 320, W - 60
    lines = ['pip install "lionstone[all] @',
             '  git+https://github.com/ismailarslantas/lionstone"',
             "lionstone fx list --category motion-fx",
             "lionstone fx preview glass-type --input talk.mp4",
             "lionstone fx apply plan.json frame-break --source 0-3",
             "lionstone fx clip vertigo talk.mp4 -o out.mp4",
             "lionstone fx showcase orbit talk.mp4"]
    y1 = y0 + 80 + len(lines) * 62 + 30
    d.rounded_rectangle((x0, y0, x1, y1), 26, fill=(14, 14, 16), outline=GOLD2, width=3)
    for i, c in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        d.ellipse((x0 + 30 + i * 36, y0 + 26, x0 + 54 + i * 36, y0 + 50), fill=c)
    fm = font(MONO, 27)
    for i, line in enumerate(lines):
        y = y0 + 90 + i * 62
        if not line.startswith("  "):
            d.text((x0 + 28, y), ">", font=fm, fill=GOLD)
        d.text((x0 + 62, y), line.strip() if line.startswith("  ") else line, font=fm,
               fill="white")
    chips = ("9:16 · 1:1 · 16:9", "Preview = export", "Runs on your computer")
    cx = 60
    fc = font(BOLD, 27)
    for c in chips:
        cw = text_w(d, c, fc) + 50
        d.rounded_rectangle((cx, y1 + 60, cx + cw, y1 + 124), 32, outline=GOLD, width=3)
        d.text((cx + 25, y1 + 72), c, font=fc, fill="white")
        cx += cw + 22
    footer(d, W, H, page, "Same builders for preview, showcase and export")
    return im


def sheet(frames, path: Path) -> None:
    """Docs image: all 17 real renders with their names (1600 wide)."""
    cols, tw = 9, 168
    th = int(tw * 16 / 9)
    W = 40 + cols * (tw + 8)
    H = 150 + 2 * (th + 56) + 20
    im = background(W, H)
    d = ImageDraw.Draw(im)
    d.text((40, 30), "Motion FX Pack", font=font(BOLD, 52), fill="white")
    d.text((40 + text_w(d, "Motion FX Pack ", font(BOLD, 52)), 30), "real renders",
           font=font(BOLD, 52), fill=GOLD)
    d.text((40, 96), "17 effects, one fictional demo character, the exact FFmpeg code used for "
           "export.", font=font(MED, 22), fill=GREY)
    for i, (slug, name, *_rest) in enumerate(FX):
        r, c = divmod(i, cols)
        x, y = 40 + c * (tw + 8), 150 + r * (th + 56)
        pic = rounded(frames[slug].resize((tw, th), Image.LANCZOS), 12)
        im.paste(pic, (x, y), pic)
        d.text((x, y + th + 8), name, font=font(BOLD, 17), fill="white")
    im.convert("RGB").save(path, quality=90)


def banner(cover: Path, frames, path: Path) -> None:
    W, H = 1280, 640
    im = background(W, H)
    hd = header(cover, 760).resize((640, 101))
    im.paste(hd, (40, 30), hd)
    d = ImageDraw.Draw(im)
    d.text((60, 190), "Motion FX Pack", font=font(BOLD, 64), fill="white")
    d.text((60, 270), "17 effects", font=font(BOLD, 64), fill=GOLD)
    for i, line in enumerate(("One command each. An AI person matte", "puts you in front of the frame.")):
        d.text((60, 380 + i * 38), line, font=font(MED, 26), fill=(225, 225, 230))
    d.text((60, 560), "100% free · open source · runs on your computer", font=font(BOLD, 24),
           fill=GOLD)
    for i, slug in enumerate(("frame-break", "glass-type", "couch-wall", "orbit")):
        tw, th = 128, 228
        x, y = 700 + i * 140, 200 + (i % 2) * 40
        pic = rounded(frames[slug].resize((tw, th), Image.LANCZOS), 14)
        d.rounded_rectangle((x - 2, y - 2, x + tw + 2, y + th + 2), 16, outline=GOLD2, width=2)
        im.paste(pic, (x, y), pic)
    im.convert("RGB").save(path, quality=90)


def matte_compare(frames, path: Path) -> None:
    W, H = 1280, 760
    im = background(W, H)
    d = ImageDraw.Draw(im)
    d.text((40, 24), "With the person matte", font=font(BOLD, 44), fill="white")
    tw, th = 230, 409
    for i, (key, cap) in enumerate((("original", "Your shot"), ("matte", "Matte"),
                                    ("frame-break", "Frame Break"), ("glass-type", "Glass Type"),
                                    ("green-screen", "Green Screen"))):
        x = 40 + i * (tw + 12)
        pic = rounded(frames[key].resize((tw, th), Image.LANCZOS), 14)
        im.paste(pic, (x, 110), pic)
        d.text((x, 110 + th + 12), cap, font=font(BOLD, 24), fill="white")
    d.text((40, 640), "Automatic with lionstone[all] or lionstone[vision]. Without OpenCV the same "
           "effects render their plain FFmpeg versions.", font=font(MED, 22), fill=GREY)
    im.convert("RGB").save(path, quality=90)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("portrait", type=Path)
    ap.add_argument("cover", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "motionfx")
    a = ap.parse_args()
    wd = a.out / "work"
    wd.mkdir(parents=True, exist_ok=True)
    frames = renders(demo_clip(a.portrait, wd), wd)
    groups = [FX[0:3], FX[3:6], FX[6:9], FX[9:12], FX[12:15], FX[15:17]]
    slides = {"02": matte_slide(a.cover, frames, "02/10"), "09": command_slide(a.cover, "09/10")}
    first = 1
    for k, g in enumerate(groups):
        slides[f"{k + 3:02d}"] = effect_slide(a.cover, frames, [(s, n, p) for s, n, p, *_ in g],
                                              first, f"{k + 3:02d}/10")
        first += len(g)
    for k, im in slides.items():
        im.convert("RGB").save(a.out / f"lionstone-v1-slide{k}.png")
    img = ROOT / "docs" / "img"
    sheet(frames, img / "motionfx-real-renders.jpg")
    banner(a.cover, frames, img / "motionfx-banner.jpg")
    matte_compare(frames, img / "motionfx-matte.jpg")
    shutil.copyfile(wd / "glass-type.mp4", a.out / "glass-type-demo.mp4")
    print("slides and docs images written to", a.out, "and", img)
    return 0


if __name__ == "__main__":
    sys.exit(main())
