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
