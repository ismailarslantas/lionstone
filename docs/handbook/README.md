# Lionstone Reel Handbook (Lionstone 0.4.1)

A designed A4 guide to every Lionstone feature, free for everyone: Lionstone Reels, your brand identity and the numbered
visual catalogue, looks, effects, transitions, motion, text, the 12-effect Reel FX Pack, and a step-by-step Reel build.

- [English PDF](lionstone-reel-handbook-v0.4.1-en.pdf)
- [Türkçe PDF](lionstone-reel-handbook-v0.4.1-tr.pdf)

Images in `src/img/real/` are real Lionstone renders; the man in the catalogue pages is a fictional example. The chapter
illustrations in `src/img/0*.jpg` are concept art.

## Rebuild

```bash
python src/gallery.py            # writes src/build/en.html and src/build/tr.html
```

Then print each build page to A4 PDF with a Chromium browser (no headers/footers), e.g.

```bash
chrome --headless=new --no-pdf-header-footer --virtual-time-budget=15000 \
  --print-to-pdf=lionstone-reel-handbook-v0.4.1-en.pdf src/build/en.html
```
