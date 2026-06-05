import argparse
import os

import numpy as np
from PIL import Image


def embed_lsb_exact_match(cover_path, output_path, secret_text):
    if not os.path.exists(cover_path):
        print(f"[-] 원본 이미지를 찾을 수 없습니다: {cover_path}")
        return False

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with Image.open(cover_path) as pil_img:
        pil_img = pil_img.convert("RGB")
        if pil_img.size != (256, 256):
            pil_img = pil_img.resize((256, 256), Image.Resampling.BILINEAR)
        img_array = np.array(pil_img)

    secret_data = secret_text + " [END]"
    binary_secret = "".join(format(ord(char), "08b") for char in secret_data)

    flat_array = img_array.flatten()
    if len(binary_secret) > len(flat_array):
        raise ValueError("페이로드가 이미지 용량보다 큽니다.")

    for i, bit in enumerate(binary_secret):
        flat_array[i] = (flat_array[i] & 0xFE) | int(bit)

    stego_array = flat_array.reshape(img_array.shape)
    stego_img = Image.fromarray(stego_array.astype(np.uint8))
    stego_img.save(output_path, format="PNG")
    print(f"[+] 실전 학습용 LSB 주입 완료: {output_path}")
    return True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--img_dir", default="../test_images")
    parser.add_argument("--images", nargs="*", default=["dog.png", "quokka.png"])
    parser.add_argument("--payload", default="IndraNet /etc/friends Basic LSB Attack Payload Simulation " * 15)
    parser.add_argument("--prefix", default="stego_")
    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_args()
    for image_name in opt.images:
        input_path = os.path.join(opt.img_dir, image_name)
        output_path = os.path.join(opt.img_dir, opt.prefix + image_name)
        embed_lsb_exact_match(input_path, output_path, opt.payload)
