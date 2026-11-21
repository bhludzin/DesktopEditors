# PowerPoint rendering rules

These are the rules PowerPoint follows, as measured from its PDF export, from test decks built
with PowerPoint itself (COM automation) and from the 838-slide review. Each rule links to the
issue that implements it or still needs it. Where the evidence is thin, the issue's confidence
says so. The numbers come from PowerPoint's PDF unless stated otherwise.

## Implemented in the fork

| Rule | Issue |
|---|---|
| Pair kerning applies when `a:rPr/@kern` > 0 and the font size is at least `kern`/100 pt. If `kern` is missing from the whole style chain there is no kerning (the spec text says otherwise). `kern="0"` means none. A `kern` equal to the size kerns; `kern="1801"` at 18 pt does not. | [F-001](issues/F-001.md) |
| Punctuation and digits (Unicode script Common) are shaped together with the surrounding Latin text, so letter+period and letter+comma pairs are kerned. | [F-002](issues/F-002.md) |
| Text wraps as if the line were about 0.25 pt narrower than the box width minus the insets. This was fitted, not derived, and may be compensating for K2. | [F-003](issues/F-003.md), [K3](issues/K3.md) |
| `a:rPr/@sz` is used exactly, in hundredths of a point (12.75 pt stays 12.75 pt), for advances, glyphs and line pitch. | [I-001](issues/I-001.md) |

## Not implemented yet

### Text

| Rule | Issue |
|---|---|
| Glyph advances seem quantized to PowerPoint's 576-dpi master grid: each advance is rounded to whole 1/576-inch units at the run size, and the kerning delta is truncated. This is a hypothesis: it fits regular text (0.70 px RMS) but not every bold measurement. | [K2](issues/K2.md) |
| Kerning also applies across spaces (space+A, space+T, A+space). | [I-005](issues/I-005.md) |
| A letter followed by a hyphen-minus is not kerned. | [I-011](issues/I-011.md) |
| Latin text may break at any space, including before `.`, `,`, `;` or `)`, so a spaced ellipsis can start a line. | [I-004](issues/I-004.md) |
| A line holding only whitespace takes its height from its runs, not from the paragraph-end properties. | [I-002](issues/I-002.md) |
| The gap between paragraphs is space-after of the first plus space-before of the next. They are added, not collapsed. | [I-003](issues/I-003.md) |
| `spcPts` values seem rounded to whole points before layout (4.5 → 5, 13.5 → 14; 6, 9 and 15 unchanged). | [I-009](issues/I-009.md) |
| A superscript with `baseline="30000"` is raised by 30% of the run size and drawn at 2/3 of the size. | [I-010](issues/I-010.md) |
| When a line is centred, its trailing space counts in the line width. | [I-013](issues/I-013.md) |
| Underline (and strikeout) position and thickness come from the font's own metrics (`post` and `OS/2`). | [K4](issues/K4.md) |
| Theme fonts for other scripts (`a:font script="Hebr"`) are used for runs in that script. | [I-006](issues/I-006.md) |
| Run-level effects (`a:rPr/a:effectLst`, such as `outerShdw`) are drawn: a blurred, offset copy of the text. | [I-015](issues/I-015.md) |
| With `normAutofit lnSpcReduction`, the first baseline moves up by about 0.21 em at 80% spacing (low confidence). | [I-017](issues/I-017.md) |

### Lines, shapes and pictures

| Rule | Issue |
|---|---|
| Line ends are filled, never stroked. A triangle head is sm 2×, med 3× or lg 5× the line width (with a floor of about 2 pt) in width and in length. The tip sits exactly on the end point, and the shaft is shortened under the head. | [K1](issues/K1.md) |
| An `a:ln` with no `w` and no `p:style/a:lnRef` is 9525 EMU (0.75 pt) wide. With an `lnRef`, the theme's `lnStyleLst` width applies. | [I-007](issues/I-007.md) |
| When no join is specified, strokes use a round join; `<a:miter/>` gives a miter join. Seen once: `rightArrow` strokes with a miter join anyway. | [I-008](issues/I-008.md) |
| Picture outlines are stroked on the picture's rectangle grown by half the line width, so the line lies entirely outside the image. | [I-012](issues/I-012.md) |
| `outerShdw` uses `blurRad`: the shadow is a blurred silhouette. | [I-014](issues/I-014.md) |
| Elliptical arcs become cubic Béziers with control length k = 4/3·tan(Δθ/4) over the parametric sweep. | [I-019](issues/I-019.md) |
| Pictures are drawn as clipped images, not tiling-pattern fills. A PNG stays lossless in the PDF. | [K6](issues/K6.md) |
