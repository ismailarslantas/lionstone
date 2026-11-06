"""Brand identity for Reels, measured from one talking-head take and 3-5 example Reels.

``analyze`` writes ``brands/<slug>/identity/``: what can be measured (tempo, pauses,
loudness, colour, palette, lengths, speech rate, opening lines) as plain JSON, plus contact
sheets so the agent can look at what can't be measured (caption look, text placement).
Anything that can't run is recorded as skipped with the reason, never guessed.
"""

from __future__ import annotations

import colorsys
import datetime as dt
import json
import shutil
import statistics
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from ..ff import analyze_filter, parse_loudness, parse_silences, run
from ..ingest import probe
from ..models import Word
from ..pro.style import describe, learn
from . import memory
from .brand import Brand, home

MIN_EXAMPLES, MAX_EXAMPLES = 3, 5


def identity_dir(brand: Brand, root: Path | None = None) -> Path:
    return home(brand, root) / brand.slug / "identity"


def archive(brand: Brand, root: Path | None = None) -> Path | None:
    """A new identity never destroys the old one: it and its choices move to identity-archive/."""
    current = identity_dir(brand, root)
    if not (current / "identity.json").exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = current.parent / "identity-archive" / stamp
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(current), str(dest))
    choices = current.parent / "choices.json"
    if choices.exists():
        shutil.move(str(choices), str(dest / "choices.json"))
    return dest


def load_identity(brand: Brand, root: Path | None = None) -> dict[str, Any] | None:
    p = identity_dir(brand, root) / "identity.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# --- pure measurements ----------------------------------------------------------------
def dominant_colors(rgb: bytes, top: int = 5) -> list[str]:
    """Saturated colours in raw RGB24 pixels, most common first. Greys and near-black or
    near-white pixels say nothing about a brand, so they don't count."""
    buckets: Counter[tuple[int, int, int]] = Counter()
    for i in range(0, len(rgb) - 2, 3):
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
        _, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s >= 0.35 and 0.3 <= v:
            buckets[(r // 24, g // 24, b // 24)] += 1
    return ["#{:02X}{:02X}{:02X}".format(*(min(255, c * 24 + 12) for c in key))
            for key, _ in buckets.most_common(top)]


def speech_gap_ratio(words: list[Word], duration: float) -> float:
    """Share of the runtime with no word being said (gaps over 0.25 s)."""
    if not words or duration <= 0:
        return 0.0
    gaps = sum(max(0.0, b.start - a.end) for a, b in zip(words, words[1:])
               if b.start - a.end > 0.25)
    return gaps / duration


def music_likely(silence_ratio: float, gap_ratio: float | None) -> bool:
    """Estimate: sound keeps going while nobody speaks, so something is under the voice.
    Without a transcript, near-zero silence is the only signal."""
    if gap_ratio is None:
        return silence_ratio < 0.03
    return gap_ratio > 0.08 and silence_ratio < gap_ratio * 0.4


def opening_line(words: list[Word], max_words: int = 14) -> str:
    out = []
    for w in words[:max_words]:
        out.append(w.text)
        if w.text.rstrip().endswith((".", "?", "!")):
            break
    return " ".join(out)


# --- media steps ----------------------------------------------------------------------
def _palette(path: Path, duration: float) -> list[str]:
    step = max(duration / 24, 0.25)
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf",
         f"fps=1/{step:.3f},scale=32:32", "-frames:v", "24", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"], capture_output=True, check=False)
    return dominant_colors(proc.stdout) if proc.returncode == 0 else []


def _sheet(path: Path, out: Path, duration: float, frames: int = 6) -> Path:
    step = max(duration / frames, 0.1)
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-vf",
         f"fps=1/{step:.3f},scale=270:-2,tile={frames}x1", "-frames:v", "1", "-q:v", "3",
         "-update", "1", str(out)])
    return out


def _words(path: Path, asr: bool, model: str, language: str) -> tuple[list[Word], str]:
    if not asr:
        return [], "speech recognition turned off"
    try:
        from ..transcribe import TranscriptionUnavailable, transcribe
        try:
            return transcribe(path, model=model, language=language), ""
        except TranscriptionUnavailable as e:
            return [], str(e)
    except ImportError as e:
        return [], str(e)


def _clip(path: Path, role: str, out_dir: Path, name: str, asr: bool, model: str,
          language: str) -> dict[str, Any]:
    info = probe(path)
    if not info.video:
        raise ValueError(f"{role}: no video stream: {path}")
    d = info.duration
    v = info.video
    has_audio = bool(info.audio)
    silence, lufs = None, None
    if has_audio:
        sil = parse_silences(analyze_filter(str(path), af="silencedetect=noise=-35dB:d=0.25"), d)
        silence = round(sum(b - a for a, b in sil) / max(d, 1e-9), 3)
        lufs = parse_loudness(analyze_filter(str(path), af="ebur128=peak=true",
                                             extra=["-vn"]))["integrated_lufs"]
    words, why = _words(path, asr and has_audio, model, language) if has_audio else ([], "no audio")
    gap = round(speech_gap_ratio(words, d), 3) if words else None
    clip = {"file": path.name, "role": role, "seconds": round(d, 2),
            "size": [v.width, v.height], "vertical": v.height > v.width,
            "fps": round(v.fps, 3) if v.fps else None, "has_audio": has_audio,
            "silence_ratio": silence, "lufs": lufs, "palette": _palette(path, d),
            "sheet": _sheet(path, out_dir / "frames" / f"{name}.jpg", d).name,
            "words": len(words), "asr_skipped": "" if words else (why or "no speech recognised"),
            "words_per_second": round(len(words) / max(d * (1 - (gap or 0)), 1e-9), 2)
            if words else None, "speech_gap_ratio": gap, "opening_line": opening_line(words)}
    clip["music_likely"] = music_likely(silence, gap) if has_audio else False
    return clip


def analyze(brand: Brand, footage: Path, examples: list[Path], *, asr: bool = True,
            model: str = "small", root: Path | None = None, log=print) -> dict[str, Any]:
    if not MIN_EXAMPLES <= len(examples) <= MAX_EXAMPLES:
        raise ValueError(f"{MIN_EXAMPLES}-{MAX_EXAMPLES} example Reels needed, "
                         f"{len(examples)} given")
    for p in [footage, *examples]:
        if not Path(p).is_file():
            raise FileNotFoundError(f"file not found: {p}")
    # everything is checked above, so a typo can't cost the identity already on disk
    previous = archive(brand, root)
    if previous:
        log(f"🗄️ Previous identity archived → {previous}")
    out = identity_dir(brand, root)
    out.mkdir(parents=True, exist_ok=True)
    lang = brand.language
    log(f"🎥 Talking-head take: {Path(footage).name}")
    head = _clip(Path(footage), "footage", out, "footage", asr, model, lang)
    if not head["has_audio"]:
        raise ValueError(f"the talking-head take has no audio: {footage}")
    clips = []
    for i, ex in enumerate(examples, 1):
        log(f"🎞️ Example {i}/{len(examples)}: {Path(ex).name}")
        clips.append(_clip(Path(ex), "example", out, f"example-{i}", asr, model, lang))
    log("📐 Measuring rhythm, sound and colour")
    profile = learn([str(p) for p in examples], name=brand.slug)
    profile.save(out / "style.json")
    secs = [c["seconds"] for c in clips]
    colors = Counter(c for clip in clips for c in clip["palette"])
    identity = {
        "brand": brand.name, "language": lang, "footage": head, "examples": clips,
        "style": {k: getattr(profile, k) for k in (
            "tempo", "avg_shot_seconds", "cuts_per_minute", "pause_ratio", "intensity",
            "loudness_lufs", "luma", "contrast", "saturation", "warmth", "color_filter")},
        "target_seconds": [round(min(secs), 1), round(max(secs), 1)],
        "typical_seconds": round(statistics.median(secs), 1),
        "palette": [c for c, _ in colors.most_common(5)],
        "music_in_examples": sum(c["music_likely"] for c in clips),
        "opening_lines": [c["opening_line"] for c in clips if c["opening_line"]],
        "words_per_second": head["words_per_second"],
        "skipped": sorted({f"{c['file']}: {c['asr_skipped']}" for c in [head, *clips]
                           if c["asr_skipped"]}),
    }
    (out / "identity.json").write_text(json.dumps(identity, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    (out / "identity.md").write_text(_summary(identity, describe(profile)), encoding="utf-8")
    memory.remember(brand.slug, brand.name, home(brand, root), use=True, identity_at=memory.now(),
                    setup_at="")
    return identity


def _summary(i: dict[str, Any], style_text: str) -> str:
    head = i["footage"]
    rows = [f"| {c['file']} | {c['seconds']} s | {c['size'][0]}x{c['size'][1]} | "
            f"{'yes' if c['music_likely'] else 'no'} | {c['opening_line'] or '-'} |"
            for c in i["examples"]]
    lines = [f"# {i['brand']}: Reels identity", "",
             "Measured by Lionstone. Music is an estimate. Look at `frames/` for what can't be",
             "measured (caption look, text placement, framing), then complete `brand.md`.", "",
             "## Example Reels", "", "| File | Length | Size | Music (estimate) | Opening line |",
             "|---|---|---|---|---|", *rows, "", "## Learned style", "", "```", style_text, "```",
             "", "## Talking-head take", "",
             f"- {head['file']}: {head['seconds']} s, {head['size'][0]}x{head['size'][1]}, "
             f"{'vertical' if head['vertical'] else 'not vertical'}, {head['lufs']} LUFS",
             f"- Speech rate: {head['words_per_second'] or 'not measured'} words/s", "",
             "## Brand", "", f"- Palette from the examples: {', '.join(i['palette']) or 'none'}",
             f"- Typical length: {i['typical_seconds']} s "
             f"(range {i['target_seconds'][0]}-{i['target_seconds'][1]} s)"]
    if i["skipped"]:
        lines += ["", "## Not measured", "", *[f"- {s}" for s in i["skipped"]]]
    return "\n".join(lines) + "\n"
