"""
Image CDR sanitizer for the /etc/friends gateway.

The sanitizer intentionally reconstructs images instead of copying them.
This reduces the chance that metadata, ancillary chunks, or pixel-level
steganographic payloads survive delivery.
"""

import io
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


class CDRSanitizer:
    """
    Image reconstruction pipeline.

    Step 1: Strip metadata by copying only pixel data.
    Step 2: Remove alpha/palette channels.
    Step 3: Round-trip through YCrCb color space.
    Step 4: Normalize least-significant RGB bits.
    Step 5: Resize down and restore.
    Step 6: Re-encode as JPEG.
    """

    def __init__(self, jpeg_quality: int = 85, resize_ratio: float = 0.95, lsb_clear_bits: int = 2):
        self.jpeg_quality = jpeg_quality
        self.resize_ratio = resize_ratio
        self.lsb_clear_bits = max(0, min(int(lsb_clear_bits), 7))
        self.steps_log = []

    def step1_strip_metadata(self, img: Image.Image) -> Image.Image:
        """Copy decoded pixels into a fresh object to drop metadata/chunks safely."""
        if img.mode == "P":
            img = img.convert("RGBA")
        elif img.mode == "LA":
            img = img.convert("RGBA")
        elif img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        clean = img.copy()
        clean.load()
        self.steps_log.append("Step 1: metadata and ancillary data stripped")
        return clean

    def step2_remove_alpha(self, img: Image.Image) -> Image.Image:
        """Flatten alpha/palette modes into RGB."""
        if img.mode == "P":
            img = img.convert("RGBA")

        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            mask = img.split()[-1]
            background.paste(img.convert("RGB"), mask=mask)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        self.steps_log.append("Step 2: alpha and palette channels normalized")
        return img

    def step3_color_conversion(self, img: Image.Image) -> Image.Image:
        """Round-trip through YCrCb to disturb fragile pixel-level encodings."""
        arr = np.array(img)
        ycbcr = cv2.cvtColor(arr, cv2.COLOR_RGB2YCrCb)
        rgb_back = cv2.cvtColor(ycbcr, cv2.COLOR_YCrCb2RGB)
        self.steps_log.append("Step 3: RGB/YCrCb/RGB color conversion")
        return Image.fromarray(rgb_back)

    def step4_clear_lsb(self, img: Image.Image) -> Image.Image:
        """Clear the lowest RGB bits to directly damage LSB steganography payloads."""
        if self.lsb_clear_bits <= 0:
            self.steps_log.append("Step 4: LSB normalization skipped")
            return img

        arr = np.array(img.convert("RGB"), dtype=np.uint8)
        mask = 0xFF << self.lsb_clear_bits & 0xFF
        normalized = np.bitwise_and(arr, mask).astype(np.uint8)
        self.steps_log.append(f"Step 4: cleared lowest {self.lsb_clear_bits} RGB bit(s)")
        return Image.fromarray(normalized, mode="RGB")

    def step5_resize_restore(self, img: Image.Image) -> Image.Image:
        """Resample down and back up to break position-dependent payloads."""
        original_size = img.size
        small_size = (
            max(int(original_size[0] * self.resize_ratio), 1),
            max(int(original_size[1] * self.resize_ratio), 1),
        )
        small = img.resize(small_size, Image.LANCZOS)
        restored = small.resize(original_size, Image.LANCZOS)
        self.steps_log.append(f"Step 5: resize round-trip ({int(self.resize_ratio * 100)}% to 100%)")
        return restored

    def step6_jpeg_reencode(self, img: Image.Image) -> Image.Image:
        """Force lossy re-encoding to reconstruct the final delivered image."""
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=self.jpeg_quality, optimize=True)
        buffer.seek(0)
        reencoded = Image.open(buffer)
        reencoded.load()
        self.steps_log.append(f"Step 6: JPEG re-encode (quality={self.jpeg_quality})")
        return reencoded

    def sanitize(self, input_path: str, output_path: str) -> dict:
        """Run the full CDR chain and return metrics for audit/demo output."""
        self.steps_log = []

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        original = Image.open(input_path)
        original_mode = original.mode
        original_size = original.size

        img = self.step1_strip_metadata(original)
        img = self.step2_remove_alpha(img)
        img = self.step3_color_conversion(img)
        img = self.step4_clear_lsb(img)
        img = self.step5_resize_restore(img)
        img = self.step6_jpeg_reencode(img)

        output_path = str(Path(output_path).with_suffix(".jpg"))
        img.save(output_path, format="JPEG", quality=self.jpeg_quality)

        original_rgb_image = original.convert("RGB")
        with Image.open(output_path) as sanitized_file:
            sanitized_rgb_image = sanitized_file.convert("RGB")

        if original_rgb_image.size == sanitized_rgb_image.size:
            max_diff_side = 1024
            if max(original_rgb_image.size) > max_diff_side:
                ratio = max_diff_side / max(original_rgb_image.size)
                sample_size = (
                    max(int(original_rgb_image.size[0] * ratio), 1),
                    max(int(original_rgb_image.size[1] * ratio), 1),
                )
                original_rgb_image = original_rgb_image.resize(sample_size, Image.BILINEAR)
                sanitized_rgb_image = sanitized_rgb_image.resize(sample_size, Image.BILINEAR)

        original_rgb = np.array(original_rgb_image)
        sanitized_rgb = np.array(sanitized_rgb_image)
        if original_rgb.shape == sanitized_rgb.shape:
            pixel_diff = float(np.mean(np.abs(original_rgb.astype(int) - sanitized_rgb.astype(int))))
        else:
            pixel_diff = -1.0

        return {
            "status": "success",
            "input_path": input_path,
            "output_path": output_path,
            "original_mode": original_mode,
            "original_size": original_size,
            "original_kb": round(os.path.getsize(input_path) / 1024, 2),
            "sanitized_kb": round(os.path.getsize(output_path) / 1024, 2),
            "avg_pixel_diff": round(pixel_diff, 4),
            "lsb_clear_bits": self.lsb_clear_bits,
            "steps_executed": self.steps_log.copy(),
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python cdr_sanitizer.py <input_image_path>")
        sys.exit(1)

    sanitizer = CDRSanitizer(jpeg_quality=85, resize_ratio=0.95, lsb_clear_bits=2)
    result = sanitizer.sanitize(sys.argv[1], "sanitized_output.jpg")

    print("\nCDR sanitization complete")
    for step in result["steps_executed"]:
        print(f" - {step}")
    print(f"Input:  {result['original_kb']} KB")
    print(f"Output: {result['sanitized_kb']} KB -> {result['output_path']}")
    print(f"Average pixel diff: {result['avg_pixel_diff']}")
