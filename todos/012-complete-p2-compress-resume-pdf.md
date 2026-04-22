---
status: done
priority: p2
issue_id: 012
tags: [code-review, performance, pdf]
dependencies: [002]
---

# Compress resume.pdf from 464 KB to ~150 KB via Ghostscript

## Problem Statement

`resume.pdf` is 474,955 bytes (463.8 KB). For a 1–2 page résumé this is roughly 2–3× what a Ghostscript-compressed PDF would produce. Recruiters download this; faster = faster first impression.

After the headshot optimization (todo #002), regenerate the PDF — the print stylesheet hides the headshot in print anyway, so most of the size is PDF fonts/structure.

## Findings

From performance-oracle agent (P2 finding):
- Current: 474,955 B
- `-dPDFSETTINGS=/ebook` target: 100–180 KB
- `-dPDFSETTINGS=/prepress` target: 250–350 KB

## Proposed Solutions

### Option A (Recommended): Ghostscript `/ebook` post-process
- After each Chrome `--print-to-pdf` generation, pipe through Ghostscript
- Add a Makefile or shell script
- **Effort:** Small (~10 min) • **Savings:** ~280–350 KB • **Pros:** one-time setup, automatic for future regenerations

### Option B: Hand-tune print CSS to reduce embedded fonts
- Eliminate webfont embedding if any; use system stack only (already done)
- Reduce image DPI in print stylesheet
- **Effort:** Medium • **Savings:** smaller than A • **Pros:** no new tool

### Option C: Accept the size
- 464 KB is fine for a résumé download
- **Effort:** None • **Cons:** 3× perf opportunity lost

## Technical Details

Shell command:
```bash
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 \
   -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=resume-compressed.pdf resume.pdf && \
   mv resume-compressed.pdf resume.pdf
```

Optional: add a script at `/Users/jameschang/Projects/jameschang.co/bin/regen-resume.sh`:
```bash
#!/usr/bin/env bash
set -e
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=resume.pdf --virtual-time-budget=5000 \
  "http://localhost:3062/"
gs -sDEVICE=pdfwrite -dPDFSETTINGS=/ebook \
   -dNOPAUSE -dQUIET -dBATCH \
   -sOutputFile=resume-small.pdf resume.pdf
mv resume-small.pdf resume.pdf
echo "resume.pdf → $(du -h resume.pdf | cut -f1)"
```

## Acceptance Criteria

- [ ] `resume.pdf` is ≤ 200 KB
- [ ] Visual quality indistinguishable at 100% zoom
- [ ] Text is still selectable / copy-able (not rasterized)
- [ ] ATS parsers still extract correctly (test with `pdftotext -layout resume.pdf -`)
- [ ] Regen script committed for future use

## Work Log

_(blank)_

## Resources

- Performance review output
- Ghostscript docs: https://ghostscript.readthedocs.io/en/latest/VectorDevices.html
