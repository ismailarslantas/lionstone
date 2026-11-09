"""Property-based fuzzing of the parsers that take user text (Hypothesis)."""

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from lionstone.planner import parse_chapter, parse_speaker, parse_timecode  # noqa: E402
from lionstone.speech import is_filler, norm  # noqa: E402


@given(st.integers(0, 99), st.integers(0, 59), st.integers(0, 59))
def test_timecode_round_trip(h, m, s):
    assert parse_timecode(f"{h}:{m:02d}:{s:02d}") == h * 3600 + m * 60 + s


@given(st.text())
def test_timecode_rejects_bad_text_with_value_error_only(s):
    try:
        assert isinstance(parse_timecode(s), float)
    except ValueError:
        pass


@given(st.text())
def test_chapter_and_speaker_never_crash(s):
    try:
        parse_chapter(s)
    except ValueError:
        pass
    sp = parse_speaker(s)
    assert isinstance(sp.name, str)


@given(st.text())
def test_norm_is_clean_and_filler_check_never_crashes(s):
    t = norm(s)
    assert isinstance(t, str) and not any(c.isspace() for c in t)
    assert isinstance(is_filler(s), bool)
