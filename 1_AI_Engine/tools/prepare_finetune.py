import argparse
import os
import shutil


def create_mixed_dataset(src_cover, src_advanced_stego, src_simple_stego, target_cover, target_stego, simple_count, advanced_count):
    for path in [src_cover, src_advanced_stego, src_simple_stego]:
        if not os.path.isdir(path):
            print(f"[-] 입력 폴더를 찾을 수 없습니다: {path}")
            return

    os.makedirs(target_cover, exist_ok=True)
    os.makedirs(target_stego, exist_ok=True)

    print("[*] 파인튜닝용 하이브리드 데이터셋 구축을 시작합니다...")

    valid_extensions = (".png", ".jpg", ".jpeg", ".pgm")
    cover_files = {f for f in os.listdir(src_cover) if f.lower().endswith(valid_extensions)}
    simple_files = {f for f in os.listdir(src_simple_stego) if f.lower().endswith(valid_extensions)}
    advanced_files = {f for f in os.listdir(src_advanced_stego) if f.lower().endswith(valid_extensions)}

    simple_candidates = sorted(cover_files.intersection(simple_files))
    advanced_candidates_all = sorted(cover_files.intersection(advanced_files))

    simple_selected = simple_candidates[:simple_count]
    advanced_candidates = [f for f in advanced_candidates_all if f not in set(simple_selected)][:advanced_count]

    success_count = 0

    print(f"[*] 1/2: 단순 LSB 변조 데이터({len(simple_selected)}장) 및 쌍(Cover) 복사 중...")
    for f_name in simple_selected:
        cover_path = os.path.join(src_cover, f_name)
        stego_path = os.path.join(src_simple_stego, f_name)
        if not os.path.exists(cover_path) or not os.path.exists(stego_path):
            continue
        shutil.copy2(cover_path, os.path.join(target_cover, f_name))
        shutil.copy2(stego_path, os.path.join(target_stego, f_name))
        success_count += 1

    print(f"[*] 2/2: 고도화된 변조 데이터({len(advanced_candidates)}장) 및 쌍(Cover) 복사 중...")
    for f_name in advanced_candidates:
        cover_path = os.path.join(src_cover, f_name)
        stego_path = os.path.join(src_advanced_stego, f_name)
        if not os.path.exists(cover_path) or not os.path.exists(stego_path):
            continue
        shutil.copy2(cover_path, os.path.join(target_cover, f_name))
        shutil.copy2(stego_path, os.path.join(target_stego, f_name))
        success_count += 1

    print(f"\n[+] 작업 완료! 총 {success_count} 쌍의 하이브리드 데이터가 준비되었습니다.")
    print(f"[+] 저장 경로: {os.path.dirname(os.path.dirname(target_cover))}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src_cover", default="../dataset/train/cover")
    parser.add_argument("--src_advanced_stego", default="../dataset/train/stego")
    parser.add_argument("--src_simple_stego", default="../dataset_simple_lsb/train/stego")
    parser.add_argument("--target_cover", default="../dataset_finetune/train/cover")
    parser.add_argument("--target_stego", default="../dataset_finetune/train/stego")
    parser.add_argument("--simple_count", type=int, default=5000)
    parser.add_argument("--advanced_count", type=int, default=5000)
    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_args()
    create_mixed_dataset(
        opt.src_cover,
        opt.src_advanced_stego,
        opt.src_simple_stego,
        opt.target_cover,
        opt.target_stego,
        opt.simple_count,
        opt.advanced_count,
    )
