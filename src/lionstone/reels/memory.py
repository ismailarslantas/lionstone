"""Remembers brands across folders: which exist, where they live, when they were set up.

The brand itself stays in plain files under ``brands/<slug>/``. This small index in the user's
config folder only points at them, so a brand made in one folder is found from any other, and
the next Reel can start with "same identity, or a new one?".
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


def memory_path() -> Path:
    from ..pro.identity import config_dir
    return config_dir() / "reels-memory.json"


def _read() -> dict[str, Any]:
    try:
        data = json.loads(memory_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last_used": "", "brands": {}}
    return {"last_used": data.get("last_used", ""), "brands": data.get("brands", {})}


def now() -> str:
    return dt.datetime.now().isoformat(timespec="minutes")


def remember(slug: str, name: str, root: Path, *, use: bool = False, **stamps: str) -> None:
    """Record a brand. A read-only config folder must never stop a render, so errors pass."""
    data = _read()
    entry = data["brands"].setdefault(slug, {})
    entry.update(name=name, root=str(Path(root).resolve()), **stamps)
    if use:
        entry["last_used_at"] = now()
        data["last_used"] = slug
    try:
        p = memory_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def entries() -> dict[str, dict[str, Any]]:
    """Remembered brands whose folder still exists."""
    return {s: e for s, e in _read()["brands"].items()
            if (Path(e.get("root", "")) / s / "brand.json").exists()}


def lookup(slug: str) -> Path | None:
    e = entries().get(slug)
    return Path(e["root"]) if e else None


def last_used() -> str:
    slug = _read()["last_used"]
    return slug if slug in entries() else ""
