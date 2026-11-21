//! Visual evidence of where a candidate render differs from a reference render,
//! for reviewing slides by eye.
//!
//! slide-diff pages <ref_dir> <cand_dir> <out_dir>
//!     For every pNNNN.png in ref_dir, writes out_dir/pNNNN.png (a 2x2 sheet:
//!     reference | candidate on top, difference map | 50/50 blend below) and
//!     out_dir/pNNNN.json (the changed regions, largest first).
//!     In the difference map, red = ink only in the reference, blue = ink only
//!     in the candidate, green boxes = the regions listed in the JSON.
//! slide-diff crop <ref.png> <cand.png> <x0> <y0> <x1> <y1> <out.png>
//!     Magnified side-by-side (or stacked, for wide boxes) crop of one region,
//!     coordinates as fractions 0..1 of the page: reference, candidate, map.
use image::{imageops, imageops::FilterType, Rgb, RgbImage};
use std::{collections::VecDeque, env, fs, path::Path};

const THRESHOLD: i32 = 48; // per-channel difference that counts as changed
const DILATE: i32 = 6; // px; joins nearby changes into one region
const MIN_CHANGED: u32 = 6; // ignore regions with fewer changed pixels

fn load(p: &Path) -> RgbImage {
    image::open(p).unwrap_or_else(|e| panic!("{}: {e}", p.display())).to_rgb8()
}

fn luma(p: &Rgb<u8>) -> i32 {
    (299 * p[0] as i32 + 587 * p[1] as i32 + 114 * p[2] as i32) / 1000
}

struct Diff {
    changed: Vec<bool>,
    ref_ink: Vec<bool>, // changed and the reference is darker there
}

fn diff(a: &RgbImage, b: &RgbImage) -> Diff {
    let n = (a.width() * a.height()) as usize;
    let (mut changed, mut ref_ink) = (vec![false; n], vec![false; n]);
    for (i, (pa, pb)) in a.pixels().zip(b.pixels()).enumerate() {
        let d = (0..3).map(|c| (pa[c] as i32 - pb[c] as i32).abs()).max().unwrap();
        if d > THRESHOLD {
            changed[i] = true;
            ref_ink[i] = luma(pa) < luma(pb);
        }
    }
    Diff { changed, ref_ink }
}

struct Region {
    x0: u32, y0: u32, x1: u32, y1: u32,
    changed: u32, only_ref: u32, only_cand: u32,
}

fn regions(d: &Diff, w: u32, h: u32) -> Vec<Region> {
    let (wi, hi) = (w as i32, h as i32);
    // Dilate the changed mask with a summed-area table.
    let mut sat = vec![0u32; ((w + 1) * (h + 1)) as usize];
    for y in 0..h {
        let mut row = 0;
        for x in 0..w {
            row += d.changed[(y * w + x) as usize] as u32;
            sat[((y + 1) * (w + 1) + x + 1) as usize] = sat[(y * (w + 1) + x + 1) as usize] + row;
        }
    }
    let at = |x: i32, y: i32| sat[(y * (wi + 1) + x) as usize];
    let mut mask = vec![false; (w * h) as usize];
    for y in 0..hi {
        for x in 0..wi {
            let (x0, y0) = ((x - DILATE).max(0), (y - DILATE).max(0));
            let (x1, y1) = ((x + DILATE + 1).min(wi), (y + DILATE + 1).min(hi));
            mask[(y * wi + x) as usize] = at(x1, y1) + at(x0, y0) > at(x0, y1) + at(x1, y0);
        }
    }
    let mut seen = vec![false; mask.len()];
    let mut out = Vec::new();
    for start in 0..mask.len() {
        if !mask[start] || seen[start] {
            continue;
        }
        let mut r = Region { x0: w, y0: h, x1: 0, y1: 0, changed: 0, only_ref: 0, only_cand: 0 };
        let mut q = VecDeque::from([start]);
        seen[start] = true;
        while let Some(i) = q.pop_front() {
            let (x, y) = ((i as u32) % w, (i as u32) / w);
            if d.changed[i] {
                r.changed += 1;
                if d.ref_ink[i] { r.only_ref += 1 } else { r.only_cand += 1 }
                r.x0 = r.x0.min(x); r.y0 = r.y0.min(y);
                r.x1 = r.x1.max(x + 1); r.y1 = r.y1.max(y + 1);
            }
            for (dx, dy) in [(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
                let (nx, ny) = (x as i32 + dx, y as i32 + dy);
                if nx >= 0 && ny >= 0 && nx < wi && ny < hi {
                    let j = (ny * wi + nx) as usize;
                    if mask[j] && !seen[j] {
                        seen[j] = true;
                        q.push_back(j);
                    }
                }
            }
        }
        if r.changed >= MIN_CHANGED {
            out.push(r);
        }
    }
    out.sort_by(|a, b| b.changed.cmp(&a.changed));
    out
}

fn diff_map(a: &RgbImage, d: &Diff, boxes: &[Region]) -> RgbImage {
    let mut m = RgbImage::new(a.width(), a.height());
    for (i, (p, o)) in a.pixels().zip(m.pixels_mut()).enumerate() {
        *o = if d.changed[i] {
            if d.ref_ink[i] { Rgb([220, 30, 30]) } else { Rgb([30, 70, 235]) }
        } else {
            let v = (255 - (255 - luma(p)) * 35 / 100) as u8;
            Rgb([v, v, v])
        };
    }
    for r in boxes.iter().take(12) {
        draw_box(&mut m, r.x0.saturating_sub(3), r.y0.saturating_sub(3), r.x1 + 3, r.y1 + 3);
    }
    m
}

fn draw_box(m: &mut RgbImage, x0: u32, y0: u32, x1: u32, y1: u32) {
    let (w, h) = (m.width(), m.height());
    let (x1, y1) = (x1.min(w - 1), y1.min(h - 1));
    for t in 0..2 {
        for x in x0..=x1 {
            for y in [y0 + t, y1.saturating_sub(t)] {
                if y < h { m.put_pixel(x, y, Rgb([0, 170, 0])) }
            }
        }
        for y in y0..=y1 {
            for x in [x0 + t, x1.saturating_sub(t)] {
                if x < w { m.put_pixel(x, y, Rgb([0, 170, 0])) }
            }
        }
    }
}

fn blend(a: &RgbImage, b: &RgbImage) -> RgbImage {
    let mut m = a.clone();
    for (o, p) in m.pixels_mut().zip(b.pixels()) {
        for c in 0..3 {
            o[c] = ((o[c] as u16 + p[c] as u16) / 2) as u8;
        }
    }
    m
}

/// Lays panels out in a grid with gray gutters.
fn sheet(panels: &[&RgbImage], cols: u32) -> RgbImage {
    let (pw, ph) = (panels[0].width(), panels[0].height());
    let rows = (panels.len() as u32 + cols - 1) / cols;
    let g = 6;
    let mut s = RgbImage::from_pixel(cols * pw + (cols - 1) * g, rows * ph + (rows - 1) * g, Rgb([128, 128, 128]));
    for (i, p) in panels.iter().enumerate() {
        let (c, r) = (i as u32 % cols, i as u32 / cols);
        imageops::replace(&mut s, *p, (c * (pw + g)) as i64, (r * (ph + g)) as i64);
    }
    s
}

fn same_size(a: &RgbImage, b: RgbImage) -> RgbImage {
    if a.dimensions() == b.dimensions() { b } else { imageops::resize(&b, a.width(), a.height(), FilterType::CatmullRom) }
}

fn pages(ref_dir: &Path, cand_dir: &Path, out_dir: &Path) {
    fs::create_dir_all(out_dir).unwrap();
    let mut names: Vec<String> = fs::read_dir(ref_dir).unwrap().filter_map(|e| e.ok())
        .map(|e| e.file_name().to_string_lossy().to_string()).filter(|n| n.ends_with(".png")).collect();
    names.sort();
    for name in names {
        let a = load(&ref_dir.join(&name));
        let cand = cand_dir.join(&name);
        let b = if cand.exists() { same_size(&a, load(&cand)) } else { RgbImage::from_pixel(a.width(), a.height(), Rgb([255, 255, 255])) };
        let d = diff(&a, &b);
        let rs = regions(&d, a.width(), a.height());
        let total: u64 = d.changed.iter().filter(|&&c| c).count() as u64;
        let map = diff_map(&a, &d, &rs);
        sheet(&[&a, &b, &map, &blend(&a, &b)], 2).save(out_dir.join(&name)).unwrap();
        let (w, h) = (a.width() as f64, a.height() as f64);
        let items: Vec<String> = rs.iter().enumerate().map(|(i, r)| format!(
            "{{\"n\":{},\"px\":[{},{},{},{}],\"frac\":[{:.4},{:.4},{:.4},{:.4}],\"changed\":{},\"only_ref\":{},\"only_cand\":{}}}",
            i + 1, r.x0, r.y0, r.x1, r.y1, r.x0 as f64 / w, r.y0 as f64 / h, r.x1 as f64 / w, r.y1 as f64 / h,
            r.changed, r.only_ref, r.only_cand)).collect();
        let json = format!(
            "{{\"width\":{},\"height\":{},\"changed_px\":{},\"changed_fraction\":{:.6},\"candidate_missing\":{},\"regions\":[{}]}}\n",
            a.width(), a.height(), total, total as f64 / (w * h), !cand.exists(), items.join(","));
        fs::write(out_dir.join(name.replace(".png", ".json")), json).unwrap();
    }
}

fn crop(ref_png: &Path, cand_png: &Path, f: [f64; 4], out: &Path) {
    let a = load(ref_png);
    let b = same_size(&a, load(cand_png));
    let (w, h) = (a.width() as f64, a.height() as f64);
    let pad = 8.0;
    let x0 = ((f[0] * w - pad).max(0.0)) as u32;
    let y0 = ((f[1] * h - pad).max(0.0)) as u32;
    let x1 = ((f[2] * w + pad).min(w)) as u32;
    let y1 = ((f[3] * h + pad).min(h)) as u32;
    let (cw, ch) = ((x1 - x0).max(1), (y1 - y0).max(1));
    let ca = imageops::crop_imm(&a, x0, y0, cw, ch).to_image();
    let cb = imageops::crop_imm(&b, x0, y0, cw, ch).to_image();
    let d = diff(&ca, &cb);
    let map = diff_map(&ca, &d, &[]);
    let wide = cw > ch * 2;
    let target = 1400.0;
    let scale = if wide { (target / cw as f64).min(4.0) } else { (target / (3.0 * cw as f64)).min(4.0) }.max(1.0);
    let (sw, sh) = ((cw as f64 * scale) as u32, (ch as f64 * scale) as u32);
    let up = |m: &RgbImage| imageops::resize(m, sw, sh, FilterType::CatmullRom);
    let (ua, ub, um) = (up(&ca), up(&cb), up(&map));
    sheet(&[&ua, &ub, &um], if wide { 1 } else { 3 }).save(out).unwrap();
}

fn main() {
    let a: Vec<String> = env::args().collect();
    match a.get(1).map(|s| s.as_str()) {
        Some("pages") if a.len() == 5 => pages(Path::new(&a[2]), Path::new(&a[3]), Path::new(&a[4])),
        Some("crop") if a.len() == 9 => {
            let f: Vec<f64> = a[4..8].iter().map(|s| s.parse().expect("fractions 0..1")).collect();
            crop(Path::new(&a[2]), Path::new(&a[3]), [f[0], f[1], f[2], f[3]], Path::new(&a[8]));
        }
        _ => {
            eprintln!("usage: slide-diff pages <ref_dir> <cand_dir> <out_dir>\n       slide-diff crop <ref.png> <cand.png> <x0> <y0> <x1> <y1> <out.png>");
            std::process::exit(2);
        }
    }
}
