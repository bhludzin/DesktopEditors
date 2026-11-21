# How the comparison was done

## Ground truth

PowerPoint exports the deck to PDF (`fidelity.py reference`). Euro-Office converts the same deck
to PDF with `x2t`, the headless converter of the portable 9.3.8 app, overlaid with an `sdkjs`
bundle built from this checkout (`fidelity.py render` / `loop`). Both PDFs are rasterized
(`fidelity/windows/pdf-to-png.ps1`; 800 px wide for scoring, 1600 px for review). Their text is
extracted with xpdf `pdftotext -raw`.

Scores per run (`fidelity.py score`, `runs`):
- the share of PowerPoint's text lines that Euro-Office breaks on the same words;
- the number of slides with identical line breaks;
- SSIM of the 800-px images (computed with `fidelity/ssim-compare`, Rust).

The work folder (`../fidelity-work`, or `$FIDELITY_WORK`) holds the app, the decks, the
reference, every run and the review evidence. It stays outside the repo.

## Full-deck review

Run on 2026-11-21 against run `kern-model-commonjoin-width025` (sdkjs 7898a3e982).

1. **Facts** — `python fidelity/review_prep.py <deck-dir> <run>` writes into
   `<deck-dir>/review`:
   - pretty-printed XML of the deck;
   - per slide (`slides/NNNN.json`): scores, the text lines only one renderer has, the changed
     regions mapped to the objects under them, and every object's box (with inherited
     placeholder positions and group transforms), geometry, line ends, text, autofit and font
     sizes;
   - `index.json`, which groups byte-identical slides.

   `slide-diff pages` (`fidelity/ssim-compare/src/bin/slide-diff.rs`) writes the 2×2 sheets
   `sheets/pNNNN.png` and the region lists. `slide-diff crop` makes magnified PowerPoint |
   Euro-Office | difference crops.
2. **Pilot** — a reviewer agent looked at 7 varied slides. It found the recurring patterns
   that became the known issues K1–K6.
3. **Review** — [workflows/slide-review.js](workflows/slide-review.js) ran 116 reviewer
   agents, each on a batch of neighbouring slides. Each reviewer:
   - looked at the sheet and zoomed into every changed region;
   - measured ink positions and drift on the 1600-px renders;
   - explained each difference from the slide, layout and master XML;
   - wrote `findings/batch-NNN.json`.

   Known issues were tagged per slide (K2/K4/K5/K6) or listed per object (K1/K3). Everything
   else became a finding with a category, severity, measurements, XML evidence and a suspected
   cause. All 838 slides were covered; duplicate slides inherited their twin's result.
4. **Merge** — `python fidelity/review_merge.py <deck-dir>` checks coverage and combines the
   batches into `review/discrepancies.json` (finding ids `S<slide>-<n>`). It also writes
   per-category files for grouping.
5. **Root causes** — [workflows/discrepancy-grouping.js](workflows/discrepancy-grouping.js)
   clustered each category's findings by root cause. One agent per group:
   - checked doubtful findings against the images (7 rejected);
   - located the code in `sdkjs` and proposed a fix.

   A final agent merged issues that one code change would fix and flagged doubts.
6. **Tracker and pages** — `python fidelity/review_issues.py <deck-dir> specs` builds
   [issues.json](issues.json) (stable ids). After that, the file is edited by hand.
   `python fidelity/review_record.py <deck-dir> specs` regenerates
   [findings.json](findings.json), [issues/](issues/) and [slides.md](slides.md) from it.

## Re-checking after a fix

`fidelity.py loop` gives the deck-wide scores and lists the slides that got better or worse.
For a closer look at one issue's slides:
- run `review_prep.py` on the new run, then `slide-diff crop` on the affected regions; or
- run `fidelity.py compare <deck> <slide>`.

A full re-review (steps 1–6) is only worth it after several fixes have landed. The workflow
scripts expect the work-folder layout above, so adjust their paths if it moves.

## Lessons

- Give every parallel agent its own scratch folder. Reviewers that shared one overwrote each
  other's helper scripts, and a few slides landed in another batch's file. The merge keeps the
  entry from the batch a slide was assigned to.
- PDF text extraction is only a hint for rotated text: it extracts differently even when the
  render matches.
- Measure on the 1600-px renders. Sub-pixel edge effects at 800 px (an outline on a pixel
  boundary, a picture's last column) can look like layout differences.
