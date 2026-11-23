# Harness results

Each row is one `fidelity.py loop` (or `render`) run of the 838-slide test deck. It is scored
against PowerPoint's own PDF export of the deck. 835 pages have text to compare.

- **Lines**: text lines (PDF text extraction) that break on the same word as PowerPoint.
- **Identical**: slides whose line breaks all match PowerPoint.
- **SSIM**: mean image similarity of the 800-px renders.

SSIM alone misleads on dense text: a 1–2 px line-spacing shift scores like a wrapping error. So
read it together with the line metrics.

| Run | sdkjs | Lines | Identical | SSIM | Notes |
|---|---|---:|---:|---:|---|
| libreoffice-26.8.3 | — | 79.3% | 319/835 | 0.7957 | LibreOffice, for comparison |
| release-9.3.8 | release bundle | 87.1% | 443/835 | 0.8895 | Euro-Office 9.3.8 as shipped; the harness baseline |
| fork-v9.3.8 | a1b8cac5d1 | 87.1% | 443/835 | 0.8895 | the fork's pinned sdkjs, built here; byte-identical to the release bundle |
| exp-kern-ge12pt | experiment | 93.0% | 590/835 | 0.9414 | kerning forced on for runs ≥ 12 pt (stand-in, replaced by F-001) |
| exp-kern-ge12pt-commonjoin | experiment | 93.6% | 605/835 | 0.9494 | + F-002 |
| kern-model-commonjoin-width025 | 7898a3e982 | 95.1% | 653/835 | 0.9517 | F-001 + F-002 + F-003; 301 slides better, 54 worse than release. **The full review was done on this run.** |
| kern-fix-on-sdkjs-main | d1c4bda5bd | 95.1% | 653/835 | 0.9517 | the same fix merged into the fork's sdkjs main |
| i001-fontsize-hundredths | 414ae64bd0 | 96.7% | 673/835 | 0.9569 | I-001; vs the reviewed run 32 slides better and 0 worse on line breaks, 34 better and 0 worse on SSIM |
| i007-ln-default-075 | 7e6a447d83 | 96.7% | 673/835 | 0.9574 | I-007; vs i001 105 slides better and 6 worse on SSIM (10 better and 0 worse by more than 0.01); line breaks unchanged |
| i012-pic-outline-outside | 555e9eabe3 | 96.7% | 673/835 | 0.9575 | + I-012; vs i001 108 better and 5 worse (all 5 explained in I-007's log: 3 reference-rounding ties, 2 below 0.002); all 7 I-012 slides better |
| k1-filled-heads | 44cdab9e9f | 96.7% | 673/835 | 0.9576 | + K1; vs i012 115 better and 0 worse; 115 of the 116 K1 slides better, 1 unchanged |
| k2-adv-576 | experiment | 97.8% | 706/835 | 0.9789 | + K2 (1/576-inch advances), K3's 0.25 pt reduction kept; vs k1 89 slides better and 54 worse on breaks |
| k2-576-red0 | experiment | 98.9% | 750/835 | 0.9822 | + K2, no width reduction; vs k1 94 better and 8 worse on breaks |
| k2-k3-layout576 | e84bfe4efb | 99.6% | 774/835 | 0.9834 | + K2 + K3 (text width rounded down to 1/576 inch); vs k1 109 better and 0 worse on breaks, SSIM 828 better and 4 worse (255 -0.0068, the rest under 0.001) |
| spacing-i002-i003-i009-c | 42d5db5758 | 99.6% | 774/835 | 0.9861 | + I-002 (spaces size their line), I-003 (paragraph spacing added), I-009 (point spacing in whole points); vs k2-k3-layout576 31 slides better and 0 worse on SSIM, line breaks unchanged |
| i004-i005-i006-c | d3452db46b | 99.9% | 781/835 | 0.9866 | + I-004 (a line may start after any space), I-005 (kerning across spaces), I-006 (theme script fonts by language, right-to-left code points); vs spacing-i002-i003-i009-c 8 slides better and 0 worse on line breaks, SSIM 8 better and 1 worse (674 -0.031: the mixed Calibri/Arial line is taller, I-020) |
| i010-i011-i013-dash-c | 4c3273edbc | 100.0% | 784/835 | 0.9875 | + I-010 (superscripts at 2/3 size with the stated raise), I-011 (no kerning into a hyphen), I-013 (trailing spaces align in wrap="none" boxes), I-022 (break after an en dash); 15406 of 15410 lines; vs i004-i005-i006-c 3 slides better and 0 worse on line breaks (116, 510, 525), SSIM 62 better and 0 worse by more than 0.001 |
| k4-c | 88cc4cc6cb | 100.0% | 784/835 | 0.9887 | + K4 (underline and strikethrough from the face's post and OS/2 metrics on a 1/600-inch grid); 15406 of 15410 lines; the same as the uncommitted run k4-b; vs i010-i011-i013-dash-c line breaks unchanged, SSIM 146 slides better and 0 worse by more than 0.001 |
| i017-c | 472ee0b1ae | 100.0% | 784/835 | 0.9887 | + I-017 (lines under percentage spacing other than 100% and exact spacing placed like PowerPoint: a quarter of the line below the baseline; lnSpcReduction also taken off the paragraph's own lnSpc; the last line's extra spacing left out of ctr/b anchoring); 15406 of 15410 lines; the same as the uncommitted run i017-a; vs k4-c line breaks unchanged, only 579 and 594-596 move (all closer to PowerPoint), SSIM 3 slides better and 0 worse |
| i020-c | a9856eee47 | 100.0% | 784/835 | 0.9888 | + I-016 (a font's line split at its win ascent : descent, without the hhea line gap) and I-020 (a line that mixes fonts: the largest parts above and below the baseline, scaled back to 1.2 × the largest size; the a:br's and endParaRPr's font counts); 15406 of 15410 lines; the same as the uncommitted run i020-pre; vs i017-c line breaks unchanged, only slides 1 and 674 move (both closer to PowerPoint), SSIM 2 slides better and 0 worse |
| i008-c | 7937b6f01f | 100.0% | 784/835 | 0.9888 | + I-008 (outlines with no join stroked round, except 31 presets PowerPoint miters; explicit joins reach the PDF); 15406 of 15410 lines; vs i020-c line breaks unchanged, every stroke paired with PowerPoint's has its join (1518 round, 268 miter; 1518 were mitered), SSIM 0 slides worse; the same as the uncommitted run i008-b |
| i023-pcfonts | 7937b6f01f | 100.0% | 784/835 | 0.9888 | the harness now renders with a font list made from this PC's fonts (I-023, harness b3dfc7b); scores and text the same as i008-c, and the release app's render with it (release-9.3.8-pcfonts) the same as release-9.3.8, so the baseline stays |
| i021-core-control | 7937b6f01f | 100.0% | 784/835 | 0.9888 | the release's core (0c489c97a8) built here, unmodified (VS 2022, shared C runtime), rendered with `--core`; scores and text the same as i023-pcfonts, so the local build stands in for the release's native code |
| i021-c | 7937b6f01f | 100.0% | 784/835 | 0.9891 | + I-021 in core 2d4497c536 (each embedded font's `cmap` entryCount matches the codes it holds, so Windows draws the embedded fonts, not system fonts from ToUnicode; only PdfFile.dll differs); text and line breaks unchanged; vs i021-core-control SSIM 54 slides better and 3 worse by more than 0.001 (at most -0.0014), slide 674 draws the dagesh and shin dot; the same as the uncommitted run i021-cmap but for slide 617 (0.0001, Windows' rasterizer: the PDFs are the same apart from their dates). Every run above drew its PDF text through that fallback |
