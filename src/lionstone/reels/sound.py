"""Sound for Reels: an original synthesized SFX starter pack, cue placement, music bed.

``build_pack`` renders the starter pack with FFmpeg only (no samples shipped, no
licences to track). Drop your own licensed packs into the same folder: every
``.wav``/``.mp3``/``.m4a`` file there is picked up, its sub-folder is its category.

``mix`` is a post-pass on a rendered video: it adds SFX cues and a music bed that
ducks under the voice, then loudness-normalises. Video is stream-copied.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..ff import run
from ..ingest import probe
from ..models import EditPlan
from ..presets import LOUDNESS

AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}


def sfx_dir() -> Path:
    return Path(os.environ.get("LIONSTONE_SFX_DIR") or Path.home() / ".config/lionstone/sfx")


def _recipes() -> dict[str, tuple[str, str]]:
    """name → (category, lavfi source + filters). All original, generated on the fly."""
    r: dict[str, tuple[str, str]] = {}
    for i, (lo, hi, d) in enumerate([(300, 3000, 0.45), (500, 6000, 0.6), (200, 2500, 0.8),
                                     (800, 8000, 0.35), (150, 1800, 1.0), (400, 4000, 0.5)], 1):
        h = d / 2
        r[f"whoosh-{i:02d}"] = ("whoosh", (
            f"anoisesrc=d={d}:c=pink:a=0.9:r=48000,highpass=f={lo},lowpass=f={hi},"
            f"afade=t=in:d={h}:curve=qsin,afade=t=out:st={h}:d={h}:curve=qsin"))
    for i, (f, d) in enumerate([(520, .09), (680, .08), (880, .07), (1040, .06), (420, .11),
                                (760, .08)], 1):
        r[f"pop-{i:02d}"] = ("pop", (
            f"aevalsrc='0.9*sin(2*PI*{f}*t*(1-4*t))*exp(-38*t)':d={d}:s=48000"))
    for i, f in enumerate([1800, 2400, 3200, 4200], 1):
        r[f"click-{i:02d}"] = ("click", f"aevalsrc='0.8*sin(2*PI*{f}*t)*exp(-180*t)':d=0.03:s=48000")
    for i, (f, d) in enumerate([(1320, 0.9), (1760, 0.7), (990, 1.1), (2093, 0.6)], 1):
        r[f"ding-{i:02d}"] = ("ding", (
            f"aevalsrc='0.6*sin(2*PI*{f}*t)*exp(-5*t)+0.25*sin(2*PI*{f * 2}*t)*exp(-9*t)'"
            f":d={d}:s=48000"))
    for i, (f0, k, d) in enumerate([(180, 300, 1.5), (240, 500, 1.0), (120, 220, 2.0)], 1):
        r[f"riser-{i:02d}"] = ("riser", (
            f"aevalsrc='0.5*sin(2*PI*({f0}*t+{k}*t*t))*(t/{d})':d={d}:s=48000,"
            f"afade=t=out:st={d - 0.05}:d=0.05"))
    for i, (f, d) in enumerate([(55, 0.9), (42, 1.2), (70, 0.7)], 1):
        r[f"boom-{i:02d}"] = ("boom", (
            f"aevalsrc='0.95*sin(2*PI*{f}*t*(1-0.3*t))*exp(-4*t)':d={d}:s=48000"))
    for i, d in enumerate([0.12, 0.18, 0.25], 1):
        r[f"swipe-{i:02d}"] = ("swipe", (
            f"anoisesrc=d={d}:c=white:a=0.7:r=48000,highpass=f=2500,"
            f"afade=t=in:d={d / 3},afade=t=out:st={d / 3}:d={2 * d / 3}"))
    for i, (f, n) in enumerate([(2600, 6), (3100, 8)], 1):
        r[f"type-{i:02d}"] = ("type", (
            f"aevalsrc='0.7*sin(2*PI*{f}*t)*exp(-300*mod(t,0.09))':d={n * 0.09}:s=48000"))
    return r


def build_pack(dest: Path | None = None, force: bool = False) -> list[Path]:
    dest = dest or sfx_dir()
    out = []
    for name, (cat, src) in _recipes().items():
        p = dest / "lionstone" / cat / f"{name}.wav"
        if p.exists() and not force:
            out.append(p)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", src,
             "-ac", "2", "-ar", "48000", str(p)])
        out.append(p)
    return out


def library(root: Path | None = None) -> dict[str, Path]:
    """sound id (``category/name``) → file. User packs and the starter pack alike."""
    root = root or sfx_dir()
    if not root.exists():
        return {}
    lib = {}
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in AUDIO_EXT:
            cat = p.parent.name
            lib[f"{cat}/{p.stem}"] = p
    return lib


def resolve(sound: str, lib: dict[str, Path]) -> Path | None:
    if sound in lib:
        return lib[sound]
    if Path(sound).exists():
        return Path(sound)
    cat = sound.split("/")[0]  # "pop" → first pop in the library
    return next((p for k, p in lib.items() if k.split("/")[0] == cat or k.endswith("/" + sound)),
                None)


@dataclass
class Cue:
    at: float  # output seconds
    sound: str  # "pop", "whoosh/whoosh-02" or a file path
    gain: float = 0.5
    reason: str = ""


def auto_cues(plan: EditPlan, max_cues: int = 12) -> list[Cue]:
    """Sparse, intentional cues: a whoosh into the hook, pops on text graphics, a ding
    on the CTA. Never more than one every 1.2 s."""
    cues = [Cue(0.0, "whoosh", 0.35, "opening")]
    for g in sorted(plan.graphics, key=lambda g: g.at):
        kind = "ding" if any(k in (g.text + g.effect).lower() for k in ("cta", "takip", "kaydet")) \
            else ("whoosh" if g.layer == "titles" and g.at < 0.5 else "pop")
        cues.append(Cue(round(g.at, 3), kind, 0.45, f"graphic {g.id} {g.effect}"))
    out: list[Cue] = []
    for c in sorted(cues, key=lambda c: c.at):
        if not out or c.at - out[-1].at >= 1.2:
            out.append(c)
    return out[:max_cues]


def load_cues(path: Path) -> list[Cue]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Cue(**c) for c in (d["cues"] if isinstance(d, dict) else d)]


def mix(video: Path, out: Path, *, cues: list[Cue], music: str | None = None,
        music_volume: float = 0.18, profile: str = "social",
        lib: dict[str, Path] | None = None) -> dict:
    """Voice + SFX + ducked music → loudness-normalised AAC; video copied."""
    lib = lib if lib is not None else library()
    info = probe(video)
    inputs: list[str] = ["-i", str(video)]
    graph, labels, used, skipped = [], [], [], []
    graph.append("[0:a]aresample=48000,asplit=2[voice][key]")
    labels.append("[voice]")
    n = 1
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        graph.append(f"[{n}:a]aresample=48000,volume={music_volume:.3f},"
                     f"afade=t=in:d=0.6,afade=t=out:st={max(info.duration - 1.2, 0):.2f}:d=1.2"
                     f"[mus];[mus][key]sidechaincompress=threshold=0.02:ratio=8:attack=15:"
                     f"release=350[bed]")
        labels.append("[bed]")
        n += 1
    else:
        graph.append("[key]anullsink")
    for c in cues:
        p = resolve(c.sound, lib)
        if p is None or c.at >= info.duration:
            skipped.append(c.sound)
            continue
        ms = int(c.at * 1000)
        inputs += ["-i", str(p)]
        graph.append(f"[{n}:a]aresample=48000,volume={c.gain:.3f},adelay={ms}|{ms}[s{n}]")
        labels.append(f"[s{n}]")
        used.append({"at": c.at, "sound": str(p.stem), "reason": c.reason})
        n += 1
    tgt = LOUDNESS.get(profile) or LOUDNESS["social"]
    lufs, tp, lra = tgt.integrated, tgt.true_peak, tgt.lra
    graph.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0,"
                 f"loudnorm=I={lufs}:TP={tp}:LRA={lra}[aout]")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        gfile = Path(td) / "graph.txt"
        gfile.write_text(";".join(graph), encoding="utf-8")
        tmp = Path(td) / out.name
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
             "-filter_complex_script", str(gfile), "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
             "-movflags", "+faststart", str(tmp)])
        shutil.move(str(tmp), out)
    return {"output": str(out), "cues": used, "skipped": skipped, "music": music or "",
            "target_lufs": lufs}
