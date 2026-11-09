# Lionstone Motion FX in OpenMontage

> Source: Lionstone 1.0 (Apache-2.0), https://github.com/ismailarslantas/lionstone/blob/main/docs/motion-fx.md

## Quick Reference Card

```
TOOL:      lionstone_motion_fx   (runs `lionstone fx clip <effect> in.mp4 -o out.mp4`)
INPUT:     a talking-head clip (any aspect: 9:16, 1:1, 16:9)
WINDOW:    start / end in seconds (default: the whole clip)
PARAMS:    see `lionstone fx show <effect>`; colours as #RRGGBB, lists in text with "|"
MATTE:     frame-break, vertigo, glass-type, green-screen, doodle-boil use an AI person
           matte (CPU, cached) when OpenCV is installed; otherwise a plain version
```

## Which effect when

| Moment | Effects |
|---|---|
| Hook (first 2 s) | `zoom-through-cut`, `pull-back-reveal`, `frame-break`, `glass-type` |
| Lists, how-tos | `checklist` (params.items = "a\|b\|c"), `ui-world`, `phone-mockup` |
| Numbers, proof | `chart-grow` (params.values, params.label), `headline-wall`, `cover-story` |
| One line to stress | `digital-zoom`, `vertigo`, `orbit` |
| Change of world | `green-screen` (works without a green screen), `paper-cut`, `doodle-boil`, `couch-wall` |

Also available: the 12 Reel FX (`stage-light`, `press-mono`, `frost-panels`, `duotone-pop`,
`scan-line`, `afterimage`, `halo-orbit`, `neon-outline`, `insight-split`, `brand-frame`,
`progress-rail`, `pixel-resolve`).

## Rules

- One effect window per moment; chain tool calls for several effects (output of one is the
  input of the next), never two layout effects over the same seconds.
- Keep `zoom-through-cut` windows short (0.6 to 1 s) and centred on a cut.
- Put the words in `params` (`text`, `items`, `headlines`, `lines`, `label`); Lionstone never
  invents copy.
- Check the result before moving on: text inside the safe area, the subject's head not cropped.
