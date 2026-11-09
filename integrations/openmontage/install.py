"""Add the Lionstone tool and skill to an OpenMontage checkout.

    python integrations/openmontage/install.py C:/path/to/OpenMontage

Copies two files (tools/video/lionstone_motion_fx.py, skills/core/lionstone-motion-fx.md)
and adds one line to skills/INDEX.md. Lionstone itself is never copied into OpenMontage:
the tool calls the `lionstone` command, so the two projects keep their own licences.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROW = ("| Lionstone Motion FX | `core/lionstone-motion-fx.md` | 25 Motion FX + 12 Reel FX "
       "on talking-head clips, AI person matte | `lionstone_motion_fx` |")


def install(om: Path) -> list[str]:
    if not (om / "tools" / "base_tool.py").is_file() or not (om / "skills").is_dir():
        raise SystemExit(f"{om} is not an OpenMontage checkout (tools/base_tool.py missing)")
    done = []
    for src, dst in ((HERE / "lionstone_motion_fx.py", om / "tools" / "video"),
                     (HERE / "lionstone-motion-fx.md", om / "skills" / "core")):
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst / src.name)
        done.append(str(dst / src.name))
    index = om / "skills" / "INDEX.md"
    if index.is_file():
        text = index.read_text(encoding="utf-8")
        if "lionstone-motion-fx.md" not in text:
            index.write_text(text.rstrip("\n") + "\n" + ROW + "\n", encoding="utf-8")
            done.append(f"{index} (+1 row)")
    return done


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    for line in install(Path(sys.argv[1]).resolve()):
        print("installed", line)
