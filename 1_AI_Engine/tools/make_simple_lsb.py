import argparse
import glob
import os

import numpy as np
from PIL import Image


def embed_lsb_batch(cover_path, output_path, secret_text):
    try:
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
        return True
    except Exception as e:
        print(f"[-] {cover_path} 처리 중 에러 발생: {e}")
        return False


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_cover_dir", default="../dataset/train/cover")
    parser.add_argument("--target_stego_dir", default="../dataset_simple_lsb/train/stego")
    parser.add_argument("--target_count", type=int, default=10000)
    parser.add_argument("--payload", default="IndraNet /etc/friends Basic LSB Attack Payload Simulation " * 15)
    parser.add_argument("--ext", default="png")
    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_args()
    os.makedirs(opt.target_stego_dir, exist_ok=True)

    cover_files = sorted(glob.glob(os.path.join(opt.source_cover_dir, f"*.{opt.ext}")))

    if len(cover_files) == 0:
        print("[-] 원본 Cover 이미지를 찾을 수 없습니다. 경로를 확인하세요.")
        raise SystemExit(1)

    print(f"[*] 총 {len(cover_files)}장의 Cover 이미지 중 {opt.target_count}장을 추출하여 LSB 주입을 시작합니다.")

    success_count = 0
    for file_path in cover_files:
        if success_count >= opt.target_count:
            break

        file_name = os.path.basename(file_path)
        output_path = os.path.join(opt.target_stego_dir, file_name)

        if embed_lsb_batch(file_path, output_path, opt.payload):
            success_count += 1

        if success_count > 0 and success_count % 1000 == 0:
            print(f"[*] 진행률: {success_count} / {opt.target_count} 장 변조 완료...")

    print(f"\n[+] 작업 완료! 총 {success_count}장의 단순 LSB 변조 이미지가 생성되었습니다.")
    print(f"[+] 저장 경로: {opt.target_stego_dir}")
