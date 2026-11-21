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
**I-001…** were found by the review, numbered by severity and reach; **F-001…** were fixed
before the review.

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

## Where things stand (2026-11-21)

- Fixed: F-001 kerning, F-002 script itemization, F-003 line width, and I-001 fractional font
  sizes (sdkjs 414ae64bd0). Text lines breaking like PowerPoint rose from
  87.1% (release 9.3.8) to 96.7%, slides with identical line breaks from 443 to 673 of 835,
  and mean SSIM from 0.890 to 0.957.
- Biggest open issues:
  - **K2** glyph advances: long lines drift and borderline words wrap differently.
  - **K1** triangle arrowheads too big.
  - **K3** the 0.25 pt width reduction. It is coupled to K2: change and measure them together.
  - **I-007** default outline width of 1 pt instead of 0.75 pt.
