from pathlib import Path
from PIL import Image, ImageFile, PngImagePlugin
import argparse
import csv
import hashlib
import cv2
import numpy as np

ImageFile.LOAD_TRUNCATED_IMAGES = True
PngImagePlugin.MAX_TEXT_CHUNK = 1024 * 1024 * 1024
PngImagePlugin.MAX_TEXT_MEMORY = 1024 * 1024 * 1024

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def list_images(path):
    path = Path(path)
    return sorted([p for p in path.iterdir() if p.suffix.lower() in EXTS])


def load_rgb(path, size):
    with Image.open(path) as img:
        img = img.convert("RGB")
        if size > 0:
            img = img.resize((size, size), Image.Resampling.LANCZOS)
        return np.array(img, dtype=np.uint8)


def save_rgb(arr, path):
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").save(path)


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
    lo = float(np.min(x))
    hi = float(np.max(x))
    if hi <= lo:
        return np.zeros_like(x, dtype=np.float32)
    return (x - lo) / (hi - lo)


def profile_defaults(profile):
    # fixed_high_plus is the default for edge_adaptive_lsb.
    # It is aimed at the 78~80% range without going fully artificial.
    # Compared with fixed_high:
    # - slightly stronger and narrower payload/mask range
    # - mostly 2-channel edits
    # - small 3-channel ratio only
    # - target changed_lsb_ratio roughly 0.23~0.30
    profiles = {
        "light": {
            "target_mask_min": 0.24,
            "target_mask_max": 0.38,
            "payload_ratio_min": 0.35,
            "payload_ratio_max": 0.60,
            "channel_prob_one": 0.80,
            "channel_prob_two": 0.18,
            "channel_prob_three": 0.02,
            "canny_boost": 0.65,
            "edge_dilate_min": 0,
            "edge_dilate_max": 1,
            "min_pixel_ratio": 0.08,
        },
        "balanced": {
            "target_mask_min": 0.32,
            "target_mask_max": 0.50,
            "payload_ratio_min": 0.45,
            "payload_ratio_max": 0.75,
            "channel_prob_one": 0.70,
            "channel_prob_two": 0.25,
            "channel_prob_three": 0.05,
            "canny_boost": 0.75,
            "edge_dilate_min": 0,
            "edge_dilate_max": 1,
            "min_pixel_ratio": 0.10,
        },
        "medium_high": {
            "target_mask_min": 0.46,
            "target_mask_max": 0.66,
            "payload_ratio_min": 0.62,
            "payload_ratio_max": 0.90,
            "channel_prob_one": 0.52,
            "channel_prob_two": 0.36,
            "channel_prob_three": 0.12,
            "canny_boost": 0.88,
            "edge_dilate_min": 1,
            "edge_dilate_max": 2,
            "min_pixel_ratio": 0.14,
        },
        "fixed_high": {
            "target_mask_min": 0.54,
            "target_mask_max": 0.60,
            "payload_ratio_min": 0.78,
            "payload_ratio_max": 0.84,
            "channel_prob_one": 0.22,
            "channel_prob_two": 0.68,
            "channel_prob_three": 0.10,
            "canny_boost": 0.92,
            "edge_dilate_min": 1,
            "edge_dilate_max": 2,
            "min_pixel_ratio": 0.16,
        },
        "fixed_high_plus": {
            "target_mask_min": 0.58,
            "target_mask_max": 0.64,
            "payload_ratio_min": 0.82,
            "payload_ratio_max": 0.88,
            "channel_prob_one": 0.12,
            "channel_prob_two": 0.76,
            "channel_prob_three": 0.12,
            "canny_boost": 0.96,
            "edge_dilate_min": 1,
            "edge_dilate_max": 2,
            "min_pixel_ratio": 0.18,
        },
        "strong": {
            "target_mask_min": 0.62,
            "target_mask_max": 0.72,
            "payload_ratio_min": 0.88,
            "payload_ratio_max": 0.96,
            "channel_prob_one": 0.08,
            "channel_prob_two": 0.66,
            "channel_prob_three": 0.26,
            "canny_boost": 1.00,
            "edge_dilate_min": 2,
            "edge_dilate_max": 2,
            "min_pixel_ratio": 0.20,
        },
    }
    return profiles[profile].copy()

def build_score(rgb, rng, canny_boost, edge_dilate_min, edge_dilate_max):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    med = float(np.median(gray))
    sigma = float(rng.uniform(0.25, 0.42))
    low = int(max(5, (1.0 - sigma) * med))
    high = int(min(255, (1.0 + sigma) * med + rng.integers(12, 48)))
    if high <= low:
        high = min(255, low + 60)

    canny = cv2.Canny(gray, low, high) > 0

    dilate_iter = int(rng.integers(edge_dilate_min, edge_dilate_max + 1))
    if dilate_iter > 0:
        kernel = np.ones((3, 3), np.uint8)
        canny = cv2.dilate(canny.astype(np.uint8), kernel, iterations=dilate_iter) > 0

    sobel_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.magnitude(sobel_x, sobel_y)

    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))

    gray_f = gray.astype(np.float32)
    mean = cv2.GaussianBlur(gray_f, (5, 5), 0)
    mean_sq = cv2.GaussianBlur(gray_f * gray_f, (5, 5), 0)
    local_var = np.maximum(mean_sq - mean * mean, 0.0)

    score = (
        0.50 * normalize01(grad)
        + 0.30 * normalize01(lap)
        + 0.20 * normalize01(local_var)
    )
    score = score + canny.astype(np.float32) * float(canny_boost)

    score[:1, :] = 0.0
    score[-1:, :] = 0.0
    score[:, :1] = 0.0
    score[:, -1:] = 0.0

    return score, canny, dilate_iter


def choose_mask(score, rng, target_mask_ratio, min_pixel_ratio):
    h, w = score.shape
    total = h * w
    target = int(total * float(target_mask_ratio))
    target = max(int(total * float(min_pixel_ratio)), target)
    target = max(1, min(total, target))

    flat = score.reshape(-1)

    if float(flat.max()) <= 0.0:
        idx = rng.choice(total, size=target, replace=False)
    else:
        idx = np.argpartition(flat, -target)[-target:]
        rng.shuffle(idx)

    mask = np.zeros(total, dtype=bool)
    mask[idx] = True
    return mask.reshape(h, w)


def choose_channel_sets(count, rng, p_one, p_two, p_three):
    probs = np.array([p_one, p_two, p_three], dtype=np.float64)
    probs = probs / probs.sum()
    mode = int(rng.choice([1, 2, 3], p=probs))

    if mode == 1:
        return [rng.integers(0, 3, size=count, dtype=np.int64)]
    if mode == 2:
        first = rng.integers(0, 3, size=count, dtype=np.int64)
        second = (first + rng.integers(1, 3, size=count, dtype=np.int64)) % 3
        return [first, second]

    return [
        np.zeros(count, dtype=np.int64),
        np.ones(count, dtype=np.int64),
        np.full(count, 2, dtype=np.int64),
    ]


def embed_edge_adaptive_lsb(rgb, seed, cfg, bit_mode):
    rng = np.random.default_rng(seed)
    arr = rgb.copy()
    h, w, _ = arr.shape
    total_pixels = h * w

    score, canny, dilate_iter = build_score(
        arr,
        rng,
        canny_boost=cfg["canny_boost"],
        edge_dilate_min=cfg["edge_dilate_min"],
        edge_dilate_max=cfg["edge_dilate_max"],
    )

    target_mask_ratio = float(rng.uniform(cfg["target_mask_min"], cfg["target_mask_max"]))
    payload_ratio = float(rng.uniform(cfg["payload_ratio_min"], cfg["payload_ratio_max"]))

    mask = choose_mask(
        score,
        rng,
        target_mask_ratio=target_mask_ratio,
        min_pixel_ratio=cfg["min_pixel_ratio"],
    )

    ys, xs = np.where(mask)
    candidate_count = len(xs)
    selected_count = min(candidate_count, max(1, int(candidate_count * payload_ratio)))
    selected = rng.choice(candidate_count, size=selected_count, replace=False)
    ys = ys[selected]
    xs = xs[selected]

    channel_sets = choose_channel_sets(
        selected_count,
        rng,
        cfg["channel_prob_one"],
        cfg["channel_prob_two"],
        cfg["channel_prob_three"],
    )

    before = arr.copy()

    for channels in channel_sets:
        if bit_mode == "replace":
            new_bits = rng.integers(0, 2, size=selected_count, dtype=np.uint8)
            arr[ys, xs, channels] = (arr[ys, xs, channels] & 0xFE) | new_bits
        else:
            arr[ys, xs, channels] ^= 1

    changed_lsb_values = int(np.count_nonzero((before ^ arr) & 1))
    changed_pixels = int(np.count_nonzero(np.any(before != arr, axis=2)))

    return arr, {
        "target_mask_ratio": target_mask_ratio,
        "payload_ratio": payload_ratio,
        "mask_pixels": int(mask.sum()),
        "mask_ratio": float(mask.sum()) / float(total_pixels),
        "selected_pixels": int(selected_count),
        "selected_ratio": float(selected_count) / float(total_pixels),
        "changed_pixels": changed_pixels,
        "changed_pixel_ratio": float(changed_pixels) / float(total_pixels),
        "changed_lsb_values": changed_lsb_values,
        "changed_lsb_ratio": float(changed_lsb_values) / float(total_pixels * 3),
        "canny_ratio": float(canny.sum()) / float(total_pixels),
        "dilate_iterations": int(dilate_iter),
    }


def maybe_override(cfg, args):
    for key in [
        "target_mask_min",
        "target_mask_max",
        "payload_ratio_min",
        "payload_ratio_max",
        "channel_prob_one",
        "channel_prob_two",
        "channel_prob_three",
        "canny_boost",
        "edge_dilate_min",
        "edge_dilate_max",
        "min_pixel_ratio",
    ]:
        val = getattr(args, key)
        if val is not None:
            cfg[key] = val

    if cfg["target_mask_min"] > cfg["target_mask_max"]:
        raise ValueError("target_mask_min must be <= target_mask_max")
    if cfg["payload_ratio_min"] > cfg["payload_ratio_max"]:
        raise ValueError("payload_ratio_min must be <= payload_ratio_max")
    if cfg["edge_dilate_min"] > cfg["edge_dilate_max"]:
        raise ValueError("edge_dilate_min must be <= edge_dilate_max")
    return cfg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="real_images")
    parser.add_argument("--output_dir", default="dataset_edge_adaptive_lsb")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--profile", choices=["light", "balanced", "medium_high", "fixed_high", "fixed_high_plus", "strong"], default="fixed_high_plus")
    parser.add_argument("--bit_mode", choices=["flip", "replace"], default="flip")
    parser.add_argument("--seed", type=int, default=20260626)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--skip_existing", action="store_true")
    parser.add_argument("--stats_csv", default="")

    # Optional overrides. Normally leave these empty and use --profile.
    parser.add_argument("--target_mask_min", type=float, default=None)
    parser.add_argument("--target_mask_max", type=float, default=None)
    parser.add_argument("--payload_ratio_min", type=float, default=None)
    parser.add_argument("--payload_ratio_max", type=float, default=None)
    parser.add_argument("--channel_prob_one", type=float, default=None)
    parser.add_argument("--channel_prob_two", type=float, default=None)
    parser.add_argument("--channel_prob_three", type=float, default=None)
    parser.add_argument("--canny_boost", type=float, default=None)
    parser.add_argument("--edge_dilate_min", type=int, default=None)
    parser.add_argument("--edge_dilate_max", type=int, default=None)
    parser.add_argument("--min_pixel_ratio", type=float, default=None)

    args = parser.parse_args()

    cfg = maybe_override(profile_defaults(args.profile), args)

    images, output_dir = prepare_dirs(args.input_dir, args.output_dir)
    if args.limit and args.limit > 0:
        images = images[: args.limit]

    print("[edge_adaptive_lsb] fixed-high-plus stable generator")
    print(f"input_dir={args.input_dir}")
    print(f"output_dir={args.output_dir}")
    print(f"profile={args.profile}")
    print(f"bit_mode={args.bit_mode}")
    print(f"target_mask={cfg['target_mask_min']:.2f}~{cfg['target_mask_max']:.2f}")
    print(f"payload_ratio={cfg['payload_ratio_min']:.2f}~{cfg['payload_ratio_max']:.2f}")
    print(f"edge_dilate={cfg['edge_dilate_min']}~{cfg['edge_dilate_max']}")
    print(
        "channel_probs="
        f"one:{cfg['channel_prob_one']:.2f}, "
        f"two:{cfg['channel_prob_two']:.2f}, "
        f"three:{cfg['channel_prob_three']:.2f}"
    )
    print(f"min_pixel_ratio={cfg['min_pixel_ratio']:.2f}")
    print("target_changed_lsb_ratio ~= 0.23~0.30 for fixed_high_plus")

    stats_path = Path(args.stats_csv) if args.stats_csv else output_dir / "_edge_adaptive_lsb_stats.csv"
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    sums = {
        "mask_ratio": 0.0,
        "selected_ratio": 0.0,
        "changed_pixel_ratio": 0.0,
        "changed_lsb_ratio": 0.0,
        "canny_ratio": 0.0,
    }
    done = 0
    failed = 0

    with open(stats_path, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "file",
            "profile",
            "target_mask_ratio",
            "payload_ratio",
            "mask_ratio",
            "selected_ratio",
            "changed_pixel_ratio",
            "changed_lsb_ratio",
            "canny_ratio",
            "dilate_iterations",
            "status",
            "error",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, path in enumerate(images, start=1):
            out = output_dir / f"{path.stem}.png"
            if args.skip_existing and out.exists():
                continue

            try:
                rgb = load_rgb(path, args.size)

                # Stable per-file seed. Rebuilding produces the same dataset unless --seed changes.
                stable_name_seed = int(hashlib.sha1(path.name.encode("utf-8", errors="ignore")).hexdigest()[:8], 16)
                file_seed = (stable_name_seed + int(args.seed)) % (2**32 - 1)

                stego, stat = embed_edge_adaptive_lsb(
                    rgb,
                    seed=file_seed,
                    cfg=cfg,
                    bit_mode=args.bit_mode,
                )
                save_rgb(stego, out)

                row = {
                    "file": path.name,
                    "profile": args.profile,
                    "target_mask_ratio": stat["target_mask_ratio"],
                    "payload_ratio": stat["payload_ratio"],
                    "mask_ratio": stat["mask_ratio"],
                    "selected_ratio": stat["selected_ratio"],
                    "changed_pixel_ratio": stat["changed_pixel_ratio"],
                    "changed_lsb_ratio": stat["changed_lsb_ratio"],
                    "canny_ratio": stat["canny_ratio"],
                    "dilate_iterations": stat["dilate_iterations"],
                    "status": "ok",
                    "error": "",
                }
                writer.writerow(row)

                for k in sums:
                    sums[k] += float(stat[k])
                done += 1

            except Exception as e:
                failed += 1
                writer.writerow({
                    "file": path.name,
                    "profile": args.profile,
                    "target_mask_ratio": "",
                    "payload_ratio": "",
                    "mask_ratio": "",
                    "selected_ratio": "",
                    "changed_pixel_ratio": "",
                    "changed_lsb_ratio": "",
                    "canny_ratio": "",
                    "dilate_iterations": "",
                    "status": "failed",
                    "error": repr(e),
                })

            if idx % 5000 == 0:
                denom = max(done, 1)
                print(
                    f"[progress] {idx}/{len(images)} "
                    f"ok={done} failed={failed} "
                    f"avg_mask={sums['mask_ratio']/denom:.4f} "
                    f"avg_selected={sums['selected_ratio']/denom:.4f} "
                    f"avg_changed_pixel={sums['changed_pixel_ratio']/denom:.4f} "
                    f"avg_changed_lsb={sums['changed_lsb_ratio']/denom:.4f}"
                )

    denom = max(done, 1)
    print("[done]")
    print(f"ok={done} failed={failed}")
    print(f"stats_csv={stats_path}")
    print(
        f"avg_mask={sums['mask_ratio']/denom:.4f} "
        f"avg_selected={sums['selected_ratio']/denom:.4f} "
        f"avg_changed_pixel={sums['changed_pixel_ratio']/denom:.4f} "
        f"avg_changed_lsb={sums['changed_lsb_ratio']/denom:.4f} "
        f"avg_canny={sums['canny_ratio']/denom:.4f}"
    )


if __name__ == "__main__":
    main()
