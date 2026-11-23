# Specs: rendering PowerPoint decks like PowerPoint

This fork aims to render `.pptx` files the way PowerPoint does. These specs record every known
way Euro-Office still differs from PowerPoint, why it differs, and what has been fixed. They are
the working list: pick an issue, fix it in `sdkjs`, verify it with the fidelity harness, then
update the tracker.

The differences were found by comparing every slide of an 838-slide test deck (dense text,
connectors, groups, pictures) as rendered by PowerPoint (its own PDF export, the ground truth)
and by Euro-Office. The deck is not in the repo. The harness keeps it, the renders and the
slide images in a private work folder (`../fidelity-work`).

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
**I-001…I-019** were found by the review, numbered by severity and reach; **I-020** onwards
turned up while fixing them; **F-001…** were fixed before the review.

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

## Where things stand (2026-11-22)

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
- Open: no major issues are left. Regular 12.75 pt text still runs about 0.1% long
  (slide 255). Slide 93 still breaks one line differently (a K2 residual under 0.01 pt), and 674
  differs only in its extracted Hebrew text.
