"""Reels workflow: brand → brief → lint → make (render + SFX + QA + covers) → room → calendar."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lionstone.cli import main
from lionstone.ff import has_filter
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
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
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


def test_english_and_turkish_hook_libraries_match():
    from lionstone.reels.content import ANGLE_PAIRS, hook_library
    tr, en = hook_library("tr"), hook_library("en")
    assert set(tr["angles"]) == set(ANGLE_PAIRS) and set(en["angles"]) == set(ANGLE_PAIRS.values())
    for lib in (tr, en):
        assert sum(len(a["templates"]) for a in lib["angles"].values()) == 60
        assert len(lib["second_hook"]["templates"]) == 6 and len(lib["cta"]["templates"]) == 6


def test_hook_language_choice_and_angle_names(ws):
    b = _brand()  # a Turkish brand
    en = hook_ideas(b, "rent", ["hata"], language="en")  # Turkish angle name, English library
    assert any("bütçesiz ev bakmak" in h and "mistake" in h for h in en["mistake"])
    assert any("{number}" in h for h in en["mistake"]) and en["second_hook"] and en["cta"]
    tr = hook_ideas(b, "kira", ["mistake"], language="tr")  # and the other way round
    assert "hata" in tr and "ikinci_kanca" in tr
    assert "hata" in hook_ideas(b, "kira", ["hata"])  # the brand's language is the default
    other = brand_mod.new_brand("Marke", "de")
    assert "cta" in hook_ideas(other, "x") and "curiosity" in hook_ideas(other, "x")


def test_english_brand_defaults(ws):
    b = brand_mod.new_brand("Acme Homes", "en", audience="first-time buyers")
    p = brand_mod.save(b)
    assert b.cta == "Save this for later." and "curiosity" in hook_ideas(b, "rent")
    assert "Brand voice" in (p.parent / "brand.md").read_text(encoding="utf-8")
    assert main(["reels", "brand", "init", "Second", "--language", "en"]) == 0
    assert brand_mod.load("Second").language == "en"


def test_hooks_cli_lists_both_languages(ws, capsys):
    _brand()
    assert main(["reels", "hooks", "Örnek Emlak", "kira", "--angle", "hata", "--lang", "both"]) == 0
    out = capsys.readouterr().out
    assert "## tr · hata" in out and "## en · mistake" in out


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


@needs_ffmpeg
def test_strong_cleanup_really_removes_noise(tmp_path):
    import re

    from lionstone.render import _denoise

    def level(af, amp):
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", f"anoisesrc=c=white:a={amp}:r=48000:d=3",
             "-af", f"{af},atrim=start=1.5,astats=measure_overall=RMS_level:measure_perchannel=none",
             "-f", "null", "-"], capture_output=True, encoding="utf-8", errors="replace", check=True)
        return float(re.findall(r"RMS level dB: (-?[\d.]+)", p.stderr)[-1])
    assert level(_denoise("strong"), 0.03) < level("anull", 0.03) - 10  # a noisy room
    assert level(_denoise("light"), 0.006) < level("anull", 0.006) - 3  # an ordinary room


def test_reels_hook_sits_above_the_face():
    from lionstone.models import GraphicEvent
    from lionstone.pro.fx.builders import _center_y
    assert _center_y(GraphicEvent("g", "P05", 0, 2, "x", params={"position": "top"}), 1920) == "307"


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
    md = (deliver / "rapor.md").read_text(encoding="utf-8")
    full_ffmpeg = has_filter("subtitles") and has_filter("drawtext")
    if full_ffmpeg:
        assert code == 0 and rep["ready"] and "TESLİME HAZIR" in md, md
    else:  # e.g. Homebrew's plain ffmpeg: no captions or titles, and the report must say so
        assert code == 2 and not rep["ready"] and "GÖZDEN GEÇİR" in md and "FFmpeg'de" in md, md
    assert len(list(deliver.glob("kapak-*.jpg"))) == 3
    assert rep["cues"], "auto SFX cues placed"
    assert "#izmiremlak" in (deliver / "caption.txt").read_text(encoding="utf-8")
    assert (folder / "kurgu" / "room.html").exists()
    assert Reel.load(folder).status == ("hazır" if full_ffmpeg else "kontrol")

    assert main(["reels", "schedule", str(folder), "2026-11-10 19:00"]) == 0
    ics = to_ics(entries())
    assert "DTSTART:20261110T190000" in ics and "Kira mı ev mi" in ics


    # room edits survive --keep-plan and reach the delivered file, with SFX and final QA
    plan_file = folder / "kurgu" / "plan.json"
    long_before = EditPlan.load(plan_file).output_duration
    edits = ws / "edits.json"
    edits.write_text(json.dumps({"remove": [5, 6], "text": {"0": "KİRA"}}), encoding="utf-8")
    assert main(["reels", "room-apply", str(plan_file), str(edits)]) == 0
    main(["reels", "make", str(folder), "--transcript", str(tr), "--fast", "--keep-plan"])
    kept = EditPlan.load(plan_file)
    assert kept.words[0].text == "KİRA" and any(c.kind == "manual" for c in kept.cuts)
    assert kept.output_duration < long_before
    rep = json.loads((deliver / "rapor.json").read_text(encoding="utf-8"))
    checks = {c["name"]: c for c in rep["qa"]["checks"]}
    assert checks["plan_duration"]["status"] == "passed"
    assert "1080x1920" in checks["format"]["detail"]


def test_turkish_capitals_on_covers():
    from lionstone.reels.content import tr_upper
    assert tr_upper("kira mı ev mi") == "KİRA MI EV Mİ"


def test_covers_without_any_cut_still_give_three_frames():
    from lionstone.reels.visual import cover_source_times
    words = [Word("a", 0.0, 0.5)]
    plan = EditPlan(source="/x.mp4", duration=30.0, intensity="dynamic", words=words)
    from lionstone.speech import segments_from_cuts
    plan.segments = segments_from_cuts([], 30.0, words)
    times = cover_source_times(plan, 3)
    assert len(set(times)) == 3 and all(0 < t < 30 for t in times)


def test_ics_is_folded_and_written_as_bytes(tmp_path):
    from lionstone.reels.calendar import write_ics
    r = Reel(brand="Örnek", topic="ş" * 80, publish_at="2026-11-10T19:00",
             hooks=["Kanca"], caption="Uzun açıklama, " * 20)
    raw = write_ics(tmp_path / "t.ics", [(tmp_path, r)]).read_bytes()
    assert b"\r\r\n" not in raw  # Windows text mode would double the CR
    lines = raw.split(b"\r\n")
    assert max(len(x) for x in lines) <= 75
    for x in lines:
        x.decode("utf-8")  # never split inside a UTF-8 character
    assert b"\r\n " in raw


def test_folder_named_like_a_category_is_not_a_sound(ws):
    from lionstone.reels.sound import resolve
    (ws / "pop").mkdir()
    wav = ws / "lib.wav"
    wav.write_bytes(b"x")
    assert resolve("pop", {"pop/pop-01": wav}) == wav


def test_ding_lands_on_the_spoken_cta():
    from lionstone.reels.sound import auto_cues
    from lionstone.speech import segments_from_cuts
    text = "Bu evi kaçırma sakın bugün Kaydet lazım olacak".split()
    words = [Word(t, i * 1.0, i * 1.0 + 0.8) for i, t in enumerate(text)]
    plan = EditPlan(source="/x.mp4", duration=8.0, intensity="dynamic", words=words)
    plan.segments = segments_from_cuts([], 8.0, words)
    plan.meta["reels"] = {"cta": "Kaydet, lazım olacak."}
    dings = [c for c in auto_cues(plan) if c.sound == "ding"]
    assert len(dings) == 1 and abs(dings[0].at - 5.4) < 0.1


def test_room_cut_never_pads_into_a_neighbour_word():
    from lionstone.speech import segments_from_cuts
    words = [Word("bir", 0.0, 0.5), Word("iki", 0.505, 1.0), Word("üç", 1.005, 1.5)]
    plan = EditPlan(source="/x.mp4", duration=2.0, intensity="dynamic", words=words)
    plan.segments = segments_from_cuts([], 2.0, words)
    apply_edits(plan, {"remove": [1]})
    cut = [c for c in plan.cuts if c.kind == "manual"][0]
    assert cut.start >= 0.5 and cut.end <= 1.005


@needs_ffmpeg
def test_music_ducks_under_a_mono_voice(ws):
    import re

    from lionstone.reels.sound import mix
    _ff("-f", "lavfi", "-i", "sine=f=300:d=3:r=48000", "-f", "lavfi", "-i",
        "anullsrc=r=48000:cl=mono:d=3", "-filter_complex", "[0][1]concat=n=2:v=0:a=1", "-ac", "1",
        str(ws / "voice.wav"))
    _ff("-f", "lavfi", "-i", "testsrc2=s=108x192:r=30:d=6", "-i", str(ws / "voice.wav"),
        "-shortest", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(ws / "v.mp4"))
    _ff("-f", "lavfi", "-i", "sine=f=2000:d=2:r=44100", "-ac", "2", str(ws / "m.wav"))
    res = mix(ws / "v.mp4", ws / "o.mp4", cues=[], music=str(ws / "m.wav"), music_volume=0.3)
    assert res["music"]

    def music_level(start, dur):
        p = subprocess.run(
            ["ffmpeg", "-hide_banner", "-ss", str(start), "-t", str(dur), "-i", str(ws / "o.mp4"),
             "-af", "bandpass=f=2000:w=200,astats=measure_overall=RMS_level:measure_perchannel=none",
             "-f", "null", "-"], capture_output=True, encoding="utf-8", errors="replace", check=True)
        return float(re.findall(r"RMS level dB: (-?[\d.]+)", p.stderr)[-1])

    assert music_level(1.5, 1.0) < music_level(4.0, 1.0) - 3  # quieter while the voice speaks


def test_karaoke_captions_sit_above_the_reels_ui():
    from lionstone.captions import STYLES
    from lionstone.plugins import registry
    from lionstone.reels.visual import UI_BOTTOM
    registry()
    assert STYLES["karaoke"].margin_v_ratio >= UI_BOTTOM


def test_phantom_asr_segment_is_detected():
    from lionstone.speech import is_phantom_segment
    fake = [Word("Bir", 25.74, 27.54, 0.02), Word("sonraki", 27.54, 27.54, 0.72),
            Word("videoda", 27.54, 27.54, 0.82), Word("görüşmek", 27.54, 27.54, 0.59),
            Word("üzere.", 27.54, 28.06, 0.93)]
    real = [Word("Kaydet,", 24.06, 24.9, 0.91), Word("lazım", 25.18, 25.4, 0.99),
            Word("olacak.", 25.4, 25.74, 0.98)]
    assert is_phantom_segment(fake) and not is_phantom_segment(real)


def test_retake_removes_first_take_across_a_pause():
    from lionstone.presets import INTENSITIES
    from lionstone.speech import word_cuts
    text = "önce bütçeni yaz önce bütçeni yaz sonra bölgeyi seç".split()
    words, t = [], 0.0
    for i, x in enumerate(text):
        words.append(Word(x, t, t + 0.4))
        t += 2.0 if i == 2 else 0.5  # a long pause between the takes
    cuts = [c for c in word_cuts(words, INTENSITIES["dynamic"], t) if c.kind == "repeat"]
    assert len(cuts) == 1 and cuts[0].end <= words[3].start and cuts[0].start <= words[0].start + 0.05


def test_ding_survives_one_misheard_cta_word():
    from lionstone.reels.sound import cta_time
    from lionstone.speech import segments_from_cuts
    words = [Word("Haydet,", 0.0, 0.5), Word("lazım", 0.6, 1.0), Word("olacak.", 1.1, 1.5)]
    plan = EditPlan(source="/x.mp4", duration=2.0, intensity="dynamic", words=words)
    plan.segments = segments_from_cuts([], 2.0, words)
    plan.meta["reels"] = {"cta": "Kaydet, lazım olacak."}
    assert cta_time(plan) is not None


def test_verdict_needs_review_when_script_differs_or_could_not_run():
    from lionstone.models import QACheck, QAReport
    from lionstone.reels.deliver import report_md
    b = brand_mod.Brand(name="M")
    r = Reel(brand="M", topic="t", script="bir iki üç")
    rep = QAReport(file="x.mp4")
    rep.checks.append(QACheck("reels_script_match", "editorial", "warning", "match 77%"))
    md, ready = report_md(b, r, rep, {})
    assert not ready and "GÖZDEN GEÇİR" in md and "TESLİME HAZIR" not in md
    rep = QAReport(file="x.mp4")
    rep.checks.append(QACheck("reels_script_match", "editorial", "skipped", "no transcript"))
    md, ready = report_md(b, r, rep, {})
    assert not ready and "lionstone[whisper]" in md


@needs_ffmpeg
def test_cover_text_is_really_drawn(ws):
    from lionstone.reels.visual import make_cover
    if not has_filter("drawtext"):
        pytest.skip("this FFmpeg has no drawtext")
    _ff("-f", "lavfi", "-i", "color=c=gray:s=108x192:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(ws / "g.mp4"))
    colors = {"primary": "#808080", "accent": "#808080", "text": "#FFFFFF"}
    make_cover(ws / "g.mp4", ws / "a.jpg", "KİRA MI", at=0.1, colors=colors)
    make_cover(ws / "g.mp4", ws / "b.jpg", "ŞĞÜÖÇ", at=0.1, colors=colors)
    assert (ws / "a.jpg").read_bytes() != (ws / "b.jpg").read_bytes()


def test_unknown_hook_angle_is_an_error(ws):
    with pytest.raises(ValueError, match="bilinmeyen açı"):
        hook_ideas(_brand(), "kira", ["yok-boyle"])


def test_room_html_has_words(tmp_path):
    words = [Word("merhaba", 0, 0.4), Word("dünya", 0.5, 0.9)]
    plan = EditPlan(source=str(tmp_path / "v.mp4"), duration=1.0, intensity="dynamic",
                    words=words)
    html = write_room(plan, tmp_path / "room.html").read_text(encoding="utf-8")
    assert "merhaba" in html and "room-edits.json" in html and "</script>" in html
