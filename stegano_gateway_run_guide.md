# Stegano Gateway 실행 가이드

이 문서는 개인 PC 경로 없이 프로젝트 루트 기준 상대경로로 정리한 실행 가이드입니다.  
학습 데이터, 생성 데이터, 체크포인트, 테스트 이미지는 모두 `4_Local_Workspace` 아래에 둡니다.

---

## 1. 프로젝트 구조

```text
stegano-gateway-main/
├─ 1_AI_Engine/
│  ├─ train.py
│  ├─ finetune.py
│  ├─ inference_test.py
│  ├─ batch_test.py
│  └─ tools/
├─ 2_API_Gateway/
├─ 3_Web_Dashboard/
├─ scripts/
│  ├─ build_cover_256.py
│  ├─ build_dct_mid_stego.py
│  └─ build_dwt_haar_stego.py
├─ 4_Local_Workspace/
│  ├─ checkpoints/
│  ├─ datasets/
│  ├─ raw_images/
│  ├─ uploads/
│  ├─ sanitized/
│  ├─ quarantine/
│  └─ test_images/
├─ requirements.txt
└─ docker-compose.yml
```

---

## 2. 처음 설치

프로젝트 루트에서 실행합니다.

```bat
python -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

GPU 인식 확인:

```bat
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

GPU가 `False`로 나오면 CUDA용 PyTorch를 다시 설치합니다.

```bat
pip install --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

다시 확인:

```bat
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

---

## 3. 작업 폴더 생성

프로젝트 루트에서 실행합니다.

```bat
mkdir 4_Local_Workspace
mkdir 4_Local_Workspace\checkpoints
mkdir 4_Local_Workspace\datasets
mkdir 4_Local_Workspace\raw_images
mkdir 4_Local_Workspace\uploads
mkdir 4_Local_Workspace\sanitized
mkdir 4_Local_Workspace\quarantine
mkdir 4_Local_Workspace\test_images
```

DCT/DWT 학습용 폴더까지 한 번에 만들려면 아래를 실행합니다.

```bat
mkdir 4_Local_Workspace\raw_images\train
mkdir 4_Local_Workspace\raw_images\val

mkdir 4_Local_Workspace\datasets\dct_mid\train\cover
mkdir 4_Local_Workspace\datasets\dct_mid\train\stego
mkdir 4_Local_Workspace\datasets\dct_mid\val\cover
mkdir 4_Local_Workspace\datasets\dct_mid\val\stego

mkdir 4_Local_Workspace\datasets\dwt_haar\train\cover
mkdir 4_Local_Workspace\datasets\dwt_haar\train\stego
mkdir 4_Local_Workspace\datasets\dwt_haar\val\cover
mkdir 4_Local_Workspace\datasets\dwt_haar\val\stego

mkdir 4_Local_Workspace\checkpoints\dct_mid
mkdir 4_Local_Workspace\checkpoints\dwt_haar
```

---

## 4. 원본 이미지 배치

원본 이미지는 `4_Local_Workspace\raw_images` 아래에 넣습니다.

```text
4_Local_Workspace/
└─ raw_images/
   ├─ train/
   │  ├─ 001.png
   │  ├─ 002.png
   │  └─ ...
   └─ val/
      ├─ 1001.png
      ├─ 1002.png
      └─ ...
```

`train`은 학습용, `val`은 검증용입니다. 같은 원본 이미지를 train과 val에 중복으로 넣지 않습니다.

---

## 5. 스크립트 추가 위치

DCT/DWT 이미지 생성 스크립트는 프로젝트 루트의 `scripts` 폴더에 넣습니다.

```text
scripts/
├─ build_cover_256.py
├─ build_dct_mid_stego.py
└─ build_dwt_haar_stego.py
```

스크립트 역할:

```text
build_cover_256.py       원본 이미지를 256x256 cover 이미지로 변환
build_dct_mid_stego.py   DCT 중간주파수 조작 stego 이미지 생성
build_dwt_haar_stego.py  DWT Haar 변환 기반 stego 이미지 생성
```

---

## 6. DCT 중간주파수 데이터셋 생성

프로젝트 루트에서 실행합니다.

### DCT train cover 생성

```bat
python scripts\build_cover_256.py ^
  --input_dir ".\4_Local_Workspace\raw_images\train" ^
  --output_dir ".\4_Local_Workspace\datasets\dct_mid\train\cover" ^
  --size 256
```

### DCT train stego 생성

```bat
python scripts\build_dct_mid_stego.py ^
  --input_dir ".\4_Local_Workspace\raw_images\train" ^
  --output_dir ".\4_Local_Workspace\datasets\dct_mid\train\stego" ^
  --size 256 ^
  --strength 8
```

### DCT val cover 생성

```bat
python scripts\build_cover_256.py ^
  --input_dir ".\4_Local_Workspace\raw_images\val" ^
  --output_dir ".\4_Local_Workspace\datasets\dct_mid\val\cover" ^
  --size 256
```

### DCT val stego 생성

```bat
python scripts\build_dct_mid_stego.py ^
  --input_dir ".\4_Local_Workspace\raw_images\val" ^
  --output_dir ".\4_Local_Workspace\datasets\dct_mid\val\stego" ^
  --size 256 ^
  --strength 8
```

---

## 7. DWT Haar 데이터셋 생성

프로젝트 루트에서 실행합니다.

### DWT train cover 생성

```bat
python scripts\build_cover_256.py ^
  --input_dir ".\4_Local_Workspace\raw_images\train" ^
  --output_dir ".\4_Local_Workspace\datasets\dwt_haar\train\cover" ^
  --size 256
```

### DWT train stego 생성

```bat
python scripts\build_dwt_haar_stego.py ^
  --input_dir ".\4_Local_Workspace\raw_images\train" ^
  --output_dir ".\4_Local_Workspace\datasets\dwt_haar\train\stego" ^
  --size 256 ^
  --strength 3 ^
  --bands "LH,HL"
```

### DWT val cover 생성

```bat
python scripts\build_cover_256.py ^
  --input_dir ".\4_Local_Workspace\raw_images\val" ^
  --output_dir ".\4_Local_Workspace\datasets\dwt_haar\val\cover" ^
  --size 256
```

### DWT val stego 생성

```bat
python scripts\build_dwt_haar_stego.py ^
  --input_dir ".\4_Local_Workspace\raw_images\val" ^
  --output_dir ".\4_Local_Workspace\datasets\dwt_haar\val\stego" ^
  --size 256 ^
  --strength 3 ^
  --bands "LH,HL"
```

---

## 8. DCT 중간주파수 모델 학습

`1_AI_Engine` 폴더로 이동 후 실행합니다.

```bat
cd 1_AI_Engine

python train.py ^
  --cover_path "..\4_Local_Workspace\datasets\dct_mid\train\cover" ^
  --stego_path "..\4_Local_Workspace\datasets\dct_mid\train\stego" ^
  --valid_cover_path "..\4_Local_Workspace\datasets\dct_mid\val\cover" ^
  --valid_stego_path "..\4_Local_Workspace\datasets\dct_mid\val\stego" ^
  --checkpoints_dir "..\4_Local_Workspace\checkpoints\dct_mid" ^
  --batch_size 4 ^
  --num_epochs 10 ^
  --train_size 3345 ^
  --val_size 715
```

체크포인트 저장 위치:

```text
4_Local_Workspace/checkpoints/dct_mid/
├─ net_1.pt
├─ net_2.pt
└─ best_srnet_model.pt
```

---

## 9. DWT Haar 모델 학습

`1_AI_Engine` 폴더에서 실행합니다.

```bat
python train.py ^
  --cover_path "..\4_Local_Workspace\datasets\dwt_haar\train\cover" ^
  --stego_path "..\4_Local_Workspace\datasets\dwt_haar\train\stego" ^
  --valid_cover_path "..\4_Local_Workspace\datasets\dwt_haar\val\cover" ^
  --valid_stego_path "..\4_Local_Workspace\datasets\dwt_haar\val\stego" ^
  --checkpoints_dir "..\4_Local_Workspace\checkpoints\dwt_haar" ^
  --batch_size 4 ^
  --num_epochs 10 ^
  --train_size 3345 ^
  --val_size 715
```

체크포인트 저장 위치:

```text
4_Local_Workspace/checkpoints/dwt_haar/
├─ net_1.pt
├─ net_2.pt
└─ best_srnet_model.pt
```

---

## 10. 이어학습

같은 명령어에서 `--num_epochs`만 늘리면 마지막 `net_숫자.pt`부터 이어서 학습합니다.

예를 들어 DCT 모델을 10 epoch까지 학습한 뒤 20 epoch까지 이어서 학습하려면:

```bat
python train.py ^
  --cover_path "..\4_Local_Workspace\datasets\dct_mid\train\cover" ^
  --stego_path "..\4_Local_Workspace\datasets\dct_mid\train\stego" ^
  --valid_cover_path "..\4_Local_Workspace\datasets\dct_mid\val\cover" ^
  --valid_stego_path "..\4_Local_Workspace\datasets\dct_mid\val\stego" ^
  --checkpoints_dir "..\4_Local_Workspace\checkpoints\dct_mid" ^
  --batch_size 4 ^
  --num_epochs 20 ^
  --train_size 3345 ^
  --val_size 715
```

---

## 11. 처음부터 다시 학습

DCT 체크포인트 삭제:

```bat
del ..\4_Local_Workspace\checkpoints\dct_mid\net_*.pt
del ..\4_Local_Workspace\checkpoints\dct_mid\best_srnet_model.pt
```

DWT 체크포인트 삭제:

```bat
del ..\4_Local_Workspace\checkpoints\dwt_haar\net_*.pt
del ..\4_Local_Workspace\checkpoints\dwt_haar\best_srnet_model.pt
```

그 다음 학습 명령어를 다시 실행합니다.

---

## 12. 파인튜닝 실행

파인튜닝 데이터도 `4_Local_Workspace` 아래에 둡니다.

```text
4_Local_Workspace/
└─ datasets/
   └─ finetune/
      └─ train/
         ├─ cover/
         └─ stego/
```

실행 위치는 `1_AI_Engine`입니다.

```bat
python finetune.py ^
  --cover_path "..\4_Local_Workspace\datasets\finetune\train\cover" ^
  --stego_path "..\4_Local_Workspace\datasets\finetune\train\stego" ^
  --checkpoint_path "..\4_Local_Workspace\checkpoints\dct_mid\best_srnet_model.pt" ^
  --save_path "..\4_Local_Workspace\checkpoints\dct_mid\best_srnet_finetuned.pt" ^
  --size 10000 ^
  --batch_size 16 ^
  --epochs 3
```

DWT 모델을 파인튜닝하려면 checkpoint 경로만 `dwt_haar`로 바꿉니다.

```bat
python finetune.py ^
  --cover_path "..\4_Local_Workspace\datasets\finetune\train\cover" ^
  --stego_path "..\4_Local_Workspace\datasets\finetune\train\stego" ^
  --checkpoint_path "..\4_Local_Workspace\checkpoints\dwt_haar\best_srnet_model.pt" ^
  --save_path "..\4_Local_Workspace\checkpoints\dwt_haar\best_srnet_finetuned.pt" ^
  --size 10000 ^
  --batch_size 16 ^
  --epochs 3
```

---

## 13. 테스트 이미지 배치

테스트 이미지는 아래에 둡니다.

```text
4_Local_Workspace/test_images/
```

예:

```text
4_Local_Workspace/test_images/sample.png
4_Local_Workspace/test_images/stego_sample.png
```

---

## 14. 단일/소량 이미지 테스트

`1_AI_Engine` 폴더에서 실행합니다.

DCT 모델 테스트:

```bat
python inference_test.py ^
  --checkpoint_path "..\4_Local_Workspace\checkpoints\dct_mid\best_srnet_model.pt" ^
  --img_dir "..\4_Local_Workspace\test_images" ^
  --images "sample.png" "stego_sample.png"
```

DWT 모델 테스트:

```bat
python inference_test.py ^
  --checkpoint_path "..\4_Local_Workspace\checkpoints\dwt_haar\best_srnet_model.pt" ^
  --img_dir "..\4_Local_Workspace\test_images" ^
  --images "sample.png" "stego_sample.png"
```

---

## 15. 배치 테스트

DCT 검증 데이터셋 테스트:

```bat
python batch_test.py ^
  --checkpoint_path "..\4_Local_Workspace\checkpoints\dct_mid\best_srnet_model.pt" ^
  --cover_glob "..\4_Local_Workspace\datasets\dct_mid\val\cover\*.png" ^
  --stego_glob "..\4_Local_Workspace\datasets\dct_mid\val\stego\*.png" ^
  --batch_size 40
```

DWT 검증 데이터셋 테스트:

```bat
python batch_test.py ^
  --checkpoint_path "..\4_Local_Workspace\checkpoints\dwt_haar\best_srnet_model.pt" ^
  --cover_glob "..\4_Local_Workspace\datasets\dwt_haar\val\cover\*.png" ^
  --stego_glob "..\4_Local_Workspace\datasets\dwt_haar\val\stego\*.png" ^
  --batch_size 40
```

---

## 16. API Gateway 실행

새 CMD에서 프로젝트 루트로 이동 후 실행합니다.

```bat
.venv\Scripts\activate
cd 2_API_Gateway

uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

확인 주소:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/health
http://127.0.0.1:8000/stats
http://127.0.0.1:8000/audit
```

---

## 17. Web Dashboard 실행

새 CMD에서 프로젝트 루트로 이동 후 실행합니다.

```bat
.venv\Scripts\activate
cd 3_Web_Dashboard

set API_BASE=http://127.0.0.1:8000
streamlit run dashboard.py
```

접속 주소:

```text
http://127.0.0.1:8501
```

---

## 18. demo.py 실행

API 서버가 먼저 켜져 있어야 합니다.

```bat
.venv\Scripts\activate
cd 3_Web_Dashboard

python demo.py
```

데모 이미지는 아래 위치에 둡니다.

```text
4_Local_Workspace/test_images/
```

---

## 19. Docker로 전체 실행

Docker Desktop을 켠 뒤 프로젝트 루트에서 실행합니다.

```bat
docker compose up --build
```

접속 주소:

```text
API 서버: http://127.0.0.1:8000
Web Dashboard: http://127.0.0.1:8501
mitmproxy 프록시: 127.0.0.1:8080
mitmweb 관리창: http://127.0.0.1:9091
```

중지:

```bat
docker compose down
```

로그 확인:

```bat
docker compose logs -f
```

---

## 20. 주의사항

- `train`과 `val`에는 같은 원본 이미지가 중복되면 안 됩니다.
- DCT 모델에는 DCT stego 이미지만 넣습니다.
- DWT 모델에는 DWT Haar stego 이미지만 넣습니다.
- DWT 폴더에 DCT stego를 넣으면 DWT 탐지기가 아니라 DCT 흔적을 배우게 됩니다.
- DCT/DWT 흔적은 resize와 재압축에 약할 수 있으므로, cover와 stego 생성 후 다시 크기를 바꾸지 않습니다.
- 실제 사용할 모델은 보통 `best_srnet_model.pt`를 사용합니다.
---

## 기존 체크포인트 번호를 직접 지정해서 이어학습

기본 방식은 `checkpoints` 폴더에서 가장 큰 `net_숫자.pt`를 자동으로 찾아 이어학습한다.

특정 체크포인트 번호를 직접 지정하려면 `train.py`와 `opts/options.py`에 `--resume_epoch` 옵션이 추가되어 있어야 한다.

### 코드 수정

`1_AI_Engine/opts/options.py`에 아래 옵션을 추가한다.

```python
parser.add_argument("--resume_epoch", type=int, default=None)
```

`1_AI_Engine/train.py`에서 체크포인트를 찾는 부분을 아래처럼 바꾼다.

```python
check_point = opt.resume_epoch if opt.resume_epoch is not None else latest_checkpoint(opt.checkpoints_dir)
```

### DCT 중간주파수 모델 이어학습

예를 들어 `net_7.pt`부터 이어서 학습하려면 아래처럼 실행한다.

```bat
cd 1_AI_Engine

python train.py ^
  --cover_path "..\4_Local_Workspace\datasets\dct_mid\train\cover" ^
  --stego_path "..\4_Local_Workspace\datasets\dct_mid\train\stego" ^
  --valid_cover_path "..\4_Local_Workspace\datasets\dct_mid\val\cover" ^
  --valid_stego_path "..\4_Local_Workspace\datasets\dct_mid\val\stego" ^
  --checkpoints_dir "..\4_Local_Workspace\checkpoints\dct_mid" ^
  --resume_epoch 7 ^
  --batch_size 4 ^
  --num_epochs 20 ^
  --train_size 3345 ^
  --val_size 715
```

위 명령어는 아래 파일을 불러온다.

```text
4_Local_Workspace/checkpoints/dct_mid/net_7.pt
```

그리고 `8 epoch`부터 `20 epoch`까지 이어서 학습한다.

### DWT Haar 모델 이어학습

```bat
cd 1_AI_Engine

python train.py ^
  --cover_path "..\4_Local_Workspace\datasets\dwt_haar\train\cover" ^
  --stego_path "..\4_Local_Workspace\datasets\dwt_haar\train\stego" ^
  --valid_cover_path "..\4_Local_Workspace\datasets\dwt_haar\val\cover" ^
  --valid_stego_path "..\4_Local_Workspace\datasets\dwt_haar\val\stego" ^
  --checkpoints_dir "..\4_Local_Workspace\checkpoints\dwt_haar" ^
  --resume_epoch 7 ^
  --batch_size 4 ^
  --num_epochs 20 ^
  --train_size 3345 ^
  --val_size 715
```

### 주의사항

`--resume_epoch 7`을 쓰려면 해당 파일이 실제로 있어야 한다.

```text
4_Local_Workspace/checkpoints/dct_mid/net_7.pt
4_Local_Workspace/checkpoints/dwt_haar/net_7.pt
```

`--num_epochs`는 추가 학습 횟수가 아니라 총 epoch 수다.

예를 들어 `net_7.pt`에서 `--num_epochs 20`을 주면 `8 epoch`부터 `20 epoch`까지 학습한다.

