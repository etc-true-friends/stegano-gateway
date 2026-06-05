import argparse
import os

import numpy as np
import torch
from PIL import Image

from model.model import Srnet


def load_model(checkpoint_path):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = Srnet()

    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"가중치 파일이 없습니다: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)

    if isinstance(checkpoint, dict):
        if "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
        elif "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        else:
            state_dict = checkpoint
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict, strict=True)
    model.to(device)
    model.eval()
    return model, device


def predict_image(model, device, image_path):
    if not os.path.exists(image_path):
        return {"error": f"이미지 파일을 찾을 수 없습니다: {image_path}"}

    try:
        with Image.open(image_path) as pil_img:
            pil_img = pil_img.convert("RGB")
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
        "raw_prob_stego": f"{probabilities[1].item():.4f}",
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint_path", default="../4_Local_Workspace/checkpoints/best_srnet_finetuned.pt")
    parser.add_argument("--img_dir", default="./test_images")
    parser.add_argument("--images", nargs="*", default=["dog.png", "quokka.png", "stego_dog.png", "stego_quokka.png"])
    return parser.parse_args()


if __name__ == "__main__":
    opt = parse_args()

    print("[*] 블라인드 크로스 테스트 엔진 가동 중...")
    model, device = load_model(opt.checkpoint_path)

    print("=== 탐지 결과 성적표 ===")
    for image_name in opt.images:
        path = os.path.join(opt.img_dir, image_name)
        print(f"[*] 분석 대상: {image_name}")
        result = predict_image(model, device, path)
        if "error" in result:
            print(f" -> {result['error']}\n")
        else:
            print(f" -> 판정 결과: {result['result']} (확신도: {result['confidence']})")
            print(f"    [상세 확률] Cover: {result['raw_prob_cover']} / Stego: {result['raw_prob_stego']}\n")
