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
