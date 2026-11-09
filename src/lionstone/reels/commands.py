"""`lionstone reels …` — brand-specific Instagram Reels workflow."""

from __future__ import annotations

import json
from pathlib import Path

from . import brand as brand_mod
from .content import (
    LEGACY_STATUS,
    RAW_DIR,
    STATUSES,
    Reel,
    hook_ideas,
    lint,
    new_reel,
    normalize_status,
)


def _cfg(p) -> None:
    sub = p.add_subparsers(dest="reels_cmd", required=True)

    b = sub.add_parser("brand", help="brand profile: init · show · list · check")
    b.add_argument("action", choices=["init", "show", "list", "check"])
    b.add_argument("name", nargs="?")
    b.add_argument("--handle", default="")
    b.add_argument("--sector", default="")
    b.add_argument("--audience", default="")
    b.add_argument("--accent")
    b.add_argument("--kit", help="name of a Lionstone brand kit to apply")
    b.add_argument("--language", default="en",
                   help="the brand's language: en, tr, … (default en; used for hooks, captions, speech recognition)")

    sta = sub.add_parser("start", help="saved brand identity: produce with it or prepare a new one")
    sta.add_argument("brand", nargs="?")
    sta.add_argument("--choice", choices=["same", "new"])
    sta.add_argument("--json", action="store_true")

    i = sub.add_parser("identity", help="one talking-head take + 3-5 example Reels → brand identity")
    i.add_argument("brand")
    i.add_argument("--footage", required=True, help="talking-head video")
    i.add_argument("--example", action="append", required=True, default=[],
                   help="an example Reel in your brand's style (give 3-5)")
    i.add_argument("--no-asr", action="store_true")
    i.add_argument("--model", default="small")

    su = sub.add_parser("setup", help="effects, style, music and the other choices; every question offers 'decide for me'")
    su.add_argument("brand")
    su.add_argument("--auto", action="store_true", help="decide everything from the brand identity")
    su.add_argument("--pick", nargs="+", default=[], metavar="NO",
                    help="catalogue numbers, e.g. --pick 101 205 503 602=track.mp3 (0 = decide the rest for me)")
    su.add_argument("--set", action="append", default=[], metavar="QUESTION=VALUE",
                    help="one answer, e.g. captions=karaoke, effects=auto, music=file:track.mp3")
    su.add_argument("--questions", action="store_true", help="print the questions as JSON, save nothing")
    su.add_argument("--show", action="store_true", help="show the saved choices")

    cat = sub.add_parser("catalog", help="visual catalogue: every option's number and real picture")
    cat.add_argument("brand", nargs="?")
    cat.add_argument("--open", action="store_true", help="open in the browser")
    cat.add_argument("--json", action="store_true", help="numbers, image paths and group sheets")
    cat.add_argument("-o", "--output", help="HTML file")

    n = sub.add_parser("new", help="new Reel folder + reel.json")
    n.add_argument("brand")
    n.add_argument("topic")

    h = sub.add_parser("hooks", help="hook library templates filled in for the brand")
    h.add_argument("brand")
    h.add_argument("topic")
    h.add_argument("--angle", action="append",
                   help="curiosity, mistake, result, … or merak, hata, sonuc, …")
    h.add_argument("--lang", choices=["tr", "en", "both"],
                   help="hook language (default: the brand's language); both lists both")
    h.add_argument("--json", action="store_true")

    li = sub.add_parser("lint", help="check hooks, script, caption and hashtags")
    li.add_argument("reel", help="reel folder or reel.json")

    m = sub.add_parser("make", help="raw footage → branded, checked Reel")
    m.add_argument("reel", nargs="?", help="reel folder (footage in raw/)")
    m.add_argument("--brand", help="brand name, without a reel folder")
    m.add_argument("--video", help="footage file, without a reel folder")
    m.add_argument("--music", help="music file (licensing is yours)")
    m.add_argument("--no-sfx", action="store_true")
    m.add_argument("--covers", type=int, default=None)
    m.add_argument("--fast", action="store_true")
    m.add_argument("--transcript", help="transcript JSON with word timings")
    m.add_argument("--no-asr", action="store_true")
    m.add_argument("--model", default=None, help="faster-whisper model (default small)")
    m.add_argument("--identity", choices=["same", "new"],
                   help="saved brand identity: same produces without asking, new prepares a new one")
    m.add_argument("--keep-plan", action="store_true",
                   help="don't regenerate edit/plan.json (keeps editing-room changes)")

    r = sub.add_parser("room", help="editing room: click a word, cut it, fix it")
    r.add_argument("plan")
    r.add_argument("-o", "--output")
    ra = sub.add_parser("room-apply", help="apply room-edits.json to the plan")
    ra.add_argument("plan")
    ra.add_argument("edits")

    c = sub.add_parser("cover", help="cover versions")
    c.add_argument("video")
    c.add_argument("--brand", required=True)
    c.add_argument("--text", action="append", required=True)
    c.add_argument("-n", type=int, default=3)
    c.add_argument("-o", "--out", default="covers")

    s = sub.add_parser("sfx", help="sound effect library: build · list")
    s.add_argument("action", choices=["build", "list"])
    s.add_argument("--force", action="store_true")

    mx = sub.add_parser("mix", help="add SFX + music to a render (the video is copied)")
    mx.add_argument("video")
    mx.add_argument("plan")
    mx.add_argument("-o", "--output", required=True)
    mx.add_argument("--music")
    mx.add_argument("--music-volume", type=float, default=0.18)
    mx.add_argument("--cues", help="sfx.json: [{at, sound, gain}]")

    sc = sub.add_parser("schedule", help="set the publish date")
    sc.add_argument("reel")
    sc.add_argument("when", help='"2026-11-10 19:00"')
    st = sub.add_parser("status", help="change the status")
    st.add_argument("reel")
    st.add_argument("status", choices=[*STATUSES, *LEGACY_STATUS])
    ca = sub.add_parser("calendar", help="content calendar; --ics exports it")
    ca.add_argument("--brand")
    ca.add_argument("--ics")

    sub.add_parser("checklist", help="pre-delivery checklist")


def _brand(a) -> int:
    if a.action == "list":
        for x in brand_mod.list_brands():
            print(x)
        return 0
    if not a.name:
        raise ValueError("a brand name is required")
    if a.action == "init":
        b = brand_mod.new_brand(a.name, a.language, handle=a.handle, sector=a.sector,
                                audience=a.audience, kit=a.kit)
        if a.accent:
            b.colors["accent"] = a.accent
        p = brand_mod.save(b)
        print(f"Brand → {p}\nNotes → {p.parent / 'brand.md'}")
        for w in b.validate():
            print(f"  ! {w}")
        return 0
    b = brand_mod.load(a.name)
    if a.action == "check":
        probs = b.validate()
        for w in probs:
            print(f"  ! {w}")
        print("✅ brand profile complete" if not probs else f"{len(probs)} problem(s)")
        return 1 if probs else 0
    print(json.dumps(b.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _prompt(text: str) -> str | None:
    """A line from the user, or None when nobody is there."""
    import sys
    if not sys.stdin.isatty():
        return None
    try:
        return input(text)
    except EOFError:
        return None


def _print_next(lines: list[str]) -> None:
    for x in lines:
        print(f"  {x}")


def _start(a) -> int:
    import sys

    from . import choices as ch
    st = ch.start_state(a.brand)
    if a.json:
        print(json.dumps(st, ensure_ascii=False, indent=1))
        return 0
    if st["state"] != "ready":
        print({"new": "No saved brand identity. To begin:",
               "needs_identity": f"{st.get('brand')}: no brand identity yet:",
               "needs_setup": f"{st.get('brand')}: setup incomplete ({', '.join(st.get('missing', []))}):"
               }[st["state"]])
        _print_next(st["next"])
        return 2
    print(f"Saved brand identity: {st['brand']} · {st['identity_at'] or 'no date'} · "
          f"tempo {st['tempo']}")
    print("\n".join(ch.summary_lines(st["choices"])))
    choice = a.choice
    if not choice and sys.stdin.isatty():
        for n, o in enumerate(st["options"], 1):
            print(f"  {n}. {o['label']}")
        raw = _prompt("[1-2, Enter = 1] ")
        choice = None if raw is None else ("new" if raw.strip() == "2" else "same")
    if not choice:
        for o in st["options"]:
            print(f"{o['value']}: {o['label']}")
            _print_next(o["next"])
        return 0
    picked = next(o for o in st["options"] if o["value"] == choice)
    print(picked["label"] + ":")
    _print_next(picked["next"])
    return 0


def _show_catalog(a) -> int:
    import webbrowser

    from . import catalog as cl
    from .choices import brand_dir
    b = brand_mod.load(a.brand) if a.brand else None
    lang = b.language if b else "en"
    if a.json:
        print(json.dumps(cl.to_json(lang), ensure_ascii=False, indent=1))
        return 0
    for g in cl.to_json(lang):
        print(f"\n## {g['title']}  ({g['ask']})\n   {g['sheet']}")
        for o in g["options"]:
            print(f"  {o['number']:>4}  {o['label']}")
    out = Path(a.output) if a.output else (brand_dir(b) if b else Path(".")) / "catalog.html"
    page = cl.write_html(out, b.name if b else "<brand>", lang)
    print(f"\n0 = decide everything from my brand identity\nPage → {page}")
    print('Choose → lionstone reels setup "<brand>" --pick 101 205 503')
    if a.open:
        webbrowser.open(page.resolve().as_uri())
    return 0


def _identity(a) -> int:
    from .identity import analyze, identity_dir
    b = brand_mod.load(a.brand)
    i = analyze(b, Path(a.footage), [Path(x) for x in a.example], asr=not a.no_asr, model=a.model)
    st = i["style"]
    print(f"Tempo {st['tempo']} · {st['cuts_per_minute']} cuts/min · pauses "
          f"{st['pause_ratio'] * 100:.0f}% · palette {', '.join(i['palette']) or '-'}")
    for s in i["skipped"]:
        print(f"  not measured: {s}")
    print(f"Identity → {identity_dir(b) / 'identity.md'}\nNext → lionstone reels setup \"{a.brand}\"")
    return 0


def _setup(a) -> int:
    import sys

    from . import choices as ch
    b = brand_mod.load(a.brand)
    if a.questions:
        print(json.dumps(ch.questions(b.language), ensure_ascii=False, indent=1))
        return 0
    if a.show:
        chosen = ch.load_choices(b)
        print("\n".join(ch.summary_lines(chosen)) or "no choices yet")
        left = ch.missing(chosen)
        print(f"missing: {', '.join(left)}" if left else "✅ setup complete")
        return 0 if not left else 2
    answers = {q["id"]: ch.AUTO for q in ch.QUESTIONS} if a.auto else {}
    if a.pick:
        from .catalog import parse_picks
        answers.update(parse_picks(a.pick))
    for item in a.set:
        if "=" not in item:
            raise ValueError(f"--set must be QUESTION=VALUE: {item}")
        qid, value = item.split("=", 1)
        answers[qid.strip()] = value.strip()
    if not answers:
        if not sys.stdin.isatty():
            print("Catalogue: lionstone reels catalog --open · answer with --pick NO NO … or --auto")
            return 2
        from .catalog import write_html
        page = write_html(ch.brand_dir(b) / "catalog.html", b.name, b.language)
        print(f"Visual catalogue → {page}")
        answers = ch.ask(b)
    chosen = ch.resolve(b, answers)
    print(f"Choices → {ch.save_choices(b, chosen)}")
    print("\n".join(ch.summary_lines(chosen)))
    left = ch.missing(chosen)
    if left:
        print(f"missing: {', '.join(left)}")
        return 2
    print("✅ setup complete → lionstone reels new / make")
    return 0


def _identity_gate(b, choice: str | None) -> int | None:
    """On later Reels: same identity, or a new one? Returns an exit code to stop with."""
    import sys

    from . import choices as ch
    st = ch.start_state(b.name)
    if st["state"] != "ready":
        return None
    if not choice and sys.stdin.isatty():
        print(f"Saved brand identity: {b.name} · {st['identity_at'] or 'no date'}")
        for n, o in enumerate(st["options"], 1):
            print(f"  {n}. {o['label']}")
        raw = _prompt("[1-2, Enter = 1] ")
        choice = "new" if raw is not None and raw.strip() == "2" else "same"
    if choice == "new":
        print(st["options"][1]["label"] + ":")
        _print_next(st["options"][1]["next"])
        return 3
    print(f"🧠 Producing with the saved brand identity: {b.name} · {st['identity_at'] or 'no date'}")
    return None


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
            raise ValueError("a reel folder, or --brand + --video, is required")
        b = brand_mod.load(a.brand)
    stop = _identity_gate(b, a.identity)
    if stop is not None:
        return stop
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
    if cmd == "start":
        return _start(a)
    if cmd == "catalog":
        return _show_catalog(a)
    if cmd == "identity":
        return _identity(a)
    if cmd == "setup":
        return _setup(a)
    if cmd == "new":
        b = brand_mod.load(a.brand)
        p = new_reel(b, a.topic)
        print(f"Reel → {p}\nPut the footage here → {p.parent / RAW_DIR}")
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
        icon = {"error": "🔴", "warning": "🟠", "info": "🔵"}
        for f in fs:
            print(f"{icon[f.level]} {f.field}: {f.message}")
        errors = sum(f.level == "error" for f in fs)
        print("✅ copy ready" if not fs else f"{errors} error(s), {len(fs) - errors} note(s)")
        return 1 if errors else 0
    if cmd == "make":
        return _make(a)
    if cmd == "room":
        from ..models import EditPlan
        from .room import write_room
        plan = EditPlan.load(a.plan)
        out = Path(a.output or Path(a.plan).parent / "room.html")
        print(f"Editing room → {write_room(plan, out)}  (open it in a browser)")
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
        print(f"{stats} → lionstone reels make <reel folder> --keep-plan")
        return 0
    if cmd == "cover":
        from .visual import cover_frames, make_cover
        b = brand_mod.load(a.brand)
        for k, at in enumerate(cover_frames(Path(a.video), a.n)):
            c = make_cover(Path(a.video), Path(a.out) / f"cover-{k + 1}.jpg",
                           a.text[k % len(a.text)], at=at, colors=b.colors, font=b.font,
                           language=b.language)
            print(f"{c['file']}  @{at}s  {c['font_size']}px")
        return 0
    if cmd == "sfx":
        from . import sound
        if a.action == "build":
            files = sound.build_pack(force=a.force)
            print(f"{len(files)} effects → {sound.sfx_dir()}")
        lib = sound.library()
        cats: dict[str, int] = {}
        for k in lib:
            cats[k.split("/")[0]] = cats.get(k.split("/")[0], 0) + 1
        print(f"{len(lib)} sounds: " + ", ".join(f"{k} {v}" for k, v in sorted(cats.items())))
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
            r.status = normalize_status(a.status)
        r.save(folder / "reel.json")
        print(f"{r.topic}: {r.status} · {r.publish_at or 'no date'}")
        return 0
    if cmd == "calendar":
        from .calendar import entries, write_ics
        items = entries(brand_slug=brand_mod.slug(a.brand) if a.brand else None)
        for _folder, r in items:
            print(f"{(r.publish_at or '—').replace('T', ' '):16}  {r.status:8}  "
                  f"[{r.brand}] {r.topic}")
        if a.ics:
            write_ics(a.ics, items)
            print(f"Calendar → {a.ics}")
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
        print("\n🤖 Lionstone checks this automatically · 👀 a person looks")
        return 0
    return 1


def register(reg) -> None:
    reg.add_command("reels", "brand-specific Reels: topic → hook → script → edit → QA → calendar",
                    _cfg, _run)

