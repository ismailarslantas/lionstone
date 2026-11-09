"""Reels QA hook: script vs. what is heard, leftover repeats, text overflow.

Runs inside the normal Lionstone QA for any plan made by ``lionstone reels``
(``plan.meta["reels"]``). A check that can't run is ``skipped`` with the reason.
"""

from __future__ import annotations

from ..models import EditPlan, QACheck, QAIssue, QAReport
from .content import compare_script, tokens
from .visual import text_findings


def kept_text(plan: EditPlan) -> str:
    return " ".join(w.text for w in plan.words
                    if plan.source_to_output((w.start + w.end) / 2) is not None)


def leftover_repeats(plan: EditPlan, max_n: int = 4) -> list[tuple[str, float | None]]:
    kept = [w for w in plan.words if plan.source_to_output((w.start + w.end) / 2) is not None]
    toks = [(tokens(w.text) or [""])[0] for w in kept]
    hits, i = [], 0
    while i < len(toks):
        found = 0
        for n in range(max_n, 0, -1):
            a, b = toks[i:i + n], toks[i + n:i + 2 * n]
            if len(a) == n and a == b and all(a) and not (n == 1 and len(a[0]) < 3):
                found = n
                break
        if found:
            hits.append((" ".join(toks[i:i + found]), plan.source_to_output(kept[i].start)))
            i += 2 * found
        else:
            i += 1
    return hits


def reels_qa(report: QAReport, ctx: dict) -> None:
    plan: EditPlan | None = ctx.get("plan")
    if not plan or "reels" not in plan.meta:
        return
    meta = plan.meta["reels"]
    add, issue = report.checks.append, report.issues.append

    if not plan.words:
        for name in ("reels_repeats", "reels_script_match"):
            add(QACheck(name, "editorial", "skipped", "no transcript (ASR off or unavailable)"))
    else:
        rep = leftover_repeats(plan)
        add(QACheck("reels_repeats", "editorial", "warning" if rep else "passed",
                    f"{len(rep)} leftover repeat(s)" if rep else "no leftover repeats",
                    {"repeats": [r for r, _ in rep][:10]}))
        for r, at in rep[:5]:
            issue(QAIssue("reels_repeats", "medium", f"repeat left in: '{r}'", at))
        script = meta.get("script") or ""
        if not script.strip():
            add(QACheck("reels_script_match", "editorial", "skipped", "no script in reel.json"))
        else:
            d = compare_script(script, kept_text(plan))
            fixes = len(d.missing) + len(d.extra) + len(d.changed)
            status = "passed" if d.ratio >= 0.9 else ("warning" if d.ratio >= 0.75 else "failed")
            add(QACheck("reels_script_match", "editorial", status,
                        f"match {d.ratio:.0%} · {fixes} difference(s)",
                        {"ratio": d.ratio, "missing": d.missing[:10], "extra": d.extra[:10],
                         "changed": d.changed[:10]}))
            for m in d.missing[:5]:
                issue(QAIssue("reels_script_match", "medium", f"in the script, not in the video: '{m}'"))
            if status == "failed":
                issue(QAIssue("reels_script_match", "high",
                              f"script and video match {d.ratio * 100:.0f}%"))

    W = int(meta.get("width") or 1080)
    H = int(meta.get("height") or 1920)
    tf = text_findings(plan, W, H)
    worst = "failed" if any(f.get("severity") == "high" for f in tf) else "warning"
    add(QACheck("reels_text_fit", "editorial", worst if tf else "passed",
                f"{len(tf)} possible overflow(s) (estimate, no OCR)" if tf
                else "graphics and captions fit the safe area (estimate)", {"findings": tf[:10]}))
    for f in tf[:5]:
        issue(QAIssue("reels_text_fit", f.get("severity", "medium"), f["message"], f.get("at")))
