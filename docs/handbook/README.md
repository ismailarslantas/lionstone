# Lionstone Reel Handbook (v0.3.2)

A designed A4 guide to every Lionstone Pro & Studio v0.3.2 feature (looks, effects,
transitions, motion, text, the 12-effect Reel FX Pack), with a step-by-step Reel build.

- [English PDF](lionstone-reel-handbook-v0.3.2-en.pdf)
- [Türkçe PDF](lionstone-reel-handbook-v0.3.2-tr.pdf)

Images in `src/img/real/` are real `lionstone fx preview` renders of one source clip
(9:16); the chapter illustrations in `src/img/0*.jpg` are concept art.

## Rebuild

```bash
python src/gallery.py            # writes src/build/en.html and src/build/tr.html
```

Then print each build page to A4 PDF with a Chromium browser (no headers/footers), e.g.

```bash
chrome --headless=new --no-pdf-header-footer --virtual-time-budget=15000 \
  --print-to-pdf=lionstone-reel-handbook-v0.3.2-en.pdf src/build/en.html
```
