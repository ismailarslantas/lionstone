"""Motion FX pack (Lionstone 1.0): catalog, renderers, person-matte wiring."""

import subprocess

import pytest

from lionstone.ff import has_filter
from lionstone.pro import matte
from lionstone.pro.features.catalog import Catalog
from lionstone.pro.features.params import resolve
from lionstone.pro.features.renderers import ffmpeg_adapter as fa
from lionstone.pro.features.renderers import motion_fx

CAT = Catalog()
MOTION = [p for p in CAT.presets.values() if p.category == "motion-fx"]
NAMES = {"Orbit", "Couch Wall", "UI World", "Frame Break", "Digital Zoom", "Phone Mockup",
         "Checklist", "Headline Wall", "Zoom-through Cut", "Chart Grow", "Pull-back Reveal",
         "Green Screen", "Paper Cut", "Doodle Boil", "Vertigo", "Cover Story", "Glass Type"}


def test_pack_is_the_17_effects():
    assert {p.name for p in MOTION} == NAMES
    for p in MOTION:
        assert p.usable and p.kind == "effect" and p.pipeline == "filter"
        assert p.license["source"] == "lionstone-original"
        assert fa.implemented(p.id), p.id
        assert " — " in p.description
    assert set(motion_fx.MOTION_FILTERS) == {p.id for p in MOTION}
    assert {p.id for p in MOTION if "matte" in p.tags} == matte.MATTE_EFFECTS


def _ff(graph: str, w: int, h: int, extra_inputs=()):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=s={w}x{h}:r=25:d=2",
         *extra_inputs, "-filter_complex", graph, "-map", "[o]", "-f", "null", "-"],
        capture_output=True, text=True)
    assert out.returncode == 0, out.stderr[-800:]


def _frag(pid, w, h, params=None, matte_on=False):
    p = CAT.get(pid)
    c = fa.RCtx(w, h, 25, 2.0, matte=matte_on)
    return fa.FILTERS[p.id](resolve(p.parameters, params), [(0.3, 1.7)], c), c


@pytest.mark.parametrize("pid", sorted(p.id for p in MOTION))
def test_renders_vertical_and_landscape(pid):
    for w, h in ((108, 192), (192, 108)):
        frag, c = _frag(pid, w, h)
        assert c.mattes == 0
        _ff(f"[0:v]format=yuv420p[s];[s]{frag},format=yuv420p[o]", w, h)


# a soft grey oval stands in for the model's output
FAKE_MATTE = ["-f", "lavfi", "-i", "color=c=black:s={w}x{h}:r=25:d=2,format=gray,"
              "geq=lum='255*lt(hypot((X-W/2)/(W*0.3),(Y-H*0.45)/(H*0.3)),1)'"]


@pytest.mark.parametrize("pid", sorted(matte.MATTE_EFFECTS))
def test_matte_versions_render(pid):
    w, h = 108, 192
    frag, c = _frag(pid, w, h, {"method": "matte"} if pid.endswith("green-screen") else None,
                    matte_on=True)
    assert c.mattes >= 1 and matte.uses_in(frag) == c.mattes
    mg = matte.graph_inputs(1, c.mattes, w, h, 25)
    fake = [x.format(w=w, h=h) for x in FAKE_MATTE]
    _ff(f"{mg};[0:v]format=yuv420p[s];[s]{frag},format=yuv420p[o]", w, h, fake)


def test_matte_graph_follows_the_cuts():
    g = matte.graph_inputs(3, 2, 1080, 1920, 30, trims=[(0.0, 1.5), (4.0, 6.0)])
    assert "[3:v]fps=30,split=2" in g and "concat=n=2:v=1:a=0" in g
    assert "trim=start=4.000000:end=6.000000" in g
    assert g.endswith("[lsmatte1][lsmatte2]")


def test_matte_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("LIONSTONE_MATTE", "0")
    assert not matte.wants(["lionstone.frame-break"])
    monkeypatch.setenv("LIONSTONE_MATTE", "1")
    assert matte.wants(["lionstone.frame-break"]) and not matte.wants(["lionstone.orbit"])


@pytest.mark.skipif(not has_filter("drawtext"), reason="FFmpeg build without drawtext")
def test_text_is_literal_and_fonts_load(tmp_path):
    # '%' used to be read as a drawtext expansion and broke the whole graph
    frag, _ = _frag("chart-grow", 192, 108, {"label": "+240% 100%"})
    assert "expansion=none" in frag
    _ff(f"[0:v]format=yuv420p[s];[s]{frag},format=yuv420p[o]", 192, 108)
    font = motion_fx._font(motion_fx.BOLD)  # copied to an ASCII temp path for FreeType
    assert font.endswith("Poppins-Bold.ttf") and all(ord(ch) < 128 for ch in font)


def test_plan_render_feeds_the_matte(plan_copy, media, tmp_path, monkeypatch):
    """Compile → plan.color["matte"] → render adds the matte input and trims it like the video."""
    from lionstone.models import EditPlan
    from lionstone.pro.features import timeline as tl
    from lionstone.pro.features.compile import compile_plan
    from lionstone.pro.features.entitlements import for_tier
    from lionstone.render import RenderOptions, render

    fake = tmp_path / "matte.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=black:s=120x68:r=10:d=40,format=gray,"
                    "geq=lum='255*lt(hypot((X-W/2)/(W*0.25),(Y-H/2)/(H*0.4)),1)'",
                    "-pix_fmt", "yuv420p", str(fake)], check=True)
    monkeypatch.setattr(matte, "ensure", lambda src: fake)
    plan = EditPlan.load(plan_copy)
    for pid, seg in (("glass-type", 0), ("orbit", 1)):
        p = CAT.get(pid)
        tl.add(plan, tl.FxInstance(preset=p.id, version=p.version,
                                   anchor=tl.segment_anchor(plan, seg), params={}))
    rep = compile_plan(plan, CAT, for_tier("studio"))
    assert len(rep.applied) == 2 and not rep.skipped
    assert plan.color["matte"]["uses"] >= 1 and "[lsmatte1]" in plan.color["filter"]
    res = render(plan, tmp_path / "final.mp4", RenderOptions(captions="none", denoise="off"))
    assert res.output.exists()
    graph = (tmp_path / ".lionstone" / "graph_render.txt").read_text(encoding="utf-8")
    assert "concat=n=" in graph and "[lsmatte1]" in graph


def test_without_opencv_the_plain_versions_are_used(plan_copy, monkeypatch):
    from lionstone.models import EditPlan
    from lionstone.pro.features import timeline as tl
    from lionstone.pro.features.compile import compile_plan
    from lionstone.pro.features.entitlements import for_tier

    monkeypatch.setattr(matte, "ensure", lambda src: None)
    plan = EditPlan.load(plan_copy)
    p = CAT.get("frame-break")
    tl.add(plan, tl.FxInstance(preset=p.id, version=p.version,
                               anchor=tl.segment_anchor(plan, 0), params={}))
    rep = compile_plan(plan, CAT, for_tier("studio"))
    assert len(rep.applied) == 1 and "matte" not in plan.color
    assert "lsmatte" not in plan.color["filter"]
    assert any("person matte unavailable" in n for n in rep.notes)


def test_fx_clip_renders_at_the_clip_size(tmp_path):
    from lionstone.pro.features.clipfx import apply_to_clip
    clip = tmp_path / "c.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=180x320:r=25:d=2",
                    "-f", "lavfi", "-i", "sine=d=2", "-shortest", "-pix_fmt", "yuv420p",
                    str(clip)], check=True)
    out = apply_to_clip("orbit", clip, tmp_path / "o.mp4", start=0.5, end=1.5)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                            "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout
    assert "video,180,320" in probe and "audio" in probe


def test_openmontage_installer_copies_only_the_adapter(tmp_path):
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "integrations" / "openmontage"
    spec = importlib.util.spec_from_file_location("om_install", root / "install.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    om = tmp_path / "OpenMontage"
    (om / "tools").mkdir(parents=True)
    (om / "tools" / "base_tool.py").write_text("", encoding="utf-8")
    (om / "skills").mkdir()
    (om / "skills" / "INDEX.md").write_text("| Skill | File |\n", encoding="utf-8")
    mod.install(om)
    mod.install(om)  # idempotent
    assert (om / "tools" / "video" / "lionstone_motion_fx.py").is_file()
    assert (om / "skills" / "INDEX.md").read_text(encoding="utf-8").count("lionstone-motion-fx") == 1
    with pytest.raises(SystemExit):
        mod.install(tmp_path / "not-openmontage")


@pytest.mark.parametrize("pid", ["checklist", "headline-wall", "chart-grow", "cover-story",
                                 "glass-type"])
def test_text_effects_render_without_drawtext(pid, monkeypatch):
    """FFmpeg builds without libfreetype (plain Homebrew) get bars instead of text, never an error."""
    monkeypatch.setattr(motion_fx, "has_filter", lambda name: name != "drawtext")
    frag, _ = _frag(pid, 108, 192)
    assert "drawtext" not in frag
    _ff(f"[0:v]format=yuv420p[s];[s]{frag},format=yuv420p[o]", 108, 192)
