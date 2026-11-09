"""Person matte for Motion FX: a grey "sidecar" video where the speaker is white.

Frame Break, Vertigo, Glass Type, Green Screen and Doodle Boil use it to put the
speaker in front of the frame, the type or the new backdrop. Without it they fall
back to their pure-FFmpeg versions, so a render never fails because of the matte.

* Model: U²-Net small (``u2netp.onnx``, 4.6 MB, Apache-2.0, Qin et al.), downloaded
  once from the rembg GitHub release and checked by SHA-256. Nothing is bundled.
* Runtime: OpenCV DNN on the CPU (``pip install "lionstone[vision]"``), no GPU needed.
* Speed: inference at 10 fps and 320 px, smoothed over time, then upsampled by FFmpeg,
  roughly 2-4x real time on a laptop. Results are cached per source file.

    lionstone fx matte talk.mp4          # build (or reuse) the matte now
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from .identity import config_dir

MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
MODEL_SHA256 = "309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8"
SIZE = 320       # model input
MATTE_FPS = 10   # inference rate; FFmpeg upsamples to the output rate
SMOOTH = 0.45    # temporal smoothing (0 = none)
MATTE_EFFECTS = {"lionstone.frame-break", "lionstone.vertigo", "lionstone.glass-type",
                 "lionstone.green-screen", "lionstone.doodle-boil"}


class MatteError(RuntimeError):
    pass


def available() -> bool:
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        return False
    return hasattr(__import__("cv2"), "dnn")


def _dir(name: str) -> Path:
    d = config_dir() / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _download(url: str, dst: Path) -> None:
    tmp = dst.with_suffix(".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "lionstone"})
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
    except Exception as e:  # e.g. Python without a CA store on Windows → system curl
        if not shutil.which("curl"):
            raise MatteError(f"could not download the matte model: {e}") from e
        subprocess.run(["curl", "-sSLf", "-o", str(tmp), url], check=True, timeout=300)
    tmp.replace(dst)


def model_path() -> Path:
    """The verified model file, downloaded on first use."""
    p = _dir("models") / "u2netp.onnx"
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != MODEL_SHA256:
        print("lionstone: downloading the person-matte model (4.6 MB, once)", file=sys.stderr)
        _download(MODEL_URL, p)
        if hashlib.sha256(p.read_bytes()).hexdigest() != MODEL_SHA256:
            p.unlink(missing_ok=True)
            raise MatteError("matte model checksum mismatch; download refused")
    return p


def cache_path(src: str | Path) -> Path:
    s = Path(src).resolve()
    st = s.stat()
    key = hashlib.sha1(f"{s}|{st.st_size}|{int(st.st_mtime)}|{MODEL_SHA256[:8]}|{MATTE_FPS}"
                       .encode()).hexdigest()[:20]
    return _dir("mattes") / f"{key}.mp4"


def _net():
    import cv2
    import numpy as np
    # bytes, not a path: OpenCV can't open non-ASCII paths on Windows
    return cv2.dnn.readNetFromONNX(np.fromfile(str(model_path()), dtype=np.uint8))


def _probe_size(src: Path) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(src)],
                         capture_output=True, text=True, check=True).stdout.strip()
    w, h = (int(x) for x in out.split(",")[:2])
    return w, h


def make_matte(src: str | Path, out: str | Path | None = None, *, progress: bool = True) -> Path:
    """Write the matte video for `src` (grey, same duration, MATTE_FPS) and return its path."""
    if not available():
        raise MatteError('person matte needs OpenCV: pip install "lionstone[vision]"')
    import numpy as np
    src = Path(src).resolve()
    dst = Path(out) if out else cache_path(src)
    w, h = _probe_size(src)
    mw, mh = max(2, round(w / 8) * 2), max(2, round(h / 8) * 2)  # quarter size, even
    net = _net()
    mean, std = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225],
                                                                      np.float32)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(src), "-an", "-vf",
                            f"fps={MATTE_FPS},scale={SIZE}:{SIZE}:flags=area", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    tmp = dst.with_name(dst.stem + ".part.mp4")
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray",
                            "-s", f"{SIZE}x{SIZE}", "-r", str(MATTE_FPS), "-i", "-", "-vf",
                            f"scale={mw}:{mh}:flags=bicubic,format=yuv420p", "-c:v", "libx264",
                            "-crf", "16", "-preset", "veryfast", str(tmp)], stdin=subprocess.PIPE)
    prev, n, frame_bytes = None, 0, SIZE * SIZE * 3
    try:
        while True:
            buf = dec.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            x = (np.frombuffer(buf, np.uint8).reshape(SIZE, SIZE, 3).astype(np.float32) / 255
                 - mean) / std
            net.setInput(x.transpose(2, 0, 1)[None].copy())
            m = net.forward()[0, 0]
            m = np.clip((m - 0.05) / 0.9, 0, 1)  # u2netp is already 0-1; trim the soft floor
            prev = m if prev is None else SMOOTH * prev + (1 - SMOOTH) * m
            enc.stdin.write((prev * 255).astype(np.uint8).tobytes())
            n += 1
            if progress and n % 50 == 0:
                print(f"\rlionstone: person matte {n / MATTE_FPS:.0f}s", end="", file=sys.stderr)
    finally:
        enc.stdin.close()
        enc.wait()
        dec.wait()
    if progress:
        print(f"\rlionstone: person matte done ({n / MATTE_FPS:.0f}s)   ", file=sys.stderr)
    if n == 0 or enc.returncode:
        tmp.unlink(missing_ok=True)
        raise MatteError(f"could not build a matte for {src.name}")
    tmp.replace(dst)
    return dst


def enabled() -> bool:
    """LIONSTONE_MATTE=0 turns the person matte off (plain FFmpeg versions)."""
    return os.environ.get("LIONSTONE_MATTE", "1").lower() not in ("0", "false", "no", "off")


def wants(preset_ids) -> bool:
    return enabled() and any(pid in MATTE_EFFECTS for pid in preset_ids)


def uses_in(graph: str) -> int:
    """Number of matte labels a built filtergraph expects (lsmatte1..N)."""
    return len(set(re.findall(r"\[lsmatte(\d+)\]", graph)))


def ensure(src: str | Path) -> Path | None:
    """Cached matte for `src`, building it if OpenCV is installed; None when unavailable."""
    try:
        p = cache_path(src)
        if p.exists():
            return p
        if not available():
            return None
        return make_matte(src, p)
    except (MatteError, OSError, subprocess.CalledProcessError) as e:
        print(f"lionstone: person matte unavailable ({e}); using the plain version",
              file=sys.stderr)
        return None


def graph_inputs(matte_input: int, uses: int, W: int, H: int, fps: float,
                 trims: list[tuple[float, float]] | None = None) -> str:
    """Filtergraph that turns input `matte_input` into `uses` labels lsmatte1..N (W×H, grey).

    `trims` are the kept source ranges (seconds) of an edit plan, in output order.
    """
    outs = "".join(f"[lsmatte{i + 1}]" for i in range(uses))
    head = f"[{matte_input}:v]fps={fps}"
    tail = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"format=gray,gblur=sigma=1.2,setsar=1,split={uses}{outs}")
    if not trims:
        return f"{head},{tail}"
    segs = [f"[lsmsrc{i}]trim=start={a:.6f}:end={b:.6f},setpts=PTS-STARTPTS[lsmt{i}]"
            for i, (a, b) in enumerate(trims)]
    src = f"{head},split={len(trims)}" + "".join(f"[lsmsrc{i}]" for i in range(len(trims)))
    cat = "".join(f"[lsmt{i}]" for i in range(len(trims)))
    return ";".join([src, *segs]) + f";{cat}concat=n={len(trims)}:v=1:a=0,{tail}"
