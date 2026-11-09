# Lionstone + OpenMontage

[OpenMontage](https://github.com/OpenMontageInc/OpenMontage) is an open-source, agent-driven
video production system (scripts, scene plans, generated footage, Remotion compositions).
Lionstone 1.0 plugs into it as a tool, so an OpenMontage production can finish a talking-head
shot with any of the 17 Motion FX or the 12 Reel FX, including the AI person matte.

## Install

```bash
# 1. OpenMontage, as its README says (its own folder and virtual environment)
git clone https://github.com/OpenMontageInc/OpenMontage.git
cd OpenMontage && make setup            # or the Windows steps in its README

# 2. Lionstone inside OpenMontage's environment
pip install "lionstone[all] @ git+https://github.com/ismailarslantas/lionstone"

# 3. the Lionstone tool and skill
python path/to/lionstone/integrations/openmontage/install.py .
```

Step 3 copies two files and adds one line to `skills/INDEX.md`:

* `tools/video/lionstone_motion_fx.py`: the `lionstone_motion_fx` tool (auto-discovered).
* `skills/core/lionstone-motion-fx.md`: when to use which effect.

Then ask your agent, for example: *"Use lionstone_motion_fx to put frame-break on the first
3 seconds of the host clip and glass-type with the text FOCUS at 12-15 s."*

## What the tool runs

```bash
lionstone fx clip <effect> in.mp4 -o out.mp4 [--start S] [--end S] [--param k=v ...]
```

`fx clip` applies one effect to a whole clip at the clip's own size, with the same builders as
the Lionstone export, and copies the audio. You can use it on its own too.

## Licences

OpenMontage is AGPL-3.0; Lionstone is Apache-2.0. They stay separate programs: the tool calls
the `lionstone` command as a separate process and no code from either project is copied into
the other. The adapter files are Apache-2.0, which the AGPL allows inside an AGPL project.
