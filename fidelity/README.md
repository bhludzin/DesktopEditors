# Rendering fidelity harness

Measures how closely Euro-Office renders a PowerPoint deck compared with
Microsoft PowerPoint itself, slide by slide, and shows whether a change to
`sdkjs` (where text layout and line wrapping live) makes that better or worse.

For each deck it keeps PowerPoint's own PDF export as the reference, renders
the same deck with Euro-Office's headless converter (`x2t`), and scores every
slide two ways:

- **Line breaks** — the share of PowerPoint's text lines that Euro-Office ends
  on the same word (text pulled from both PDFs with `pdftotext -raw`). This is
  the measure to watch for text-layout work: it is exact and explainable.
- **Image similarity (SSIM)** — grayscale SSIM of 800-px-wide slide images,
  1.0 = identical. It catches non-text problems (shapes, pictures, connectors),
  but on dense text a 1–2 px shift in line spacing costs as much as a real
  wrapping error, so read it alongside the line-break score.

## Your decks stay out of the repository

Decks and everything rendered from them live in a **work folder outside the
repo** — by default `../fidelity-work` next to this checkout (override with
`--work DIR` or the `FIDELITY_WORK` environment variable). Never copy a deck
or its renders into the repo.

```
fidelity-work/
  apps/euro-office-<version>/   released portable app (never modified)
  runtime/euro-office-<version>/  private converter copy that loads your sdkjs build
  fonts/                        font list made from this PC's fonts (see Fonts below)
  decks/<name>/
    deck.pptx                   copy of the deck (the original is never touched)
    baseline.txt                the run other runs are compared with
    reference/                  PowerPoint's PDF, slide images, text
    runs/<label>/               one folder per render: PDF, images, text, scores,
                                run.json (what produced it), sdkjs.diff (if uncommitted changes)
    compare/                    side-by-side images
```

## Requirements (Windows)

- **Microsoft PowerPoint** — only to export the reference, once per deck.
- **Euro-Office portable build** unpacked to `fidelity-work/apps/euro-office-<version>`
  (the `windows-x64.zip` asset of a [release](https://github.com/Euro-Office/DesktopEditors/releases)).
  Use the release that matches the `sdkjs` commit you are working from.
- **Python 3.9+**, **Node.js** (to build sdkjs), **Rust** via rustup
  (`ssim-compare/rust-toolchain.toml` pins the toolchain), and **pdftotext**
  (ships with Git for Windows).

## Setting up a deck

```powershell
# 1. Copy the deck in and export PowerPoint's reference (opens PowerPoint invisibly, read-only)
python fidelity/fidelity.py reference "C:\path\to\deck.pptx" --name my-deck

# 2. Render it with the released app; the first release run becomes the baseline
python fidelity/fidelity.py render my-deck --release
```

## The everyday loop

Edit sdkjs, then:

```powershell
python fidelity/fidelity.py loop my-deck
```

This builds `sdkjs`'s slide bundle exactly the way the desktop release is built
(`NODE_ENV=production SDK_PLATFORM=desktop`, about 25 s; an unmodified checkout
builds byte-for-byte identical to the released bundle), renders the deck with
it, scores every slide, and lists the slides that got better or worse than the
baseline. A full loop on an 800-slide deck takes about two minutes.

Then look at any slide side by side (PowerPoint, baseline, latest run):

```powershell
python fidelity/fidelity.py compare my-deck 523
python fidelity/fidelity.py compare my-deck 523 release-9.3.8 some-run   # pick runs
```

Other commands:

```powershell
python fidelity/fidelity.py runs my-deck               # every run with its headline scores
python fidelity/fidelity.py baseline my-deck <label>   # compare future runs with <label>
python fidelity/fidelity.py score my-deck <label>      # rescore one run
python fidelity/fidelity.py render my-deck --sdkjs <deploy dir>   # render any built sdkjs
python fidelity/fidelity.py render my-deck --sdkjs <deploy dir> --core <core bin dir>   # and a native core build
```

Each run records the sdkjs commit it was built from, and when the checkout has
uncommitted changes, the full diff (`sdkjs.diff`) — so every result can be
traced back to the code that produced it.

## Good to know

- **Development builds don't load in x2t.** x2t concatenates `sdk-all-min.js`
  and `sdk-all.js` into one script, and in development mode both declare
  webpack's runtime (`Identifier '__webpack_require__' has already been
  declared`). The loop therefore always makes a production build.
- **webpack's filesystem cache fails on Windows** (its folder names contain
  `:`), so every build is a cold build. Harmless, just slower; `loop --verbose`
  shows the warnings.
- **Hidden slides**: PowerPoint's PDF export may leave them out while x2t
  renders them, which misaligns the slides. The harness warns when the slide
  counts differ.
- **Fonts**: renders use a font list made from this PC's fonts, as the desktop
  app makes its own at start: `x2t -create-allfonts` writes `AllFonts.js` and
  `font_selection.bin` to `fidelity-work/fonts` (refreshed before every render,
  rewritten only when the installed fonts change), and x2t is pointed at that
  folder. It holds what PowerPoint can draw, Office's own fonts and its cloud
  fonts such as Aptos included. The list shipped in the app's converter was made
  on the build server and lacks them; `--shipped-fonts` renders with it, as runs
  made before this change did. `run.json` records which list a run used and its
  hash. Check that the fonts your deck uses are on this machine, or PowerPoint and
  Euro-Office will substitute differently.
- **Native code**: renders use the release's x2t and libraries unless `render` or
  `loop` is given `--core <folder>`, a native core build's folder of x2t and DLLs
  (its `package/bin`). Its `.dll` and `.exe` files are copied over a separate
  runtime copy (`runtime/<app>-core`), so runs without `--core` keep the release's
  native code. `run.json` records the folder, a hash of its files and the note in
  its `core-commit.txt`, if it has one. Build core the way the release does: x64
  Release with the shared C runtime (`-DCMAKE_POLICY_DEFAULT_CMP0091=NEW`; core's
  own top-level CMake otherwise links every DLL with its own static runtime, and
  that x2t crashes). Built that way, the release's core commit renders the same
  scores and text as the release.
- **macOS / Linux**: the scoring parts (`fidelity.py score`, `ssim-compare`,
  `pdftotext`) are cross-platform, but exporting the reference, rendering with
  x2t and rasterizing are Windows-only for now.
