import os
from PIL import Image

def clean_corrupted_images():
    cover_dir = r"D:\final_project\dataset_finetune\train\cover"
    stego_dir = r"D:\final_project\dataset_finetune\train\stego"
    
    if not os.path.exists(cover_dir) or not os.path.exists(stego_dir):
        print("[-] 경로를 찾을 수 없습니다. 경로를 확인해주세요.")
        return

    files = os.listdir(cover_dir)
    bad_files = []
    
    print(f"[*] 총 {len(files)} 쌍의 이미지 무결성 검사를 시작합니다...")
    
    for f in files:
        cover_path = os.path.join(cover_dir, f)
        stego_path = os.path.join(stego_dir, f)
        
        # 1. 0바이트 껍데기 파일 검사
        if os.path.getsize(cover_path) == 0 or os.path.getsize(stego_path) == 0:
            bad_files.append(f)
            continue
            
        # 2. 헤더가 깨진 손상 파일 검사
        try:
            with Image.open(cover_path) as img:
                img.verify()
            with Image.open(stego_path) as img:
                img.verify()
        except Exception:
            bad_files.append(f)

    print(f"\n[*] 검사 완료! 발견된 손상 파일 쌍: {len(bad_files)}개")
    
    for f in bad_files:
        c_path = os.path.join(cover_dir, f)
        s_path = os.path.join(stego_dir, f)
        if os.path.exists(c_path): os.remove(c_path)
        if os.path.exists(s_path): os.remove(s_path)
        print(f"[-] 삭제 완료 (Cover & Stego 동시 제거): {f}")
        
    if len(bad_files) == 0:
        print("[+] 0바이트나 손상된 파일이 없습니다. 데이터셋이 깨끗합니다.")
    else:
        print(f"[+] 총 {len(bad_files)}쌍의 파일이 제거되었습니다. 이제 학습을 다시 시작하셔도 됩니다.")

if __name__ == "__main__":
    clean_corrupted_images()