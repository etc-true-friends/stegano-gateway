# 🛡️ 스테가노그래피 이상 징후 탐지 및 CDR 무해화 시스템

> **AI 기반 이미지 무해화 망연계 게이트웨이**  
> 구름 정보보호 부트캠프 17기 파이널 프로젝트

---

## 📌 프로젝트 개요

스테가노그래피(Steganography)는 이미지 파일의 픽셀 최하위 비트(LSB)에 기밀 데이터를 은닉하는 기법으로, 육안으로는 정상 이미지와 구별이 불가능합니다.

본 시스템은 **3단계 파이프라인**으로 이를 탐지하고 무해화합니다:

```
[업로드] → [AI 탐지] → [CDR 무해화] → [격리/감사로그]
```

### 핵심 컨셉: Zero Trust
> "AI가 놓쳐도 CDR이 반드시 파괴한다"

탐지율에 의존하지 않고, 모든 파일을 무조건 무해화하여 100% 차단을 보장합니다.

---

## 🏗️ 시스템 아키텍처

```
[내부망]          [게이트웨이]                    [외부망]
직원 PC  ──────▶  ① 정책 엔진 (확장자/크기)
                  ② AI 탐지 (EfficientNet-B0)  ──▶ 무해화된 파일
                  ③ CDR 무해화 (5단계 체인)
                  ④ 격리 + 감사 로그
```

---

## 🔧 기술 스택

| 분류 | 기술 |
|------|------|
| AI 탐지 | EfficientNet-B0 (ImageNet 전이학습) |
| 통계 탐지 | Aletheia (SPA / RS 분석) |
| 무해화 | OpenCV + Pillow (5단계 CDR 체인) |
| 백엔드 | FastAPI + Uvicorn |
| 대시보드 | Streamlit |
| 컨테이너 | Docker (예정) |

---

## 📊 성능

| 모델 | 정확도 | 학습 시간 |
|------|--------|----------|
| SRNet (from scratch) | 50% (실패) | 14시간 |
| **EfficientNet-B0 (전이학습)** | **82.88%** | **2.3시간** |

### CDR 무해화 성능
```
평균 픽셀 변화량: 0.6507 (육안 차이 없음)
LSB 데이터 파괴: 100% (IndexError 확인)
처리 시간: 즉시
```

---

## 🚀 빠른 시작

### 환경 설정
```bash
git clone https://github.com/팀아이디/stego-cdr-gateway.git
cd stego-cdr-gateway

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### API 서버 실행
```bash
uvicorn api:app --reload --port 8000
```
→ http://localhost:8000/docs (Swagger UI)

### 대시보드 실행
```bash
streamlit run dashboard.py
```
→ http://localhost:8501

### 시연 스크립트
```bash
python demo.py
```

---

## 📡 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/scan` | **탐지 + 무해화 (메인)** |
| POST | `/detect` | AI 탐지만 |
| POST | `/upload` | CDR 무해화만 |
| GET | `/download/{id}` | 무해화 파일 다운로드 |
| GET | `/audit` | 감사 로그 조회 |
| GET | `/docs` | Swagger UI |

### /scan 응답 예시
```json
{
  "file_id": "cf31bb50",
  "filename": "test_hidden.png",
  "pipeline": {
    "step1_detection": {
      "stego_probability": "2.56%",
      "risk_level": "LOW",
      "verdict": "CLEAN"
    },
    "step2_sanitization": {
      "status": "완료",
      "steps": [
        "Step 1: 메타데이터/EXIF 제거",
        "Step 2: 알파채널 제거",
        "Step 3: 색공간 변환 (RGB→YCbCr→RGB)",
        "Step 4: 리사이즈 손실 (95%→100%)",
        "Step 5: JPEG 재인코딩 (Q=85)"
      ],
      "pixel_diff": 0.6507
    },
    "step3_quarantine": {
      "quarantined": false
    }
  },
  "summary": "정상 파일 무해화 완료 (위험도: 2.56%)"
}
```

---

## 🔬 CDR 무해화 5단계 체인

```python
Step 1: 메타데이터/EXIF 제거    ← 외부 정보 차단
Step 2: 알파채널 제거           ← 숨김 채널 차단
Step 3: 색공간 변환 RGB→YCbCr  ← 라운딩 손실로 LSB 깨짐
Step 4: 리사이즈 후 원복        ← 정보 손실 강제
Step 5: JPEG 재인코딩 (Q=85)   ← LSB 비트 완전 파괴
```

---

## 🧪 검증 결과 (2026.04.30)

```
[검증 환경]
OS: Windows 11
GPU: NVIDIA GeForce RTX 5060 Laptop GPU
RAM: 32GB
Python: 3.12.9

[CDR 무해화]
무해화 전: lsb.reveal() → 'TOP_SECRET_DEFENSE_DOC_2026_CONFIDENTIAL' 추출 성공
무해화 후: lsb.reveal() → IndexError (추출 불가) ✅

[Aletheia 통계 탐지]
SPA: Hidden data found in channel R 0.251
RS:  Hidden data found in channel R 0.174 ✅

[EfficientNet-B0]
검증 정확도: 82.88% ✅
```

---

## 📁 프로젝트 구조

```
stego-cdr-gateway/
├── api.py                 # FastAPI 게이트웨이
├── cdr_sanitizer.py       # CDR 무해화 엔진
├── dashboard.py           # Streamlit 관제 대시보드
├── demo.py                # 시연 자동화 스크립트
├── build_dataset.py       # 학습 데이터셋 생성
├── train_srnet.py         # SRNet 학습 (트러블슈팅용)
├── train_efficientnet.py  # EfficientNet-B0 학습
├── test_cdr.py            # CDR 무해화 검증
├── requirements.txt
├── .gitignore
├── docs/
│   └── SRNet_troubleshooting.md
└── samples/
    ├── test_clean.png
    ├── test_hidden.png
    └── test_sanitized.jpg
```

---

## 🔥 트러블슈팅 하이라이트

| 문제 | 원인 | 해결 |
|------|------|------|
| RTX 5060 CUDA 미인식 | sm_120 미지원 | PyTorch Nightly cu128 |
| 윈도우 DataLoader 충돌 | spawn vs fork | freeze_support + workers=0 |
| 1920초/epoch 학습 | 디스크 I/O 병목 | 메모리 캐싱 → 241초 |
| SRNet 50% 고정 | from-scratch 수렴 실패 | EfficientNet 전이학습 전환 |

→ 자세한 내용: [SRNet 트러블슈팅 보고서](docs/SRNet_troubleshooting.md)

---

## 👥 팀 구성

| 역할 | 담당 |
|------|------|
| PM / 인프라 | 쿼카 |
| AI/ML | - |
| Backend | - |
| Frontend | - |

---

## 📅 개발 일정

| 기간 | 단계 |
|------|------|
| 5/15~5/27 | 팀빌딩 + 아이디어 발표 |
| 5/28~6/5 | 기획안 제작 + 멘토링 |
| 6/8~6/22 | 1차 개발 |
| 6/23~7/9 | 통합 + 고도화 |
| 7/14 | 최종 발표 |

---

## 📄 라이선스

MIT License
