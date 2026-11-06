"""Reels onboarding: identity from footage + examples, choices, memory, same-or-new identity."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lionstone.cli import main
from lionstone.models import EditPlan, Word
from lionstone.reels import brand as brand_mod
from lionstone.reels import choices as ch
from lionstone.reels import identity as idn
from lionstone.reels import memory
from lionstone.reels.content import Reel, lint, tokens

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


def _ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LIONSTONE_SFX_DIR", str(tmp_path / "sfx"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    return tmp_path


def _identity(tempo="fast", vertical=True, palette=("#FC0C0C",), music=0, color_filter="eq=1"):
    return {"style": {"tempo": tempo, "cuts_per_minute": 40 if tempo == "fast" else 5,
                      "avg_shot_seconds": 1.5, "pause_ratio": 0.05, "intensity": "dynamic",
                      "saturation": 0.5, "color_filter": color_filter},
            "footage": {"vertical": vertical, "words_per_second": 2.9},
            "examples": [{}, {}, {}], "music_in_examples": music, "palette": list(palette),
            "target_seconds": [15.0, 40.0], "words_per_second": 2.9}


@pytest.fixture()
def clips(ws):
    _ff("-f", "lavfi", "-i", "sine=f=300:d=4:r=48000", "-af", "volume=2", "-ac", "1", str(ws / "v.wav"))
    out = []
    for name, col in (("footage", "gray"), ("ex1", "red"), ("ex2", "crimson"), ("ex3", "orangered")):
        p = ws / f"{name}.mp4"
        _ff("-f", "lavfi", "-i", f"color=c={col}:s=360x640:r=30:d=4", "-i", str(ws / "v.wav"),
            "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(p))
        out.append(p)
    return out


def test_every_question_offers_decide_for_me_in_both_languages():
    for lang, label in (("tr", "Marka kimliğime göre sen belirle"),
                        ("en", "Decide for me from my brand identity")):
        qs = ch.questions(lang)
        assert {"opening", "captions", "grade", "effects", "music", "sfx"} <= {q["id"] for q in qs}
        assert all(q["options"][-1] == {"value": "auto", "label": label} for q in qs)


def test_every_question_has_an_auto_rule_that_returns_a_valid_answer():
    b = brand_mod.Brand(name="M")
    for tempo in ("fast", "medium", "slow"):
        for qdef in ch.QUESTIONS:
            value, why = ch.decide(qdef["id"], _identity(tempo), b)
            assert why and ch.validate(qdef["id"], value) == value


def test_auto_follows_the_measurements():
    b = brand_mod.Brand(name="M")
    assert ch.decide("sfx", _identity("slow"), b)[0] == "minimal"
    assert ch.decide("sfx", _identity("fast"), b)[0] == "sparse"
    assert ch.decide("effects", _identity("fast"), b)[0] == "agent:energetic"
    assert ch.decide("effects", _identity("slow"), b)[0] == "agent:minimal"
    assert ch.decide("grade", _identity(color_filter=""), b)[0] == "natural"
    assert ch.decide("colors", _identity(palette=()), b)[0] == "brand"


def test_auto_never_invents_music():
    b = brand_mod.Brand(name="M")
    value, why = ch.decide("music", _identity(music=3), b)
    assert value == "none" and "licensed" in why
    b.style["music"] = "bed.mp3"
    assert ch.decide("music", _identity(music=3), b)[0] == "file:bed.mp3"


def test_validate_rejects_what_cannot_run(ws):
    with pytest.raises(ValueError):
        ch.validate("captions", "nope")
    with pytest.raises(ValueError):
        ch.validate("nope", "x")
    with pytest.raises(FileNotFoundError):
        ch.validate("music", "file:missing.mp3")
    if not ch._face_tracking_available():
        with pytest.raises(ValueError, match="vision"):
            ch.validate("framing", "face")


def test_choices_reach_the_brand_style(ws):
    b = brand_mod.Brand(name="M", audience="a")
    brand_mod.save(b)
    chosen = ch.resolve(b, {"opening": "none", "captions": "bold", "grade": "film", "pace": "natural",
                            "effects": "fx:brand-frame", "music_level": "low", "sfx": "minimal",
                            "cleanup": "off", "covers": "2"})
    ch.save_choices(b, chosen)
    st = brand_mod.load("M").style
    assert (st["hook_title"], st["caption_style"], st["color"], st["intensity"]) == (
        False, "bold", "film", "natural")
    assert (st["effects"], st["music_volume"], st["sfx_density"], st["denoise"], st["covers"]) == (
        "fx:brand-frame", 0.10, "minimal", "off", 2)
    assert "music" in ch.missing(chosen)


def test_auto_needs_an_identity_first(ws):
    b = brand_mod.Brand(name="M")
    brand_mod.save(b)
    with pytest.raises(ValueError, match="identity"):
        ch.resolve(b, {"captions": "auto"})


def test_plan_args_follow_the_choices(ws):
    from lionstone.reels.deliver import plan_args
    b = brand_mod.Brand(name="M")
    b.style.update(caption_style="none", color="film", denoise="off", intensity="natural",
                   hook_title=False)
    args = plan_args(b, Reel(brand="M", topic="t", hooks=["h"]), Path("a.mp4"), Path("o"), [])
    joined = " ".join(args)
    assert "--captions none" in joined and "--caption-style" not in joined
    assert "--color film" in joined and "--denoise off" in joined and "--title" not in joined


def test_minimal_sfx_keeps_only_opening_and_cta():
    from lionstone.models import GraphicEvent
    from lionstone.reels.sound import auto_cues
    from lionstone.speech import segments_from_cuts
    text = "Bu evi kaçırma sakın bugün Kaydet lazım olacak".split()
    words = [Word(t, i * 1.0, i * 1.0 + 0.8) for i, t in enumerate(text)]
    plan = EditPlan(source="/x.mp4", duration=8.0, intensity="dynamic", words=words,
                    graphics=[GraphicEvent("g", "T02", 3.0, 1.0, "metin")])
    plan.segments = segments_from_cuts([], 8.0, words)
    plan.meta["reels"] = {"cta": "Kaydet, lazım olacak."}
    assert [c.sound for c in auto_cues(plan, density="minimal")] == ["whoosh", "ding"]
    assert "pop" in [c.sound for c in auto_cues(plan)]


def test_lint_uses_the_speakers_measured_rate():
    b = brand_mod.Brand(name="M", target_seconds=(5, 6))
    script = " ".join(["kelime"] * 20)
    r = Reel(brand="M", topic="t", script=script)
    assert any(f.field == "script" and "tahmini" in f.message for f in lint(r, b))  # 8 s at 2.5/s
    b.style["words_per_second"] = 4.0  # 5 s for this speaker
    assert not any(f.field == "script" and "tahmini" in f.message for f in lint(r, b))
    assert len(tokens(script)) == 20


def test_pure_measurements():
    assert idn.dominant_colors(bytes([250, 10, 10] * 50 + [10, 10, 250] * 5 + [128, 128, 128] * 500))[0] == "#FC0C0C"
    assert idn.dominant_colors(bytes([128, 128, 128] * 50)) == []
    words = [Word("a", 0, 1), Word("b", 3, 4)]
    assert idn.speech_gap_ratio(words, 10.0) == pytest.approx(0.2)
    assert idn.music_likely(0.01, None) and not idn.music_likely(0.2, None)
    assert idn.music_likely(0.01, 0.3) and not idn.music_likely(0.3, 0.3)
    assert idn.opening_line([Word("Bir", 0, 1), Word("iki.", 1, 2), Word("üç", 2, 3)]) == "Bir iki."


@needs_ffmpeg
def test_identity_needs_three_to_five_examples(clips):
    b = brand_mod.Brand(name="M")
    brand_mod.save(b)
    with pytest.raises(ValueError, match="3-5"):
        idn.analyze(b, clips[0], clips[1:3], asr=False)
    with pytest.raises(ValueError, match="3-5"):
        idn.analyze(b, clips[0], [clips[1]] * 6, asr=False)
    assert not idn.load_identity(b)


@needs_ffmpeg
def test_identity_measures_and_records_what_it_skipped(clips):
    assert main(["reels", "brand", "init", "Örnek", "--audience", "a"]) == 0
    b = brand_mod.load("Örnek")
    args = ["reels", "identity", "Örnek", "--footage", str(clips[0]), "--no-asr"]
    for c in clips[1:]:
        args += ["--example", str(c)]
    assert main(args) == 0
    i = idn.load_identity(b)
    assert i["footage"]["vertical"] and len(i["examples"]) == 3
    assert i["palette"] and i["style"]["color_filter"]
    assert all("turned off" in s for s in i["skipped"])
    folder = idn.identity_dir(b)
    assert (folder / "identity.md").exists() and (folder / "style.json").exists()
    assert len(list((folder / "frames").glob("*.jpg"))) == 4

    assert main(["reels", "setup", "Örnek", "--auto"]) == 0
    b = brand_mod.load("Örnek")
    assert b.colors["accent"] == i["palette"][0]
    chosen = ch.load_choices(b)
    assert not ch.missing(chosen) and all(c["by"] == "auto" and c["reason"] for c in chosen.values())


@needs_ffmpeg
def test_new_identity_archives_the_old_one_and_asks_again(clips):
    b = brand_mod.Brand(name="M")
    brand_mod.save(b)
    b = brand_mod.load("M")
    idn.analyze(b, clips[0], clips[1:], asr=False, log=lambda *_: None)
    ch.save_choices(b, ch.resolve(b, {q["id"]: "auto" for q in ch.QUESTIONS}))
    assert ch.start_state("M")["state"] == "ready"
    idn.analyze(b, clips[0], clips[1:], asr=False, log=lambda *_: None)
    assert ch.start_state("M")["state"] == "needs_setup"
    old = list((idn.identity_dir(b).parent / "identity-archive").iterdir())
    assert len(old) == 1 and (old[0] / "identity.json").exists() and (old[0] / "choices.json").exists()


def test_catalog_numbers_are_unique_and_every_option_has_a_picture():
    from lionstone.reels import catalog as cl
    items = cl.entries()
    numbers = [e["number"] for e in items]
    assert len(numbers) == len(set(numbers)) and cl.ALL_AUTO not in numbers
    for q in ch.QUESTIONS:
        values = {e["value"] for e in items if e["question"] == q["id"]}
        assert values == {o["value"] for o in q["options"]} | {"auto"}
        assert cl.sheet_path(q["id"]).exists() and q["id"] in cl.GROUP_TITLES
    for e in items:
        assert cl.image_path(e["number"]).exists(), e


def test_pick_turns_numbers_into_answers(ws):
    from lionstone.reels.catalog import number_of, parse_picks
    n = number_of("captions", "bold")
    assert n // 100 == 2 and parse_picks([str(n)]) == {"captions": "bold"}
    assert parse_picks(["200", "101,301"]) == {"captions": "auto", "opening": "T02", "grade": "learned"}
    assert number_of("music", "none") == 601 and number_of("effects", "none") == 501
    full = parse_picks(["0", str(n)])
    assert full["captions"] == "bold" and full["opening"] == "auto" and len(full) == len(ch.QUESTIONS)
    music = number_of("music", "file:<path>")
    assert parse_picks([f"{music}=bed.mp3"]) == {"music": "file:bed.mp3"}
    with pytest.raises(ValueError, match="dosya"):
        parse_picks([str(music)])
    with pytest.raises(ValueError, match="iki numara"):
        parse_picks(["101", "102"])
    with pytest.raises(ValueError, match="numara"):
        parse_picks(["9999"])
    with pytest.raises(ValueError, match="numarası değil"):
        parse_picks(["abc"])


def test_setup_pick_reaches_the_brand(ws, capsys):
    from lionstone.reels.catalog import number_of
    brand_mod.save(brand_mod.Brand(name="M", audience="a"))
    n = number_of("captions", "bold")
    assert main(["reels", "setup", "M", "--pick", str(n)]) == 2  # the rest is still open
    assert "eksik" in capsys.readouterr().out
    assert brand_mod.load("M").style["caption_style"] == "bold"


def test_catalog_page_lists_every_number(ws):
    from lionstone.reels.catalog import entries, write_html
    page = write_html(ws / "c.html", "Örnek", "en").read_text(encoding="utf-8")
    assert all(f'data-n="{e["number"]}"' in page for e in entries())
    assert "Örnek" in page and "--pick" in page and "Decide for me" in page


def test_a_prompt_with_no_one_there_never_crashes(ws, monkeypatch):
    import builtins
    import sys

    from lionstone.reels.commands import _prompt

    class FakeTty:  # Windows NUL says it is a terminal, then ends at once
        def isatty(self):
            return True

    def eof(_):
        raise EOFError
    monkeypatch.setattr(sys, "stdin", FakeTty())
    monkeypatch.setattr(builtins, "input", eof)
    assert _prompt("? ") is None


def test_memory_finds_a_brand_from_another_folder(ws, monkeypatch):
    b = brand_mod.Brand(name="Örnek Marka", audience="a")
    brand_mod.save(b)
    other = ws / "baska"
    other.mkdir()
    monkeypatch.chdir(other)
    loaded = brand_mod.load("Örnek Marka")
    assert loaded.audience == "a" and brand_mod.list_brands() == ["ornek-marka"]
    loaded.tone = "yeni"
    brand_mod.save(loaded)  # saved back where it lives, not into this folder
    assert not (other / "brands").exists()
    assert json.loads((ws / "brands/ornek-marka/brand.json").read_text(encoding="utf-8"))["tone"] == "yeni"


def test_memory_forgets_deleted_brands(ws):
    brand_mod.save(brand_mod.Brand(name="M"))
    assert "m" in memory.entries()
    shutil.rmtree(ws / "brands")
    assert memory.entries() == {} and memory.last_used() == ""


def test_start_with_nothing_remembered_shows_the_first_steps(ws, capsys):
    assert main(["reels", "start"]) == 2
    assert "identity" in capsys.readouterr().out


@needs_ffmpeg
def test_start_offers_same_or_new_identity(clips, capsys):
    b = brand_mod.Brand(name="M")
    brand_mod.save(b)
    b = brand_mod.load("M")
    idn.analyze(b, clips[0], clips[1:], asr=False, log=lambda *_: None)
    ch.save_choices(b, ch.resolve(b, {q["id"]: "auto" for q in ch.QUESTIONS}))
    capsys.readouterr()
    assert main(["reels", "start", "--json"]) == 0  # remembers the last brand without a name
    st = json.loads(capsys.readouterr().out)
    assert st["state"] == "ready" and st["brand"] == "M"
    assert [o["label"] for o in st["options"]] == [
        "Aynı marka kimliğimle üret", "Yeni marka kimliği ile hazırla"]
    assert main(["reels", "start", "--choice", "new"]) == 0
    assert "reels identity" in capsys.readouterr().out
    assert main(["reels", "start", "--choice", "same"]) == 0
    assert "reels new" in capsys.readouterr().out


def test_make_with_new_identity_stops_before_rendering(ws, monkeypatch, capsys):
    from lionstone.reels.commands import _identity_gate
    b = brand_mod.Brand(name="M")
    brand_mod.save(b)
    monkeypatch.setattr(ch, "start_state", lambda _: {
        "state": "ready", "identity_at": "2026-11-06", "options": [
            {"value": "same", "label": "S", "next": []},
            {"value": "new", "label": "N", "next": ["lionstone reels identity"]}]})
    assert _identity_gate(b, "new") == 3
    assert "reels identity" in capsys.readouterr().out
    assert _identity_gate(b, "same") is None
    assert "Kayıtlı marka kimliğiyle" in capsys.readouterr().out
