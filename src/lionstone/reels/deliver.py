"""`lionstone reels make`: raw footage → branded, checked, publish-ready Reel.

plan (9:16, brand style, Turkish word captions) → brand kit → render → SFX + music
→ final QA on the mixed file → cover variants → caption file → editing room →
delivery report. Each step writes plain files into the reel's folder.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .. import qa as qa_mod
from ..cli import _catalog
from ..cli import main as cli_main
from ..ingest import probe
from ..models import EditPlan, QAReport
from . import sound, visual
from .brand import Brand, slug
from .content import Reel, lint
from .room import write_room

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}

ROWS = [  # report row → QA checks behind it
    ("Tekrar taraması", ["reels_repeats"]),
    ("Kesim noktaları", ["word_integrity", "join_clicks", "low_confidence_cuts"]),
    ("Senaryo karşılaştırması", ["reels_script_match"]),
    ("Yazı taşması", ["reels_text_fit", "graphics_rules"]),
    ("Ses seviyesi", ["loudness", "true_peak"]),
    ("Görüntü", ["decode_full", "format", "black_frames", "frozen_frames", "av_length"]),
]


def find_footage(folder: Path, reel: Reel | None) -> Path:
    if reel and reel.footage:
        p = Path(reel.footage[0])
        return p if p.is_absolute() else folder / p
    for sub in (folder / "ham", folder):
        vids = sorted(p for p in sub.glob("*") if p.suffix.lower() in VIDEO_EXT)
        if vids:
            return vids[0]
    raise FileNotFoundError(f"çekim bulunamadı: {folder / 'ham'} içine videoyu koy")


def plan_args(brand: Brand, reel: Reel | None, src: Path, out: Path, extra: list[str]) -> list[str]:
    st = brand.style
    args = ["plan", str(src), "-o", str(out), "--aspect", st.get("aspect", "9:16"),
            "--intensity", st.get("intensity", "dynamic"), "--profile", "social",
            "--captions", "burn", "--caption-style", st.get("caption_style", "karaoke"),
            "--color", st.get("color", "punchy"), "--accent", brand.accent]
    if brand.language and "--language" not in extra:
        args += ["--language", brand.language]
    if brand.font:
        args += ["--font", brand.font]
    if reel and st.get("hook_title", True) and reel.hooks:
        fx = st.get("title_effect", "T02")
        hook = visual.title_lines(reel.hooks[0]) if fx == "T02" else reel.hooks[0]
        args += ["--title", hook, "--title-effect", fx]
    return args + extra


def _row_status(report: QAReport, names: list[str]) -> tuple[str, str]:
    checks = [c for c in report.checks if c.name in names]
    if not checks:
        return "Atlandı", "kontrol çalışmadı"
    ran = [c for c in checks if c.status != "skipped"]
    if not ran:
        return "Atlandı", "; ".join(c.detail for c in checks)[:120]
    if any(c.status == "failed" for c in ran):
        return "Düzelt", "; ".join(c.detail for c in ran if c.status == "failed")[:120]
    if any(c.status == "warning" for c in ran):
        return "Bak", "; ".join(c.detail for c in ran if c.status == "warning")[:120]
    return "Temiz", ""


def report_md(brand: Brand, reel: Reel | None, report: QAReport, extras: dict) -> tuple[str, bool]:
    high = [i for i in report.issues if i.severity in ("critical", "high")]
    ready = report.deliverable and not high and not extras.get("lint_errors")
    lines = [f"# {brand.name} · {reel.topic if reel else Path(report.file).stem}", "",
             f"**{'TESLİME HAZIR ✅' if ready else 'DÜZELTME GEREKİYOR 🛑'}**", "",
             "| Kontrol | Durum | Not |", "|---|---|---|"]
    for label, names in ROWS:
        s, note = _row_status(report, names)
        lines.append(f"| {label} | {s} | {note} |")
    lines.append(f"| Kapak | {'Temiz' if extras.get('covers') else 'Yok'} | "
                 f"{len(extras.get('covers', []))} versiyon |")
    le = extras.get("lint_errors", [])
    lines.append(f"| Metin (kanca/script/caption) | {'Düzelt' if le else 'Temiz'} | "
                 f"{'; '.join(le)[:120]} |")
    lines += ["", f"Video: `{Path(report.file).name}` · {extras.get('duration', 0):.1f} sn",
              f"SFX: {len(extras.get('cues', []))} · Müzik: {extras.get('music') or 'yok'}", ""]
    if report.issues:
        lines.append("## Bulgular")
        for i in report.issues:
            at = f" @ {i.at:.1f}s" if isinstance(i.at, (int, float)) else ""
            lines.append(f"- {qa_mod.SEV_ICON.get(i.severity, '')} {i.check}{at}: {i.message}")
    skipped = [c for c in report.checks if c.status == "skipped"]
    if skipped:
        lines += ["", "## Çalışmayan kontroller (dürüst kayıt)"]
        lines += [f"- {c.name}: {c.detail}" for c in skipped]
    return "\n".join(lines) + "\n", ready


def make(brand: Brand, *, folder: Path | None = None, footage: Path | None = None,
         extra: list[str] | None = None, fast: bool = False, covers: int = 3,
         music: str | None = None, sfx: bool | None = None, log=print) -> dict:
    reel = Reel.load(folder) if folder and (folder / "reel.json").exists() else None
    base = folder or Path(footage).parent
    src = Path(footage) if footage else find_footage(base, reel)
    out = (folder / "kurgu") if folder else src.with_name(f"{src.stem}_reels")
    deliver = (folder / "teslim") if folder else out / "teslim"
    deliver.mkdir(parents=True, exist_ok=True)

    log(f"🎬 {brand.name} · {src.name}")
    code = cli_main(plan_args(brand, reel, src, out, list(extra or [])))
    if code != 0:
        raise RuntimeError(f"plan adımı başarısız (kod {code})")
    plan_path = out / "plan.json"
    if brand.kit:
        cli_main(["brand", "apply", str(plan_path), brand.kit])
    plan = EditPlan.load(plan_path)
    w, h = 1080, 1920
    plan.meta["reels"] = {"brand": brand.name, "script": reel.script if reel else "",
                          "topic": reel.topic if reel else "", "width": w, "height": h}
    plan.save(plan_path)

    render_path = out / "render.mp4"
    cli_main(["render", str(plan_path), "-o", str(render_path), *(["--fast"] if fast else [])])
    plan = EditPlan.load(plan_path)

    stem = slug(reel.topic)[:40] if reel and reel.topic else src.stem
    final = deliver / f"{brand.slug}-{stem}.mp4"
    use_sfx = brand.style.get("sfx", True) if sfx is None else sfx
    cues: list[sound.Cue] = []
    if use_sfx:
        if not sound.library():
            log("🔊 SFX başlangıç paketi oluşturuluyor")
            sound.build_pack()
        custom = (folder / "sfx.json") if folder else None
        cues = sound.load_cues(custom) if custom and custom.exists() else sound.auto_cues(plan)
    music = music or brand.style.get("music") or None
    log(f"🔊 Ses: {len(cues)} efekt · müzik: {Path(music).name if music else 'yok'}")
    mixed = sound.mix(render_path, final, cues=cues, music=music,
                      music_volume=float(brand.style.get("music_volume", 0.18)))

    info = probe(final)
    vs = info.video
    report = qa_mod.run_qa(final, plan, catalog=_catalog(), expect={
        "duration": info.duration, "width": vs.width if vs else w,
        "height": vs.height if vs else h, "fps": vs.fps if vs else 30})
    qa_mod.save(report, deliver, "qa")

    cover_files = []
    texts = (reel.cover_text if reel and reel.cover_text else
             ([reel.hooks[0]] if reel and reel.hooks else []))
    for k, at in enumerate(visual.cover_source_times(plan, covers)):
        if not texts:
            break
        txt = texts[k % len(texts)]
        c = visual.make_cover(Path(plan.source), deliver / f"kapak-{k + 1}.jpg", txt, at=at,
                              colors=brand.colors, font=brand.font)
        cover_files.append(c)

    lint_errors = []
    if reel:
        findings = lint(reel, brand)
        lint_errors = [f"{f.field}: {f.message}" for f in findings if f.level == "hata"]
        tags = " ".join(t if t.startswith("#") else f"#{t}" for t in reel.hashtags)
        (deliver / "caption.txt").write_text(
            reel.caption.strip() + ("\n\n" + tags if tags else "") + "\n", encoding="utf-8")
        (deliver / "metin-kontrol.json").write_text(
            json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=1), "utf-8")

    write_room(plan, out / "room.html", f"{brand.name} · düzenleme odası")
    extras = {"covers": cover_files, "cues": mixed["cues"], "music": mixed["music"],
              "duration": info.duration, "lint_errors": lint_errors}
    md, ready = report_md(brand, reel, report, extras)
    (deliver / "rapor.md").write_text(md, encoding="utf-8")
    (deliver / "rapor.json").write_text(json.dumps(
        {"ready": ready, "qa": report.to_dict(), **extras}, ensure_ascii=False, indent=1,
        default=str), "utf-8")
    if reel:
        reel.status = "hazır" if ready else "kontrol"
        reel.save(folder / "reel.json")
    log(("✅ TESLİME HAZIR" if ready else "🛑 DÜZELTME GEREKİYOR") + f" → {deliver / 'rapor.md'}")
    return {"ready": ready, "video": str(final), "deliver": str(deliver),
            "room": str(out / "room.html"), "plan": str(plan_path)}
