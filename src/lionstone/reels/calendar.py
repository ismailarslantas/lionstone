"""Content calendar built from the reel briefs themselves (one source of truth).

Every ``projects/<brand>/<reel>/reel.json`` with a ``publish_at`` is a calendar
entry; ``to_ics`` exports them for Google / Apple / Outlook calendars.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

from .content import Reel


def entries(root: Path | None = None, brand_slug: str | None = None) -> list[tuple[Path, Reel]]:
    root = root or Path("projects")
    pattern = f"{brand_slug}/*/reel.json" if brand_slug else "*/*/reel.json"
    items = [(p.parent, Reel.load(p)) for p in sorted(root.glob(pattern))]
    return sorted(items, key=lambda x: (x[1].publish_at or "9999", x[1].created))


def parse_when(s: str) -> dt.datetime:
    s = s.strip().replace(" ", "T")
    if len(s) == 10:
        s += "T19:00"
    return dt.datetime.fromisoformat(s)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", r"\;").replace(",", r"\,").replace("\n", r"\n")


def to_ics(items: list[tuple[Path, Reel]], minutes: int = 30) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Lionstone//Reels//TR",
             "CALSCALE:GREGORIAN"]
    for folder, r in items:
        if not r.publish_at:
            continue
        start = parse_when(r.publish_at)
        end = start + dt.timedelta(minutes=minutes)
        uid = hashlib.sha1(str(folder.resolve()).encode()).hexdigest()[:16]
        desc = "\n".join(x for x in [
            f"Kanca: {r.hooks[0]}" if r.hooks else "", f"Durum: {r.status}",
            f"Klasör: {folder}", "", r.caption[:900]] if x is not None)
        lines += ["BEGIN:VEVENT", f"UID:{uid}@lionstone", f"DTSTAMP:{stamp}",
                  f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                  f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
                  f"SUMMARY:{_esc(f'[{r.brand}] Reel: {r.topic}')}",
                  f"DESCRIPTION:{_esc(desc)}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
