//! Usage: ssim-compare <ref_dir> <candidate_dir> <out_csv>
//! Grayscale SSIM (7x7 uniform window, K1=0.01, K2=0.03) per page; the
//! candidate is resized to the reference size. Pages present only in the
//! reference score 0.
use image::{imageops::FilterType, GrayImage};
use std::{env, fs, io::Write, path::Path};

fn integral(img: &[f64], w: usize, h: usize) -> Vec<f64> {
    let mut s = vec![0.0; (w + 1) * (h + 1)];
    for y in 0..h {
        let mut row = 0.0;
        for x in 0..w {
            row += img[y * w + x];
            s[(y + 1) * (w + 1) + x + 1] = s[y * (w + 1) + x + 1] + row;
        }
    }
    s
}

fn rect(s: &[f64], w: usize, x0: usize, y0: usize, x1: usize, y1: usize) -> f64 {
    let w1 = w + 1;
    s[y1 * w1 + x1] - s[y0 * w1 + x1] - s[y1 * w1 + x0] + s[y0 * w1 + x0]
}

fn ssim(a: &GrayImage, b: &GrayImage) -> f64 {
    let (w, h) = (a.width() as usize, a.height() as usize);
    let fa: Vec<f64> = a.as_raw().iter().map(|&v| v as f64).collect();
    let fb: Vec<f64> = b.as_raw().iter().map(|&v| v as f64).collect();
    let aa: Vec<f64> = fa.iter().map(|v| v * v).collect();
    let bb: Vec<f64> = fb.iter().map(|v| v * v).collect();
    let ab: Vec<f64> = fa.iter().zip(&fb).map(|(x, y)| x * y).collect();
    let (sa, sb, saa, sbb, sab) = (
        integral(&fa, w, h), integral(&fb, w, h), integral(&aa, w, h),
        integral(&bb, w, h), integral(&ab, w, h),
    );
    let (c1, c2) = ((0.01f64 * 255.0).powi(2), (0.03f64 * 255.0).powi(2));
    let r = 3usize;
    let n = 49.0;
    let (mut total, mut count) = (0.0, 0u64);
    for y in r..h.saturating_sub(r) {
        for x in r..w.saturating_sub(r) {
            let (x0, y0, x1, y1) = (x - r, y - r, x + r + 1, y + r + 1);
            let ma = rect(&sa, w, x0, y0, x1, y1) / n;
            let mb = rect(&sb, w, x0, y0, x1, y1) / n;
            let va = (rect(&saa, w, x0, y0, x1, y1) / n - ma * ma) * n / (n - 1.0);
            let vb = (rect(&sbb, w, x0, y0, x1, y1) / n - mb * mb) * n / (n - 1.0);
            let cov = (rect(&sab, w, x0, y0, x1, y1) / n - ma * mb) * n / (n - 1.0);
            total += ((2.0 * ma * mb + c1) * (2.0 * cov + c2))
                / ((ma * ma + mb * mb + c1) * (va + vb + c2));
            count += 1;
        }
    }
    if count == 0 { 0.0 } else { total / count as f64 }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let (ref_dir, cand_dir, out) = (Path::new(&args[1]), Path::new(&args[2]), &args[3]);
    let mut pages: Vec<_> = fs::read_dir(ref_dir).unwrap()
        .filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().to_string())
        .filter(|n| n.ends_with(".png")).collect();
    pages.sort();
    let mut csv = fs::File::create(out).unwrap();
    writeln!(csv, "page,ssim").unwrap();
    let (mut sum, mut missing) = (0.0, 0);
    for p in &pages {
        let a = image::open(ref_dir.join(p)).unwrap().to_luma8();
        let score = match image::open(cand_dir.join(p)) {
            Ok(img) => {
                let b = image::imageops::resize(&img.to_luma8(), a.width(), a.height(), FilterType::Lanczos3);
                ssim(&a, &b)
            }
            Err(_) => { missing += 1; 0.0 }
        };
        sum += score;
        writeln!(csv, "{},{:.4}", p.trim_start_matches('p').trim_end_matches(".png"), score).unwrap();
    }
    println!("pages={} missing={} mean_ssim={:.4}", pages.len(), missing, sum / pages.len() as f64);
}
