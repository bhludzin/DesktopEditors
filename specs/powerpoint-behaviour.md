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
| Text is laid out in whole 1/576-inch units (1/8 pt). Each glyph's own advance is rounded to a whole unit at the run's size (S pt = 8·S units per em, halves up), spaces included, and pair kerning is then added unrounded. Bold and regular follow the same rule. Word start positions in PowerPoint's PDF follow this to within about 0.02 pt per 100 pt at 13.5, 15 and 18 pt regular and 13.5, 24 and 30 pt bold. Exact design widths drift by +0.05 to +0.21 pt per 100 pt (regular) and -0.32 (bold 13.5). Truncating the kerning instead (the first hypothesis) drifts by -0.1 pt per 100 pt. Regular 12.75 pt is the one size that fits less well (about 0.1% long). | [K2](issues/K2.md) |
| A line wraps when it would be wider than the box width minus the insets rounded down to whole 1/576-inch units. This replaces the fitted 0.25 pt reduction of F-003. | [K3](issues/K3.md), [F-003](issues/F-003.md) |
| `a:rPr/@sz` is used exactly, in hundredths of a point (12.75 pt stays 12.75 pt), for advances, glyphs and line pitch. | [I-001](issues/I-001.md) |
| Line ends are filled, never stroked. A triangle head is sm 2×, med 3× or lg 5× the line width (with a floor of about 2 pt) in width and in length. The tip sits exactly on the end point, and the shaft is shortened under the head. | [K1](issues/K1.md) |
| An `a:ln` with no `w` and no `p:style/a:lnRef` is 9525 EMU (0.75 pt) wide. With an `lnRef`, the theme's `lnStyleLst` width applies. | [I-007](issues/I-007.md) |
| Picture outlines are stroked on the picture's rectangle grown by half the line width, so the line lies entirely outside the image. | [I-012](issues/I-012.md) |
| A space sizes its line like text does. A line holding only spaces takes its height from them (a 13.5 pt space makes a 16.2 pt line, whatever `endParaRPr` says), and a larger space on a text line makes that line taller. Empty paragraphs take their height from `endParaRPr`. | [I-002](issues/I-002.md) |
| The gap between paragraphs is the space after the first plus the space before the next: they are added, not collapsed (10 + 10 pt gives 20 pt). Percentage spacing adds the same way. The first paragraph's space before and the last paragraph's space after are not used. | [I-003](issues/I-003.md) |
| Spacing given in points (`spcBef`, `spcAft` and `lnSpc` `spcPts`) is used in whole points, halves up: 4.2 → 4, 4.5 → 5, 0.5 → 1, 2.5 → 3, 13.5 → 14, 20.5 → 21. Percentage spacing is not rounded. | [I-009](issues/I-009.md) |
| Latin text may break at any space, including before `.`, `,`, `;`, `:`, `!`, `?`, `)`, `]`, `%` or a closing quote (`”`, `’`, `»`), so a spaced ellipsis can start a line. Without a space before it, the punctuation stays with its word. | [I-004](issues/I-004.md) |
| Kerning also applies across spaces (space+A, space+T, A+space and so on) in kerned runs, also where a run boundary falls next to the space, as long as the font and size are the same on both sides. | [I-005](issues/I-005.md) |
| Complex-script characters (Hebrew, Arabic, Thai, Indic and so on) use the run's `cs` font. When the theme leaves the `cs` typeface empty, the theme's `a:font script` entry for the run's **language** is used (he-IL → Hebr, ar-SA → Arab), whatever script the letters are in: Arabic letters in a he-IL run use the Hebr font. Spaces and punctuation in such a run use that font too. Hebrew in an en-US run uses Arial for the letters and the Latin font for the spaces. | [I-006](issues/I-006.md) |
| A line may break after an en dash (U+2013), between digits (`8:34–35`, `1850–1851`) as between letters (`slain–army`). The dash stays at the end of the line. | [I-022](issues/I-022.md) |
| Superscripts and subscripts (`a:rPr/@baseline`) are drawn at exactly 2/3 of the run size, with no rounding (13.5 → 9 pt, 12.75 → 8.5 pt). The baseline moves by the stated fraction of the run size: `baseline="30000"` raises 18 pt text by 5.4 pt, `-25000` lowers it by 4.5 pt. | [I-010](issues/I-010.md) |
| A letter followed by a hyphen-minus is not kerned (`T-`, `r-`, `V-`). Pairs with en and em dashes are kerned as usual. | [I-011](issues/I-011.md) |
| In a box with `wrap="none"`, trailing spaces count in the line width for centred and right-aligned lines, on every line, including one that ends at `<a:br/>`. In a wrapped box they do not count, even when the text fits on one line. | [I-013](issues/I-013.md) |
| Underlines and strikethroughs are filled bars sized from the face's own metrics, on a 1/600-inch (0.12 pt) grid counted from the text box. The baseline is rounded down to the grid. The underline's top is `post.underlinePosition` below it and the bar is `post.underlineThickness` thick. The strike's top is OS/2 `yStrikeoutPosition` above it and the bar is `yStrikeoutSize` thick. Each value is scaled to the run size and rounded to whole grid steps. So Calibri Bold strikes, and Times New Roman Bold and Arial Bold underlines, are thicker than regular ones. A strike follows its own run (a superscript's at 2/3 size on its raised baseline), and so does a subscript's underline. A superscript's underline stays on the line's baseline at the full run size. Touching underlines on one baseline become one bar: its top and bottom are the runs' width-weighted means, each rounded. `dblStrike` draws two bars of the strike's thickness, directly above and below the single strike's place. | [K4](issues/K4.md) |

## Not implemented yet

### Text

| Rule | Issue |
|---|---|
| Glyphs are drawn (not laid out) at 600 dpi: the PDF's font size is the run size rounded to 1/600 inch (13.5 → 13.56, 12.75 → 12.72, 40 → 39.96) and the glyphs inside a word sit at 600-dpi rounded advances. The difference from the 1/576-inch layout is absorbed by the spaces, so word starts follow the layout. Not reproduced: the differences are below 0.06 pt, invisible at the review resolution. | [K2](issues/K2.md) |
| `u="dbl"` and `u="heavy"` underlines (measured once, 24 pt Calibri, in grid steps below the baseline): `dbl` is two bars 10–17 and 29–36 (the single underline is 23–36), and `heavy` is one bar 10–30. Euro-Office draws both as a single underline. The review deck uses neither. | [K4](issues/K4.md) |
| A line that mixes fonts is only a little taller than a line in its main font: 13.5 pt Calibri with an Arial run is 0.04 pt taller, with its baseline 0.16 pt lower (measured once; the rule is not known yet). | [I-020](issues/I-020.md) |
| Hebrew letters that combine with a mark into one glyph (bet with dagesh) are drawn with the mark. | [I-021](issues/I-021.md) |
| Run-level effects (`a:rPr/a:effectLst`, such as `outerShdw`) are drawn: a blurred, offset copy of the text. | [I-015](issues/I-015.md) |
| With `normAutofit lnSpcReduction`, the first baseline moves up by about 0.21 em at 80% spacing (low confidence). Line spacing other than 100% also moves the first baseline: at `lnSpc` 150% it sits 7.6 pt lower at 18 pt and 5.64 pt lower at 13.5 pt (both about 0.42 em), and exact 20 / 21 pt spacing puts it 0.36 / 0.18 pt higher than Euro-Office does. | [I-017](issues/I-017.md) |

### Lines, shapes and pictures

| Rule | Issue |
|---|---|
| When no join is specified, strokes use a round join; `<a:miter/>` gives a miter join. Seen once: `rightArrow` strokes with a miter join anyway. | [I-008](issues/I-008.md) |
| `outerShdw` uses `blurRad`: the shadow is a blurred silhouette. | [I-014](issues/I-014.md) |
| Elliptical arcs become cubic Béziers with control length k = 4/3·tan(Δθ/4) over the parametric sweep. | [I-019](issues/I-019.md) |
| Pictures are drawn as clipped images, not tiling-pattern fills. A PNG stays lossless in the PDF. | [K6](issues/K6.md) |
