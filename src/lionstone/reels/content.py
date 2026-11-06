"""Reel brief: topic → hooks → script → caption, and the checks that keep them honest.

Claude writes the creative parts (topic, why it will work, hooks, script, caption)
into ``reel.json``; this module scaffolds the file, offers hook templates from the
library and lints what was written. Nothing here invents copy on its own.
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from .brand import Brand, slug

WORDS_PER_SECOND = {"tr": 2.5, "en": 2.7}  # relaxed speech on camera
HOOK_MAX_WORDS = 14
CAPTION_MAX = 2200  # Instagram caption limit
HASHTAG_MAX = 30  # Instagram hashtag limit
HASHTAG_SOFT = 5


@dataclass
class Reel:
    brand: str
    topic: str
    why: str = ""  # why this will work for this audience
    angle: str = ""
    hooks: list[str] = field(default_factory=list)  # first = main hook, others = A/B
    second_hook: str = ""
    script: str = ""
    cta: str = ""
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    cover_text: list[str] = field(default_factory=list)  # 1-3 cover variants
    footage: list[str] = field(default_factory=list)
    status: str = "fikir"  # fikir · script · çekim · kurgu · kontrol · hazır · yayında
    publish_at: str = ""  # ISO local datetime
    created: str = field(default_factory=lambda: dt.date.today().isoformat())
    meta: dict[str, Any] = field(default_factory=dict)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> Reel:
        p = Path(path)
        if p.is_dir():
            p = p / "reel.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


STATUSES = ("fikir", "script", "çekim", "kurgu", "kontrol", "hazır", "yayında")


def projects_dir(brand: Brand, root: Path | None = None) -> Path:
    return (root or Path("projects")) / brand.slug


def new_reel(brand: Brand, topic: str, root: Path | None = None) -> Path:
    folder = projects_dir(brand, root) / f"{dt.date.today().isoformat()}-{slug(topic)[:32]}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "ham").mkdir(exist_ok=True)
    r = Reel(brand=brand.name, topic=topic, cta=brand.cta, hashtags=list(brand.hashtags[:5]))
    return r.save(folder / "reel.json")


# --- hooks ---------------------------------------------------------------------------
HOOK_FILES = {"tr": "hooks.json", "en": "hooks.en.json"}
# same ten angles in both libraries: either name works with either language
ANGLE_PAIRS = {"merak": "curiosity", "hata": "mistake", "sonuc": "result", "karsit": "contrarian",
               "liste": "list", "hikaye": "story", "soru": "question", "gosterim": "demo",
               "uyari": "warning", "kolaylik": "ease"}
_ANGLE_NAMES = {**ANGLE_PAIRS, **{en: tr for tr, en in ANGLE_PAIRS.items()}}


def hook_language(language: str | None) -> str:
    """Libraries exist for Turkish and English; any other brand language gets English."""
    return language if language in HOOK_FILES else "en"


def hook_library(language: str = "tr") -> dict[str, Any]:
    name = HOOK_FILES[hook_language(language)]
    raw = resources.files("lionstone").joinpath(f"data/reels/{name}").read_text("utf-8")
    return json.loads(raw)


def fill(template: str, values: dict[str, str]) -> str:
    def rep(m: re.Match) -> str:
        return values.get(m.group(1)) or m.group(0)
    return re.sub(r"\{(\w+)\}", rep, template)


def hook_ideas(brand: Brand, topic: str, angles: list[str] | None = None,
               extra: dict[str, str] | None = None,
               language: str | None = None) -> dict[str, list[str]]:
    """Templates filled with what we know; unknown slots stay visible as {slot}.
    ``language`` picks the library (default: the brand's language)."""
    lang = hook_language(language or brand.language)
    lib = hook_library(lang)
    product = brand.products[0] if brand.products else ""
    promise = brand.promises[0] if brand.promises else ""
    pain = brand.pains[0] if brand.pains else ""
    values = {"konu": topic, "kitle": brand.audience, "marka": brand.name,
              "hesap": brand.handle, "anahtar": brand.cta_keyword,
              "ürün": product, "sonuç": promise, "hata": pain,
              "topic": topic, "audience": brand.audience, "brand": brand.name,
              "handle": brand.handle, "keyword": brand.cta_keyword,
              "product": product, "result": promise, "mistake": pain, **(extra or {})}
    known = {a: a if a in lib["angles"] else _ANGLE_NAMES.get(a) for a in
             (angles or brand.hook_angles or list(lib["angles"]))}
    unknown = [a for a, name in known.items() if name not in lib["angles"]]
    if angles and unknown:
        raise ValueError(f"bilinmeyen açı: {', '.join(unknown)} (geçerli: "
                         f"{', '.join(lib['angles'])})")
    out = {}
    for name in known.values():
        if name in lib["angles"]:
            out[name] = [fill(t, values) for t in lib["angles"][name]["templates"]]
    second = "second_hook" if lang == "en" else "ikinci_kanca"
    out[second] = [fill(t, values) for t in lib["second_hook"]["templates"]]
    out["cta"] = [fill(t, values) for t in lib["cta"]["templates"]]
    return out


# --- lint -----------------------------------------------------------------------------
def tr_lower(s: str) -> str:
    return unicodedata.normalize("NFC", s).replace("I", "ı").replace("İ", "i").lower()


def tr_upper(s: str) -> str:
    """Turkish capitals: i → İ, ı → I (Python's str.upper maps both to I)."""
    return s.replace("i", "İ").replace("ı", "I").upper()


def tokens(text: str) -> list[str]:
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text)  # stage directions [B-roll] (gülümse)
    return [t for t in (re.sub(r"[^\wçğıöşü'-]", "", w) for w in tr_lower(text).split()) if t]


def speak_seconds(text: str, language: str = "tr") -> float:
    return len(tokens(text)) / WORDS_PER_SECOND.get(language, WORDS_PER_SECOND["en"])


@dataclass
class Finding:
    level: str  # hata | uyarı | bilgi
    field: str
    message: str


def lint(reel: Reel, brand: Brand) -> list[Finding]:
    f: list[Finding] = []
    add = lambda lvl, fld, msg: f.append(Finding(lvl, fld, msg))
    if not reel.why:
        add("uyarı", "why", "konunun neden tutacağı yazılmamış")
    if not reel.hooks:
        add("hata", "hooks", "kanca yok")
    for i, h in enumerate(reel.hooks):
        n = len(tokens(h))
        if n > HOOK_MAX_WORDS:
            add("uyarı", f"hooks[{i}]", f"{n} kelime; ilk 2 saniyede okunmaz (≤{HOOK_MAX_WORDS})")
        if "{" in h:
            add("hata", f"hooks[{i}]", "doldurulmamış şablon alanı var")
    if len(reel.hooks) < 2:
        add("bilgi", "hooks", "A/B için en az 2 farklı açıdan kanca önerilir")
    if not reel.second_hook:
        add("uyarı", "second_hook", "ikinci kanca yok (3-6. saniye tutma)")
    if not reel.script:
        add("hata", "script", "script yok")
    else:
        secs = speak_seconds(reel.script, brand.language)
        measured = brand.style.get("words_per_second")
        if measured:  # the speaker's own rate from `reels identity`
            secs = len(tokens(reel.script)) / float(measured)
        lo, hi = brand.target_seconds
        if not lo * 0.8 <= secs <= hi * 1.15:
            add("uyarı", "script", f"tahmini süre {secs:.0f} sn; hedef {lo:.0f}–{hi:.0f} sn")
        first = reel.script.strip().splitlines()[0] if reel.script.strip() else ""
        if reel.hooks and tokens(reel.hooks[0])[:3] != tokens(first)[:3]:
            add("bilgi", "script", "script ana kancayla başlamıyor")
        last = tokens(reel.script.strip().splitlines()[-1])
        cta = tokens(reel.cta or brand.cta)
        if cta and not set(cta[:4]) & set(last):
            add("uyarı", "script", "script çağrıyla (CTA) bitmiyor")
    text_all = " ".join([*reel.hooks, reel.second_hook, reel.script, reel.caption])
    low = tr_lower(text_all)
    for w in brand.banned_words:
        if w and tr_lower(w) in low:
            add("hata", "marka", f"yasaklı ifade kullanılmış: {w!r}")
    if len(reel.caption) > CAPTION_MAX:
        add("hata", "caption", f"{len(reel.caption)} karakter (Instagram sınırı {CAPTION_MAX})")
    tags = [t for t in reel.hashtags if t] + re.findall(r"#\w+", reel.caption)
    if len(set(tags)) > HASHTAG_MAX:
        add("hata", "hashtags", f"{len(set(tags))} hashtag (sınır {HASHTAG_MAX})")
    elif len(set(tags)) > HASHTAG_SOFT:
        add("bilgi", "hashtags", f"{len(set(tags))} hashtag; 3-5 odaklı etiket genelde yeter")
    if not reel.cover_text:
        add("uyarı", "cover_text", "kapak yazısı yok")
    return f


# --- script ↔ final audio -------------------------------------------------------------
@dataclass
class ScriptDiff:
    ratio: float
    missing: list[str]  # in the script, not heard in the video
    extra: list[str]  # heard, not in the script
    changed: list[tuple[str, str]]
    script_words: int
    heard_words: int


def compare_script(script: str, heard: str) -> ScriptDiff:
    a, b = tokens(script), tokens(heard)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    missing, extra, changed = [], [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "delete":
            missing.append(" ".join(a[i1:i2]))
        elif op == "insert":
            extra.append(" ".join(b[j1:j2]))
        elif op == "replace":
            changed.append((" ".join(a[i1:i2]), " ".join(b[j1:j2])))
    return ScriptDiff(round(sm.ratio(), 3), missing, extra, changed, len(a), len(b))
