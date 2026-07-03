
from pathlib import Path
from PIL import Image, ImageFile, PngImagePlugin
import argparse
import csv
import cv2
import numpy as np

ImageFile.LOAD_TRUNCATED_IMAGES = True
PngImagePlugin.MAX_TEXT_CHUNK = 1024 * 1024 * 1024
PngImagePlugin.MAX_TEXT_MEMORY = 1024 * 1024 * 1024

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def list_images(path):
    return sorted([p for p in Path(path).iterdir() if p.suffix.lower() in EXTS])


def load_rgb(path, size):
    with Image.open(path) as img:
        img = img.convert("RGB")
        if size > 0:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return np.array(img, dtype=np.uint8)


def save_rgb(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(path)


def prepare_dirs(input_dir, output_dir):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not input_dir.exists():
        raise FileNotFoundError(f"input_dir not found: {input_dir}")
    images = list_images(input_dir)
    if not images:
        raise RuntimeError(f"no images found: {input_dir}")
    return images, output_dir


def normalize01(x):
    x = x.astype(np.float32)
    lo, hi = float(np.min(x)), float(np.max(x))
    if hi <= lo:
        return np.zeros_like(x, dtype=np.float32)
    return (x - lo) / (hi - lo)


def profile_defaults(profile):
    profiles = {
        # Default: lower and cleaner than high_plus.
        # Expected changed_lsb_ratio: about 0.24~0.31.
        "mid_stable": {
            "target_mask_min": 0.42, "target_mask_max": 0.56,
            "payload_ratio_min": 0.68, "payload_ratio_max": 0.84,
            "channel_prob_one": 0.35, "channel_prob_two": 0.55, "channel_prob_three": 0.10,
            "texture_weight": 0.74, "edge_weight": 0.16, "hf_weight": 0.10,
            "min_pixel_ratio": 0.12, "score_power_min": 1.10, "score_power_max": 1.45,
            "jitter_ratio": 0.02,
        },
        "mid_light": {
            "target_mask_min": 0.36, "target_mask_max": 0.48,
            "payload_ratio_min": 0.62, "payload_ratio_max": 0.78,
            "channel_prob_one": 0.45, "channel_prob_two": 0.48, "channel_prob_three": 0.07,
            "texture_weight": 0.78, "edge_weight": 0.14, "hf_weight": 0.08,
            "min_pixel_ratio": 0.10, "score_power_min": 1.15, "score_power_max": 1.55,
            "jitter_ratio": 0.02,
        },
        "mid_high": {
            "target_mask_min": 0.48, "target_mask_max": 0.60,
            "payload_ratio_min": 0.72, "payload_ratio_max": 0.88,
            "channel_prob_one": 0.28, "channel_prob_two": 0.60, "channel_prob_three": 0.12,
            "texture_weight": 0.70, "edge_weight": 0.18, "hf_weight": 0.12,
            "min_pixel_ratio": 0.14, "score_power_min": 1.05, "score_power_max": 1.35,
            "jitter_ratio": 0.03,
        },
    }
    return profiles[profile].copy()


def texture_score(rgb, cfg, score_power):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

    mean = cv2.blur(gray, (7, 7))
    mean_sq = cv2.blur(gray * gray, (7, 7))
    variance = np.maximum(mean_sq - mean * mean, 0.0)

    sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(sx, sy)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))

    score = (
        cfg["texture_weight"] * normalize01(variance)
        + cfg["edge_weight"] * normalize01(grad)
        + cfg["hf_weight"] * normalize01(lap)
    )
    score = np.power(np.clip(score, 0.0, 1.0), float(score_power))
    score[:1, :] = 0.0
    score[-1:, :] = 0.0
    score[:, :1] = 0.0
    score[:, -1:] = 0.0
    return score


def choose_mask_by_target(score, rng, target_mask_ratio, min_pixel_ratio, jitter_ratio):
    h, w = score.shape
    total = h * w
    target = max(1, min(total, max(int(total * target_mask_ratio), int(total * min_pixel_ratio))))
    flat = score.reshape(-1)

    if float(flat.max()) <= 0.0:
        idx = rng.choice(total, size=target, replace=False)
    else:
        pool_n = min(total, max(target, int(target * (1.0 + jitter_ratio))))
        pool = np.argpartition(flat, -pool_n)[-pool_n:]
        idx = rng.choice(pool, size=target, replace=False)

    mask = np.zeros(total, dtype=bool)
    mask[idx] = True
    return mask.reshape(h, w)


def choose_channel_sets(count, rng, cfg):
    probs = np.array([cfg["channel_prob_one"], cfg["channel_prob_two"], cfg["channel_prob_three"]], dtype=np.float64)
    probs /= probs.sum()
    mode = int(rng.choice([1, 2, 3], p=probs))

    if mode == 1:
        return [rng.integers(0, 3, size=count, dtype=np.int64)]
    if mode == 2:
        first = rng.integers(0, 3, size=count, dtype=np.int64)
        second = (first + rng.integers(1, 3, size=count, dtype=np.int64)) % 3
        return [first, second]
    return [np.zeros(count, dtype=np.int64), np.ones(count, dtype=np.int64), np.full(count, 2, dtype=np.int64)]


def embed_texture_adaptive_lsb(rgb, seed, cfg, target_mask_ratio, payload_ratio, score_power, bit_mode):
    rng = np.random.default_rng(seed)
    arr = rgb.copy()
    h, w, _ = arr.shape
    total_pixels = h * w

    score = texture_score(arr, cfg, score_power)
    mask = choose_mask_by_target(score, rng, target_mask_ratio, cfg["min_pixel_ratio"], cfg["jitter_ratio"])

    ys, xs = np.where(mask)
    candidate_count = len(xs)
    selected_count = min(candidate_count, max(1, int(candidate_count * payload_ratio)))
    selected = rng.choice(candidate_count, size=selected_count, replace=False)
    ys, xs = ys[selected], xs[selected]

    before = arr.copy()
    for channels in choose_channel_sets(selected_count, rng, cfg):
        if bit_mode == "replace":
            bits = rng.integers(0, 2, size=selected_count, dtype=np.uint8)
            arr[ys, xs, channels] = (arr[ys, xs, channels] & 0xFE) | bits
        else:
            arr[ys, xs, channels] ^= 1

    changed_lsb_values = int(np.count_nonzero((before ^ arr) & 1))
    changed_pixels = int(np.count_nonzero(np.any(before != arr, axis=2)))

    return arr, {
        "mask_ratio": float(mask.sum()) / float(total_pixels),
        "selected_ratio": float(selected_count) / float(total_pixels),
        "changed_pixel_ratio": float(changed_pixels) / float(total_pixels),
        "changed_lsb_ratio": float(changed_lsb_values) / float(total_pixels * 3),
        "score_mean": float(np.mean(score)),
        "score_std": float(np.std(score)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_texture_adaptive_lsb/stego")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--profile", choices=["mid_light", "mid_stable", "mid_high"], default="mid_stable")
    parser.add_argument("--payload_ratio_min", type=float, default=None)
    parser.add_argument("--payload_ratio_max", type=float, default=None)
    parser.add_argument("--target_mask_min", type=float, default=None)
    parser.add_argument("--target_mask_max", type=float, default=None)
    parser.add_argument("--bit_mode", choices=["flip", "replace"], default="flip")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--report_csv", default="")
    parser.add_argument("--progress_every", type=int, default=5000)
    args = parser.parse_args()

    cfg = profile_defaults(args.profile)
    if args.payload_ratio_min is not None:
        cfg["payload_ratio_min"] = float(args.payload_ratio_min)
    if args.payload_ratio_max is not None:
        cfg["payload_ratio_max"] = float(args.payload_ratio_max)
    if args.target_mask_min is not None:
        cfg["target_mask_min"] = float(args.target_mask_min)
    if args.target_mask_max is not None:
        cfg["target_mask_max"] = float(args.target_mask_max)

    images, output_dir = prepare_dirs(args.input_dir, args.output_dir)
    rng = np.random.default_rng(args.seed)
    report_path = Path(args.report_csv) if args.report_csv else output_dir / "_texture_adaptive_lsb_report.csv"

    print("[texture_adaptive_lsb] mid-stable texture generator")
    print(f"input_dir={args.input_dir}")
    print(f"output_dir={args.output_dir}")
    print(f"profile={args.profile}")
    print(f"target_mask_ratio={cfg['target_mask_min']:.2f}~{cfg['target_mask_max']:.2f}")
    print(f"payload_ratio={cfg['payload_ratio_min']:.2f}~{cfg['payload_ratio_max']:.2f}")
    print(f"channel_probs=one:{cfg['channel_prob_one']:.2f}, two:{cfg['channel_prob_two']:.2f}, three:{cfg['channel_prob_three']:.2f}")
    print(f"score_power={cfg['score_power_min']:.2f}~{cfg['score_power_max']:.2f}")
    print(f"bit_mode={args.bit_mode}")
    print("target_changed_lsb_ratio ~= 0.24~0.31 for mid_stable")

    ok, skipped = 0, 0
    sums = {"mask_ratio": 0.0, "selected_ratio": 0.0, "changed_pixel_ratio": 0.0, "changed_lsb_ratio": 0.0}

    with report_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "file", "profile", "payload_ratio", "target_mask_ratio", "score_power",
            "mask_ratio", "selected_ratio", "changed_pixel_ratio", "changed_lsb_ratio",
            "score_mean", "score_std"
        ])
        writer.writeheader()

        for idx, path in enumerate(images):
            try:
                payload_ratio = float(rng.uniform(cfg["payload_ratio_min"], cfg["payload_ratio_max"]))
                target_mask_ratio = float(rng.uniform(cfg["target_mask_min"], cfg["target_mask_max"]))
                score_power = float(rng.uniform(cfg["score_power_min"], cfg["score_power_max"]))

                rgb = load_rgb(path, args.size)
                stego, stat = embed_texture_adaptive_lsb(
                    rgb, args.seed + idx, cfg, target_mask_ratio, payload_ratio, score_power, args.bit_mode
                )
                save_rgb(stego, output_dir / f"{path.stem}.png")

                writer.writerow({
                    "file": path.name, "profile": args.profile,
                    "payload_ratio": payload_ratio, "target_mask_ratio": target_mask_ratio,
                    "score_power": score_power, **stat
                })

                ok += 1
                for k in sums:
                    sums[k] += stat[k]

                if args.progress_every > 0 and ok % args.progress_every == 0:
                    d = max(1, ok)
                    print(
                        f"[progress] {ok}/{len(images)} "
                        f"avg_mask={sums['mask_ratio']/d:.4f} "
                        f"avg_selected={sums['selected_ratio']/d:.4f} "
                        f"avg_changed_pixel={sums['changed_pixel_ratio']/d:.4f} "
                        f"avg_changed_lsb={sums['changed_lsb_ratio']/d:.4f}"
                    )
            except Exception as exc:
                skipped += 1
                print(f"[SKIP] {path.name}: {exc}")

    d = max(1, ok)
    print(f"done: {ok} texture adaptive LSB stego images saved to {output_dir} / skipped: {skipped}")
    print(
        f"avg_mask={sums['mask_ratio']/d:.4f}, "
        f"avg_selected={sums['selected_ratio']/d:.4f}, "
        f"avg_changed_pixel={sums['changed_pixel_ratio']/d:.4f}, "
        f"avg_changed_lsb={sums['changed_lsb_ratio']/d:.4f}"
    )
    print(f"report_csv={report_path}")


if __name__ == "__main__":
    main()
