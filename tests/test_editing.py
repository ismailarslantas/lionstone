"""Lionstone Editing: brief, stage runner, resume, review stop, skipped stages."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lionstone import editing
from lionstone.cli import main


def _brief(tmp_path: Path, **fields) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "take.mp4").write_bytes(b"")
    editing.init(tmp_path, "take.mp4", **fields)
    return tmp_path


def test_init_leaves_copy_empty_and_updates_in_place(tmp_path):
    editing.init(tmp_path, "take.mp4", platform="reels")
    b = editing.load_brief(tmp_path)
    assert b["goal"] == b["title"] == b["subtitle"] == "" and b["fx"] == []
    editing.init(tmp_path, title="Mine")
    b = editing.load_brief(tmp_path)
    assert (b["footage"], b["platform"], b["title"]) == ("take.mp4", "reels", "Mine")
    with pytest.raises(ValueError, match="unknown brief fields"):
        editing.init(tmp_path, colour="red")


def test_validate_lists_every_problem(tmp_path):
    editing.init(tmp_path, "missing.mp4", platform="vimeo", chapters=["intro"],
                 fx=[{"effect": "frame-break", "start": 3, "end": 1}, {}])
    errs = editing.validate(editing.load_brief(tmp_path), tmp_path)
    assert any("footage not found" in e for e in errs)
    assert any(e.startswith("platform") for e in errs)
    assert any("chapter" in e for e in errs)
    assert any("end must be after start" in e for e in errs)
    assert any("fx[1]" in e for e in errs)
    assert editing.validate(editing.load_brief(_brief(tmp_path / "ok")), tmp_path / "ok") == []


@pytest.fixture
def fake_stages(monkeypatch):
    calls = []

    def make(name):
        def fn(prod, brief, log):
            calls.append(name)
            if name == "review":
                return editing._review(prod, brief, log)
            return "done", name
        return fn
    monkeypatch.setattr(editing, "STAGE_FNS", {s: make(s) for s in editing.STAGES})
    return calls


def test_runs_in_order_and_resumes(tmp_path, fake_stages):
    _brief(tmp_path)
    st = editing.run(tmp_path, log=lambda m: None)
    assert fake_stages == list(editing.STAGES)
    assert st["next"] is None
    assert st["stages"]["review"]["status"] == "skipped"  # review off: skipped, not done
    fake_stages.clear()
    editing.run(tmp_path, log=lambda m: None)
    assert fake_stages == []  # nothing repeated
    editing.run(tmp_path, "render", log=lambda m: None)
    assert fake_stages == ["render", "fx", "qa", "report"]
    with pytest.raises(ValueError):
        editing.run(tmp_path, "colour", log=lambda m: None)


def test_review_stops_then_continues(tmp_path, fake_stages):
    _brief(tmp_path, review=True)
    st = editing.run(tmp_path, log=lambda m: None)
    assert fake_stages == ["brief", "plan", "review"]
    assert st["next"] == "review" and st["stages"]["review"]["status"] == "waiting"
    st = editing.run(tmp_path, log=lambda m: None)
    assert st["stages"]["review"]["status"] == "done" and st["next"] is None


def test_failed_stage_is_recorded(tmp_path, fake_stages, monkeypatch):
    _brief(tmp_path)

    def boom(prod, brief, log):
        raise RuntimeError("no disk")
    monkeypatch.setitem(editing.STAGE_FNS, "render", boom)
    with pytest.raises(RuntimeError):
        editing.run(tmp_path, log=lambda m: None)
    st = editing.status(tmp_path)
    assert st["stages"]["render"]["status"] == "failed" and "no disk" in st["stages"]["render"]["note"]
    assert st["next"] == "render"


def test_bad_brief_fails_the_brief_stage(tmp_path):
    editing.init(tmp_path, "missing.mp4")
    with pytest.raises(ValueError, match="footage not found"):
        editing.run(tmp_path, log=lambda m: None)
    assert editing.status(tmp_path)["stages"]["brief"]["status"] == "failed"


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_end_to_end(tmp_path):
    def ff(*args):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)
    ff("-f", "lavfi", "-i", "sine=f=220:d=2:r=48000,volume=0.4", str(tmp_path / "a1.wav"))
    ff("-f", "lavfi", "-i", "anoisesrc=d=2.5:c=pink:a=0.003:r=48000", str(tmp_path / "s.wav"))
    ff("-f", "lavfi", "-i", "sine=f=300:d=2:r=48000,volume=0.4", str(tmp_path / "a2.wav"))
    ff("-i", str(tmp_path / "a1.wav"), "-i", str(tmp_path / "s.wav"), "-i",
       str(tmp_path / "a2.wav"), "-filter_complex", "concat=n=3:v=0:a=1", str(tmp_path / "a.wav"))
    ff("-f", "lavfi", "-i", "testsrc2=s=640x360:r=25:d=6.5", "-i", str(tmp_path / "a.wav"),
       "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
       "-c:a", "aac", str(tmp_path / "take.mp4"))
    prod = tmp_path / "prod"
    assert main(["editing", "init", str(prod), "--footage", str(tmp_path / "take.mp4")]) == 0
    editing.init(prod, asr="none", goal="Test production", fx=[{"effect": "no-such-effect"}])
    assert main(["editing", "run", str(prod)]) == 0
    st = editing.status(prod)
    assert st["next"] is None and st["deliverable"] is True
    assert st["stages"]["fx"]["status"] == "skipped"
    assert "no-such-effect skipped" in st["stages"]["fx"]["note"]
    assert (prod / "out" / "take.mp4").exists()
    qa = json.loads((prod / "out" / "qa.json").read_text(encoding="utf-8"))
    assert {c["name"]: c["status"] for c in qa["checks"]}["word_integrity"] == "skipped"
    report = (prod / "report.md").read_text(encoding="utf-8")
    assert "Test production" in report and "| fx | skipped |" in report
    assert "| report | done |" in report
