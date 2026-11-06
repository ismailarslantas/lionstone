"""The visual catalogue: every option has a number and a picture, so choices are made by looking.

Numbers follow the questions: the first question is 1xx, the second 2xx, and so on. ``x00`` is
"decide for me" for that question and ``0`` is "decide everything for me". Pictures are real
Lionstone renders on one fictional example character (``scripts/build_reels_catalog.py``), so what
you see is what that option does.
"""

from __future__ import annotations

import html
import json
from importlib import resources
from pathlib import Path
from typing import Any

from .choices import AUTO, AUTO_LABEL, QUESTIONS

ALL_AUTO = 0
GROUP_TITLES = {
    "opening": ("Kanca yazısı", "Hook title"), "captions": ("Altyazı", "Captions"),
    "grade": ("Renk", "Colour"), "pace": ("Tempo", "Pace"), "effects": ("Efektler", "Effects"),
    "music": ("Müzik", "Music"), "music_level": ("Müzik seviyesi", "Music level"),
    "sfx": ("Ses efektleri", "Sound effects"), "framing": ("Kadraj", "Framing"),
    "cleanup": ("Gürültü temizliği", "Noise cleanup"), "covers": ("Kapak", "Covers"),
    "colors": ("Vurgu rengi", "Accent colour")}


def entries() -> list[dict[str, Any]]:
    """Every option with its number. Adding an option at the end of a question keeps the rest."""
    out = []
    for i, q in enumerate(QUESTIONS, 1):
        base = i * 100
        out.append({"number": base, "question": q["id"], "value": AUTO,
                    "tr": AUTO_LABEL["tr"], "en": AUTO_LABEL["en"]})
        for k, o in enumerate(q["options"], 1):
            out.append({"number": base + k, "question": q["id"], "value": o["value"],
                        "tr": o["tr"], "en": o["en"]})
    return out


def number_of(question: str, value: str) -> int:
    return next(e["number"] for e in entries() if e["question"] == question and e["value"] == value)


def parse_picks(picks: list[str]) -> dict[str, str]:
    """``["101", "205", "602=track.mp3", "0"]`` → answers. One number per question."""
    by_number = {e["number"]: e for e in entries()}
    answers: dict[str, str] = {}
    all_auto = False
    for raw in picks:
        for item in raw.replace(",", " ").split():
            num, _, extra = item.partition("=")
            if not num.isdigit():
                raise ValueError(f"not a catalogue number: {item}")
            n = int(num)
            if n == ALL_AUTO:
                all_auto = True
                continue
            if n not in by_number:
                raise ValueError(f"no such number in the catalogue: {n} (`lionstone reels catalog`)")
            e = by_number[n]
            if e["question"] in answers:
                raise ValueError(f"two numbers given for {e['question']}: {n}")
            value = e["value"]
            if value == "file:<path>":
                if not extra:
                    raise ValueError(f"{n} needs a file: {n}=track.mp3")
                value = f"file:{extra}"
            answers[e["question"]] = value
    if all_auto:
        answers = {**{q["id"]: AUTO for q in QUESTIONS}, **answers}
    return answers


def _root():
    return resources.files("lionstone").joinpath("data/reels/catalog")


def image_path(number: int) -> Path:
    return Path(str(_root().joinpath(f"{number}.jpg")))


def sheet_path(question: str) -> Path:
    return Path(str(_root().joinpath(f"sheets/{question}.jpg")))


def to_json(language: str = "tr") -> list[dict[str, Any]]:
    lang = "tr" if language == "tr" else "en"
    return [{"question": q["id"], "title": GROUP_TITLES[q["id"]][0 if lang == "tr" else 1],
             "ask": q[lang], "sheet": str(sheet_path(q["id"])),
             "options": [{"number": e["number"], "value": e["value"], "label": e[lang],
                          "image": str(image_path(e["number"]))}
                         for e in entries() if e["question"] == q["id"]]} for q in QUESTIONS]


def write_html(out: Path, brand_name: str = "<brand>", language: str = "tr") -> Path:
    """A local page: look, click one card per group, copy the ready-made command."""
    lang = "tr" if language == "tr" else "en"
    tr = lang == "tr"
    groups = []
    for g in to_json(lang):
        cards = "".join(
            f'<button class="card" data-q="{html.escape(g["question"])}" data-n="{o["number"]}" '
            f'data-file="{"1" if o["value"] == "file:<path>" else ""}">'
            f'<img loading="lazy" src="{image_path(o["number"]).resolve().as_uri()}" alt="">'
            f'<b>{o["number"]}</b><span>{html.escape(o["label"])}</span></button>'
            for o in g["options"])
        groups.append(f'<section><h2>{html.escape(g["title"])}</h2><p>{html.escape(g["ask"])}</p>'
                      f'<div class="grid">{cards}</div></section>')
    page = PAGE.replace("__TITLE__", "Lionstone Reels · " + ("katalog" if tr else "catalogue")) \
        .replace("__INTRO__", html.escape(
            "Her gruptan bir kart seç ya da numaraları elle yaz. Görsellerdeki kurgusal erkek karakter "
            "yalnızca örnektir; Reel'in senin kendi çekiminle üretilir. Kararsızsan her grubun ilk "
            "kartı ya da 0: marka kimliğine göre Lionstone belirler." if tr else
            "Pick one card per group, or type the numbers yourself. The fictional man in the pictures "
            "is only an example: your Reel is made from your own footage. Not sure? The first card in "
            "each group, or 0, lets Lionstone decide from your brand identity.")) \
        .replace("__AUTOALL__", html.escape("0 · " + AUTO_LABEL[lang])) \
        .replace("__COPY__", "Kopyala" if tr else "Copy") \
        .replace("__BRAND__", json.dumps(brand_name, ensure_ascii=False)) \
        .replace("__GROUPS__", "".join(groups))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><style>
:root{--bg:#111114;--panel:#1b1b20;--ink:#f3f1ea;--mute:#a09f99;--acc:#E8B04B;--line:#2e2e35}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;padding:16px 16px 110px}
h1{margin:0 0 4px;font-size:22px}h2{margin:28px 0 2px;font-size:18px;color:var(--acc)}p{margin:0 0 12px;color:var(--mute)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.card{background:var(--panel);border:2px solid var(--line);border-radius:10px;padding:6px;color:inherit;font:inherit;text-align:left;cursor:pointer}
.card img{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:6px;display:block;background:#000}
.card b{display:block;margin-top:6px;color:var(--acc);font-size:17px}.card span{display:block;font-size:13px;color:var(--ink)}
.card.on{border-color:var(--acc)}.bar{position:fixed;left:0;right:0;bottom:0;background:#000;border-top:1px solid var(--line);padding:10px 16px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
code{flex:1;min-width:200px;font:13px ui-monospace,Consolas,monospace;word-break:break-all}.bar button{background:var(--acc);color:#111;border:0;border-radius:8px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}
#all{background:var(--panel);color:var(--ink);border:1px solid var(--line)}
</style></head><body><h1>__TITLE__</h1><p>__INTRO__</p>__GROUPS__
<div class="bar"><button id="all">__AUTOALL__</button><code id="cmd"></code><button id="copy">__COPY__</button></div>
<script>
const brand=__BRAND__,picked={};let all=false;const cmd=document.getElementById('cmd');
function draw(){const nums=[...(all?['0']:[]),...Object.values(picked)];cmd.textContent=`lionstone reels setup "${brand}" --pick ${nums.join(' ')}`;}
document.querySelectorAll('.card').forEach(c=>c.onclick=()=>{const q=c.dataset.q,on=c.classList.contains('on');
document.querySelectorAll(`.card[data-q="${q}"]`).forEach(x=>x.classList.remove('on'));
if(on){delete picked[q];}else{c.classList.add('on');picked[q]=c.dataset.n+(c.dataset.file?'=track.mp3':'');}draw();});
document.getElementById('all').onclick=e=>{all=!all;e.target.style.borderColor=all?'#E8B04B':'';draw();};
document.getElementById('copy').onclick=()=>navigator.clipboard.writeText(cmd.textContent);draw();
</script></body></html>
"""
