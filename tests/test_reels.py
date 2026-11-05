"""Reels workflow: brand → brief → lint → make (render + SFX + QA + covers) → room → calendar."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lionstone.cli import main
from lionstone.models import EditPlan, Word
from lionstone.reels import brand as brand_mod
from lionstone.reels.calendar import entries, to_ics
from lionstone.reels.checks import leftover_repeats
from lionstone.reels.content import Reel, compare_script, hook_ideas, lint, speak_seconds, tokens
from lionstone.reels.room import apply_edits, write_room
from lionstone.reels.visual import fit_size, wrap

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")

SCRIPT = ("Kira artışı seni korkutuyor mu? Bu hatayı yapma. "
          "Önce bütçeni yaz sonra bölgeyi seç. Kaydet lazım olacak.")


def _ff(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LIONSTONE_SFX_DIR", str(tmp_path / "sfx"))
    return tmp_path


def _brand():
    b = brand_mod.Brand(name="Örnek Emlak", handle="@ornekemlak",
                        audience="İzmir'de ev arayan aileler", banned_words=["garanti"],
                        pains=["bütçesiz ev bakmak"], target_seconds=(5, 30))
    brand_mod.save(b)
    return b


def test_brand_roundtrip_and_slug(ws):
    b = _brand()
    assert b.slug == "ornek-emlak"
    assert brand_mod.load("Örnek Emlak").handle == "@ornekemlak"
    assert brand_mod.list_brands() == ["ornek-emlak"]
    assert brand_mod.load("Örnek Emlak").style["caption_style"] == "karaoke"


def test_hooks_fill_known_slots_only(ws):
    ideas = hook_ideas(_brand(), "kira artışı", ["hata"])
    assert any("bütçesiz ev bakmak" in h for h in ideas["hata"])
    assert any("{sayı}" in h for h in ideas["hata"])  # unknown slot stays visible
    assert ideas["ikinci_kanca"] and ideas["cta"]


def test_lint_flags_real_problems(ws):
    b = _brand()
    r = Reel(brand=b.name, topic="kira", hooks=["{konu} hakkında"], script="Garanti kazanç.",
             caption="x" * 2300)
    levels = {(f.field, f.level) for f in lint(r, b)}
    assert ("hooks[0]", "hata") in levels
    assert ("marka", "hata") in levels
    assert ("caption", "hata") in levels
    good = Reel(brand=b.name, topic="kira", why="aileler kira artışından korkuyor",
                hooks=["Kira artışı seni korkutuyor mu?", "Ev bakmadan önce bunu izle."],
                second_hook="Ama asıl mesele bu değil.", script=SCRIPT,
                cta="Kaydet, lazım olacak.", caption="Kaydet.", cover_text=["KİRA Mİ EV Mİ?"])
    assert not [f for f in lint(good, b) if f.level != "bilgi"]


def test_turkish_tokens_and_timing():
    assert tokens("İzmir'de IŞIK [B-roll] (gülümse)") == ["izmir'de", "ışık"]
    assert 5 < speak_seconds(SCRIPT) < 10


def test_compare_script_finds_missing_words():
    d = compare_script(SCRIPT, SCRIPT.replace("Önce bütçeni yaz", ""))
    assert d.ratio < 1 and any("bütçeni" in m for m in d.missing)
    assert compare_script(SCRIPT, SCRIPT.lower()).ratio == 1.0


def test_leftover_repeats_and_room_apply():
    words = [Word(t, i * 0.5, i * 0.5 + 0.4) for i, t in
             enumerate("bence bence bu ev çok güzel".split())]
    plan = EditPlan(source="/x.mp4", duration=3.0, intensity="dynamic", words=words)
    from lionstone.speech import segments_from_cuts
    plan.segments = segments_from_cuts([], 3.0, words)
    assert leftover_repeats(plan)[0][0] == "bence"
    stats = apply_edits(plan, {"remove": [0], "restore": [], "text": {"3": "EV"}})
    assert stats == {"removed": 1, "restored": 0, "text": 1}
    assert plan.source_to_output(0.2) is None and plan.words[3].text == "EV"
    assert not leftover_repeats(plan)


def test_overflow_blocks_and_vertical_title_fits():
    from lionstone.models import GraphicEvent
    from lionstone.reels.visual import text_findings, title_lines
    hook = "Kira artışı seni gerçekten korkutuyor mu?"
    plan = EditPlan(source="/x.mp4", duration=5, intensity="dynamic", graphics=[
        GraphicEvent("g0", "F01", 0.2, 2.0, hook)])
    assert text_findings(plan)[0]["severity"] == "high"  # F01 doesn't wrap on 9:16
    plan.graphics[0] = GraphicEvent("g0", "T02", 0.2, 2.0, title_lines(hook))
    assert not text_findings(plan)


def test_cover_text_fits():
    lines = wrap("KİRA MI EV ALMAK MI? BU HATAYI YAPMA", 14)
    fs = fit_size(lines, 1080 * 0.84, 1440 * 0.42, 124)
    assert max(len(x) for x in lines) * fs * 0.56 <= 1080 * 0.84 + 1


@needs_ffmpeg
def test_make_end_to_end(ws):
    b = _brand()
    folder = Path("projects") / b.slug / "r1"
    (folder / "ham").mkdir(parents=True)
    # three "sentences" of tone separated by pauses; words placed on the tones
    parts = [("t", 2.4), ("s", 1.4), ("t", 2.4), ("s", 1.2), ("t", 2.4)]
    files = []
    for i, (k, d) in enumerate(parts):
        p = ws / f"p{i}.wav"
        src = (f"anoisesrc=d={d}:c=pink:a=0.003:r=48000" if k == "s" else
               f"sine=f={200 + 30 * i}:d={d}:r=48000,volume=0.4,tremolo=f=5:d=0.6")
        _ff("-f", "lavfi", "-i", src, "-ac", "1", str(p))
        files.append(p)
    _ff(*sum((["-i", str(p)] for p in files), []), "-filter_complex",
        f"concat=n={len(files)}:v=0:a=1", str(ws / "a.wav"))
    video = folder / "ham" / "cekim.mp4"
    _ff("-f", "lavfi", "-i", "testsrc2=s=720x1280:r=30:d=9.8", "-i", str(ws / "a.wav"),
        "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", str(video))
    sents = [("Kira artışı seni korkutuyor mu? Bu hatayı yapma.", 0.1),
             ("Önce bütçeni yaz sonra bölgeyi seç.", 3.9),
             ("Kaydet lazım olacak.", 7.5)]
    words = []
    for text, t0 in sents:
        ws_ = text.split()
        step = 2.2 / len(ws_)
        words += [{"word": w, "start": round(t0 + j * step, 3),
                   "end": round(t0 + j * step + step * 0.85, 3)} for j, w in enumerate(ws_)]
    tr = ws / "words.json"
    tr.write_text(json.dumps({"words": words}, ensure_ascii=False), encoding="utf-8")
    reel = Reel(brand=b.name, topic="Kira mı ev mi", why="korku", hooks=[
        "Kira artışı seni korkutuyor mu?", "Ev bakmadan önce izle."],
        second_hook="Ama asıl mesele bu değil.", script=SCRIPT, cta="Kaydet, lazım olacak.",
        caption="Ev ararken bütçe her şeydir.", hashtags=["izmiremlak", "kira"],
        cover_text=["KİRA MI EV Mİ?"])
    reel.save(folder / "reel.json")

    code = main(["reels", "make", str(folder), "--transcript", str(tr), "--fast"])
    deliver = folder / "teslim"
    rep = json.loads((deliver / "rapor.json").read_text(encoding="utf-8"))
    names = {c["name"]: c["status"] for c in rep["qa"]["checks"]}
    assert names["reels_script_match"] == "passed", rep["qa"]["checks"]
    assert names["reels_repeats"] == "passed"
    assert names["loudness"] == "passed"
    assert names["reels_text_fit"] == "passed", rep["qa"]["checks"]
    assert code == 0 and rep["ready"], (deliver / "rapor.md").read_text(encoding="utf-8")
    assert len(list(deliver.glob("kapak-*.jpg"))) == 3
    assert rep["cues"], "auto SFX cues placed"
    assert "TESLİME HAZIR" in (deliver / "rapor.md").read_text(encoding="utf-8")
    assert "#izmiremlak" in (deliver / "caption.txt").read_text(encoding="utf-8")
    assert (folder / "kurgu" / "room.html").exists()
    assert Reel.load(folder).status == "hazır"

    assert main(["reels", "schedule", str(folder), "2026-11-10 19:00"]) == 0
    ics = to_ics(entries())
    assert "DTSTART:20261110T190000" in ics and "Kira mı ev mi" in ics


def test_room_html_has_words(tmp_path):
    words = [Word("merhaba", 0, 0.4), Word("dünya", 0.5, 0.9)]
    plan = EditPlan(source=str(tmp_path / "v.mp4"), duration=1.0, intensity="dynamic",
                    words=words)
    html = write_room(plan, tmp_path / "room.html").read_text(encoding="utf-8")
    assert "merhaba" in html and "room-edits.json" in html and "</script>" in html
