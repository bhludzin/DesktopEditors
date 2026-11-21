export const meta = {
  name: 'slide-review',
  description: 'Compare every slide of the deck in PowerPoint vs Euro-Office and record each remaining difference',
  phases: [
    { title: 'Review', detail: 'one reviewer per batch of neighbouring slides' },
    { title: 'Retry', detail: 'slides a reviewer missed' },
  ],
}

const ROOT = 'C:\\Documents\\Projects\\PPTX\\fidelity-work\\decks\\great-roll'
const TOOL = '"C:\\Documents\\Projects\\PPTX\\DesktopEditors\\fidelity\\ssim-compare\\target\\release\\slide-diff.exe"'
const BATCHES = args.batches

const KNOWN = `Known recurring issues (found in a pilot review). Tag them; do not re-measure them in depth:
K1 arrowhead oversize: triangle line ends (headEnd/tailEnd type="triangle", seen with w="med" len="med") are drawn about 1.5x too large in Euro-Office (e.g. 11 px wide vs 7.4 px for a 2.25 pt line) and the tip overshoots the line's end point by 2-4 px. Seen on prstGeom line, straightConnector1, arc and custGeom. List every affected object as a finding (category connector-arrow, severity major, known "K1", one short sentence of detail). Any other line-end type (stealth, arrow, oval, diamond) or size that does not fit this pattern is a NEW finding: measure and describe it fully.
K2 glyph-advance drift: where line breaks match, glyphs drift along a line by up to about 1.5 px (Euro-Office's advances for regular Calibri are slightly smaller; bold can drift slightly the other way), giving red/blue fringes on letters and lines that end 0-1.5 px early. Tag it once per slide in "known" with the objects and the largest drift seen. It becomes a finding only if drift exceeds 2 px or changes a line break.
K3 borderline wrap: Euro-Office fits one more word (or one fewer) on a line than PowerPoint, and the rest of that paragraph reflows. Always a full finding (category text-wrap, severity major, known "K3") naming the first line that differs and the words that move.
K4 underline: underlines sit about 0.6 px higher and about 0.1 px thinner. Tag in "known".
K5 tiny vertical text offsets: whole lines 0.3 px or less higher or lower. Tag in "known".
K6 picture resampling: a picture in the same place and size, interpolated slightly more smoothly. Tag in "known".
Anything else is NEW: describe it fully. New problems are the most valuable part of this review.`

function reviewPrompt(batch, slides) {
  return `You are reviewing how Euro-Office (an open-source office suite we are fixing) renders slides of a PowerPoint deck, compared with PowerPoint itself, which is the ground truth. Engineers will work through your record to fix Euro-Office, so every real visual difference matters and each finding must be specific and checkable.

Working directory for all relative paths: ${ROOT}
Your slides: ${slides.join(', ')}
Write your result to: review/findings/batch-${batch}.json

For each slide N (NNNN = N with 4 digits):
1. Read review/slides/NNNN.json: scores; the text lines that differ (lines_only_in_powerpoint / lines_only_in_euro_office, from PDF text extraction, so treat them as hints: rotated text often extracts differently without any visual difference); the changed regions (n, px box in the 800x600 sheet space, frac box, and the objects each overlaps); and every drawing object (id, name, kind, box_px in 800x600 space, rotation, placeholder, text excerpt, font sizes, autofit, line_ends, ...).
2. Look at the sheet review/sheets/pNNNN.png (the Read tool shows images). It has four 800x600 panels: top-left PowerPoint, top-right Euro-Office, bottom-left the difference map (red = ink only in PowerPoint, blue = ink only in Euro-Office, gray = unchanged, green boxes = the 12 largest regions), bottom-right a 50/50 blend (doubled edges = offsets).
3. Zoom in on everything that is not plainly K2/K5 fringe noise:
   ${TOOL} crop review/hires/ppt/pNNNN.png review/hires/eo/pNNNN.png <x0> <y0> <x1> <y1> review/crops/NNNN-<k>.png
   Coordinates are fractions (0..1) of the slide; start from a region's frac and widen it a little. The crop shows PowerPoint, then Euro-Office, then the difference map (left to right, or top to bottom for wide boxes). Read it. Compare like with like: the same line, the same word.
   Measuring helpers (run with plain "python", not "python -I"; coordinates in 800x600 sheet px; they read the 1600-px renders):
   python review/tools/meas.py N x0 y0 x1 y1   -> text-line bands with ink extents and centroids, PowerPoint vs Euro-Office
   python review/tools/drift.py N x0 y0 x1 y1 [window]   -> horizontal/vertical shift of Euro-Office vs PowerPoint along the box, by cross-correlation
   Give offsets in pixels of the 800-px sheet (1 px is about 0.9 pt).
4. Explain each new difference from the XML. The slide is review/xml/ppt/slides/slideN.xml (pretty-printed); layouts, masters and the theme are under review/xml/ppt/ (the facts give the layout's path). These files can be long, so Grep for the object's cNvPr id or name with context instead of reading whole files. Note the properties that matter (bodyPr insets/anchor/wrap/autofit, lnSpc/spcBef/spcAft, algn, marL/indent, buChar/buAutoNum, rPr sz/b/i/u/kern/spc/baseline/latin, xfrm rot/flipH/flipV, prstGeom, ln w/headEnd/tailEnd, srcRect, ...), including values inherited from the layout, master or presentation defaults when they matter.

${KNOWN}

What counts as a finding: any difference a careful viewer could see at normal size or zoomed in that is not a K2/K4/K5/K6 tag. Examples: different line breaks; a line or paragraph at a different height; a block shifted; different spacing between characters beyond K2; a different font, size or weight; colors; bullets or numbering (glyph, size, position, indent); shape outline or fill; arrowheads; connector routes; image crop, scale or position; missing or extra elements; rotated or flipped items placed differently; table borders or cell padding. Do not report pure anti-aliasing (faint fringes on glyphs that sit in the same place).
One finding = one distinct difference on one object. If a text box both wraps differently and has larger line spacing, that is two findings. If the same new difference repeats on several identical objects of one slide (e.g. four identical labels), report it once and name the other objects in "detail".

category (exactly one): text-wrap, text-line-spacing, text-position, text-glyph-spacing, font, text-decoration, text-color-effects, bullets-numbering, shape-geometry, shape-fill-line, connector-arrow, picture, table, group-transform, background, missing-element, extra-element, other.
severity: major = visible at normal size (different line breaks, an element missing or misplaced by more than about 3 px, wrong font, wrong arrowhead); minor = visible when looking closely (1-3 px offsets, slightly different spacing); trivial = sub-pixel, visible only in the difference map.
A slide whose only differences are K2/K4/K5/K6 tags gets verdict "match" (with its tags in "known") and no findings.

Output file (write it with Python: json.dump(data, f, ensure_ascii=False, indent=1), UTF-8, so it is valid JSON). Rewrite the whole file after each slide so progress is not lost:
{"batch": "${batch}", "slides": [{"slide": 297, "verdict": "differs", "summary": "one sentence", "known": [{"id": "K2", "objects": ["6:Rectangle 5"], "note": "drift up to 0.9 px"}], "findings": [{"category": "...", "severity": "...", "known": null, "object": "6:Rectangle 5", "region": 1, "powerpoint": "what PowerPoint shows", "euro_office": "what Euro-Office shows", "detail": "measurements, lines, words", "xml_evidence": "the XML that matters", "suspected_cause": "what Euro-Office likely does wrong", "confidence": "high|medium|low"}]}]}
("known" in a finding is "K1"/"K3" or null; "region" is the facts' region n, or null.)

Spend your effort where it pays: new kinds of difference get careful measurement and XML evidence; known issues get a tag or a one-line finding. Do not modify anything outside review/findings and review/crops (you may write temporary scripts in your own scratch space). Your final answer is the structured summary; keep its notes under 600 characters and use them for new problems that recur or for trouble with the tools.`
}

const SUMMARY = {
  type: 'object',
  properties: {
    batch: { type: 'string' },
    slides_reviewed: { type: 'array', items: { type: 'integer' } },
    findings: { type: 'integer' },
    new_findings: { type: 'integer', description: 'findings that are not K1/K3' },
    notes: { type: 'string' },
  },
  required: ['batch', 'slides_reviewed', 'findings', 'new_findings', 'notes'],
}

const pad = (n) => String(n).padStart(3, '0')
phase('Review')
log(`${BATCHES.length} batches, ${BATCHES.flat().length} slides`)
const first = await parallel(BATCHES.map((slides, i) => () =>
  agent(reviewPrompt(pad(i + 1), slides), { label: `batch ${pad(i + 1)}: slides ${slides[0]}-${slides[slides.length - 1]}`, phase: 'Review', schema: SUMMARY })))

const missing = []
BATCHES.forEach((slides, i) => {
  const done = new Set((first[i] && first[i].slides_reviewed) || [])
  const left = slides.filter((s) => !done.has(s))
  if (left.length) missing.push({ batch: pad(i + 1) + 'r', slides: left })
})
let retry = []
if (missing.length) {
  phase('Retry')
  log(`retrying ${missing.flatMap((m) => m.slides).length} slides from ${missing.length} batches`)
  retry = await parallel(missing.map((m) => () =>
    agent(reviewPrompt(m.batch, m.slides), { label: `batch ${m.batch}: slides ${m.slides.join(',')}`, phase: 'Retry', schema: SUMMARY })))
}

const all = [...first, ...retry].filter(Boolean)
const reviewed = new Set(all.flatMap((r) => r.slides_reviewed))
return {
  batches_ok: all.length,
  slides_reviewed: reviewed.size,
  still_missing: BATCHES.flat().filter((s) => !reviewed.has(s)),
  findings: all.reduce((a, r) => a + r.findings, 0),
  new_findings: all.reduce((a, r) => a + r.new_findings, 0),
  notes: all.filter((r) => r.notes && r.notes.trim()).map((r) => `${r.batch}: ${r.notes.slice(0, 400)}`),
}
