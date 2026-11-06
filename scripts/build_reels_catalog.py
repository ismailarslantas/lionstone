"""Build the Reels visual catalogue: every option rendered by Lionstone on one example character.

Maintainer tool, not part of the runtime (needs Pillow, edge-tts and faster-whisper):

    python scripts/build_reels_catalog.py portrait.png landscape.png --work build/catalog

portrait.png (9:16) and landscape.png (16:9) show a fictional person. Picture options are frames
from real `lionstone reels make` runs; sound options are waveforms or spectrograms of real output.
Finished cards are kept, so an interrupted run can continue.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import edge_tts
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

from lionstone.ff import font_path
from lionstone.reels.catalog import entries

CARD = (360, 640)
SENTENCES = ["Is rising rent scaring you?", "Don't make this mistake.", "First write your budget.",
             "Then pick the neighbourhood.", "Save this for later."]
SCRIPT = " ".join(SENTENCES)
HOOK = SENTENCES[0]
BRAND = "Catalog"
OUT = Path(__file__).resolve().parents[1] / "src/lionstone/data/reels/catalog"
INK, GOLD, WHITE, MUTE = "#111114", "#E8B04B", "#FFFFFF", "#A09F99"
FONT = font_path()


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        probe = f"{cur} {word}".strip()
        if draw.textlength(probe, font=f) <= width:
            cur = probe
        else:
            lines.append(cur)
            cur = word
    return [*lines, cur] if cur else lines


def label(img: Image.Image, number: int, text: str) -> Image.Image:
    """Number and English name, baked in so a screenshot of the card still works."""
    card = img.convert("RGB").resize(CARD, Image.LANCZOS)
    d = ImageDraw.Draw(card, "RGBA")
    f = font(23)
    lines = wrap(d, text, f, CARD[0] - 28)[:3]
    h = 66 + 28 * len(lines)
    d.rectangle((0, CARD[1] - h, CARD[0], CARD[1]), fill=(17, 17, 20, 235))
    d.text((14, CARD[1] - h + 10), str(number), font=font(38), fill=GOLD)
    for i, line in enumerate(lines):
        d.text((14, CARD[1] - h + 58 + i * 28), line, font=f, fill=WHITE)
    return card


def text_card(title: str, body: str) -> Image.Image:
    img = Image.new("RGB", CARD, INK)
    d = ImageDraw.Draw(img)
    y = 150
    for line in wrap(d, title, font(40), CARD[0] - 50):
        d.text((25, y), line, font=font(40), fill=GOLD)
        y += 50
    y += 16
    for line in wrap(d, body, font(25), CARD[0] - 50):
        d.text((25, y), line, font=font(25), fill=WHITE)
        y += 34
    return img


def plot_card(picture: Path, title: str, caption: str = "") -> Image.Image:
    """A waveform or spectrogram of real output on a card."""
    img = Image.new("RGB", CARD, INK)
    d = ImageDraw.Draw(img)
    d.text((22, 120), title, font=font(30), fill=GOLD)
    plot = Image.open(picture).convert("RGB").resize((CARD[0] - 40, 190))
    img.paste(plot, (20, 180))
    y = 395
    for line in wrap(d, caption, font(22), CARD[0] - 44):
        d.text((22, y), line, font=font(22), fill=MUTE)
        y += 30
    return img


class Builder:
    def __init__(self, portrait: Path, landscape: Path, work: Path):
        self.portrait, self.landscape, self.work = portrait.resolve(), landscape.resolve(), work
        work.mkdir(parents=True, exist_ok=True)
        os.chdir(work)
        os.environ.update(LIONSTONE_SFX_DIR=str(work / "sfx"), XDG_CONFIG_HOME=str(work / "cfg"),
                          PYTHONUTF8="1")
        self.ls = str(Path(sys.executable).with_name("lionstone"))
        self.folder = Path("projects/catalog/reel")

    def run(self, *args: str, check: bool = False) -> int:
        p = subprocess.run([self.ls, *args], capture_output=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL)
        if check and p.returncode:
            raise RuntimeError(f"{args}: {p.stdout[-400:]} {p.stderr[-400:]}")
        return p.returncode

    def media(self) -> None:
        if Path("speech.wav").exists():
            return

        async def tts():
            for i, s in enumerate(SENTENCES):
                await edge_tts.Communicate(s, "en-US-GuyNeural").save(f"s{i}.mp3")
        asyncio.run(tts())
        ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.8", "sil.wav")
        ins, fc = [], ""
        for i in range(len(SENTENCES)):
            ins += ["-i", f"s{i}.mp3", "-i", "sil.wav"]
            fc += (f"[{2 * i}:a]aresample=48000,aformat=channel_layouts=mono[a{i}];"
                   f"[{2 * i + 1}:a]aresample=48000[b{i}];")
        fc += "".join(f"[a{i}][b{i}]" for i in range(len(SENTENCES)))
        ff(*ins, "-filter_complex", fc + f"concat=n={len(SENTENCES) * 2}:v=0:a=1", "speech.wav")
        # a small hand-held sway, so motion effects have motion to work on
        sway = "x='60+40*sin(t*1.7)':y='70+30*sin(t*1.1)'"
        ff("-loop", "1", "-r", "30", "-i", str(self.portrait), "-i", "speech.wav", "-shortest",
           "-vf", f"scale=1200:2134:force_original_aspect_ratio=increase,crop=1080:1920:{sway}",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "portrait.mp4")
        ff("-loop", "1", "-r", "30", "-i", str(self.landscape), "-i", "speech.wav", "-shortest",
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
           "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "landscape.mp4")
        ff("-f", "lavfi", "-i", "sine=f=196:r=48000:d=30", "-f", "lavfi", "-i", "sine=f=247:r=48000:d=30",
           "-filter_complex", "[0][1]amix=inputs=2,tremolo=f=2:d=0.5,volume=4", "-ac", "2", "music.wav")
        ff("-i", "speech.wav", "-f", "lavfi", "-i", "anoisesrc=c=white:a=0.03:r=48000:d=30",
           "-filter_complex", "[0][1]amix=inputs=2:duration=first:normalize=0", "noisy.wav")

    def setup_project(self) -> None:
        if self.folder.exists():
            return
        self.run("reels", "brand", "init", BRAND, "--language", "en", "--audience", "first-time buyers",
                 "--accent", GOLD, check=True)
        for f in OUT.glob("*.jpg"):
            f.unlink()
        b = Path("brands/catalog/brand.json")
        d = json.loads(b.read_text(encoding="utf-8"))
        d["target_seconds"] = [5, 40]
        b.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.folder / "ham").mkdir(parents=True)
        reel = {"brand": BRAND, "topic": "Rent or buy", "why": "fear of rent",
                "hooks": [HOOK, "Watch this first."], "second_hook": "But that's not the real problem.",
                "script": SCRIPT, "cta": SENTENCES[-1], "caption": "Budget first.",
                "cover_text": ["Rent or buy?", "Budget first", "Don't guess"]}
        (self.folder / "reel.json").write_text(json.dumps(reel, ensure_ascii=False, indent=2), "utf-8")
        shutil.copy("portrait.mp4", self.folder / "ham" / "take.mp4")
        self.run("reels", "make", str(self.folder), "--identity", "same", "--fast", "--no-sfx")
        plan = json.loads((self.folder / "kurgu/plan.json").read_text(encoding="utf-8"))
        said = SCRIPT.split()  # the script is known: keep Whisper's timing, not its spelling
        heard = plan["words"]
        if len(said) != len(heard):
            raise RuntimeError(f"expected {len(said)} words, heard {[w['text'] for w in heard]}")
        Path("words.json").write_text(json.dumps({"words": [
            {"word": t, "start": w["start"], "end": w["end"]} for t, w in zip(said, heard)]},
            ensure_ascii=False), encoding="utf-8")
        # a warm, saturated look as the "learned" example, written the way `reels identity` does
        from lionstone.pro.style import StyleProfile, color_filter
        look = StyleProfile(name="catalog", saturation=0.45, contrast=0.85, warmth=0.12)
        look.color_filter = color_filter(look)
        look.apply = ["color"]
        out = Path("brands/catalog/identity")
        out.mkdir(parents=True, exist_ok=True)
        look.save(out / "style.json")

    def style(self, **overrides) -> None:
        b = Path("brands/catalog/brand.json")
        d = json.loads(b.read_text(encoding="utf-8"))
        d["style"] = {"intensity": "dynamic", "caption_style": "karaoke", "color": "natural",
                      "title_effect": "T02", "music": "", "music_volume": 0.18, "sfx": False,
                      "hook_title": True, "effects": "none", "denoise": "light", "reframe": "center",
                      "sfx_density": "sparse", "covers": 1, **{k: v for k, v in overrides.items()
                                                                if k not in ("accent",)}}
        d["colors"]["accent"] = overrides.get("accent", GOLD)
        b.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def make(self, footage: str = "portrait.mp4", **overrides) -> Path:
        self.style(**overrides)
        shutil.copy(footage, self.folder / "ham" / "take.mp4")
        for old in (self.folder / "teslim").glob("*.mp4"):
            old.unlink()
        self.run("reels", "make", str(self.folder), "--identity", "same", "--fast",
                 "--transcript", "words.json")
        return next((self.folder / "teslim").glob("*.mp4"))

    @staticmethod
    def frame(video: Path, t: float, name: str = "frame.png") -> Image.Image:
        ff("-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-update", "1", name)
        return Image.open(name).convert("RGB")

    def strongest(self, video: Path, against: Path, times=(0.25, 0.6, 1.0, 1.4)) -> Image.Image:
        """The moment an effect shows most, so its card doesn't look like "no effect"."""
        best, score = None, -1.0
        for t in times:
            a, b = self.frame(video, t, "a.png"), self.frame(against, t, "b.png")
            s = sum(ImageStat.Stat(ImageChops.difference(a, b)).mean)
            if s > score:
                best, score = a.copy(), s
        return best

    def wave(self, media: str, out: str, color: str = "E8B04B") -> str:
        ff("-i", media, "-filter_complex", f"showwavespic=s=640x240:colors=0x{color}", "-frames:v", "1",
           "-update", "1", out)
        return out

    def spectrum(self, media: str, out: str) -> str:
        ff("-i", media, "-lavfi", "showspectrumpic=s=640x240:legend=0:scale=log", "-update", "1", out)
        return out

    def picture_for(self, q: str, v: str, base: Path) -> Image.Image:
        if q == "opening":
            if v == "none":
                return self.frame(self.make(hook_title=False), 0.9)
            return self.frame(self.make(title_effect=v), 1.2)
        if q == "captions":
            return self.frame(self.make(caption_style=v, hook_title=False), 2.6 if v != "none" else 1.0)
        if q == "grade":
            return self.frame(self.make(color=v, hook_title=False), 1.0)
        if q == "effects":
            video = self.make(effects=v, hook_title=False)
            return self.frame(video, 2.6) if v == "none" else self.strongest(video, base)
        if q == "framing":
            if v == "face":
                try:
                    import cv2  # noqa: F401
                except ImportError:
                    return text_card("Follow the face", "Needs lionstone[vision]. Keeps the speaker centred when the take is not vertical.")
            return self.frame(self.make("landscape.mp4", reframe=v, hook_title=False), 2.0)
        if q == "colors":
            return self.frame(self.make(accent=GOLD if v == "brand" else "#D9432F"), 1.2)
        if q == "covers":
            self.style(covers=int(v))
            for x in (self.folder / "teslim").glob("kapak-*.jpg"):
                x.unlink()
            self.run("reels", "make", str(self.folder), "--identity", "same", "--fast", "--transcript",
                     "words.json", "--covers", v)
            covers = sorted((self.folder / "teslim").glob("kapak-*.jpg"))
            n = len(covers)
            cols = 1 if n == 1 else 2
            rows = (n + 1) // 2 if n > 1 else 1
            sheet = Image.new("RGB", CARD, INK)
            w, h = CARD[0] // cols, CARD[1] // rows
            for i, c in enumerate(covers):
                sheet.paste(Image.open(c).resize((w, h)), ((i % cols) * w, (i // cols) * h))
            return sheet
        if q == "pace":
            video = self.make(intensity=v, hook_title=False)
            secs = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                   str(video)], capture_output=True, text=True).stdout.strip()
            return plot_card(Path(self.wave(str(video), "w.png")), v.title(),
                             f"The same take comes out at {float(secs):.1f} s (the raw take has long pauses).")
        if q == "music":
            if v == "none":
                return plot_card(Path(self.wave("speech.wav", "w.png")), "No music", "Voice only.")
            video = self.make(music=str(Path("music.wav").resolve()), sfx=False, hook_title=False)
            return plot_card(Path(self.wave(str(video), "w.png")), "Your own file",
                             "Your licensed track under the voice. Lionstone ships no music.")
        if q == "music_level":
            from lionstone.reels.choices import MUSIC_LEVELS
            video = self.make(music=str(Path("music.wav").resolve()), music_volume=MUSIC_LEVELS[v], hook_title=False)
            return plot_card(Path(self.wave(str(video), "w.png")), v.title(),
                             f"Music at {MUSIC_LEVELS[v]:.2f}, ducking under the voice.")
        if q == "sfx":
            video = self.make(sfx=v != "off", sfx_density="sparse" if v == "off" else v)
            caption = {"sparse": "Whoosh on the opening, pop on graphics, ding on the CTA.",
                       "minimal": "Only the opening whoosh and the CTA ding.", "off": "No sound effects."}[v]
            return plot_card(Path(self.wave(str(video), "w.png")), v.title(), caption)
        if q == "cleanup":
            ff("-loop", "1", "-r", "30", "-i", str(self.portrait), "-i", "noisy.wav", "-shortest", "-vf",
               "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
               "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "noisy.mp4")
            video = self.make("noisy.mp4", denoise=v, hook_title=False)
            return plot_card(Path(self.spectrum(str(video), "w.png")), v.title(),
                             "Spectrogram of a take with room noise: the dark bands are the pauses.")
        raise ValueError(q)

    def build(self) -> None:
        self.media()
        self.setup_project()
        base = None
        OUT.mkdir(parents=True, exist_ok=True)
        for e in entries():
            target = OUT / f"{e['number']}.jpg"
            if target.exists():
                continue
            if e["value"] == "auto":
                img = text_card("Decide for me", "Lionstone picks this from your brand identity and tells you why.")
            else:
                if base is None:
                    Path("base_fx.mp4").write_bytes(self.make(hook_title=False).read_bytes())
                    base = Path("base_fx.mp4")
                img = self.picture_for(e["question"], e["value"], base)
            label(img, e["number"], e["en"]).save(target, quality=82)
            print(e["number"], e["question"], e["value"], flush=True)
        self.sheets()

    @staticmethod
    def sheets() -> None:
        groups: dict[str, list[dict]] = {}
        for e in entries():
            groups.setdefault(e["question"], []).append(e)
        (OUT / "sheets").mkdir(parents=True, exist_ok=True)
        tile = (216, 384)
        for q, items in groups.items():
            cols = min(6, len(items))
            rows = (len(items) + cols - 1) // cols
            sheet = Image.new("RGB", (cols * (tile[0] + 8) + 8, rows * (tile[1] + 8) + 8), INK)
            for i, e in enumerate(items):
                im = Image.open(OUT / f"{e['number']}.jpg").resize(tile, Image.LANCZOS)
                sheet.paste(im, (8 + (i % cols) * (tile[0] + 8), 8 + (i // cols) * (tile[1] + 8)))
            sheet.save(OUT / "sheets" / f"{q}.jpg", quality=80)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("portrait", type=Path)
    ap.add_argument("landscape", type=Path)
    ap.add_argument("--work", type=Path, default=Path("build/catalog"))
    a = ap.parse_args()
    Builder(a.portrait, a.landscape, a.work.resolve()).build()
