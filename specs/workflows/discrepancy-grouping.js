export const meta = {
  name: 'discrepancy-grouping',
  description: 'Group the slide-review findings into root-cause issues with code locations, then merge issues across categories',
  phases: [
    { title: 'Group', detail: 'one agent per category group: cluster findings by root cause, locate the code' },
    { title: 'Combine parts', detail: 'merge the two halves of the largest category' },
    { title: 'Consolidate', detail: 'find issues in different groups that share a root cause' },
  ],
}

const R = 'C:/Documents/Projects/PPTX/fidelity-work/decks/great-roll/review'
const SDK = 'C:/Documents/Projects/PPTX/DesktopEditors/sdkjs'

const KNOWN = `Known issues the reviewers were given (K-ids):
K1 arrowhead oversize: triangle line ends (headEnd/tailEnd type="triangle") drawn about 1.5x too large in Euro-Office and the tip overshoots the line end by 2-4 px. Reviewers listed every affected object as a finding (known "K1").
K2 glyph-advance drift: where line breaks match, glyphs drift along a line by up to ~1.5 px (Euro-Office's advances for regular Calibri slightly smaller; bold can drift the other way). Slide-level tag only; became a finding when drift > 2 px or it changed a line break.
K3 borderline wrap: Euro-Office fits one more word (or one fewer) on a line than PowerPoint and the paragraph reflows. Always a finding (known "K3"). Background: kerning from a:rPr/@kern was just fixed; the remaining K3 cases were thought to be lines where the extra word fits by under ~0.5 pt.
K4 underline ~0.6 px higher and ~0.1 px thinner (tag only). K5 whole lines 0.3 px or less higher/lower (tag only). K6 picture interpolated slightly more smoothly (tag only).`

const CONTEXT = `Context: an 838-slide PowerPoint deck was rendered by PowerPoint (its own PDF export, the reference) and by Euro-Office (an ONLYOFFICE fork; layout and drawing are in sdkjs, the JavaScript engine at ${SDK}, checked out on branch pptx-text-fidelity, READ ONLY - never edit, build or git-modify it). Reviewer agents compared every slide and wrote findings. You now turn findings into root-cause issues that a developer can fix one at a time in sdkjs.

${KNOWN}

Files under ${R}:
- by-category/<name>.json: findings, each {id, slide, category, severity, object, powerpoint, euro_office, detail, xml_evidence, suspected_cause, confidence}
- reviewer-notes.txt: each review batch's cross-slide notes (recurring patterns, measurements, code pointers some reviewers already found, e.g. ShapeDrawer.js falling back to 12700 EMU when a:ln has no w). Read it - grep it for your topic.
- sheets/pNNNN.png: 2x2 sheet per slide (PowerPoint | Euro-Office on top; difference map | blend below; in the map red = ink only in PowerPoint, blue = only in Euro-Office). 800 px per panel.
- hires/ppt/pNNNN.png and hires/eo/pNNNN.png: 1600 px renders. crops/NNNN-*.png: reviewers' magnified crops.
- slides/NNNN.json: facts per slide (objects with boxes, text lines from both renderers, regions). xml/: the slide, layout and master XML pretty-printed (slides/NNNN.json names the files).
- tools: C:/Documents/Projects/PPTX/DesktopEditors/fidelity/ssim-compare/target/release/slide-diff.exe crop <ref.png> <cand.png> x0 y0 x1 y1 <out.png> (fractions 0..1) makes a magnified PowerPoint | Euro-Office | map crop; python ${R}/tools/meas.py N x0 y0 x1 y1 measures ink in both hires renders.
Keep any helper scripts and crops of yours in your own folder ${R}/grouping/work-<your group name>/ (other agents run at the same time; never write anywhere else except your output file). Run Python as plain \`python\`.`

const ISSUE_FORMAT = `Output file format (JSON, UTF-8):
{"group": "<group name>", "issues": [{"key": "<group>/<n>" (or "K1".."K6" for the issue that IS that known issue), "title": "short statement of what Euro-Office does wrong", "severity": "major|minor|trivial" (major = a typical viewer notices at normal size, e.g. different line breaks, visibly wrong sizes; minor = visible when you look closely; trivial = sub-pixel/zoom-only), "categories": [...], "findings": ["S0123-1", ...], "description": "what differs, how often, magnitude", "powerpoint": "what PowerPoint does (the rule, with numbers)", "euro_office": "what Euro-Office does instead", "suspected_cause": "the mechanism", "code_area": "sdkjs file:function (line) where it happens, or 'not located'", "fix_idea": "concrete change to try", "confidence": "high|medium|low", "representative": [2-4 finding ids that show it best]}], "rejected": [{"id": "S0123-1", "reason": "why this is not a real Euro-Office difference"}]}`

const RULES = `How to group:
1. Read every finding in your input (use Python to tabulate fields if the file is long). Read reviewer-notes.txt for your topic.
2. Cluster by ROOT CAUSE - the one thing Euro-Office does wrong that a single code change would fix - not by surface symptom or slide. Findings that differ only in magnitude, object or slide belong together. Use the XML evidence (attributes such as ln w, spcBef/spcAft, lnSpc, buSzPct, marL/indent, bodyPr insets/anchor, normAutofit fontScale/lnSpcReduction, sz values, rot, kern, font face) to tell different causes apart, and split a cluster when the XML shows two different mechanisms.
3. Where a cluster or finding is unclear, look at 1-3 representative sheets/crops (or make a crop) and check the XML yourself. If, after looking, a finding is not a real Euro-Office rendering difference (pure anti-aliasing, reviewer misread, the same in both renders), put it in "rejected" with the reason. Do not reject merely because it is small.
4. For each issue, find where sdkjs implements the behaviour (grep ${SDK}; drawing is mostly in common/Drawings and word/Drawing, text layout in word/Editor/Paragraph*.js and common/Shapes, file reading in common/Shapes/Serialize.js) and give file:function (line) plus a concrete fix idea. Spend at most a few minutes per issue; say 'not located' rather than guess.
5. Every input finding id must appear exactly once: in one issue's "findings" or in "rejected". Before finishing, check this with a Python script (input ids == assigned + rejected, no duplicates) and fix any mismatch.
${ISSUE_FORMAT}`

const SUMMARY = {
  type: 'object',
  properties: {
    file: { type: 'string' },
    issues: { type: 'integer' },
    assigned: { type: 'integer' },
    rejected: { type: 'integer' },
    titles: { type: 'array', items: { type: 'string' } },
  },
  required: ['file', 'issues', 'assigned', 'rejected', 'titles'],
}

const GROUPS = [
  { name: 'arrows', files: ['known-K1.json', 'connector-arrow.json'], focus: 'Line ends and connectors. Check whether all K1 findings really share one mechanism (reviewers noticed the excess is a constant ~1.45 line widths at med and lg sizes, consistent with the filled head also being stroked with the line pen with miter joins; and a different ratio on 0.75 pt lines). Keep the issue that is K1 under key "K1"; split real outliers (other sizes, types, thin-line minimum) into their own issues only if a different code change is needed.' },
  { name: 'wrap-k3', files: ['known-K3.json'], focus: 'Line-break differences tagged K3. Do not assume they all have one cause: for each, look at the measurements in detail (how much room was left, font, size, bold, kern attribute present or not, punctuation at the break, run boundaries, sz values like 1275, space-only paragraphs, bullets/indent). Split into causes such as: wrap decided by accumulated glyph-advance drift on long lines (K2 mechanism), font-size rounding, break-opportunity rules (e.g. no break before "."), width or inset differences, residual borderline. The issue for genuinely borderline lines keeps key "K3".' },
  { name: 'wrap-other', files: ['text-wrap.json'], focus: 'Line-break differences reviewers did NOT tag as K3. Find their distinct causes (break-opportunity rules, size rounding, widths, autofit, etc.).' },
  { name: 'vertical', files: ['text-line-spacing.json', 'text-position.json'], focus: 'Vertical text layout: line pitch, paragraph spacing, empty or space-only paragraphs, anchoring, insets, autofit, baseline position.' },
  { name: 'glyphs-fonts', files: ['text-glyph-spacing.json', 'font.json', 'text-color-effects.json', 'text-decoration.json'], focus: 'Glyph advances, kerning, font selection and size (e.g. sz=1275 drawn as 13 pt), bold/italic, strikethrough/underline, text colour and effects. Glyph drift beyond 2 px is likely the K2 mechanism - say so and key that issue "K2" if it is the same cause.' },
  { name: 'pictures-misc', files: ['picture.json', 'shape-geometry.json', 'other.json'], focus: 'Pictures (edges, cropping, scaling, the unpainted last column at x=799 in 800-px renders), shape geometry and anything else.' },
  { name: 'outlines', parts: ['shape-fill-line.part1.json', 'shape-fill-line.part2.json'], focus: 'Shape outlines and fills. Reviewers found a recurring default 0.75 pt outline (a:ln with no w) drawn about 1 pt / 2-3 px thick; verify the cause in sdkjs (ShapeDrawer.js 12700 fallback) and check what PowerPoint uses as the default width, and whether pixel-snapping is a separate cause. Separate any other outline/fill causes.' },
]

const groupPrompt = (g, files, outFile, part) => `${CONTEXT}

Your group: "${g.name}"${part ? ` (part ${part} of the findings; another agent has the other part - group only yours)` : ''}. Input: ${files.map(f => `${R}/by-category/${f}`).join(', ')}.
Focus: ${g.focus}

${RULES}

Write your result to ${R}/grouping/${outFile} and return a short summary.`

phase('Group')
const results = await pipeline(
  GROUPS,
  async g => {
    if (!g.parts) {
      return agent(groupPrompt(g, g.files, `${g.name}.issues.json`), { label: `group: ${g.name}`, phase: 'Group', schema: SUMMARY })
    }
    const parts = await parallel(g.parts.map((f, i) => () =>
      agent(groupPrompt(g, [f], `${g.name}.part${i + 1}.issues.json`, i + 1), { label: `group: ${g.name} part ${i + 1}`, phase: 'Group', schema: SUMMARY })))
    return agent(`${CONTEXT}

Two agents grouped the two halves of the "${g.name}" findings (${g.parts.map(f => `${R}/by-category/${f}`).join(', ')}) into issues, written to ${g.parts.map((_, i) => `${R}/grouping/${g.name}.part${i + 1}.issues.json`).join(' and ')}. Combine them into one file: merge issues from the two halves that share a root cause (union their findings, keep the better-evidenced text, re-number keys as "${g.name}/<n>"), keep the rest. Re-check any root-cause claim the halves disagree on against sdkjs and the images. Every finding id from both input files must appear exactly once (in an issue or in rejected) - verify with Python.
Focus: ${g.focus}
${ISSUE_FORMAT}

Write ${R}/grouping/${g.name}.issues.json and return a short summary.`, { label: `combine: ${g.name}`, phase: 'Combine parts', schema: SUMMARY })
  },
)
const done = results.filter(Boolean)
log(`${done.length}/${GROUPS.length} groups written; ${done.reduce((a, r) => a + r.issues, 0)} issues`)

phase('Consolidate')
const MERGES = {
  type: 'object',
  properties: {
    merges: { type: 'integer' },
    file: { type: 'string' },
    notes: { type: 'string' },
  },
  required: ['merges', 'file'],
}
const consolidated = await agent(`${CONTEXT}

Agents have grouped all findings into root-cause issues, one file per group: ${GROUPS.map(g => `${R}/grouping/${g.name}.issues.json`).join(', ')}. Issues in different groups may share one root cause (e.g. glyph drift that causes both a wrap issue and a glyph-spacing issue; an outline width issue that shows up in pictures and shapes; the same font-size rounding seen in wrap and font groups; a space-only paragraph height issue seen in vertical and wrap groups). Find those: read every issue (title, description, suspected_cause, code_area, a few findings), check against sdkjs or the images when unsure, and decide which issues should be merged because ONE code change would fix them. Do not merge issues that merely look alike or share a category. Also flag any issue whose cause looks wrong to you.
Tag-only known issues that have no issue entry yet: K2, K4, K5, K6 (definitions above). An issue that is the same as one of them may be merged "into" that K-id.

Write ${R}/grouping/merges.json: {"merges": [{"into": "<key that survives, or K2/K4/K5/K6>", "absorb": ["<other keys>"], "title": "new title if the merged issue needs one, else null", "suspected_cause": "combined cause if it changes, else null", "why": "evidence they share a cause"}], "doubts": [{"key": "...", "note": "..."}]}. Return a short summary.`, { label: 'consolidate across groups', phase: 'Consolidate', schema: MERGES })

return { groups: done, consolidated }
