"""Synfig backend: `lionstone fx synfig overlay.sif --input talk.mp4 -o out.mp4`.

Renders a Synfig Studio animation (.sif / .sifz) to a PNG sequence with the `synfig`
command-line renderer, then composites it over your clip with FFmpeg (alpha kept).

Licence: Synfig is GPL-3.0. Lionstone (Apache-2.0) never imports, bundles or links it;
it only runs the `synfig` program you installed, as a separate process, like FFmpeg.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from lionstone.ff import FFmpegError, run

INSTALL_HINT = ("Synfig is not installed (the `synfig` command was not found on PATH). "
                "It is optional: install Synfig Studio from https://www.synfig.org/download/ "
                "(Windows/macOS) or `sudo apt install synfig` (Linux), then make sure "
                "`synfig --help` works in a terminal.")


class SynfigError(RuntimeError):
    pass


def find() -> str | None:
    return shutil.which("synfig")


def _exec(cmd: list[str], cwd: Path) -> None:
    run(cmd, cwd=cwd)


def render_frames(sif: Path, out_dir: Path, width: int, height: int, fps: float) -> list[Path]:
    """Render `sif` to out_dir/f00000.png, f00001.png, … and return the frames."""
    exe = find()
    if exe is None:
        raise SynfigError(INSTALL_HINT)
    sif = Path(sif).resolve()
    if sif.suffix.lower() not in (".sif", ".sifz", ".sfg"):
        raise SynfigError(f"{sif.name}: expected a Synfig file (.sif, .sifz or .sfg)")
    if not sif.is_file():
        raise FileNotFoundError(sif)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / "raw"
    raw.mkdir(exist_ok=True)
    try:
        _exec([exe, str(sif), "-t", "png", "-o", str(raw / "frame.png"), "-w", str(width),
               "-h", str(height), "--fps", f"{fps:g}"], cwd=out_dir)
    except FFmpegError as e:  # ff.run raises this for any failed command
        raise SynfigError(f"synfig failed to render {sif.name}:\n{e}") from e
    # synfig names a sequence frame.0000.png … (a still is just frame.png)
    got = sorted(raw.glob("frame*.png"))
    if not got:
        raise SynfigError(f"synfig rendered no frames for {sif.name}")
    frames = []
    for i, f in enumerate(got):
        dst = out_dir / f"f{i:05d}.png"
        f.replace(dst)
        frames.append(dst)
    raw.rmdir()
    return frames


def overlay(sif: str | Path, clip: str | Path, out: str | Path, *, start: float = 0.0) -> Path:
    """Render `sif` at the clip's size and frame rate and composite it from `start` seconds."""
    from lionstone.ingest import probe
    src = Path(clip).resolve()
    info = probe(src)
    v = info.video
    if v is None or not v.width or not v.height:
        raise ValueError(f"{src.name} has no video stream")
    W, H = v.width // 2 * 2, v.height // 2 * 2
    fps = round(v.avg_fps or v.fps or 30.0, 3)
    wd = Path(tempfile.mkdtemp(prefix="lssynfig-"))
    try:
        render_frames(Path(sif), wd, W, H, fps)
        dst = Path(out).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        graph = (f"[1:v]scale={W}:{H},format=rgba,setpts=PTS-STARTPTS+{max(0.0, start):.3f}/TB[ov];"
                 f"[0:v]scale={W}:{H},setsar=1[bg];[bg][ov]overlay=0:0:eof_action=pass,"
                 f"format=yuv420p[o]")
        run(["ffmpeg", "-hide_banner", "-y", "-loglevel", "error", "-i", str(src),
             "-framerate", f"{fps:g}", "-i", "f%05d.png", "-filter_complex", graph,
             "-map", "[o]", "-map", "0:a?", "-c:a", "copy", "-c:v", "libx264", "-crf", "18",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", f"{info.duration:.3f}",
             str(dst)], cwd=wd)
        return dst
    finally:
        shutil.rmtree(wd, ignore_errors=True)
