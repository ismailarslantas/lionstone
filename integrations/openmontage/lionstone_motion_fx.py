# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Lionstone contributors.
"""OpenMontage tool: apply a Lionstone Motion FX / Reel FX effect to a clip.

Copied into an OpenMontage checkout (tools/video/) by
``python integrations/openmontage/install.py <OpenMontage dir>``. It runs the
``lionstone`` command as a separate process, so Lionstone (Apache-2.0) and
OpenMontage (AGPL-3.0) stay separate programs. Lionstone must be installed in
the Python environment OpenMontage uses:

    pip install "lionstone[all] @ git+https://github.com/ismailarslantas/lionstone"
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

EFFECTS = [
    "orbit", "couch-wall", "ui-world", "frame-break", "digital-zoom", "phone-mockup",
    "checklist", "headline-wall", "zoom-through-cut", "chart-grow", "pull-back-reveal",
    "green-screen", "paper-cut", "doodle-boil", "vertigo", "cover-story", "glass-type",
    "stage-light", "press-mono", "frost-panels", "duotone-pop", "scan-line", "afterimage",
    "halo-orbit", "neon-outline", "insight-split", "brand-frame", "progress-rail",
    "pixel-resolve",
]


def _lionstone() -> list[str]:
    exe = os.environ.get("LIONSTONE_BIN") or shutil.which("lionstone")
    return [exe] if exe else [sys.executable, "-m", "lionstone"]


class LionstoneMotionFx(BaseTool):
    name = "lionstone_motion_fx"
    version = "1.0.0"
    tier = ToolTier.ENHANCE
    capability = "video_effects"
    provider = "lionstone"
    stability = ToolStability.PRODUCTION
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg"]
    install_instructions = ('pip install "lionstone[all] @ '
                            'git+https://github.com/ismailarslantas/lionstone"')
    agent_skills = ["lionstone-motion-fx"]
    capabilities = ["motion_fx", "reel_fx", "person_matte"]

    input_schema = {
        "type": "object",
        "required": ["input_path", "effect", "output_path"],
        "properties": {
            "input_path": {"type": "string", "description": "talking-head clip"},
            "output_path": {"type": "string"},
            "effect": {"type": "string", "enum": EFFECTS},
            "start": {"type": "number", "minimum": 0, "description": "effect start (s)"},
            "end": {"type": "number", "minimum": 0, "description": "effect end (s)"},
            "params": {"type": "object", "description": "effect parameters, see "
                       "`lionstone fx show <effect>` (e.g. {\"text\": \"FOCUS\"})"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=2048, vram_mb=0, disk_mb=2000)
    idempotency_key_fields = ["input_path", "effect", "start", "end", "params"]
    side_effects = ["writes the processed video to output_path",
                    "may download a 4.6 MB person-matte model once and cache mattes"]
    user_visible_verification = [
        "Watch the effect window: text readable, subject not cut off",
        "Frame Break / Glass Type / Vertigo: edges of the person look clean",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        t0 = time.time()
        src = Path(inputs["input_path"])
        if not src.is_file():
            return ToolResult(success=False, error=f"Input not found: {src}")
        effect = inputs["effect"]
        if effect not in EFFECTS:
            return ToolResult(success=False, error=f"Unknown Lionstone effect: {effect}")
        cmd = [*_lionstone(), "fx", "clip", effect, str(src), "-o", str(inputs["output_path"])]
        for key in ("start", "end"):
            if inputs.get(key) is not None:
                cmd += [f"--{key}", str(float(inputs[key]))]
        for k, v in (inputs.get("params") or {}).items():
            cmd += ["--param", f"{k}={v}"]
        try:
            self.run_command(cmd, timeout=3600)
        except Exception as e:  # noqa: BLE001  (surface Lionstone's own message)
            return ToolResult(success=False, error=f"Lionstone failed: {e}")
        return ToolResult(success=True, data={"effect": effect, "output_path":
                                              str(inputs["output_path"])},
                          artifacts=[str(inputs["output_path"])],
                          duration_seconds=round(time.time() - t0, 2))
