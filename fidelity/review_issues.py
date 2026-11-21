#!/usr/bin/env python3
"""Builds review/issues.json (the fix tracker) from the root-cause grouping.

    python fidelity/review_issues.py <deck-dir> <specs-dir>

Reads review/grouping/<group>.issues.json (one per group; the .partN files are
inputs to a combined file and are skipped), review/grouping/merges.json
(cross-group merges) and review/known.json (definitions of the known-issue ids
K1..Kn used during review). Writes <specs-dir>/issues.json with stable ids: known
issues keep their K-id, the rest become I-001.. ordered by severity, then by
number of slides. Refuses to overwrite an issues.json that has statuses other
than "open" unless --force is given.
"""
import json
import sys
from pathlib import Path

SEV_ORDER = {'major': 0, 'minor': 1, 'trivial': 2}
TEXT_FIELDS = ('description', 'powerpoint', 'euro_office', 'suspected_cause', 'code_area', 'fix_idea')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        sys.exit(__doc__)
    review = Path(args[0]) / 'review'
    out = Path(args[1]) / 'issues.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and '--force' not in sys.argv:
        old = json.loads(out.read_text(encoding='utf-8'))
        if any(i.get('status', 'open') != 'open' for i in old['issues']):
            sys.exit(f'{out} already tracks progress; pass --force to rebuild it')
    known = json.loads((review / 'known.json').read_text(encoding='utf-8'))
    record = json.loads((review / 'discrepancies.json').read_text(encoding='utf-8'))
    slide_of = {f['id']: s['slide'] for s in record['slides'] for f in s.get('findings', [])}

    issues, rejected = {}, []
    for path in sorted((review / 'grouping').glob('*.issues.json')):
        if '.part' in path.name:
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        rejected += data.get('rejected', [])
        for i in data['issues']:
            key = i['key']
            if key in issues:  # the same K-id from two groups
                issues[key]['severity'] = min(issues[key].get('severity'), i.get('severity'), key=lambda v: SEV_ORDER.get(v, 3))
                issues[key]['findings'] += i.get('findings', [])
                issues[key]['representative'] += i.get('representative', [])
                issues[key].setdefault('also', []).append(i)
            else:
                issues[key] = dict(i, group=data.get('group', path.stem))
    for k, d in known.items():
        issues.setdefault(k, {'key': k, 'title': d['title'], 'categories': d['categories'], 'findings': [],
                              'representative': [], 'description': d['description'], 'group': 'known',
                              'severity': d.get('severity')})
        if k in issues:
            issues[k]['tag'] = k

    merges_path = review / 'grouping' / 'merges.json'
    consolidation = json.loads(merges_path.read_text(encoding='utf-8')) if merges_path.exists() else {}
    merges = consolidation.get('merges', [])
    for m in merges:
        into = issues.get(m['into'])
        if not into:
            print('SKIP merge into unknown', m['into'])
            continue
        for key in m.get('absorb', []):
            other = issues.pop(key, None)
            if not other or other is into:
                print('SKIP absorb of unknown', key)
                continue
            into['severity'] = min(into.get('severity'), other.get('severity'), key=lambda v: SEV_ORDER.get(v, 3))
            into['findings'] += other.get('findings', [])
            into['representative'] += other.get('representative', [])
            into['categories'] = sorted(set(into.get('categories', [])) | set(other.get('categories', [])))
            into.setdefault('merged_from', []).append({'key': key, 'title': other.get('title'),
                                                       **{f: other.get(f) for f in TEXT_FIELDS if other.get(f)}})
        if m.get('title'):
            into['title'] = m['title']
        if m.get('suspected_cause'):
            into['suspected_cause'] = m['suspected_cause']
        into.setdefault('merge_notes', []).append(m.get('why'))

    for d in consolidation.get('doubts', []):
        target = issues.get(d['key']) or next((i for i in issues.values()
                                               if d['key'] in [m['key'] for m in i.get('merged_from', [])]), None)
        if target:
            target.setdefault('doubts', []).append(d['note'])
        else:
            print('SKIP doubt about unknown', d['key'])

    def rank(i):
        return (SEV_ORDER.get(i.get('severity'), 3), -len({slide_of.get(f) for f in i['findings']}), i['key'])
    numbered = sorted((i for i in issues.values() if not i['key'].startswith('K')), key=rank)
    result = []
    for k in known:
        if k in issues:
            result.append(dict(issues[k], id=k))
    for n, i in enumerate(numbered, 1):
        result.append(dict(i, id=f'I-{n:03d}'))
    for i in result:
        i['findings'] = sorted(set(i['findings']), key=lambda f: (slide_of.get(f, 0), f))
        i['representative'] = list(dict.fromkeys(i.get('representative', [])))
        i['status'] = 'open'
        i['fixed_in'] = None
        i['log'] = []
    out.write_text(json.dumps({'issues': result, 'rejected': rejected}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(result)} issues ({len(merges)} merges applied), {len(rejected)} findings rejected')


if __name__ == '__main__':
    main()
