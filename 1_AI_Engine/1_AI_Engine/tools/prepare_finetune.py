import os
import shutil
import glob
import random

def create_mixed_dataset():
    # 1. 경로 설정
    BASE_DIR = r"D:\final_project"
    
    # 소스(Source) 경로
    SRC_COVER = os.path.join(BASE_DIR, r"dataset_real\train\cover")
    SRC_ADVANCED_STEGO = os.path.join(BASE_DIR, r"dataset_real\train\stego")
    SRC_SIMPLE_STEGO = os.path.join(BASE_DIR, r"dataset_simple_lsb\train\stego")
    
    # 타깃(Target) 경로 (파인튜닝 전용 독립 폴더)
    TARGET_COVER = os.path.join(BASE_DIR, r"dataset_finetune\train\cover")
    TARGET_STEGO = os.path.join(BASE_DIR, r"dataset_finetune\train\stego")
    
    # 폴더 생성
    os.makedirs(TARGET_COVER, exist_ok=True)
    os.makedirs(TARGET_STEGO, exist_ok=True)
    
    print("[*] 파인튜닝용 5:5 하이브리드 데이터셋 구축을 시작합니다...")

    # 2. 방금 만든 단순 LSB 파일 목록 가져오기
    simple_files = sorted(os.listdir(SRC_SIMPLE_STEGO))
    
    # 5000장 단순 LSB 세트 할당
    simple_selected = simple_files[:5000]
    
    # 나머지 파일 중 5000장 고도화(Advanced) 세트 할당
    advanced_candidates = simple_files[5000:10000] 
    
    success_count = 0
    
    # 3. 단순 LSB 데이터(5000장) 복사
    print("[*] 1/2: 단순 LSB 변조 데이터(5,000장) 및 쌍(Cover) 복사 중...")
    for f_name in simple_selected:
        # Cover 복사
        shutil.copy2(os.path.join(SRC_COVER, f_name), os.path.join(TARGET_COVER, f_name))
        # Simple Stego 복사
        shutil.copy2(os.path.join(SRC_SIMPLE_STEGO, f_name), os.path.join(TARGET_STEGO, f_name))
        success_count += 1
        
    # 4. 고도화된 변조 데이터(5000장) 복사
    print("[*] 2/2: 고도화된 변조 데이터(5,000장) 및 쌍(Cover) 복사 중...")
    for f_name in advanced_candidates:
        # Cover 복사
        shutil.copy2(os.path.join(SRC_COVER, f_name), os.path.join(TARGET_COVER, f_name))
        # Advanced Stego 복사
        shutil.copy2(os.path.join(SRC_ADVANCED_STEGO, f_name), os.path.join(TARGET_STEGO, f_name))
        success_count += 1

    print(f"\n[+] 작업 완료! 총 {success_count} 쌍의 하이브리드 데이터가 준비되었습니다.")
    print(f"[+] 저장 경로: {os.path.join(BASE_DIR, 'dataset_finetune')}")

if __name__ == "__main__":
    create_mixed_dataset()