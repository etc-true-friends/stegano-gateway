import numpy as np
from PIL import Image
import os
import glob

def embed_lsb_batch(cover_path, output_path, secret_text):
    """단일 이미지에 LSB를 주입하고 고정 규격으로 저장하는 함수"""
    try:
        with Image.open(cover_path) as pil_img:
            pil_img = pil_img.convert('RGB')
            # 규격 강제 고정 (안전장치)
            if pil_img.size != (256, 256):
                pil_img = pil_img.resize((256, 256), Image.Resampling.BILINEAR)
            img_array = np.array(pil_img)
        
        secret_data = secret_text + " [END]"
        binary_secret = ''.join(format(ord(char), '08b') for char in secret_data)
        data_len = len(binary_secret)
        
        flat_array = img_array.flatten()
        for i in range(data_len):
            flat_array[i] = (flat_array[i] & 0xFE) | int(binary_secret[i])
            
        stego_array = flat_array.reshape(img_array.shape)
        stego_img = Image.fromarray(stego_array.astype(np.uint8))
        stego_img.save(output_path, format="PNG")
        return True
    except Exception as e:
        print(f"[-] {cover_path} 처리 중 에러 발생: {e}")
        return False

if __name__ == "__main__":
    # 1. 경로 설정 (환경에 맞게 폴더가 존재하는지 확인)
    SOURCE_COVER_DIR = r"D:\final_project\dataset_real\train\cover"
    TARGET_STEGO_DIR = r"D:\final_project\dataset_simple_lsb\train\stego"
    
    # 목표 생성 수량 (전체 데이터의 약 5~10% 수준인 1만 장)
    TARGET_COUNT = 10000 
    PAYLOAD = "IndraNet /etc/friends Basic LSB Attack Payload Simulation " * 15

    if not os.path.exists(TARGET_STEGO_DIR):
        os.makedirs(TARGET_STEGO_DIR)

    # 2. 원본(Cover) 파일 목록 수집
    cover_files = sorted(glob.glob(os.path.join(SOURCE_COVER_DIR, "*.png")))
    
    if len(cover_files) == 0:
        print("[-] 원본 Cover 이미지를 찾을 수 없습니다. 경로를 확인하세요.")
        exit(1)
        
    print(f"[*] 총 {len(cover_files)}장의 Cover 이미지 중 {TARGET_COUNT}장을 추출하여 LSB 주입을 시작합니다.")

    # 3. 변조 이미지 생성 루프
    success_count = 0
    for i, file_path in enumerate(cover_files):
        if success_count >= TARGET_COUNT:
            break
            
        file_name = os.path.basename(file_path)
        output_path = os.path.join(TARGET_STEGO_DIR, file_name)
        
        if embed_lsb_batch(file_path, output_path, PAYLOAD):
            success_count += 1
            
        # 진행 상황 모니터링 (1000장 단위 출력)
        if success_count % 1000 == 0:
            print(f"[*] 진행률: {success_count} / {TARGET_COUNT} 장 변조 완료...")

    print(f"\n[+] 작업 완료! 총 {success_count}장의 단순 LSB 변조 이미지가 생성되었습니다.")
    print(f"[+] 저장 경로: {TARGET_STEGO_DIR}")