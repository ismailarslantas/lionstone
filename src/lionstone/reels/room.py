"""Editing room: one local HTML page — video + every word, click to jump, cut or fix.

``write_room`` produces ``room.html`` next to the plan (no server, no upload: the
video plays from disk). The page exports ``room-edits.json``; ``apply_edits``
turns it into cuts / restores / caption fixes on the plan, which you then render.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from ..models import Cut, EditPlan
from ..speech import segments_from_cuts


def room_words(plan: EditPlan) -> list[dict]:
    out = []
    for i, w in enumerate(plan.words):
        mid = (w.start + w.end) / 2
        out.append({"i": i, "t": w.text, "s": round(w.start, 3), "e": round(w.end, 3),
                    "cut": plan.source_to_output(mid) is None,
                    "c": round(w.confidence, 2)})
    return out


def write_room(plan: EditPlan, out: Path, title: str = "Düzenleme odası") -> Path:
    data = {"video": Path(plan.source).resolve().as_uri(), "words": room_words(plan),
            "duration": plan.duration,
            "cuts": [[round(c.start, 3), round(c.end, 3)] for c in plan.cuts if c.enabled]}
    page = ROOM_HTML.replace("__TITLE__", html.escape(title)).replace(
        "__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def _spans(idx: list[int], plan: EditPlan, pad: float = 0.02) -> list[tuple[float, float]]:
    """Runs of removed words, padded into the surrounding gaps but never into a neighbour."""
    runs: list[list[int]] = []
    for i in sorted(idx):
        if runs and runs[-1][1] == i - 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    words, out = plan.words, []
    for first, last in runs:
        lo = words[first - 1].end if first else 0.0
        hi = words[last + 1].start if last + 1 < len(words) else plan.duration
        out.append((max(lo, words[first].start - pad), min(hi, words[last].end + pad)))
    return out


def apply_edits(plan: EditPlan, edits: dict) -> dict:
    stats = {"removed": 0, "restored": 0, "text": 0}
    remove = [int(i) for i in edits.get("remove", []) if 0 <= int(i) < len(plan.words)]
    restore = [int(i) for i in edits.get("restore", []) if 0 <= int(i) < len(plan.words)]
    n = sum(1 for c in plan.cuts if c.kind == "manual")
    for a, b in _spans(remove, plan):
        plan.cuts.append(Cut(id=f"m{n:04d}", start=round(a, 3), end=round(b, 3), kind="manual",
                             reason="düzenleme odasında silindi"))
        n += 1
        stats["removed"] += 1
    for i in restore:
        w = plan.words[i]
        mid = (w.start + w.end) / 2
        for c in plan.cuts:
            if c.enabled and c.start <= mid <= c.end:
                c.enabled = False
                stats["restored"] += 1
    for k, v in (edits.get("text") or {}).items():
        i = int(k)
        if 0 <= i < len(plan.words) and v.strip():
            plan.words[i].text = v.strip()
            stats["text"] += 1
    plan.segments = segments_from_cuts(plan.cuts, plan.duration, plan.words)
    plan.meta.setdefault("reels", {})["room_edits"] = stats
    return stats


ROOM_HTML = r"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#0d0d0f;--panel:#16161a;--ink:#f3f1ea;--mute:#8b8a85;--acc:#E8B04B;--cut:#5a2a2a;--line:#2a2a30}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
header{display:flex;gap:12px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}
h1{font-size:15px;margin:0 auto 0 0;font-weight:600}
button{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:7px 12px;font:inherit;cursor:pointer}
button.on{border-color:var(--acc);color:var(--acc)}button.primary{background:var(--acc);color:#111;border-color:var(--acc);font-weight:600}
main{display:grid;grid-template-columns:minmax(240px,380px) 1fr;gap:16px;padding:16px}
@media(max-width:760px){main{grid-template-columns:1fr}}
video{width:100%;max-height:72vh;background:#000;border-radius:10px}
#words{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;max-height:78vh;overflow:auto;line-height:2}
.w{padding:2px 3px;border-radius:4px;cursor:pointer}.w:hover{background:#2b2b33}
.w.cut{text-decoration:line-through;color:var(--mute);background:var(--cut)}
.w.now{outline:2px solid var(--acc)}.w.low{border-bottom:2px dotted #c77}.w.edited{color:var(--acc)}
.help{color:var(--mute);font-size:13px;padding:0 16px 8px}
#stat{color:var(--mute);font-size:13px}
</style></head><body>
<header><h1>__TITLE__</h1><span id="stat"></span>
<button id="mode" title="Kesme modu: kelimeye tıklayınca keser / geri alır">✂︎ Kes modu</button>
<button id="preview" class="on" title="Kesilen yerleri atlayarak oynat">Önizleme: açık</button>
<button id="export" class="primary">Değişiklikleri indir</button></header>
<p class="help">Kelimeye tıkla → o ana git. Kes modunda tıkla → kes / geri al. Çift tıkla → altyazı yazımını düzelt. Noktalı alt çizgi: tanıma güveni düşük.</p>
<main><video id="v" controls playsinline preload="metadata"></video><div id="words"></div></main>
<script>
const D=__DATA__;const v=document.getElementById('v');v.src=D.video;
const box=document.getElementById('words');let cutMode=false,preview=true;
const orig=D.words.map(w=>w.cut);const text={};
D.words.forEach(w=>{const s=document.createElement('span');s.className='w'+(w.cut?' cut':'')+(w.c<0.6?' low':'');
s.textContent=w.t;s.dataset.i=w.i;box.appendChild(s);box.appendChild(document.createTextNode(' '));w.el=s;});
function stat(){const r=D.words.filter((w,i)=>w.cut&&!orig[i]).length,b=D.words.filter((w,i)=>!w.cut&&orig[i]).length;
document.getElementById('stat').textContent=`${r} kelime kesildi · ${b} geri alındı · ${Object.keys(text).length} düzeltme`;}
box.addEventListener('click',e=>{const el=e.target.closest('.w');if(!el)return;const w=D.words[el.dataset.i];
if(cutMode){w.cut=!w.cut;el.classList.toggle('cut',w.cut);stat();}else{v.currentTime=w.s;v.play();}});
box.addEventListener('dblclick',e=>{const el=e.target.closest('.w');if(!el)return;const w=D.words[el.dataset.i];
const t=prompt('Altyazıda görünecek yazım:',w.t);if(t&&t.trim()&&t!==w.t){w.t=t.trim();el.textContent=w.t;text[w.i]=w.t;el.classList.add('edited');stat();}});
document.getElementById('mode').onclick=e=>{cutMode=!cutMode;e.target.classList.toggle('on',cutMode);};
document.getElementById('preview').onclick=e=>{preview=!preview;e.target.classList.toggle('on',preview);e.target.textContent='Önizleme: '+(preview?'açık':'kapalı');};
const restored=()=>D.words.filter((w,i)=>!w.cut&&orig[i]);
let last=null;v.addEventListener('timeupdate',()=>{const t=v.currentTime;
if(preview){const c=D.cuts.find(c=>t>=c[0]&&t<c[1]&&!restored().some(w=>(w.s+w.e)/2>=c[0]&&(w.s+w.e)/2<=c[1]));if(c){v.currentTime=c[1];return;}}
const w=D.words.find(w=>t>=w.s&&t<w.e);if(last&&last!==w)last.el.classList.remove('now');
if(w){w.el.classList.add('now');last=w;if(preview&&w.cut){let j=w.i;while(j<D.words.length&&D.words[j].cut)j++;
v.currentTime=j<D.words.length?D.words[j].s:D.duration;}}});
document.getElementById('export').onclick=()=>{const out={remove:[],restore:[],text};
D.words.forEach((w,i)=>{if(w.cut&&!orig[i])out.remove.push(i);if(!w.cut&&orig[i])out.restore.push(i);});
const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,1)],{type:'application/json'}));
a.download='room-edits.json';a.click();};stat();
</script></body></html>
"""
