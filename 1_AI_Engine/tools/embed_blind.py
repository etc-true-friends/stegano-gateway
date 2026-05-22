import numpy as np
from PIL import Image
import os

def embed_lsb_exact_match(cover_path, output_path, secret_text):
    if not os.path.exists(cover_path):
        return
        
    with Image.open(cover_path) as pil_img:
        pil_img = pil_img.convert('RGB')
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
    print(f"[+] 실전 학습용 LSB 주입 완료: {output_path}")

if __name__ == "__main__":
    IMG_DIR = r"D:\final_project\test_images"
    
    # 학습 데이터셋과 완전히 동일한 페이로드 사용
    PAYLOAD = "IndraNet /etc/friends Basic LSB Attack Payload Simulation " * 15
    
    embed_lsb_exact_match(os.path.join(IMG_DIR, "dog.png"), os.path.join(IMG_DIR, "stego_dog.png"), PAYLOAD)
    embed_lsb_exact_match(os.path.join(IMG_DIR, "quokka.png"), os.path.join(IMG_DIR, "stego_quokka.png"), PAYLOAD)