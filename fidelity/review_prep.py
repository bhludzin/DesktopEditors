#!/usr/bin/env python3
"""Builds per-slide review packets: evidence for comparing one Euro-Office run
with PowerPoint slide by slide, by eye or by agent.

    python fidelity/review_prep.py <deck-dir> <run-label>

Expects <deck-dir>/review/sheets/pNNNN.{png,json} from `slide-diff pages` and
<deck-dir>/review/hires/{ppt,eo}/pNNNN.png (1600 px renders, for crops).
Writes <deck-dir>/review/:
  xml/            the deck's XML parts, pretty-printed (slides, layouts, masters...)
  slides/NNNN.json facts for one slide: scores, the text lines that differ,
                  every drawing object with its box, and which objects each
                  changed region overlaps
  index.json      one entry per slide, plus groups of visually identical slides
"""
import collections
import csv
import hashlib
import json
import posixpath
import re
import sys
import unicodedata
import zipfile
import xml.dom.minidom
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}
A, P = '{%s}' % NS['a'], '{%s}' % NS['p']
KINDS = {P + 'sp': 'shape', P + 'pic': 'picture', P + 'cxnSp': 'connector',
         P + 'grpSp': 'group', P + 'graphicFrame': 'graphicFrame'}


def rels_of(z, part):
    d, b = posixpath.split(part)
    path = posixpath.join(d, '_rels', b + '.rels')
    out = {}
    if path not in z.namelist():
        return out
    for rel in ET.fromstring(z.read(path)):
        tgt = rel.get('Target')
        if rel.get('TargetMode') != 'External':
            tgt = posixpath.normpath(posixpath.join(d, tgt))
        out[rel.get('Id')] = (rel.get('Type').rsplit('/', 1)[-1], tgt)
    return out


def first_rel(z, part, typ):
    return next((t for k, t in rels_of(z, part).values() if k == typ), None)


def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s)).lstrip('•–-—*')


def text_of(el):
    paras = []
    for p in el.iter(A + 'p'):
        paras.append(''.join((t.text or '') for t in p.iter(A + 't')))
    return '\n'.join(x for x in paras if x)


def ph_key(el):
    ph = el.find('p:nvSpPr/p:nvPr/p:ph', NS)
    if ph is None:
        ph = el.find('.//p:nvPr/p:ph', NS)
    return None if ph is None else (ph.get('type', 'body'), ph.get('idx'))


def xfrm_of(el):
    for path in ('p:spPr/a:xfrm', 'p:grpSpPr/a:xfrm', 'p:xfrm'):
        x = el.find(path, NS)
        if x is not None:
            return x
    return None


def placeholder_xfrm(z, part, key, depth=0):
    """Position of a placeholder inherited from the layout, then the master."""
    if depth > 2 or part is None:
        return None
    root = ET.fromstring(z.read(part))
    typ, idx = key
    cands = []
    for sp in root.iter(P + 'sp'):
        k = ph_key(sp)
        if k is None:
            continue
        score = (2 if idx is not None and k[1] == idx else 0) + (1 if k[0] == typ else 0)
        if typ in ('title', 'ctrTitle') and k[0] in ('title', 'ctrTitle'):
            score += 1
        if score:
            cands.append((score, sp))
    for _, sp in sorted(cands, key=lambda c: -c[0]):
        x = xfrm_of(sp)
        if x is not None and x.find('a:off', NS) is not None:
            return x
    nxt = first_rel(z, part, 'slideLayout') or first_rel(z, part, 'slideMaster')
    return placeholder_xfrm(z, nxt, key, depth + 1)


def walk(z, part, tree, scale, out, transform=(0, 0, 1, 1), parent=None, depth=0):
    """Collects drawing objects with boxes in output pixels."""
    ox, oy, sx, sy = transform
    for el in tree:
        kind = KINDS.get(el.tag)
        if kind is None:
            if el.tag.endswith('AlternateContent'):
                choice = el.find('{http://schemas.openxmlformats.org/markup-compatibility/2006}Choice')
                if choice is not None:
                    walk(z, part, choice, scale, out, transform, parent, depth)
            continue
        nv = el.find('.//p:cNvPr', NS)
        key = ph_key(el)
        x = xfrm_of(el)
        inherited = False
        if (x is None or x.find('a:off', NS) is None) and key is not None:
            x = placeholder_xfrm(z, first_rel(z, part, 'slideLayout'), key)
            inherited = x is not None
        item = {'id': nv.get('id') if nv is not None else None,
                'name': nv.get('name') if nv is not None else None,
                'kind': kind, 'depth': depth}
        if parent:
            item['in_group'] = parent
        if key:
            item['placeholder'] = {'type': key[0], 'idx': key[1], 'position_from_layout': inherited}
        box = None
        if x is not None and x.find('a:off', NS) is not None:
            off, ext = x.find('a:off', NS), x.find('a:ext', NS)
            X, Y = int(off.get('x')), int(off.get('y'))
            W, H = int(ext.get('cx')), int(ext.get('cy'))
            x0, y0 = ox + X * sx, oy + Y * sy
            box = [x0, y0, x0 + W * sx, y0 + H * sy]
            item['box_px'] = [round(v * scale, 1) for v in box]
            if x.get('rot'):
                item['rot_deg'] = int(x.get('rot')) / 60000
            if x.get('flipH') == '1' or x.get('flipV') == '1':
                item['flip'] = ''.join(f for f, on in (('H', x.get('flipH') == '1'), ('V', x.get('flipV') == '1')) if on)
        geom = el.find('p:spPr/a:prstGeom', NS)
        if geom is not None:
            item['geometry'] = geom.get('prst')
        elif el.find('p:spPr/a:custGeom', NS) is not None:
            item['geometry'] = 'custom'
        if kind == 'connector':
            ln = el.find('p:spPr/a:ln', NS)
            if ln is not None:
                heads = {t: ln.find('a:' + t, NS).get('type') for t in ('headEnd', 'tailEnd') if ln.find('a:' + t, NS) is not None}
                if heads:
                    item['line_ends'] = heads
        body = el.find('p:txBody', NS)
        if body is not None:
            txt = text_of(body)
            if txt:
                item['text'] = txt[:160] + ('…' if len(txt) > 160 else '')
            bp = body.find('a:bodyPr', NS)
            if bp is not None:
                fit = next((t.tag.split('}')[1] for t in bp if t.tag.split('}')[1] in ('normAutofit', 'spAutoFit', 'noAutofit')), None)
                if fit:
                    item['autofit'] = fit
                if bp.get('anchor'):
                    item['anchor'] = bp.get('anchor')
            sizes = sorted({int(r.get('sz')) / 100 for r in body.iter() if r.tag in (A + 'rPr', A + 'endParaRPr') and r.get('sz')})
            if sizes:
                item['font_sizes_pt'] = sizes
            if body.find('.//a:buChar', NS) is not None or body.find('.//a:buAutoNum', NS) is not None:
                item['bullets'] = True
        if kind == 'picture':
            blip = el.find('.//a:blip', NS)
            if blip is not None:
                rid = blip.get('{%s}embed' % NS['r'])
                item['image'] = rels_of(z, part).get(rid, (None, None))[1]
            if el.find('.//a:srcRect', NS) is not None:
                item['cropped'] = True
        if kind == 'graphicFrame':
            gd = el.find('.//a:graphicData', NS)
            if gd is not None:
                item['content'] = gd.get('uri', '').rsplit('/', 1)[-1]
        out.append(item)
        if kind == 'group' and box is not None:
            g = el.find('p:grpSpPr/a:xfrm', NS)
            ch_off, ch_ext = g.find('a:chOff', NS), g.find('a:chExt', NS)
            if ch_off is not None and ch_ext is not None and int(ch_ext.get('cx')) and int(ch_ext.get('cy')):
                csx = (box[2] - box[0]) / int(ch_ext.get('cx'))
                csy = (box[3] - box[1]) / int(ch_ext.get('cy'))
                t = (box[0] - int(ch_off.get('x')) * csx, box[1] - int(ch_off.get('y')) * csy, csx, csy)
                walk(z, part, el, scale, out, t, item['name'], depth + 1)


def overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return max(0, w) * max(0, h)


def main():
    deck_dir, run = Path(sys.argv[1]), sys.argv[2]
    review = deck_dir / 'review'
    z = zipfile.ZipFile(deck_dir / 'deck.pptx')
    xml_dir = review / 'xml'
    for name in z.namelist():
        if name.endswith(('.xml', '.rels')):
            dst = xml_dir / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                pretty = xml.dom.minidom.parseString(z.read(name)).toprettyxml(indent='  ')
            except Exception:
                pretty = z.read(name).decode('utf-8', 'replace')
            dst.write_text(pretty, encoding='utf-8')

    pres = 'ppt/presentation.xml'
    proot = ET.fromstring(z.read(pres))
    sld = proot.find('p:sldSz', NS)
    slide_w = int(sld.get('cx'))
    prels = rels_of(z, pres)
    order = [prels[s.get('{%s}id' % NS['r'])][1] for s in proot.find('p:sldIdLst', NS)]

    def pages(path):
        return [[l for l in pg.splitlines() if l.strip()] for pg in Path(path).read_text(encoding='utf-8').split('\f')]
    ref_text = pages(deck_dir / 'reference' / 'text.txt')
    run_text = pages(deck_dir / 'runs' / run / 'text.txt')
    scores = {int(r['slide']): r for r in csv.DictReader(open(deck_dir / 'runs' / run / 'scores.csv'))}

    out_dir = review / 'slides'
    out_dir.mkdir(parents=True, exist_ok=True)
    index, groups = [], collections.defaultdict(list)
    for i, part in enumerate(order, 1):
        sheet = json.loads((review / 'sheets' / f'p{i:04d}.json').read_text())
        scale = sheet['width'] / slide_w
        root = ET.fromstring(z.read(part))
        objects = []
        walk(z, part, root.find('p:cSld/p:spTree', NS), scale, objects)
        layout = first_rel(z, part, 'slideLayout')
        layout_name = ET.fromstring(z.read(layout)).find('p:cSld', NS).get('name') if layout else None
        for r in sheet['regions']:
            hits = [(overlap(r['px'], o['box_px']), o) for o in objects if 'box_px' in o and o['kind'] != 'group']
            hits = [h for h in hits if h[0] > 0]
            hits.sort(key=lambda h: -h[0])
            r['objects'] = [f"{o['id']}:{o['name']}" for _, o in hits[:4]]
        ref_lines = ref_text[i - 1] if i - 1 < len(ref_text) else []
        run_lines = run_text[i - 1] if i - 1 < len(run_text) else []
        rc = collections.Counter(norm(l) for l in ref_lines)
        cc = collections.Counter(norm(l) for l in run_lines)
        only_ref = [l for l in ref_lines if (rc - cc)[norm(l)] > 0]
        only_run = [l for l in run_lines if (cc - rc)[norm(l)] > 0]
        s = scores.get(i, {})
        facts = {
            'slide': i, 'part': part, 'xml': f'review/xml/{part}', 'layout': layout_name,
            'layout_xml': f'review/xml/{layout}' if layout else None,
            'sheet': f'review/sheets/p{i:04d}.png',
            'hires': {'powerpoint': f'review/hires/ppt/p{i:04d}.png', 'euro_office': f'review/hires/eo/p{i:04d}.png'},
            'scores': {'ssim': float(s.get('ssim', 0)), 'text_lines': int(s.get('ref_lines', 0)),
                       'lines_matching': int(s.get('matched_lines', 0))},
            'changed_fraction': sheet['changed_fraction'],
            'text_powerpoint': ref_lines, 'text_euro_office': run_lines,
            'lines_only_in_powerpoint': only_ref, 'lines_only_in_euro_office': only_run,
            'regions': sheet['regions'][:20], 'regions_total': len(sheet['regions']),
            'objects': objects,
        }
        (out_dir / f'{i:04d}.json').write_text(json.dumps(facts, indent=1, ensure_ascii=False), encoding='utf-8')
        h = hashlib.sha256()
        for img in (review / 'hires' / 'ppt' / f'p{i:04d}.png', review / 'hires' / 'eo' / f'p{i:04d}.png'):
            h.update(img.read_bytes() if img.exists() else b'missing')
        groups[h.hexdigest()].append(i)
        index.append({'slide': i, 'changed_fraction': sheet['changed_fraction'], 'regions': len(sheet['regions']),
                      'ssim': facts['scores']['ssim'], 'objects': len(objects)})
    dup = {g[0]: g[1:] for g in groups.values() if len(g) > 1}
    (review / 'index.json').write_text(json.dumps({'run': run, 'slides': index, 'identical_groups': dup}, indent=1), encoding='utf-8')
    print(f'{len(index)} slides; {sum(len(v) for v in dup.values())} are visually identical to an earlier slide '
          f'({len(index) - sum(len(v) for v in dup.values())} distinct)')


if __name__ == '__main__':
    main()
