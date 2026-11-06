"""Editorial decisions for the Reels looks: which word to stress, what text goes where and when.

Pure planning, kept apart from the FFmpeg builders in ``look_fx``: the plan says what happens, the
renderer only draws it. Text always comes from the user's own script, hooks and profile.
"""

from __future__ import annotations

import re

from ..models import EditPlan, GraphicEvent
from .brand import Brand
from .content import Reel

LOOK_PREFIX = "look-"
STOPWORDS = {
    "the", "and", "you", "your", "for", "with", "that", "this", "are", "but", "not", "have", "from",
    "will", "what", "when", "here", "there", "they", "them", "then", "just", "into", "about", "some",
    "bir", "bu", "şu", "ve", "ile", "için", "ama", "çok", "daha", "gibi", "kadar", "sonra", "önce",
    "ben", "sen", "biz", "siz", "onlar", "olarak", "olan", "değil", "şey", "yani", "mı", "mi", "mu",
    "mü", "de", "da", "ne", "nasıl", "neden",
}


def _clean(word: str) -> str:
    return re.sub(r"[^\w%$€₺]", "", word)


def pick_keyword(words: list[str]) -> int:
    """Which word carries the line: a number first, otherwise the longest meaningful word.
    The first of equals wins, so the same line always stresses the same word."""
    best, score = -1, 0
    for i, w in enumerate(words):
        c = _clean(w)
        if any(ch.isdigit() for ch in c):
            return i
        if c.lower() in STOPWORDS or len(c) < 4:
            continue
        if len(c) > score:
            best, score = i, len(c)
    return best


def keywords(text: str, n: int = 2) -> list[str]:
    """The words a script stresses most, one per sentence, without repeats."""
    out: list[str] = []
    for sentence in re.split(r"[.!?\n]+", text):
        words = sentence.split()
        i = pick_keyword(words)
        if i >= 0:
            word = _clean(words[i])
            if word.lower() not in {x.lower() for x in out}:
                out.append(word)
        if len(out) == n:
            break
    return out


def number_or_keyword(text: str) -> str:
    match = re.search(r"[$€₺]?\d[\d.,]*%?", text)
    if match:
        return match.group(0).rstrip(".,")
    found = keywords(text, 1)
    return found[0] if found else ""


def beats(plan: EditPlan) -> list[float]:
    """Output times where a sentence starts."""
    out: list[float] = []
    fresh = True
    for w in plan.words:
        at = plan.source_to_output((w.start + w.end) / 2)
        if at is None:
            continue
        if fresh:
            out.append(round(max(0.0, at - (w.end - w.start) / 2), 3))
        fresh = w.text.rstrip().endswith((".", "?", "!"))
    return out


def look_events(plan: EditPlan, choice: str, brand: Brand, reel: Reel | None) -> list[GraphicEvent]:
    """The graphics a look adds. One beat per graphic, so they never pile up."""
    if not choice.startswith("look:"):
        return []
    kind = choice[5:]
    parts = {"editorial": ["glass", "pills", "countdown"], "bold": ["card"]}.get(kind, [kind])
    total = plan.output_duration
    marks = beats(plan) or [total * 0.25, total * 0.5, total * 0.75]
    # the top of the frame belongs to the hook title until it is gone
    clear = max((g.at + g.duration for g in plan.graphics
                 if g.layer == "titles" and not g.id.startswith(LOOK_PREFIX)), default=0.0)
    later = [m for m in marks[1:] if m >= clear] or [max(clear, marks[0])]
    script = reel.script if reel else ""
    events: list[GraphicEvent] = []

    def add(name: str, effect: str, at: float, duration: float, text: str, subtext: str = "") -> None:
        if text and at < total:
            events.append(GraphicEvent(f"{LOOK_PREFIX}{name}", effect, round(at, 3),
                                       round(min(duration, total - at), 3), text, subtext,
                                       params={"size": 40.0}, layer="overlays"))

    if "glass" in parts:
        message = (reel.second_hook if reel else "") or (reel.hooks[-1] if reel and reel.hooks else "")
        add("glass", "L03", later[0], 3.0, brand.handle or brand.name, message)
    if "pills" in parts:
        words = keywords(script, 2)
        if words:
            add("pills", "L04", later[min(1, len(later) - 1)], 2.8, " / ".join(words))
    if "card" in parts:
        add("card", "L05", later[0], 3.0, number_or_keyword(script))
    if "countdown" in parts:
        add("countdown", "L06", 0.0, total, f"{int(total)}")
    return events


def apply_look(plan: EditPlan, brand: Brand, reel: Reel | None) -> list[str]:
    """Refresh the look's graphics; room edits can change the timing, so this runs on every make."""
    plan.graphics = [g for g in plan.graphics if not g.id.startswith(LOOK_PREFIX)]
    events = look_events(plan, brand.style.get("effects") or "none", brand, reel)
    plan.graphics.extend(events)
    return [e.effect for e in events]
