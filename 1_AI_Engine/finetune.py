import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import os

from dataset.dataset import DatasetLoad
from model.model import Srnet

def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"[*] 파인튜닝 구동 장치: {device}")

    # 1. 경로 설정 (방금 만든 하이브리드 데이터셋)
    BASE_DIR = r"D:\final_project\dataset_finetune\train"
    COVER_DIR = os.path.join(BASE_DIR, "cover")
    STEGO_DIR = os.path.join(BASE_DIR, "stego")
    
    CHECKPOINT_PATH = "./checkpoints/best_srnet_model.pt"
    SAVE_PATH = "./checkpoints/best_srnet_finetuned.pt"

    # 2. 데이터로더 설정
    print("[*] 데이터셋 로드 중...")
    dataset = DatasetLoad(COVER_DIR, STEGO_DIR, size=10000, transform=None)
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True, num_workers=4)
    print(f"[+] 총 {len(dataset)} 쌍의 이미지 세트 준비 완료.")

    # 3. 모델 초기화 및 기존 가중치(18만장 학습본) 로드
    model = Srnet().to(device)
    if not os.path.exists(CHECKPOINT_PATH):
        print(f"[-] 가중치 파일을 찾을 수 없습니다: {CHECKPOINT_PATH}")
        return

    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=False)
    state_dict = checkpoint['model_state_dict'] if 'model_state_dict' in checkpoint else checkpoint
    model.load_state_dict(state_dict, strict=True)
    print("[+] 기존 18만장 학습 베스트 가중치 로드 완료. (파국적 망각 방지)")

    # 4. 옵티마이저 및 손실 함수
    criterion = nn.CrossEntropyLoss()
    # 핵심: 기존 지식을 잊지 않도록 학습률(Learning Rate)을 아주 작게 설정 (1e-4)
    optimizer = optim.Adamax(model.parameters(), lr=0.0001, weight_decay=1e-4)

    # 5. 파인튜닝 루프
    EPOCHS = 3
    print("\n[*] 본격적인 파인튜닝을 시작합니다. (목표: 3 Epochs)")
    
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for i, data in enumerate(dataloader):
            cover = data['cover'].to(device)
            stego = data['stego'].to(device)
            
            # 배치 사이즈에 맞게 정답 레이블(Cover=0, Stego=1) 생성
            B = cover.size(0)
            labels_cover = torch.zeros(B, dtype=torch.long).to(device)
            labels_stego = torch.ones(B, dtype=torch.long).to(device)
            
            # Cover와 Stego를 하나의 배치로 병합 연산 (효율성 극대화)
            inputs = torch.cat([cover, stego], dim=0)
            labels = torch.cat([labels_cover, labels_stego], dim=0)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

            if (i + 1) % 50 == 0:
                print(f"    - Epoch [{epoch+1}/{EPOCHS}], Step [{i+1}/{len(dataloader)}], Loss: {loss.item():.4f}")
        
        epoch_acc = 100 * correct / total
        print(f"[+] Epoch {epoch+1} 완료 | 평균 Loss: {running_loss/len(dataloader):.4f} | Accuracy: {epoch_acc:.2f}%\n")

    # 6. 파인튜닝 완료 가중치 독립 저장
    torch.save({'model_state_dict': model.state_dict()}, SAVE_PATH)
    print(f"[+] 파인튜닝 완료! 새로운 통합 가중치가 안전하게 저장되었습니다: {SAVE_PATH}")

if __name__ == "__main__":
    main()