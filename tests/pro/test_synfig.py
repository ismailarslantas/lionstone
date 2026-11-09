"""Synfig backend: optional external `synfig` CLI, composited with FFmpeg."""

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from lionstone.pro import commands_fx, synfig


def _fake_synfig(monkeypatch, n=6):
    """Stand-in for the synfig CLI: writes frame.0000.png … like the real renderer."""
    monkeypatch.setattr(synfig, "find", lambda: "synfig")

    def fake(cmd, cwd):
        out = Path(cmd[cmd.index("-o") + 1])
        w, h = cmd[cmd.index("-w") + 1], cmd[cmd.index("-h") + 1]
        assert cmd[0] == "synfig" and cmd[2:4] == ["-t", "png"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        f"color=c=red@0.5:s={w}x{h}:r=10:d={n / 10},format=rgba",
                        str(out.with_name("frame.%04d.png"))], check=True)
    monkeypatch.setattr(synfig, "_exec", fake)


def _args(**kw):
    base = dict(sif="x.sif", input=None, output="out", start=0.0, width=64, height=96, fps=10.0)
    return Namespace(**{**base, **kw})


def test_missing_synfig_prints_install_hint(monkeypatch, capsys):
    monkeypatch.setattr(synfig, "find", lambda: None)
    assert commands_fx._synfig(_args(), None, None) == 2
    assert synfig.INSTALL_HINT in capsys.readouterr().err
    with pytest.raises(synfig.SynfigError):
        synfig.render_frames(Path("x.sif"), Path("out"), 64, 96, 10)


def test_rejects_non_synfig_files(monkeypatch, tmp_path):
    monkeypatch.setattr(synfig, "find", lambda: "synfig")
    with pytest.raises(synfig.SynfigError, match="expected a Synfig file"):
        synfig.render_frames(tmp_path / "evil.mp4", tmp_path / "o", 64, 96, 10)


def test_frames_are_renumbered(monkeypatch, tmp_path):
    _fake_synfig(monkeypatch)
    sif = tmp_path / "logo.sif"
    sif.write_text("<canvas/>", encoding="utf-8")
    frames = synfig.render_frames(sif, tmp_path / "png", 64, 96, 10)
    assert [f.name for f in frames] == [f"f{i:05d}.png" for i in range(6)]
    assert not (tmp_path / "png" / "raw").exists()


def test_overlay_composites_over_the_clip(monkeypatch, tmp_path):
    _fake_synfig(monkeypatch)
    sif = tmp_path / "logo.sif"
    sif.write_text("<canvas/>", encoding="utf-8")
    clip = tmp_path / "c.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=64x96:r=10:d=2",
                    "-f", "lavfi", "-i", "sine=d=2", "-shortest", "-pix_fmt", "yuv420p", str(clip)],
                   check=True)
    out = tmp_path / "o.mp4"
    assert commands_fx._synfig(_args(sif=str(sif), input=str(clip), output=str(out), start=0.5),
                               None, None) == 0
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout
    assert "video,64,96" in probe and "audio" in probe
    # red overlay visible at 0.8 s (inside), gone at 1.8 s (after its 0.6 s)
    def px(t):
        return subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(out), "-frames:v", "1",
                               "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                              capture_output=True).stdout
    assert px(0.8)[0] > 80 and px(1.8)[0] < 40
