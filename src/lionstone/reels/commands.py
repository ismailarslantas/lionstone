"""`lionstone reels …` — brand-specific Instagram Reels workflow."""

from __future__ import annotations

import json
from pathlib import Path

from . import brand as brand_mod
from .content import STATUSES, Reel, hook_ideas, lint, new_reel


def _cfg(p) -> None:
    sub = p.add_subparsers(dest="reels_cmd", required=True)

    b = sub.add_parser("brand", help="marka profili: init · show · list")
    b.add_argument("action", choices=["init", "show", "list", "check"])
    b.add_argument("name", nargs="?")
    b.add_argument("--handle", default="")
    b.add_argument("--sector", default="")
    b.add_argument("--audience", default="")
    b.add_argument("--accent")
    b.add_argument("--kit", help="uygulanacak Lionstone brand kit adı")
    b.add_argument("--language", default="tr",
                   help="markanın dili: tr, en, … (varsayılan tr; kanca, altyazı, konuşma tanıma)")

    n = sub.add_parser("new", help="yeni Reel klasörü + reel.json")
    n.add_argument("brand")
    n.add_argument("topic")

    h = sub.add_parser("hooks", help="kanca kütüphanesinden markaya göre doldurulmuş öneriler")
    h.add_argument("brand")
    h.add_argument("topic")
    h.add_argument("--angle", action="append",
                   help="merak, hata, sonuc, … ya da curiosity, mistake, result, …")
    h.add_argument("--lang", choices=["tr", "en", "both"],
                   help="kanca dili (varsayılan: markanın dili); both iki dili de listeler")
    h.add_argument("--json", action="store_true")

    li = sub.add_parser("lint", help="kanca / script / caption / hashtag kontrolü")
    li.add_argument("reel", help="reel klasörü ya da reel.json")

    m = sub.add_parser("make", help="ham çekim → markalı, kontrol edilmiş Reel")
    m.add_argument("reel", nargs="?", help="reel klasörü (ham/ içinde çekim)")
    m.add_argument("--brand", help="reel klasörü yoksa marka adı")
    m.add_argument("--video", help="reel klasörü yoksa çekim dosyası")
    m.add_argument("--music", help="müzik dosyası (lisansı sende)")
    m.add_argument("--no-sfx", action="store_true")
    m.add_argument("--covers", type=int, default=3)
    m.add_argument("--fast", action="store_true")
    m.add_argument("--transcript", help="kelime zamanlı transcript JSON")
    m.add_argument("--no-asr", action="store_true")
    m.add_argument("--model", default=None, help="faster-whisper modeli (varsayılan small)")
    m.add_argument("--keep-plan", action="store_true",
                   help="kurgu/plan.json'u yeniden üretme (düzenleme odası değişiklikleri korunur)")

    r = sub.add_parser("room", help="düzenleme odası: kelimeye tıkla, kes, düzelt")
    r.add_argument("plan")
    r.add_argument("-o", "--output")
    ra = sub.add_parser("room-apply", help="room-edits.json'u plana uygula")
    ra.add_argument("plan")
    ra.add_argument("edits")

    c = sub.add_parser("cover", help="kapak versiyonları")
    c.add_argument("video")
    c.add_argument("--brand", required=True)
    c.add_argument("--text", action="append", required=True)
    c.add_argument("-n", type=int, default=3)
    c.add_argument("-o", "--out", default="kapaklar")

    s = sub.add_parser("sfx", help="ses efekti kütüphanesi: build · list")
    s.add_argument("action", choices=["build", "list"])
    s.add_argument("--force", action="store_true")

    mx = sub.add_parser("mix", help="render'a SFX + müzik ekle (video kopyalanır)")
    mx.add_argument("video")
    mx.add_argument("plan")
    mx.add_argument("-o", "--output", required=True)
    mx.add_argument("--music")
    mx.add_argument("--music-volume", type=float, default=0.18)
    mx.add_argument("--cues", help="sfx.json: [{at, sound, gain}]")

    sc = sub.add_parser("schedule", help="yayın tarihi ver")
    sc.add_argument("reel")
    sc.add_argument("when", help='"2026-11-10 19:00"')
    st = sub.add_parser("status", help="durum değiştir")
    st.add_argument("reel")
    st.add_argument("status", choices=list(STATUSES))
    ca = sub.add_parser("calendar", help="içerik takvimi; --ics ile dışa aktar")
    ca.add_argument("--brand")
    ca.add_argument("--ics")

    sub.add_parser("checklist", help="teslim öncesi kontrol listesi")


def _brand(a) -> int:
    if a.action == "list":
        for x in brand_mod.list_brands():
            print(x)
        return 0
    if not a.name:
        raise ValueError("marka adı gerekli")
    if a.action == "init":
        b = brand_mod.new_brand(a.name, a.language, handle=a.handle, sector=a.sector,
                                audience=a.audience, kit=a.kit)
        if a.accent:
            b.colors["accent"] = a.accent
        p = brand_mod.save(b)
        print(f"Marka → {p}\nNotlar → {p.parent / 'brand.md'}")
        for w in b.validate():
            print(f"  ! {w}")
        return 0
    b = brand_mod.load(a.name)
    if a.action == "check":
        probs = b.validate()
        for w in probs:
            print(f"  ! {w}")
        print("✅ marka profili tamam" if not probs else f"{len(probs)} sorun")
        return 1 if probs else 0
    print(json.dumps(b.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _make(a) -> int:
    from .deliver import make
    folder = Path(a.reel) if a.reel else None
    if folder and folder.is_file():
        folder = folder.parent
    if folder:
        reel = Reel.load(folder)
        b = brand_mod.load(a.brand or reel.brand)
    else:
        if not (a.brand and a.video):
            raise ValueError("reel klasörü ya da --brand + --video gerekli")
        b = brand_mod.load(a.brand)
    extra = []
    if a.transcript:
        extra += ["--transcript", a.transcript]
    if a.no_asr:
        extra.append("--no-asr")
    if a.model:
        extra += ["--model", a.model]
    res = make(b, folder=folder, footage=Path(a.video) if a.video else None, extra=extra,
               fast=a.fast, covers=a.covers, music=a.music, sfx=False if a.no_sfx else None,
               keep_plan=a.keep_plan)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["ready"] else 2


def _run(a) -> int:
    cmd = a.reels_cmd
    if cmd == "brand":
        return _brand(a)
    if cmd == "new":
        b = brand_mod.load(a.brand)
        p = new_reel(b, a.topic)
        print(f"Reel → {p}\nÇekimi buraya koy → {p.parent / 'ham'}")
        return 0
    if cmd == "hooks":
        b = brand_mod.load(a.brand)
        langs = ["tr", "en"] if a.lang == "both" else [a.lang or b.language]
        ideas = {lg: hook_ideas(b, a.topic, a.angle, language=lg) for lg in langs}
        if a.json:
            print(json.dumps(ideas if a.lang == "both" else ideas[langs[0]],
                             ensure_ascii=False, indent=1))
        else:
            for lg, sets in ideas.items():
                for k, v in sets.items():
                    print(f"\n## {f'{lg} · ' if a.lang == 'both' else ''}{k}")
                    for x in v:
                        print(f"- {x}")
        return 0
    if cmd == "lint":
        r = Reel.load(Path(a.reel))
        fs = lint(r, brand_mod.load(r.brand))
        icon = {"hata": "🔴", "uyarı": "🟠", "bilgi": "🔵"}
        for f in fs:
            print(f"{icon[f.level]} {f.field}: {f.message}")
        errors = sum(f.level == "hata" for f in fs)
        print("✅ metin hazır" if not fs else f"{errors} hata, {len(fs) - errors} not")
        return 1 if errors else 0
    if cmd == "make":
        return _make(a)
    if cmd == "room":
        from ..models import EditPlan
        from .room import write_room
        plan = EditPlan.load(a.plan)
        out = Path(a.output or Path(a.plan).parent / "room.html")
        print(f"Düzenleme odası → {write_room(plan, out)}  (tarayıcıda aç)")
        return 0
    if cmd == "room-apply":
        from ..models import EditPlan
        from ..pipeline import replan_graphics
        from .room import apply_edits
        plan = EditPlan.load(a.plan)
        stats = apply_edits(plan, json.loads(Path(a.edits).read_text(encoding="utf-8")))
        from ..cli import _catalog
        replan_graphics(plan, _catalog())
        plan.save(a.plan)
        print(f"{stats} → lionstone reels make <reel klasörü> --keep-plan")
        return 0
    if cmd == "cover":
        from .visual import cover_frames, make_cover
        b = brand_mod.load(a.brand)
        for k, at in enumerate(cover_frames(Path(a.video), a.n)):
            c = make_cover(Path(a.video), Path(a.out) / f"kapak-{k + 1}.jpg",
                           a.text[k % len(a.text)], at=at, colors=b.colors, font=b.font,
                           language=b.language)
            print(f"{c['file']}  @{at}s  {c['font_size']}px")
        return 0
    if cmd == "sfx":
        from . import sound
        if a.action == "build":
            files = sound.build_pack(force=a.force)
            print(f"{len(files)} efekt → {sound.sfx_dir()}")
        lib = sound.library()
        cats: dict[str, int] = {}
        for k in lib:
            cats[k.split("/")[0]] = cats.get(k.split("/")[0], 0) + 1
        print(f"{len(lib)} ses: " + ", ".join(f"{k} {v}" for k, v in sorted(cats.items())))
        return 0
    if cmd == "mix":
        from ..models import EditPlan
        from . import sound
        plan = EditPlan.load(a.plan)
        cues = sound.load_cues(Path(a.cues)) if a.cues else sound.auto_cues(plan)
        res = sound.mix(Path(a.video), Path(a.output), cues=cues, music=a.music,
                        music_volume=a.music_volume)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    if cmd in ("schedule", "status"):
        from .calendar import parse_when
        p = Path(a.reel)
        folder = p if p.is_dir() else p.parent
        r = Reel.load(folder)
        if cmd == "schedule":
            r.publish_at = parse_when(a.when).isoformat(timespec="minutes")
        else:
            r.status = a.status
        r.save(folder / "reel.json")
        print(f"{r.topic}: {r.status} · {r.publish_at or 'tarih yok'}")
        return 0
    if cmd == "calendar":
        from .calendar import entries, write_ics
        items = entries(brand_slug=brand_mod.slug(a.brand) if a.brand else None)
        for _folder, r in items:
            print(f"{(r.publish_at or '—').replace('T', ' '):16}  {r.status:8}  "
                  f"[{r.brand}] {r.topic}")
        if a.ics:
            write_ics(a.ics, items)
            print(f"Takvim → {a.ics}")
        return 0
    if cmd == "checklist":
        from importlib import resources
        data = json.loads(resources.files("lionstone").joinpath(
            "data/reels/checklist.json").read_text("utf-8"))
        for group in data["groups"]:
            print(f"\n## {group['name']}")
            for item in group["items"]:
                mark = "🤖" if item.get("auto") else "👀"
                print(f"{mark} {item['text']}")
        print("\n🤖 Lionstone otomatik kontrol eder · 👀 göz ile bakılır")
        return 0
    return 1


def register(reg) -> None:
    reg.add_command("reels", "markaya özel Reels: konu → hook → script → kurgu → kontrol → takvim",
                    _cfg, _run)

