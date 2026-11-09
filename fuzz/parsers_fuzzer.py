"""Atheris fuzzer for the parsers that take user text (run by ClusterFuzzLite)."""

import sys

import atheris

with atheris.instrument_imports():
    from lionstone.planner import parse_chapter, parse_speaker, parse_timecode
    from lionstone.speech import is_filler, norm


def TestOneInput(data: bytes) -> None:
    s = atheris.FuzzedDataProvider(data).ConsumeUnicodeNoSurrogates(256)
    for parse in (parse_timecode, parse_chapter):
        try:
            parse(s)
        except ValueError:  # the documented error for bad input
            pass
    parse_speaker(s)
    norm(s)
    is_filler(s)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
