# Specs: rendering PowerPoint decks like PowerPoint

This fork aims to render `.pptx` files the way PowerPoint does. These specs record every known
way Euro-Office still differs from PowerPoint, why it differs, and what has been fixed. They are
the working list: pick an issue, fix it in `sdkjs`, verify it with the fidelity harness, then
update the tracker.

The differences were found by comparing every slide of an 838-slide test deck (dense text,
connectors, groups, pictures) as rendered by PowerPoint (its own PDF export, the ground truth)
and by Euro-Office. The deck is not in the repo. The harness keeps it, the renders and the
slide images in a private work folder (`../fidelity-work`).

After K6 a later, 1646-slide version of the deck (377 slides the same, 75 with changed
text, 1194 new) was compared slide by slide in the same way. Its results are in
[results.md](results.md), and what it added is in I-027 and in the logs of K2 and I-015.

## Contents

| File | What it is |
|---|---|
| [issues/README.md](issues/README.md) | All issues, open ones first, with their status, severity and slide counts |
| [issues/](issues/) | One spec per issue: what differs, what PowerPoint does, what Euro-Office does, suspected cause, where in `sdkjs`, fix idea, open questions, slides, findings |
| [issues.json](issues.json) | **The tracker** (source of truth for the issue pages): edit `status`, `fixed_in` and `log` here |
| [findings.json](findings.json) | Every reviewed slide with its verdict and every finding (measurements, XML evidence, object), each stamped with its issue |
| [slides.md](slides.md) | Every slide with a finding, and its issues |
| [powerpoint-behaviour.md](powerpoint-behaviour.md) | The PowerPoint rendering rules measured so far, implemented or not |
| [results.md](results.md) | Scores of each harness run against PowerPoint |
| [methodology.md](methodology.md) | How the comparison and the review were done, and how to re-run them |
| [workflows/](workflows/) | The Claude Code workflow scripts that ran the slide review and the root-cause grouping |

Issue ids: **K1–K6** were known before the full review (from a pilot) and kept their ids;
**I-001…I-019** were found by the review, numbered by severity and reach; **I-020…I-026**
turned up while fixing them; **I-027** onwards came from the 1646-slide deck; **F-001…** were
fixed before the review.

## Working through an issue

1. Read `issues/<id>.md`. Its slides link to the side-by-side sheets in the work folder
   (PowerPoint | Euro-Office on top; difference map, where red is ink only PowerPoint has and
   blue is ink only Euro-Office has; and a blend).
2. Fix it in `sdkjs` (a branch off `pptx-text-fidelity` for now).
3. `python fidelity/fidelity.py loop <deck> --label <name>` builds `sdkjs`, renders the deck,
   and scores it against PowerPoint and the baseline run. The issue's slides should improve
   and no slide should get worse.
4. In `issues.json`, set `status` to `fixed`, fill in `fixed_in` (the commit) and add a `log`
   entry with the numbers. Then run
   `python fidelity/review_record.py <work>/decks/<deck> specs` to refresh these pages.
5. Add the new run to [results.md](results.md).

Statuses: `open`, `in-progress`, `fixed`, `wontfix`, `not-a-bug`.

## Where things stand (2026-11-23)

- Fixed: F-001 kerning, F-002 script itemization and F-003 line width (sdkjs 7898a3e982),
  I-001 fractional font sizes (414ae64bd0), I-007 default outline width 0.75 pt (7e6a447d83),
  I-012 picture outlines outside the picture (555e9eabe3), K1 filled triangle arrowheads
  (44cdab9e9f), K2 + K3 (e84bfe4efb): PowerPoint lays text out in whole 1/576-inch units
  (each glyph advance rounded, kerning added exactly, the text width rounded down), which
  replaces F-003's fitted 0.25 pt reduction, and I-002 + I-003 + I-009 (42d5db5758): spaces
  size their line, paragraph spacing after and before are added, and point spacing is used
  in whole points. I-004 + I-005 + I-006 (d3452db46b): a line may start after any space,
  kerning applies across spaces, and complex-script runs use the theme's script font for
  their language, with right-to-left text no longer garbled. I-010 + I-011 + I-013 +
  I-022 (4c3273edbc): superscripts at 2/3 size with the stated raise, no kerning
  into a hyphen, trailing spaces counted when aligning in `wrap="none"` boxes, and a line
  break allowed after an en dash. K4 (88cc4cc6cb): underlines and strikethroughs
  placed and sized from the font's own metrics, as PowerPoint does. I-017 (38734b3eb3 and
  472ee0b1ae): lines under line spacing other than 100% placed as PowerPoint does. I-016 + I-020
  (a9856eee47): a font's line split at its win ascent and descent, and a line that mixes
  fonts sized as PowerPoint sizes it. I-008 (7937b6f01f): outlines with no line join
  stroked round, as PowerPoint does, with its 31 mitered presets. Text lines breaking like
  PowerPoint rose from 87.1% (release 9.3.8) to 99.97%, slides with identical line breaks
  from 443 to 784 of 835, and mean SSIM from 0.890 to 0.989 (run i008-c). The harness
  renders with a font list made from this PC's fonts (I-023, b3dfc7b), so fonts
  installed only here (Office fonts, Aptos) are no longer substituted in its renders.
  I-021 (core 2d4497c536, the first fix in the native code): every font embedded in
  Euro-Office's PDF had a `cmap` that ran past its end, so Windows drew all PDF text with
  system fonts and a composed bet with dagesh lost its dot. The harness renders with a
  local core build for this (`fidelity.py --core`); mean SSIM 0.9891 (run i021-c).
  I-014 (39a69b18c4): outer shadows with a blur drawn as PowerPoint draws them, a
  silhouette blurred with a Gaussian of blurRad / 3 at PowerPoint's image resolution
  (run i014-c; the 11 slides with such shadows closer, none worse).
  K5 (f1e24ab652): each line's baseline placed as PowerPoint places it, a whole number of
  1/600 inch below the top of the text, with its PDF's slight stretch and 1/3000-inch grid;
  99.1% of the deck's lines now sit on PowerPoint's baseline, against 12.7% before, and mean
  SSIM rose to 0.9920 (run k5-c). I-018 (the centred title on slides 35 and 36) turned out
  fixed by K2 + K3.
  K6 (core 88cf859ae7, in the PDF writer): pictures drawn as images clipped to their shape,
  as PowerPoint draws them, instead of tiling-pattern fills, and encoded as PowerPoint
  encodes them (lossless when they have few colours, otherwise JPEG at quality 75, cropped
  to what is shown, transparency premultiplied with a matte). Picture edges are no longer
  half transparent, and inside pictures the difference to PowerPoint fell from 1.93 to 0.55
  levels; mean SSIM 0.9925, 97 slides closer and none worse (run k6-c).
  I-027 (d90da7a1d0): text drawn in glyph runs on PowerPoint's PDF grid, as its PDF draws it:
  line starts stretched slightly about the slide's left edge and rounded to 1/3000 inch, and
  a run that starts just past a grid step drawn one step longer per glyph. Long lines no
  longer drift by up to 1.6 pt: on the 1646-slide deck lines more than 1 pt off fell from 311
  to 30 and mean SSIM rose to 0.9929 (run i027-h, 90 slides closer, none worse by more than
  0.01); on the 838-slide deck 0.9937.
  I-024 (f53e0a4a15): each glyph drawn where PowerPoint's 600-dpi device and PDF writer put
  it (whole-pixel advances held near the layout, word starts on the nearest pixel, and the
  writer's adjustments made only once they reach 3 units of 1/1000 em, so lines come out a
  little shorter than their layout, by font and size). Glyphs within 0.03 pt of PowerPoint's
  rose from 20% to 84%; mean SSIM 0.9978 on both decks (run i024-c: 237 slides closer on the
  1646-slide deck, 66 on the 838-slide deck, none worse by more than 0.006).
- A third deck, 3963 slides in the same series and nearly all new, was reviewed slide by slide
  after I-024 (run i024-c: mean SSIM 0.9968 against the release's 0.8145; 3798 of 3839 slides
  break lines like PowerPoint). New open issues: major I-029 (colour emoji drawn as outlines),
  I-030 (picture clrChange, duotone and lum ignored), I-031 (lines over by under 0.005 pt no
  longer wrapped, a regression since the release), I-032 (scene3d camera rotation, so pictures
  are not mirrored), I-033 (an opening quote before spaces cannot end a line), I-034 (negative
  first-line indent not clamped); minor I-035 to I-040 (glyph drift left by I-024 and I-027,
  spc runs, scene3d lighting, JPEG where PowerPoint keeps pictures lossless, a Japanese font);
  trivial I-041.
  I-031 (c845723170): slide text widths rounded, not cut, so lines are measured exactly as
  K2 has them; 471 and 2822 and I-028's lines on 93 and 906 now break like PowerPoint. What is
  left of I-028 is 6 slides within 0.005 pt of the edge, 3 each way (now trivial).
  I-029 (d18576da6a): glyphs of a colour font (Segoe UI Emoji) drawn in their colours, as their
  COLR layers in palette 0, where they were black outlines; the knife emoji on 11 slides of
  the 3963-slide deck now matches PowerPoint's, and nothing else changes.
  I-030 (429072eb3f): pictures' colour change, brightness/contrast and duotone applied as
  PowerPoint does (colour changes first, on the original pixels, then the rest in order); the
  5 slides of the 3963-slide deck that use them now match PowerPoint's pictures, and nothing
  else changes.
  I-032 (1587814993): flat shapes and pictures drawn as their scene3d camera sees them (mirrored,
  turned or foreshortened, text included), and square-on pictures lit as PowerPoint lights them;
  the two mirrored pictures of the 3963-slide deck (931, 1046) now match PowerPoint's, and
  nothing else changes.
- Open: I-028 (trivial): line breaks within 0.005 pt of the edge (slides 15, 1308, 1564 of the
  1646-slide deck, 806 of the 838-slide deck, 962 and 3185 of the 3963-slide deck).
  Run-level text shadows are still not drawn (I-015; 11 slides of the new deck). Slide 674
  differs only in its extracted Hebrew text. PowerPoint's PDF downsamples pictures drawn
  above about 270 dpi to 200 dpi (I-025) and draws a flipped tiled picture unmirrored
  (I-026).
