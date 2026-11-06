"""What Lionstone asks before the first Reel: effects, style, music and the rest.

Every question offers real Lionstone options plus "auto": decide from the brand identity.
Answers live in ``brands/<slug>/choices.json`` with who decided and why, and are written into
the brand's ``style``, which is what ``lionstone reels make`` follows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import memory
from .brand import HEX, Brand, home, save
from .identity import load_identity

AUTO = "auto"
AUTO_LABEL = {"tr": "Marka kimliğime göre sen belirle", "en": "Decide for me from my brand identity"}
# one effect window: chart panels need the user's own numbers, so insight-split is not offered
HOOK_FX = ("stage-light", "press-mono", "frost-panels", "duotone-pop", "scan-line", "afterimage",
           "halo-orbit", "neon-outline", "pixel-resolve")
WHOLE_FX = ("brand-frame", "progress-rail")
AGENT_STYLES = ("minimal", "social", "energetic", "cinematic", "documentary")
MUSIC_LEVELS = {"low": 0.10, "medium": 0.18, "high": 0.28}


def _q(id_: str, tr: str, en: str, options: list[tuple[str, str, str]]) -> dict[str, Any]:
    return {"id": id_, "tr": tr, "en": en,
            "options": [{"value": v, "tr": t, "en": e} for v, t, e in options]}


QUESTIONS: list[dict[str, Any]] = [
    _q("opening", "Kanca yazısı nasıl gelsin?", "How should the hook title appear?", [
        ("T02", "Satır satır (dikeye uygun)", "Line by line (fits vertical)"),
        ("T01", "Kelime kelime patlayarak", "Word pop, one word at a time"),
        ("P05", "Kelimeler sırayla gelsin", "Words land one after another"),
        ("none", "Kanca yazısı olmasın", "No hook title"),
        ("L01", "Editoryal: kademeli satırlar, iri italik serif", "Editorial: staggered lines, large italic serif"),
        ("L02", "Parlayan büyük başlık", "Glowing heavy headline")]),
    _q("captions", "Altyazı stili?", "Caption style?", [
        ("karaoke", "Karaoke: konuşulan kelime vurgulu", "Karaoke: the spoken word is highlighted"),
        ("social", "Büyük sosyal medya altyazısı", "Large social captions"),
        ("bold", "Kutulu, kalın", "Bold on a box"),
        ("clean", "Sade", "Clean"),
        ("none", "Altyazı yok", "No captions"),
        ("editorial", "Editoryal: ince yazı, anahtar kelime iri italik", "Editorial: quiet text, key word in large italic"),
        ("keyword-pop", "Kalın yazı, anahtar kelime parlayan renkli", "Heavy text, key word glowing in colour")]),
    _q("grade", "Renk görünümü?", "Colour look?", [
        ("learned", "Örnek Reel'lerimden öğren", "Learn it from my example Reels"),
        ("punchy", "Canlı", "Punchy"), ("natural", "Doğal", "Natural"),
        ("warm", "Sıcak", "Warm"), ("cool", "Soğuk", "Cool"), ("film", "Film", "Film"),
        ("none", "Dokunma", "Untouched")]),
    _q("pace", "Kurgu temposu?", "Editing pace?", [
        ("dynamic", "Sıkı: kısa duraklar", "Tight: short pauses"),
        ("balanced", "Dengeli", "Balanced"),
        ("natural", "Rahat: doğal duraklar", "Relaxed: natural pauses")]),
    _q("effects", "Efektler?", "Effects?", [
        ("none", "Efekt yok", "No effects"),
        *[(f"agent:{s}", f"Lionstone Agent, {s} tarzı", f"Lionstone Agent, {s} style")
          for s in AGENT_STYLES],
        *[(f"fx:{x}", f"Açılışta Reel FX: {x}", f"Reel FX on the opening: {x}") for x in HOOK_FX],
        *[(f"fx:{x}", f"Tüm video Reel FX: {x}", f"Reel FX on the whole video: {x}")
          for x in WHOLE_FX],
        ("look:editorial", "Editoryal görünüm: cam kart, neon etiket, geri sayım",
         "Editorial look: glass card, neon pills, countdown"),
        ("look:bold", "Güçlü görünüm: kesik çizgili kart, vurgu zoomları",
         "Bold look: dashed card, emphasis zooms"),
        ("look:glass", "Cam bildirim kartı (ikinci kanca)", "Glass notification card (second hook)"),
        ("look:pills", "Neon etiketler (anahtar kelimeler)", "Neon pills (key words)"),
        ("look:card", "Kesik çizgili kart (sayı ya da kelime)", "Dashed card (a number or word)"),
        ("look:countdown", "Geri sayım saati", "Countdown clock")]),
    _q("music", "Müzik?", "Music?", [
        ("none", "Müzik yok", "No music"),
        ("file:<path>", "Kendi lisanslı dosyam", "My own licensed file")]),
    _q("music_level", "Müzik seviyesi (konuşma altında kısılır)?",
       "Music level (it ducks under the voice)?", [
        ("low", "Düşük", "Low"), ("medium", "Orta", "Medium"), ("high", "Yüksek", "High")]),
    _q("sfx", "Ses efektleri?", "Sound effects?", [
        ("sparse", "Seyrek: açılış, grafikler, CTA", "Sparse: opening, graphics, CTA"),
        ("minimal", "Çok az: yalnızca açılış ve CTA", "Minimal: opening and CTA only"),
        ("off", "Kapalı", "Off")]),
    _q("framing", "Dikey kadraj?", "Vertical framing?", [
        ("center", "Ortadan kırp", "Centre crop"),
        ("face", "Yüzü takip et (lionstone[vision] gerekir)", "Follow the face (needs lionstone[vision])")]),
    _q("cleanup", "Gürültü temizliği?", "Noise cleanup?", [
        ("light", "Hafif", "Light"), ("strong", "Güçlü", "Strong"), ("off", "Kapalı", "Off")]),
    _q("covers", "Kaç kapak versiyonu?", "How many cover versions?", [
        ("1", "1 kapak", "1 cover"), ("2", "2 kapak", "2 covers"), ("3", "3 kapak", "3 covers"),
        ("4", "4 kapak", "4 covers")]),
    _q("colors", "Marka vurgu rengi?", "Brand accent colour?", [
        ("brand", "Profildeki renk kalsın", "Keep the colour in my profile"),
        ("examples", "Örnek Reel'lerden al", "Take it from my example Reels"),
        ("#6B2A5E", "Koyu erik", "Deep plum"), ("#FFD60A", "Parlak sarı", "Signal yellow")]),
]
BY_ID = {q["id"]: q for q in QUESTIONS}


def questions(language: str = "tr") -> list[dict[str, Any]]:
    """The questions in the brand's language, with the "decide for me" option on each."""
    lang = "tr" if language == "tr" else "en"
    return [{"id": q["id"], "question": q[lang],
             "options": [{"value": o["value"], "label": o[lang]} for o in q["options"]]
             + [{"value": AUTO, "label": AUTO_LABEL[lang]}]} for q in QUESTIONS]


def validate(qid: str, value: str) -> str:
    if qid not in BY_ID:
        raise ValueError(f"bilinmeyen soru: {qid} (geçerli: {', '.join(BY_ID)})")
    if value == AUTO:
        return value
    if qid == "music" and value.startswith("file:"):
        path = value[5:]
        if not Path(path).is_file():
            raise FileNotFoundError(f"müzik dosyası yok: {path}")
        return value
    if qid == "colors" and value.startswith("#"):
        if not HEX.match(value):
            raise ValueError(f"renk #RRGGBB olmalı: {value}")
        return value
    if qid == "effects" and value.startswith("fx:"):
        return value  # any usable catalog preset; checked against the catalog when applied
    if qid == "framing" and value == "face" and not _face_tracking_available():
        raise ValueError('yüz takibi için: pip install "lionstone[vision]"')
    allowed = [o["value"] for o in BY_ID[qid]["options"]]
    if value not in allowed:
        raise ValueError(f"{qid} için geçersiz değer: {value} (geçerli: {', '.join(allowed)}, auto)")
    return value


# --- "decide for me" -------------------------------------------------------------------
def _face_tracking_available() -> bool:
    try:
        import cv2  # type: ignore  # noqa: F401
    except ImportError:
        return False
    return True


def decide(qid: str, identity: dict[str, Any], brand: Brand) -> tuple[str, str]:
    """(value, reason), from measurements only. Every rule states what it looked at."""
    st = identity["style"]
    tempo = st["tempo"]
    cuts = st["cuts_per_minute"]
    music_n = identity["music_in_examples"]
    n = len(identity["examples"])
    if qid == "opening":
        return "T02", f"{tempo} examples: a title that wraps for vertical and stays readable"
    if qid == "captions":
        return (("clean", "slow examples: captions that stay out of the way") if tempo == "slow"
                else ("karaoke", f"{tempo} examples: word-by-word captions hold attention"))
    if qid == "grade":
        return (("learned", "colour measured from your examples") if st["color_filter"]
                else ("natural", "no colour could be measured from the examples"))
    if qid == "pace":
        return st["intensity"], (f"examples: {st['pause_ratio'] * 100:.0f}% pauses, "
                                 f"{tempo} tempo")
    if qid == "effects":
        if cuts >= 30 and st["saturation"] >= 0.3:
            return "agent:energetic", f"{cuts} cuts/min and saturated colour in the examples"
        if tempo == "slow":
            return "agent:minimal", f"slow examples, {cuts} cuts/min: effects stay quiet"
        return "agent:social", f"{tempo} examples, {cuts} cuts/min"
    if qid == "music":
        current = brand.style.get("music") or ""
        if current:
            return f"file:{current}", "keeping the music file already in your profile"
        return "none", (f"{music_n} of {n} examples seem to have music, but Lionstone ships no "
                        "music: add your own licensed file to use it" if music_n else
                        f"no music detected in your {n} examples")
    if qid == "music_level":
        return "medium", "the default bed under the voice"
    if qid == "sfx":
        return (("minimal", "slow examples: fewer sounds") if tempo == "slow"
                else ("sparse", f"{tempo} examples: sound on the opening, graphics and CTA"))
    if qid == "framing":
        if identity["footage"]["vertical"]:
            return "center", "your take is already vertical"
        if _face_tracking_available():
            return "face", "your take is not vertical and face tracking is installed"
        return "center", ("your take is not vertical; install lionstone[vision] "
                          "to follow the face")
    if qid == "cleanup":
        return "light", "the default: removes room noise without touching the voice"
    if qid == "covers":
        return "3", "three versions to compare"
    if qid == "colors":
        if identity["palette"]:
            return "examples", f"most common saturated colour in the examples: {identity['palette'][0]}"
        return "brand", "no strong colour in the examples"
    raise ValueError(qid)


# --- storage ---------------------------------------------------------------------------
def brand_dir(brand: Brand, root: Path | None = None) -> Path:
    return home(brand, root) / brand.slug


def choices_path(brand: Brand, root: Path | None = None) -> Path:
    return home(brand, root) / brand.slug / "choices.json"


def load_choices(brand: Brand, root: Path | None = None) -> dict[str, dict[str, str]]:
    p = choices_path(brand, root)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def missing(chosen: dict[str, Any]) -> list[str]:
    return [q["id"] for q in QUESTIONS if q["id"] not in chosen]


def resolve(brand: Brand, answers: dict[str, str], root: Path | None = None
            ) -> dict[str, dict[str, str]]:
    """Merge new answers into the saved ones; "auto" becomes a value with its reason."""
    identity = load_identity(brand, root)
    chosen = load_choices(brand, root)
    for qid, value in answers.items():
        value = validate(qid, value)
        if value == AUTO:
            if not identity:
                raise ValueError("'auto' için marka kimliği gerekli: önce `lionstone reels "
                                 "identity` çalıştır")
            val, why = decide(qid, identity, brand)
            chosen[qid] = {"value": val, "by": "auto", "reason": why}
        else:
            chosen[qid] = {"value": value, "by": "user", "reason": ""}
    return chosen


def apply_to_brand(brand: Brand, chosen: dict[str, dict[str, str]],
                   root: Path | None = None) -> Brand:
    """Write the decisions into the brand profile and the identity's measured facts with them."""
    st = brand.style
    get = lambda k: chosen[k]["value"] if k in chosen else None  # noqa: E731
    if get("opening") is not None:
        st["hook_title"] = get("opening") != "none"
        if st["hook_title"]:
            st["title_effect"] = get("opening")
    if get("captions") is not None:
        st["caption_style"] = get("captions")
    if get("grade") is not None:
        st["color"] = get("grade")
    if get("pace") is not None:
        st["intensity"] = get("pace")
    if get("effects") is not None:
        st["effects"] = get("effects")
    if get("music") is not None:
        st["music"] = get("music")[5:] if get("music").startswith("file:") else ""
    if get("music_level") is not None:
        st["music_volume"] = MUSIC_LEVELS[get("music_level")]
    if get("sfx") is not None:
        st["sfx"] = get("sfx") != "off"
        st["sfx_density"] = get("sfx") if get("sfx") != "off" else "sparse"
    if get("framing") is not None:
        st["reframe"] = get("framing")
    if get("cleanup") is not None:
        st["denoise"] = get("cleanup")
    if get("covers") is not None:
        st["covers"] = int(get("covers"))
    if (get("colors") or "").startswith("#"):
        brand.colors["accent"] = get("colors")
    identity = load_identity(brand, root)
    if identity:
        if get("colors") == "examples" and identity["palette"]:
            brand.colors["accent"] = identity["palette"][0]
        lo, hi = identity["target_seconds"]
        if 5 <= lo < hi <= 180:
            brand.target_seconds = (lo, hi)
        if identity.get("words_per_second"):
            st["words_per_second"] = identity["words_per_second"]
    return brand


def save_choices(brand: Brand, chosen: dict[str, dict[str, str]], root: Path | None = None) -> Path:
    apply_to_brand(brand, chosen, root)
    save(brand, root)
    p = choices_path(brand, root)
    p.write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")
    memory.remember(brand.slug, brand.name, home(brand, root), use=True,
                    setup_at="" if missing(chosen) else memory.now())
    return p


def ask(brand: Brand, input_fn=input, print_fn=print, root: Path | None = None) -> dict[str, str]:
    """Ask every question in the terminal, by catalogue number. Enter takes "decide for me"."""
    from .catalog import entries, sheet_path
    lang = "tr" if brand.language == "tr" else "en"
    answers: dict[str, str] = {}
    for q in QUESTIONS:
        opts = [e for e in entries() if e["question"] == q["id"]]
        print_fn(f"\n{q[lang]}\n  {sheet_path(q['id'])}")
        for o in opts:
            print_fn(f"  {o['number']:>4}  {o[lang]}")
        by_number = {str(o["number"]): o["value"] for o in opts}
        while True:
            raw = input_fn(f"[Enter = {opts[0]['number']}] ").strip()
            pick = opts[0]["value"] if not raw else by_number.get(raw)
            if pick is None:
                continue
            if pick == "file:<path>":
                pick = "file:" + input_fn("Müzik dosyası / Music file: ").strip().strip('"')
            try:
                answers[q["id"]] = validate(q["id"], pick)
                break
            except (ValueError, FileNotFoundError) as e:
                print_fn(f"  ! {e}")
    return answers


SAME_LABEL = {"tr": "Aynı marka kimliğimle üret", "en": "Produce with my saved brand identity"}
NEW_LABEL = {"tr": "Yeni marka kimliği ile hazırla", "en": "Prepare with a new brand identity"}


def start_state(name: str | None = None) -> dict[str, Any]:
    """Where this user stands: what is remembered and what the next choice is."""
    from .brand import load, slug
    known = memory.entries()
    target = slug(name) if name else memory.last_used()
    if not target or (target not in known and not name):
        return {"state": "new", "brands": [e["name"] for e in known.values()],
                "next": ['lionstone reels brand init "<brand>"',
                         'lionstone reels identity "<brand>" --footage talk.mp4 --example a.mp4 '
                         "--example b.mp4 --example c.mp4",
                         'lionstone reels setup "<brand>"']}
    brand = load(name or known[target]["name"])
    q = f'"{brand.name}"'
    lang = "tr" if brand.language == "tr" else "en"
    identity = load_identity(brand)
    chosen = load_choices(brand)
    base = {"brand": brand.name, "language": brand.language,
            "brands": [e["name"] for e in known.values()]}
    if not identity:
        return {**base, "state": "needs_identity", "next": [
            f"lionstone reels identity {q} --footage talk.mp4 --example a.mp4 "
            "--example b.mp4 --example c.mp4"]}
    if missing(chosen):
        return {**base, "state": "needs_setup", "missing": missing(chosen),
                "next": [f"lionstone reels setup {q}"]}
    entry = known.get(brand.slug, {})
    return {**base, "state": "ready", "identity_at": entry.get("identity_at", ""),
            "setup_at": entry.get("setup_at", ""),
            "tempo": identity["style"]["tempo"], "choices": chosen,
            "options": [
                {"value": "same", "label": SAME_LABEL[lang],
                 "next": [f'lionstone reels new {q} "<topic>"', "lionstone reels make <reel>"]},
                {"value": "new", "label": NEW_LABEL[lang], "next": [
                    f"lionstone reels identity {q} --footage talk.mp4 --example a.mp4 "
                    "--example b.mp4 --example c.mp4",
                    f"lionstone reels setup {q}"]}]}


def summary_lines(chosen: dict[str, dict[str, str]]) -> list[str]:
    return [f"- {qid}: `{c['value']}`" + (f" (auto: {c['reason']})" if c["by"] == "auto" else "")
            for qid, c in chosen.items()]
