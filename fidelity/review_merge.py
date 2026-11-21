#!/usr/bin/env python3
"""Merges reviewers' per-batch findings into one discrepancy record.

    python fidelity/review_merge.py <deck-dir>

Reads <deck-dir>/review/findings/batch-*.json and review/index.json; writes
  review/discrepancies.json  every slide with its verdict, known-issue tags and
                             findings; each finding gets an id (S0297-1) and
                             status "open"
  review/by-category/<category>.json  findings grouped by category, with the
                             ones tagged as known issues in known-K<n>.json
                             (input for root-cause grouping)
and prints coverage and counts. A slide reported by two batch files keeps the
entry from the batch review/batches.json assigned it to.
"""
import collections
import json
import re
import sys
from pathlib import Path

SEVERITIES = ('major', 'minor', 'trivial')


def pilot_to_tags(slide):
    """The pilot predates known-issue tags; map its findings onto them."""
    known, findings = collections.defaultdict(lambda: {'objects': [], 'note': ''}), []
    for f in slide.get('findings', []):
        cat, sev, text = f['category'], f['severity'], ' '.join(str(f.get(k, '')) for k in ('euro_office', 'detail'))
        tag = None
        if cat == 'text-glyph-spacing' and sev in ('trivial', 'minor'):
            tag = 'K2'
        elif cat == 'text-decoration' and 'underline' in text.lower() and sev == 'trivial':
            tag = 'K4'
        elif cat == 'text-position' and sev == 'trivial':
            tag = 'K5'
        elif cat == 'picture' and sev == 'trivial':
            tag = 'K6'
        if tag:
            known[tag]['objects'].append(f['object'])
            continue
        if cat == 'connector-arrow' and 'arrowhead' in text.lower():
            f['known'] = 'K1'
        elif cat == 'text-wrap':
            f['known'] = 'K3'
        findings.append(f)
    slide['known'] = [{'id': k, **v} for k, v in sorted(known.items())]
    slide['findings'] = findings
    if not findings:
        slide['verdict'] = 'match'
    return slide


def main():
    review = Path(sys.argv[1]) / 'review'
    index = json.loads((review / 'index.json').read_text())
    all_slides = [e['slide'] for e in index['slides']]
    twins = {int(k): v for k, v in index['identical_groups'].items()}

    slides, problems = {}, []
    # A slide reported by more than one batch file: keep the batch it was assigned to.
    owner = {}
    if (review / 'batches.json').exists():
        for i, batch in enumerate(json.loads((review / 'batches.json').read_text()), 1):
            owner.update({n: f'{i:03d}' for n in batch})
    files = sorted((review / 'findings').glob('batch-*.json'))
    for path in files:
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception as e:  # noqa: BLE001 - report every bad file, keep going
            problems.append(f'{path.name}: not valid JSON ({e})')
            continue
        for s in data.get('slides', []):
            if not isinstance(s.get('slide'), int):
                problems.append(f'{path.name}: entry without a slide number')
                continue
            if path.name == 'batch-pilot.json':
                s = pilot_to_tags(s)
            s['batch'] = path.stem.replace('batch-', '')
            if s['slide'] in slides and owner.get(s['slide']) != s['batch']:
                continue
            slides[s['slide']] = s
    for first, copies in twins.items():
        if first in slides:
            for c in copies:
                if c not in slides:
                    slides[c] = dict(json.loads(json.dumps(slides[first])), slide=c, identical_to=first)

    by_cat = collections.defaultdict(list)
    counts = collections.Counter()
    known_counts = collections.Counter()
    for n in sorted(slides):
        s = slides[n]
        for k in s.get('known', []):
            known_counts[k.get('id')] += 1
        for i, f in enumerate(s.get('findings', []), 1):
            f['id'] = f'S{n:04d}-{i}'
            f.setdefault('status', 'open')
            sev = f.get('severity') if f.get('severity') in SEVERITIES else 'unknown'
            counts[(f.get('category', 'other'), sev)] += 1
            if f.get('known'):
                known_counts[f['known']] += 1
            group = f'known-{f["known"]}' if f.get('known') else f.get('category', 'other')
            by_cat[group].append({'id': f['id'], 'slide': n, **{k: f.get(k) for k in (
                'category', 'severity', 'object', 'powerpoint', 'euro_office', 'detail', 'xml_evidence',
                'suspected_cause', 'confidence')}})

    missing = [n for n in all_slides if n not in slides]
    record = {'run': index['run'], 'slides_total': len(all_slides), 'slides_reviewed': len(slides),
              'missing': missing, 'slides': [slides[n] for n in sorted(slides)]}
    (review / 'discrepancies.json').write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding='utf-8')
    out = review / 'by-category'
    out.mkdir(exist_ok=True)
    for old in out.glob('*.json'):
        old.unlink()
    for cat, items in by_cat.items():
        (out / f'{re.sub(r"[^A-Za-z0-9-]", "_", cat)}.json').write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding='utf-8')

    print(f'{len(files)} batch files; {len(slides)}/{len(all_slides)} slides reviewed; missing: {missing or "none"}')
    for p in problems:
        print('PROBLEM', p)
    verdicts = collections.Counter(s.get('verdict') for s in slides.values())
    print('verdicts:', dict(verdicts))
    print('known-issue tags and findings:', dict(sorted(known_counts.items())))
    cats = sorted({c for c, _ in counts})
    print(f'{"category":22}' + ''.join(f'{s:>9}' for s in SEVERITIES) + '      new')
    for c in cats:
        print(f'{c:22}' + ''.join(f'{counts[(c, s)]:9}' for s in SEVERITIES) + f'{len(by_cat.get(c, [])):9}')
    print('group files:', {g: len(v) for g, v in sorted(by_cat.items())})


if __name__ == '__main__':
    main()
