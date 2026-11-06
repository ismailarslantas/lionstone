"""Brand profile for Reels: who the brand talks to, how it sounds, how its videos look.

A brand lives in ``<brands dir>/<slug>/brand.json`` (default ``./brands``, or
``$LIONSTONE_BRANDS_DIR``). It is plain JSON so a team can share it through a
synced folder or a private repo. Visual identity can point at an existing
Lionstone brand kit (``lionstone brand create``) through ``kit``.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import memory

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def slug(s: str) -> str:
    table = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuoocc")
    s = re.sub(r"[^a-z0-9]+", "-", s.translate(table).lower())
    return s.strip("-")[:48] or "marka"


def brands_dir() -> Path:
    return Path(os.environ.get("LIONSTONE_BRANDS_DIR") or "brands")


@dataclass
class Brand:
    name: str
    handle: str = ""  # @instagram
    sector: str = ""
    audience: str = ""  # "İzmir'de ev arayan genç aileler"
    tone: str = "samimi, net, güven veren"
    language: str = "tr"
    products: list[str] = field(default_factory=list)
    promises: list[str] = field(default_factory=list)  # results the brand can honestly claim
    pains: list[str] = field(default_factory=list)  # audience mistakes / problems
    banned_words: list[str] = field(default_factory=list)
    hook_angles: list[str] = field(default_factory=lambda: ["merak", "hata", "sonuc"])
    cta: str = "Kaydet, lazım olacak."
    cta_keyword: str = ""  # ManyChat-style comment keyword
    hashtags: list[str] = field(default_factory=list)
    colors: dict[str, str] = field(default_factory=lambda: {
        "primary": "#111114", "accent": "#E8B04B", "text": "#FFFFFF"})
    font: str | None = None  # title / caption font file or fontconfig name
    kit: str | None = None  # name of a Lionstone brand kit to apply on top
    style: dict[str, Any] = field(default_factory=lambda: {
        "intensity": "dynamic", "caption_style": "karaoke", "color": "punchy",
        "title_effect": "T02", "music": "", "music_volume": 0.18, "sfx": True})
    target_seconds: tuple[float, float] = (20.0, 45.0)
    notes: str = ""

    @property
    def slug(self) -> str:
        return slug(self.name)

    @property
    def accent(self) -> str:
        return self.colors.get("accent", "#E8B04B")

    def validate(self) -> list[str]:
        out = []
        for k, c in self.colors.items():
            if not HEX.match(c or ""):
                out.append(f"renk {k}={c!r} #RRGGBB olmalı")
        if not self.audience:
            out.append("audience boş: konu ve hook yazımı kitleyi bilmeden yapılmaz")
        if self.handle and not self.handle.startswith("@"):
            out.append("handle @ ile başlamalı")
        lo, hi = self.target_seconds
        if not 5 <= lo < hi <= 180:
            out.append("target_seconds 5–180 sn aralığında ve küçükten büyüğe olmalı")
        return out

    # --- io ---------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["target_seconds"] = list(self.target_seconds)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Brand:
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        if "target_seconds" in known:
            known["target_seconds"] = tuple(known["target_seconds"])
        if "style" in known:
            known["style"] = {**_default_style(), **known["style"]}
        return cls(**known)


def _default_style() -> dict[str, Any]:
    return Brand(name="_").style


EN_DEFAULTS = {"tone": "friendly, clear, trustworthy", "cta": "Save this for later.",
               "hook_angles": ["curiosity", "mistake", "result"]}


def new_brand(name: str, language: str = "tr", **fields: Any) -> Brand:
    """A brand whose default tone, CTA and hook angles match its language."""
    defaults = {} if language == "tr" else EN_DEFAULTS
    return Brand(name=name, language=language, **{**defaults, **fields})


def path_for(name: str, root: Path | None = None) -> Path:
    return (root or brands_dir()) / slug(name) / "brand.json"


def home(b: Brand, root: Path | None = None) -> Path:
    """The brands folder this brand lives in; a loaded brand knows its own, from any cwd."""
    return Path(root or getattr(b, "root", None) or brands_dir())


def save(b: Brand, root: Path | None = None) -> Path:
    p = path_for(b.name, home(b, root))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(b.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    md = p.parent / "brand.md"
    if not md.exists():
        tmpl = BRAND_MD if b.language == "tr" else BRAND_MD_EN
        md.write_text(tmpl.format(name=b.name), encoding="utf-8")
    memory.remember(b.slug, b.name, home(b, root))
    return p


def load(name_or_path: str, root: Path | None = None) -> Brand:
    p = Path(name_or_path)
    if p.suffix == ".json" and p.exists():
        target = p
    elif p.is_dir() and (p / "brand.json").exists():
        target = p / "brand.json"
    else:
        target = path_for(name_or_path, root)
        remembered = memory.lookup(slug(name_or_path)) if not target.exists() and not root else None
        if remembered:  # made in another folder: found through the memory
            target = path_for(name_or_path, remembered)
    if not target.exists():
        raise FileNotFoundError(
            f"marka bulunamadı: {name_or_path!r} → `lionstone reels brand init \"{name_or_path}\"`")
    b = Brand.from_dict(json.loads(target.read_text(encoding="utf-8")))
    b.root = target.parent.parent.resolve()
    return b


def list_brands(root: Path | None = None) -> list[str]:
    r = root or brands_dir()
    here = {p.parent.name for p in r.glob("*/brand.json")} if r.exists() else set()
    return sorted(here if root else here | set(memory.entries()))


BRAND_MD_EN = """# {name}: brand notes

Claude reads this file when writing topics, hooks, scripts and captions. Write freely.

## Brand voice
- How we talk:
- What we never say:

## Products / services

## Audience and their problems

## Content that worked (link + why)

## Competitors and how we differ
"""

BRAND_MD = """# {name} — marka notları

Claude bu dosyayı konu, hook, script ve caption yazarken okur. Serbest yaz.

## Marka sesi
- Nasıl konuşuruz:
- Asla söylemeyiz:

## Ürünler / hizmetler

## Kitle ve sorunları

## Örnek tutmuş içerikler (link + neden tuttu)

## Rakipler ve farkımız
"""
