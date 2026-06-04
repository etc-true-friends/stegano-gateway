import torch
import torch.nn.functional as F
import imageio.v2 as io
import os
import numpy as np
from PIL import Image

from model.model import Srnet 

def load_model(checkpoint_path):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = Srnet()
    
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"가중치 파일이 없습니다: {checkpoint_path}")
        
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    
    # [핵심 디버깅] 저장된 체크포인트의 실제 키(Key) 구조를 터미널에 강제 출력
    print("\n=========================================")
    print("[디버깅] 체크포인트 내부에 존재하는 실제 Key 목록:")
    print(list(checkpoint.keys()) if isinstance(checkpoint, dict) else "Dictionary 형태가 아님")
    print("=========================================\n")
    
    # 안전하게 모델 가중치 딕셔너리 추출
    if isinstance(checkpoint, dict):
        if 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        elif 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        else:
            state_dict = checkpoint
    else:
        state_dict = checkpoint

    # strict=True로 가중치 레이어 이름이 하나라도 안 맞으면 에러를 뿜도록 강제
    try:
        model.load_state_dict(state_dict, strict=True)
        print("[+] [검증 완료] 가중치 레이어가 모델 스펙과 100% 일치하게 로드되었습니다.\n")
    except Exception as e:
        print("[-] [오류 발생] 가중치 레이어 매칭 실패! 아래 에러를 확인하세요:")
        print(e)
        print("=========================================\n")
        raise e
    
    model.to(device)
    model.eval() 
    return model, device

def predict_image(model, device, image_path):
    if not os.path.exists(image_path):
        return {"error": f"이미지 파일을 찾을 수 없습니다: {image_path}"}

    try:
        with Image.open(image_path) as pil_img:
            pil_img = pil_img.convert('RGB')
            if pil_img.size != (256, 256):
                pil_img = pil_img.resize((256, 256), Image.Resampling.BILINEAR)
            img = np.array(pil_img)
        
        input_tensor = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0
        input_tensor = input_tensor.unsqueeze(0).to(device)
        
    except Exception as e:
        return {"error": f"이미지 전처리 중 에러 발생: {e}"}

    with torch.no_grad():
        output = model(input_tensor)
        probabilities = torch.exp(output).squeeze()
        predicted_class = torch.argmax(probabilities).item()
        confidence = probabilities[predicted_class].item() * 100

    labels = {0: "Cover (원본 정상 이미지)", 1: "Stego (은닉 페이로드 탐지됨)"}
    return {
        "result": labels[predicted_class],
        "confidence": f"{confidence:.2f}%",
        "raw_prob_cover": f"{probabilities[0].item():.4f}",
        "raw_prob_stego": f"{probabilities[1].item():.4f}"
    }

if __name__ == "__main__":
    CHECKPOINT_PATH = "./checkpoints/best_srnet_finetuned.pt"
    IMG_DIR = r"D:\final_project\test_images"
    
    COVER_DOG = os.path.join(IMG_DIR, "dog.png") 
    COVER_QUOKKA = os.path.join(IMG_DIR, "quokka.png")
    STEGO_DOG = os.path.join(IMG_DIR, "stego_dog.png")
    STEGO_QUOKKA = os.path.join(IMG_DIR, "stego_quokka.png")
    
    print("[*] 블라인드 크로스 테스트 엔진 가동 중...")
    model, device = load_model(CHECKPOINT_PATH)
    
    test_cases = [
        ("완전 외부 원본 강아지 (dog.png)", COVER_DOG),
        ("완전 외부 원본 쿼카 (quokka.png)", COVER_QUOKKA),
        ("완전 외부 변조 강아지 (stego_dog.png)", STEGO_DOG),
        ("완전 외부 변조 쿼카 (stego_quokka.png)", STEGO_QUOKKA),
    ]
    
    print("=== 탐지 결과 성적표 ===")
    for desc, path in test_cases:
        print(f"[*] 분석 대상: {desc}")
        result = predict_image(model, device, path)
        if "error" in result: 
            print(f" -> {result['error']}\n")
        else:
            print(f" -> 판정 결과: {result['result']} (확신도: {result['confidence']})")
            print(f"    [상세 확률] Cover: {result['raw_prob_cover']} / Stego: {result['raw_prob_stego']}\n")