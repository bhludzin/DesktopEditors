#!/usr/bin/env python3
"""Rendering-fidelity harness for the Euro-Office fork.

Compares how Euro-Office's converter (x2t + sdkjs) renders a deck with how
Microsoft PowerPoint renders the same deck, slide by slide, and tracks whether
a change to sdkjs makes that better or worse. See fidelity/README.md.

Decks and renders never go into the repository: they live in a work folder,
by default ../fidelity-work next to the repo (override with --work or the
FIDELITY_WORK environment variable).
"""
import argparse
import collections
import csv
import datetime
import filecmp
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
import unicodedata
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
WINDOWS_SCRIPTS = HERE / 'windows'
SSIM_DIR = HERE / 'ssim-compare'
SDKJS = REPO / 'sdkjs'
EDITORS = ('word', 'cell', 'slide', 'visio')
BUNDLES = ('sdk-all-min.js', 'sdk-all.js')
WIDTH = 800
# Leading list markers that PDF producers emit either with the line or apart from it.
BULLETS = '\u2022\u2013-\u2014\u25aa\u25ab\u25cb\u25cf\u25a0\u25a1\u25ba\u25b6\u2713\u2714\u00b7*' \
          '\uf0a7\uf0b7\uf0d8\uf076\uf0fc\uf0a8'


# ---------------------------------------------------------------- helpers

def die(msg):
    sys.exit(f'error: {msg}')


def require_windows(what):
    if os.name != 'nt':
        die(f'{what} is Windows-only for now (see fidelity/README.md).')


def run(cmd, quiet=False, **kw):
    cmd = [str(c) for c in cmd]
    if not quiet:
        print('  $ ' + ' '.join(cmd), flush=True)
    result = subprocess.run(cmd, **kw)
    if result.returncode != 0:
        die(f'{Path(cmd[0]).name} failed with exit code {result.returncode}')
    return result


def powershell(script, *params):
    run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', WINDOWS_SCRIPTS / script, *params])


def work_dir(args):
    return Path(args.work or os.environ.get('FIDELITY_WORK') or REPO.parent / 'fidelity-work').resolve()


def deck_dir(args, must_exist=True):
    d = work_dir(args) / 'decks' / args.name
    if must_exist and not (d / 'reference' / 'png').is_dir():
        die(f'no reference for deck "{args.name}" in {d}; run the "reference" command first')
    return d


def default_app(work):
    apps = sorted(p for p in (work / 'apps').glob('euro-office-*') if (p / 'converter' / 'x2t.exe').exists())
    if not apps:
        die(f'no Euro-Office app found under {work / "apps"}; unpack the portable zip there or pass --app')
    return apps[-1]


def baseline_of(d):
    f = d / 'baseline.txt'
    return f.read_text(encoding='utf-8').strip() if f.exists() else None


def pdftotext():
    exe = shutil.which('pdftotext')
    if not exe and os.name == 'nt':
        for base in (os.environ.get('ProgramFiles', r'C:\Program Files'),
                     os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs')):
            candidate = Path(base) / 'Git' / 'mingw64' / 'bin' / 'pdftotext.exe'
            if candidate.exists():
                exe = str(candidate)
                break
    if not exe:
        die('pdftotext not found (it ships with Git for Windows; on macOS: brew install xpdf)')
    return exe


def ssim_tool():
    exe = SSIM_DIR / 'target' / 'release' / ('ssim-compare.exe' if os.name == 'nt' else 'ssim-compare')
    cargo = shutil.which('cargo')
    if cargo:
        # rust-toolchain.toml pins the toolchain; this is a no-op when up to date.
        run([cargo, 'build', '--release', '--quiet'], quiet=True, cwd=SSIM_DIR)
    elif not exe.exists():
        die('cargo not found; install Rust from https://rustup.rs to build the scoring tool')
    return exe


def rasterize(pdf, out):
    require_windows('Rasterizing PDFs')
    if out.exists():
        shutil.rmtree(out)
    powershell('pdf-to-png.ps1', '-Pdf', pdf, '-OutDir', out, '-Width', WIDTH)


def extract_text(pdf, out):
    run([pdftotext(), '-q', '-enc', 'UTF-8', '-raw', pdf, out])


def git(*args):
    return subprocess.run(['git', '-C', str(SDKJS), *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace').stdout


def sdkjs_version():
    """Version stamped into the bundle banner: sdkjs's latest release tag."""
    tag = git('describe', '--tags', '--abbrev=0').strip()
    if re.fullmatch(r'v?\d+(\.\d+)+', tag):
        return tag.lstrip('v')
    f = REPO / 'VERSION.txt'
    return f.read_text(encoding='utf-8').strip() if f.exists() else '0.0.0'


def percent(fraction):
    return 'n/a' if fraction is None else f'{100 * fraction:.1f}%'


# ---------------------------------------------------------------- reference

def cmd_reference(args):
    require_windows('Exporting from PowerPoint')
    src = Path(args.deck).resolve()
    if not src.is_file():
        die(f'no such deck: {src}')
    d = deck_dir(args, must_exist=False)
    deck = d / 'deck.pptx'
    if deck.exists() and not args.force:
        die(f'{d} already has a reference; pass --force to replace it')
    ref = d / 'reference'
    if ref.exists():
        shutil.rmtree(ref)
    ref.mkdir(parents=True)
    shutil.copy2(src, deck)
    pdf = ref / 'deck.pdf'
    started = time.time()
    powershell('export-powerpoint.ps1', '-Deck', deck, '-Pdf', pdf)
    seconds = time.time() - started
    if not pdf.exists():
        die('PowerPoint did not produce a PDF')
    rasterize(pdf, ref / 'png')
    extract_text(pdf, ref / 'text.txt')
    (ref / 'reference.json').write_text(json.dumps({
        'source': str(src),
        'exported': datetime.datetime.now().isoformat(timespec='seconds'),
        'export_seconds': round(seconds, 1),
        'slides': len(list((ref / 'png').glob('p*.png'))),
    }, indent=2), encoding='utf-8')
    print(f'Reference ready: {ref}')
    print(f'Next: python fidelity/fidelity.py render {args.name} --release   (baseline from the release app)')


# ---------------------------------------------------------------- rendering

X2T_PARAMS = """<?xml version="1.0" encoding="utf-8"?>
<TaskQueueDataConvert xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <m_sFileFrom>{src}</m_sFileFrom>
  <m_sFileTo>{dst}</m_sFileTo>
  <m_nFormatTo>513</m_nFormatTo>
  <m_sAllFontsPath>{allfonts}</m_sAllFontsPath>
  <m_sFontDir>{fontdir}</m_sFontDir>
  <m_sTempDir>{tmp}</m_sTempDir>
  <m_bIsNoBase64>true</m_bIsNoBase64>
</TaskQueueDataConvert>
"""


def prepare_runtime(work, app, deploy):
    """A private copy of the release converter whose editors/sdkjs bundles are
    replaced by the fork's build. The release app itself is never modified."""
    rt = work / 'runtime' / app.name
    marker = rt / '.copied'
    if not marker.exists():
        if rt.exists():
            shutil.rmtree(rt)
        print(f'Creating a private converter copy for fork builds in {rt} (one time)...', flush=True)
        for part in ('converter', 'editors/sdkjs', 'editors/web-apps/vendor/xregexp', 'dictionaries'):
            shutil.copytree(app / part, rt / part)
        marker.write_text(str(app), encoding='utf-8')
    overlaid = []
    for editor in EDITORS:
        src_dir = deploy / editor
        if not all((src_dir / b).exists() for b in BUNDLES):
            continue
        dst_dir = rt / 'editors' / 'sdkjs' / editor
        changed = False
        for bundle in BUNDLES:
            src, dst = src_dir / bundle, dst_dir / bundle
            if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                shutil.copy2(src, dst)
                changed = True
        if changed:
            # Compiled-code caches belong to the old bundle; x2t writes a new one.
            for stale in list(dst_dir.glob('*.cache')) + list(dst_dir.glob('*.bin')):
                stale.unlink()
        overlaid.append(editor)
    if 'slide' not in overlaid:
        die(f'no slide bundle in {deploy}; build sdkjs first (the "loop" command does this)')
    return rt / 'converter', overlaid


def pc_font_list(work, app):
    """The font list x2t renders with, made from this PC's fonts the way the
    desktop app makes its own at start: AllFonts.js for sdkjs and
    font_selection.bin for the native side, both in <work>/fonts. The list
    shipped in the converter was made on the build server, so fonts installed
    only here (Office's fonts, its cloud fonts such as Aptos) would be
    substituted in renders although PowerPoint draws them."""
    out = work / 'fonts'
    out.mkdir(parents=True, exist_ok=True)
    # x2t rewrites the list only when the set of font files has changed.
    extra = [app / 'fonts'] if (app / 'fonts').is_dir() else []
    run([app / 'converter' / 'x2t.exe', '-create-allfonts', out, *extra], quiet=True, cwd=app / 'converter')
    for name in ('AllFonts.js', 'font_selection.bin'):
        if not (out / name).exists():
            die(f'x2t made no {name} in {out}')
    return out


def font_list_meta(folder, kind):
    """What run.json records about the font list a run used."""
    digest = hashlib.sha256()
    for name in ('AllFonts.js', 'font_selection.bin'):
        digest.update((folder / name).read_bytes())
    js = (folder / 'AllFonts.js').read_text(encoding='utf-8-sig')
    files = re.search(r'__fonts_files"\] = \[(.*?)\];', js, re.S)
    return {'fonts': kind, 'font_list': str(folder), 'font_list_sha256': digest.hexdigest(),
            'font_files': len(re.findall(r'"[^"]+"', files.group(1))) if files else None}


def render_run(d, label, converter, meta, force=False, font_dir=None):
    """Render the deck with x2t. font_dir is the folder of the font list to use
    (see pc_font_list); None uses the list shipped in the converter."""
    out = d / 'runs' / label
    if out.exists():
        if not force:
            die(f'run "{label}" already exists; choose another --label or pass --force')
        shutil.rmtree(out)
    tmp = out / 'tmp'
    tmp.mkdir(parents=True)
    pdf = out / 'deck.pdf'
    params = out / 'x2t-params.xml'
    if font_dir is None:
        # x2t looks for font_selection.bin in m_sFontDir and then next to
        # itself, so this uses the converter's shipped list on both sides.
        allfonts = converter / 'AllFonts.js'
        fontdir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
        meta.update(font_list_meta(converter, 'shipped'))
    else:
        allfonts = font_dir / 'AllFonts.js'
        fontdir = str(font_dir)
        meta.update(font_list_meta(font_dir, 'pc'))
    params.write_text(X2T_PARAMS.format(
        src=xml_escape(str(d / 'deck.pptx')), dst=xml_escape(str(pdf)),
        allfonts=xml_escape(str(allfonts)), fontdir=xml_escape(fontdir),
        tmp=xml_escape(str(tmp))), encoding='utf-8')
    print(f'Rendering {d.name} with {converter}', flush=True)
    started = time.time()
    run([converter / 'x2t.exe', params], cwd=converter)
    seconds = time.time() - started
    shutil.rmtree(tmp, ignore_errors=True)
    if not pdf.exists():
        die('x2t exited without producing a PDF')
    print(f'  rendered in {seconds:.0f} s; rasterizing and extracting text...', flush=True)
    rasterize(pdf, out / 'png')
    extract_text(pdf, out / 'text.txt')
    meta.update({'label': label, 'converter': str(converter),
                 'rendered': datetime.datetime.now().isoformat(timespec='seconds'),
                 'render_seconds': round(seconds, 1)})
    (out / 'run.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return out


def cmd_render(args):
    require_windows('Rendering with x2t')
    d = deck_dir(args)
    work = work_dir(args)
    app = Path(args.app).resolve() if args.app else default_app(work)
    if args.sdkjs:
        converter, overlaid = prepare_runtime(work, app, Path(args.sdkjs).resolve())
        meta = {'kind': 'fork', 'app': str(app), 'sdkjs_deploy': str(Path(args.sdkjs).resolve()), 'overlaid': overlaid}
        label = args.label or datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    else:
        converter = app / 'converter'
        meta = {'kind': 'release', 'app': str(app)}
        label = args.label or 'release-' + app.name.replace('euro-office-', '')
    font_dir = None if args.shipped_fonts else pc_font_list(work, app)
    render_run(d, label, converter, meta, force=args.force, font_dir=font_dir)
    if not args.sdkjs and baseline_of(d) is None:
        (d / 'baseline.txt').write_text(label, encoding='utf-8')
        print(f'Baseline for {args.name} set to "{label}"')
    report(d, label, baseline_of(d))


def cmd_loop(args):
    """Build sdkjs from this checkout, render the deck with it, score it."""
    require_windows('Rendering with x2t')
    d = deck_dir(args)
    work = work_dir(args)
    app = Path(args.app).resolve() if args.app else default_app(work)
    npm = shutil.which('npm')
    if not npm:
        die('npm not found; install Node.js')
    build = SDKJS / 'build'
    # Reinstall when the lockfile changes, e.g. after checking out another sdkjs
    # commit whose build uses different tools.
    lock = build / 'npm-shrinkwrap.json'
    lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else ''
    stamp = build / 'node_modules' / '.fidelity-lockfile-sha256'
    if not stamp.exists() or stamp.read_text().strip() != lock_hash:
        run([npm, 'ci', '--no-audit', '--no-fund'], cwd=build)
        stamp.write_text(lock_hash + '\n')
    # The settings the desktop app's release uses: with these, an unmodified
    # sdkjs builds byte-for-byte identical to the released bundles. (Development
    # builds do not load in x2t: both bundles declare webpack's runtime.)
    env = dict(os.environ, NODE_ENV='production', SDK_PLATFORM='desktop',
               PRODUCT_VERSION=sdkjs_version(), BUILD_NUMBER='0')
    mode = 'production, SDK_PLATFORM=desktop'
    print('Building sdkjs slide bundle...', flush=True)
    started = time.time()
    # webpack's output (including harmless cache warnings on Windows) is shown
    # only with --verbose or when the build fails.
    built = subprocess.run([npm, 'run', 'build:slide'], cwd=build, env=env,
                           capture_output=not args.verbose, text=True, encoding='utf-8', errors='replace')
    if built.returncode != 0:
        if not args.verbose:
            print((built.stdout or '')[-4000:], (built.stderr or '')[-4000:], sep='\n')
        die('the sdkjs build failed')
    build_seconds = time.time() - started
    print(f'  built in {build_seconds:.0f} s', flush=True)

    commit = git('rev-parse', 'HEAD').strip()
    status = git('status', '--porcelain')
    dirty = bool(status.strip())
    label = args.label or '{}-{}{}'.format(datetime.datetime.now().strftime('%Y%m%d-%H%M'),
                                           commit[:7], '-dirty' if dirty else '')
    converter, overlaid = prepare_runtime(work, app, SDKJS / 'deploy' / 'sdkjs')
    meta = {'kind': 'fork', 'app': str(app), 'sdkjs_commit': commit, 'sdkjs_dirty': dirty,
            'build_mode': mode, 'build_seconds': round(build_seconds, 1), 'overlaid': overlaid}
    font_dir = None if args.shipped_fonts else pc_font_list(work, app)
    out = render_run(d, label, converter, meta, force=args.force, font_dir=font_dir)
    # Record exactly which code produced this run.
    if dirty:
        (out / 'sdkjs-status.txt').write_text(status, encoding='utf-8')
        (out / 'sdkjs.diff').write_text(git('diff', 'HEAD'), encoding='utf-8')
    report(d, label, args.baseline or baseline_of(d))


# ---------------------------------------------------------------- scoring

def normalize_line(line):
    s = unicodedata.normalize('NFKC', line)
    return re.sub(r'\s+', '', s).lstrip(BULLETS)


def text_pages(path, count):
    pages = path.read_text(encoding='utf-8', errors='replace').split('\f') if path.exists() else []
    result = []
    for i in range(count):
        lines = pages[i].splitlines() if i < len(pages) else []
        result.append(collections.Counter(n for n in map(normalize_line, lines) if len(n) >= 3))
    return result


def compute_scores(d, label):
    ref, out = d / 'reference', d / 'runs' / label
    count = len(list((ref / 'png').glob('p*.png')))
    got = len(list((out / 'png').glob('p*.png')))
    if got != count:
        print(f'warning: {label} has {got} slides but the PowerPoint reference has {count} '
              '(hidden slides?); slides may be misaligned')
    run([ssim_tool(), ref / 'png', out / 'png', out / 'ssim.csv'], quiet=True, stdout=subprocess.DEVNULL)
    with open(out / 'ssim.csv', newline='') as f:
        ssim = {int(r['page']): float(r['ssim']) for r in csv.DictReader(f)}
    ref_pages, run_pages = text_pages(ref / 'text.txt', count), text_pages(out / 'text.txt', count)
    rows = []
    for i in range(count):
        r, c = ref_pages[i], run_pages[i]
        ref_lines = sum(r.values())
        matched = sum((r & c).values())
        rows.append({'slide': i + 1, 'ssim': ssim.get(i + 1, 0.0), 'ref_lines': ref_lines,
                     'matched_lines': matched,
                     'line_match': matched / ref_lines if ref_lines else None,
                     'identical_breaks': (r == c) if ref_lines else None})
    with open(out / 'scores.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['slide', 'ssim', 'ref_lines', 'matched_lines', 'line_match', 'identical_breaks'])
        for row in rows:
            w.writerow([row['slide'], f"{row['ssim']:.4f}", row['ref_lines'], row['matched_lines'],
                        '' if row['line_match'] is None else f"{row['line_match']:.3f}",
                        '' if row['identical_breaks'] is None else int(row['identical_breaks'])])
    summary = summarize(rows)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return rows, summary


def load_scores(d, label):
    out = d / 'runs' / label
    if not (out / 'png').is_dir():
        die(f'no run "{label}" for deck {d.name}')
    if not (out / 'scores.csv').exists():
        return compute_scores(d, label)
    rows = []
    with open(out / 'scores.csv', newline='') as f:
        for r in csv.DictReader(f):
            ref_lines, matched = int(r['ref_lines']), int(r['matched_lines'])
            rows.append({'slide': int(r['slide']), 'ssim': float(r['ssim']), 'ref_lines': ref_lines,
                         'matched_lines': matched,
                         # Recomputed from the counts: the CSV column is rounded for reading.
                         'line_match': matched / ref_lines if ref_lines else None,
                         'identical_breaks': bool(int(r['identical_breaks'])) if r['identical_breaks'] else None})
    return rows, summarize(rows)


def summarize(rows):
    ssim = [r['ssim'] for r in rows]
    text = [r for r in rows if r['ref_lines']]
    lines = sum(r['ref_lines'] for r in text)
    return {
        'slides': len(rows),
        'mean_ssim': round(statistics.mean(ssim), 4) if ssim else 0.0,
        'ssim_bands': {'>=0.95': sum(s >= .95 for s in ssim), '0.90-0.95': sum(.90 <= s < .95 for s in ssim),
                       '0.80-0.90': sum(.80 <= s < .90 for s in ssim), '0.70-0.80': sum(.70 <= s < .80 for s in ssim),
                       '<0.70': sum(s < .70 for s in ssim)},
        'text_slides': len(text),
        'lines': lines,
        'lines_matched': sum(r['matched_lines'] for r in text),
        'line_match': round(sum(r['matched_lines'] for r in text) / lines, 4) if lines else None,
        'identical_slides': sum(1 for r in text if r['identical_breaks']),
    }


def report(d, label, baseline, top=12):
    rows, s = compute_scores(d, label)
    base_rows = base = None
    if baseline and baseline != label:
        base_rows, base = load_scores(d, baseline)
    print()
    print(f'{d.name} / {label}' + (f'   (baseline: {baseline})' if base else ''))
    print(f'  {"":34}{"this run":>12}' + (f'{"baseline":>12}' if base else ''))

    def line(name, fmt):
        print(f'  {name:34}{fmt(s):>12}' + (f'{fmt(base):>12}' if base else ''))
    line('Text lines breaking like PowerPoint', lambda x: percent(x['line_match']))
    line('Slides with identical line breaks', lambda x: f"{x['identical_slides']}/{x['text_slides']}")
    line('Mean image similarity (SSIM)', lambda x: f"{x['mean_ssim']:.4f}")
    if not base:
        return
    by_slide = {r['slide']: r for r in base_rows}
    better, worse, ssim_better, ssim_worse = [], [], 0, 0
    for r in rows:
        b = by_slide.get(r['slide'])
        if not b:
            continue
        if r['ref_lines'] and r['matched_lines'] != b['matched_lines']:
            delta = (r['matched_lines'] - b['matched_lines']) / r['ref_lines']
            (better if delta > 0 else worse).append((delta, r, b))
        # SSIM is stored to 4 decimals, so compare at that precision.
        ssim_delta = round(r['ssim'], 4) - round(b['ssim'], 4)
        ssim_better += ssim_delta > 0.01
        ssim_worse += ssim_delta < -0.01
    print(f'  Line breaks vs baseline: {len(better)} slides better, {len(worse)} worse')
    print(f'  Image similarity vs baseline (change > 0.01): {ssim_better} slides better, {ssim_worse} worse')

    def show(title, items):
        if not items:
            return
        print(f'  {title}:')
        for delta, r, b in items[:top]:
            print(f"    slide {r['slide']:>4}: lines matching {b['matched_lines']}/{b['ref_lines']} -> "
                  f"{r['matched_lines']}/{r['ref_lines']}   SSIM {b['ssim']:.3f} -> {r['ssim']:.3f}")
        if len(items) > top:
            print(f'    ... and {len(items) - top} more (see scores.csv)')
    show('Worse than baseline', sorted(worse, key=lambda t: t[0]))
    show('Better than baseline', sorted(better, key=lambda t: -t[0]))
    if worse or better:
        example = (sorted(worse, key=lambda t: t[0]) or sorted(better, key=lambda t: -t[0]))[0][1]['slide']
        print(f'  See a slide side by side: python fidelity/fidelity.py compare {d.name} {example}')


def cmd_score(args):
    d = deck_dir(args)
    report(d, args.label, args.baseline or baseline_of(d))


def cmd_runs(args):
    d = deck_dir(args)
    baseline = baseline_of(d)
    runs = sorted((d / 'runs').glob('*/png'), key=lambda p: p.stat().st_mtime)
    print(f'{"run":40}{"lines":>9}{"identical":>12}{"SSIM":>9}')
    for png in runs:
        label = png.parent.name
        _, s = load_scores(d, label)
        mark = '  <- baseline' if label == baseline else ''
        print(f"{label:40}{percent(s['line_match']):>9}{s['identical_slides']:>7}/{s['text_slides']:<4}"
              f"{s['mean_ssim']:>9.4f}{mark}")


def cmd_baseline(args):
    d = deck_dir(args)
    if args.label:
        if not (d / 'runs' / args.label / 'png').is_dir():
            die(f'no run "{args.label}"')
        (d / 'baseline.txt').write_text(args.label, encoding='utf-8')
    print(baseline_of(d) or '(none)')


def cmd_compare(args):
    require_windows('Side-by-side images')
    d = deck_dir(args)
    labels = args.labels
    if not labels:
        runs = sorted((d / 'runs').glob('*/run.json'), key=lambda p: p.stat().st_mtime)
        latest = runs[-1].parent.name if runs else None
        labels = [l for l in dict.fromkeys([baseline_of(d), latest]) if l]
    name = f'p{args.slide:04d}.png'
    images = [d / 'reference' / 'png' / name] + [d / 'runs' / l / 'png' / name for l in labels]
    for image in images:
        if not image.exists():
            die(f'missing {image}')
    out = d / 'compare' / f"slide{args.slide:04d}-{'-vs-'.join(labels)}.png"
    powershell('montage.ps1', '-Out', out, '-Images', '|'.join(map(str, images)),
               '-Labels', '|'.join([f'PowerPoint (slide {args.slide})'] + labels))
    print(out)


# ---------------------------------------------------------------- CLI

SHIPPED_FONTS_HELP = ('use the font list shipped in the converter (made on the build server) instead of one '
                      'made from this PC\'s fonts, as runs made before I-023 was fixed did')


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--work', help='work folder (default: ../fidelity-work next to the repo, or $FIDELITY_WORK)')
    sub = p.add_subparsers(dest='command', required=True)

    s = sub.add_parser('reference', help='copy a deck in and export the PowerPoint reference')
    s.add_argument('deck', help='path to the .pptx (it is copied, never modified)')
    s.add_argument('--name', required=True, help='short name for the deck, e.g. great-roll')
    s.add_argument('--force', action='store_true', help='replace an existing reference')
    s.set_defaults(func=cmd_reference)

    s = sub.add_parser('render', help='render with the release app (--release) or a built sdkjs (--sdkjs)')
    s.add_argument('name')
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument('--release', action='store_true', help='use the app exactly as released')
    g.add_argument('--sdkjs', help='a built sdkjs deploy folder (containing slide/sdk-all.js)')
    s.add_argument('--label', help='name for this run')
    s.add_argument('--app', help='Euro-Office app folder (default: newest under <work>/apps)')
    s.add_argument('--force', action='store_true', help='overwrite a run with the same label')
    s.add_argument('--shipped-fonts', action='store_true', help=SHIPPED_FONTS_HELP)
    s.set_defaults(func=cmd_render)

    s = sub.add_parser('loop', help='build sdkjs from this checkout, render with it, score vs baseline')
    s.add_argument('name')
    s.add_argument('--label', help='name for this run (default: date-time plus sdkjs commit)')
    s.add_argument('--baseline', help='run to compare against (default: the deck\'s baseline)')
    s.add_argument('--app', help='Euro-Office app folder (default: newest under <work>/apps)')
    s.add_argument('--force', action='store_true', help='overwrite a run with the same label')
    s.add_argument('--verbose', action='store_true', help='show webpack output')
    s.add_argument('--shipped-fonts', action='store_true', help=SHIPPED_FONTS_HELP)
    s.set_defaults(func=cmd_loop)

    s = sub.add_parser('score', help='(re)score a run and compare it with the baseline')
    s.add_argument('name')
    s.add_argument('label')
    s.add_argument('--baseline')
    s.set_defaults(func=cmd_score)

    s = sub.add_parser('runs', help='list a deck\'s runs with their headline scores')
    s.add_argument('name')
    s.set_defaults(func=cmd_runs)

    s = sub.add_parser('baseline', help='show or set the run other runs are compared with')
    s.add_argument('name')
    s.add_argument('label', nargs='?')
    s.set_defaults(func=cmd_baseline)

    s = sub.add_parser('compare', help='side-by-side image of one slide: PowerPoint, baseline, latest run')
    s.add_argument('name')
    s.add_argument('slide', type=int)
    s.add_argument('labels', nargs='*', help='runs to show (default: baseline and latest run)')
    s.set_defaults(func=cmd_compare)

    args = p.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
