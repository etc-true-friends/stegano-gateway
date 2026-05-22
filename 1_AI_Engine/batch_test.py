"""This module is used to test the Srnet model in batches."""
from glob import glob
import torch
import numpy as np
from PIL import Image
import os

from model.model import Srnet

TEST_BATCH_SIZE = 40

# 새롭게 개편된 로컬 워크스페이스 구조로 경로 업데이트
COVER_PATH = "../4_Local_Workspace/dataset_finetune/train/cover/*.png"
STEGO_PATH = "../4_Local_Workspace/dataset_finetune/train/stego/*.png"
CHKPT = "../4_Local_Workspace/checkpoints/best_srnet_finetuned.pt"

def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[*] 대량 배치 테스트 구동 장치: {device}")

    cover_image_names = sorted(glob(COVER_PATH))
    stego_image_names = sorted(glob(STEGO_PATH))

    if not cover_image_names or not stego_image_names:
        print("[-] 테스트할 이미지를 찾을 수 없습니다. 경로를 확인해주세요.")
        return

    print(f"[*] Cover {len(cover_image_names)}장, Stego {len(stego_image_names)}장 로드 완료.")

    model = Srnet().to(device)

    # 껍데기 로드 방지용 안전한 가중치 추출 로직 적용
    checkpoint = torch.load(CHKPT, map_location=device, weights_only=False)
    state_dict = checkpoint['model_state_dict'] if 'model_state_dict' in checkpoint else checkpoint
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    print("[+] 파인튜닝 통합 가중치 로드 완료.\n")

    # [핵심 수정 1] RGB 3채널 규격으로 텐서 빈 공간 할당
    images = torch.empty((TEST_BATCH_SIZE, 3, 256, 256), dtype=torch.float)
    test_accuracy = []

    with torch.no_grad():
        for idx in range(0, len(cover_image_names), TEST_BATCH_SIZE // 2):
            cover_batch = cover_image_names[idx : idx + TEST_BATCH_SIZE // 2]
            stego_batch = stego_image_names[idx : idx + TEST_BATCH_SIZE // 2]

            # 배치 개수가 부족한 마지막 자투리 구간은 스킵하여 에러 방지
            if len(cover_batch) < TEST_BATCH_SIZE // 2 or len(stego_batch) < TEST_BATCH_SIZE // 2:
                break

            batch = []
            batch_labels = []

            xi = 0
            yi = 0
            for i in range(2 * len(cover_batch)):
                if i % 2 == 0:
                    batch.append(stego_batch[xi])
                    batch_labels.append(1)
                    xi += 1
                else:
                    batch.append(cover_batch[yi])
                    batch_labels.append(0)
                    yi += 1

            for i in range(TEST_BATCH_SIZE):
                # [핵심 수정 2] 추론 스크립트와 100% 동일한 PIL 기반 로딩 및 / 255.0 정규화
                with Image.open(batch[i]) as pil_img:
                    pil_img = pil_img.convert('RGB')
                    if pil_img.size != (256, 256):
                        pil_img = pil_img.resize((256, 256), Image.Resampling.BILINEAR)
                    img_array = np.array(pil_img)

                # (H, W, C) -> (C, H, W) 차원 변환 후 스케일링
                img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).float() / 255.0
                images[i] = img_tensor

            image_tensor = images.to(device)
            batch_labels_tensor = torch.tensor(batch_labels, dtype=torch.long).to(device)

            outputs = model(image_tensor)
            prediction = outputs.data.max(1)[1]

            accuracy = (prediction.eq(batch_labels_tensor.data).sum() * 100.0 / batch_labels_tensor.size()[0])
            test_accuracy.append(accuracy.item())
            
            print(f"    - 현재 배치 정확도 측정 중... [ {accuracy.item():.2f}% ]")

    if test_accuracy:
        final_acc = sum(test_accuracy) / len(test_accuracy)
        print(f"\n[+] 최종 대량 블라인드 테스트 평균 정확도 (Test Accuracy) = {final_acc:.2f}%")

if __name__ == "__main__":
    main()