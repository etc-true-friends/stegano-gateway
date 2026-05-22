# stegano-gateway

> **AI 기반 스테가노그래피 이상 징후 탐지 및 CDR 무해화 망연계 시스템**  
> 구름 정보보호 부트캠프 17기 파이널 프로젝트 — /etc/true/friends

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white" alt="PyTorch">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
</p>

---

## 프로젝트 소개

스테가노그래피(Steganography)는 이미지 픽셀의 최하위 비트(LSB)에 기밀 데이터나 악성코드를 숨기는 기술로, 육안으로는 정상 이미지와 구별이 불가능하며 일반 보안 솔루션으로는 탐지되지 않는 보안 사각지대입니다.

본 프로젝트는 **프록시 서버 기반 네트워크 자동 가로채기**로 사용자 개입 없이 모든 이미지 트래픽을 검사하고, **SRNet 딥러닝 모델 기반 AI 탐지**와 **CDR(Content Disarm & Reconstruction) 무해화**를 결합한 **Zero Trust 망연계 게이트웨이** 구현을 목표로 합니다.

> "AI가 놓쳐도 CDR이 반드시 파괴한다"

### 실제 사례

| 연도 | 사건 | 방식 |
|------|------|------|
| 2010 | FBI 러시아 스파이 체포 | 웹 이미지 LSB에 암호 메시지 은닉 |
| 2018 | GE 엔지니어 산업스파이 | 석양 사진에 군사 기밀 숨겨 중국 반출 |
| 2022 | 북한 APT37 국내 침투 | 사진 속 악성코드로 내부망 침투 |

---

## 아키텍처

```
stegano-gateway/
├── 1_AI_Engine/          # SRNet 추론 엔진 및 딥러닝 코어
├── 2_API_Gateway/        # FastAPI 백엔드 + CDR 무해화 + 보안 정책
├── 3_Web_Dashboard/      # Streamlit 관제 대시보드 + 시연 스크립트
└── 4_Local_Workspace/    # 모델 가중치, 격리/무해화 자산 (gitignore)
```

### 양방향 자동 방어 구조

```
[내부망 사용자]          [외부 공격자]
  파일 전송                악성코드 은닉 이미지 전송
       ↓                         ↓
       └──────────┬──────────────┘
                  ↓
        [프록시 서버] ← 네트워크 자동 가로채기
         사용자 개입 없이 모든 이미지 트래픽 검사
                  ↓
    ┌─────────────────────────────┐
    │     보안 파이프라인 (5단계)  │
    │                             │
    │ Step 1: MIME 시그니처 검증  │
    │ Step 2: SRNet AI 탐지       │
    │ Step 3: CDR 무해화          │
    │ Step 4: Quarantine 격리     │
    │ Step 5: 감사 로그 기록      │
    └─────────────────────────────┘
                  ↓
    ┌─────────────────────────────┐
    │  CLEAN     → 통과 (전달)    │
    │  SUSPICIOUS → 격리 + 무해화 │
    └─────────────────────────────┘
                  ↓
        [보안팀 관제 대시보드]
         실시간 모니터링
```

### 양방향 방어

| 방향 | 위협 | 처리 |
|------|------|------|
| Outbound (반출) | 내부 직원의 기밀 이미지 유출 시도 | 자동 탐지 + CDR 무해화 |
| Inbound (반입) | 외부 해커의 악성코드 내부망 침투 | 자동 탐지 + CDR 무해화 |

---

## 보안 파이프라인 상세

```
Step 1: MIME 시그니처 검증 (python-magic)
        → .exe를 .png로 위장한 공격 파일 헤더 수준에서 즉시 차단

Step 2: SRNet AI 탐지
        → img.crop(0,0,256,256) 원본 픽셀 직접 추론
        → 임계치 30% 이상 → SUSPICIOUS 판정
        → 파인튜닝 완료 모델 (best_srnet_finetuned.pt) 사용

Step 3: CDR 무해화 (Zero Trust)
        → AI 탐지 결과와 무관하게 무조건 실행
        → EXIF 제거 → YCbCr 색공간 변환
        → JPEG 재인코딩 (Q=85) → 리사이즈 손실

Step 4: Quarantine 격리
        → SUSPICIOUS 파일 → quarantine 폴더 강제 이송
        → 파일 권한 0o440 (Read-Only) 설정으로 2차 피해 방지

Step 5: SQLite3 감사 로그 영구 보존
        → 서버 재시작 후에도 전체 이력 보존
        → 보안팀 대시보드에서 실시간 조회
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 프록시 서버 | mitmproxy (Python 기반 네트워크 트래픽 제어) |
| AI 탐지 | SRNet (스테가노 전용 CNN), Aletheia |
| 무해화 | CDR 5단계 파이프라인 |
| 백엔드 | FastAPI, Uvicorn, SQLite3 |
| 보안 정책 | python-magic (MIME 검증) |
| 대시보드 | Streamlit |
| 배포 | Docker, AWS EC2 |

---

## 설치 방법

### 요구 사항

- Python 3.10+
- CUDA (선택, CPU도 동작)
- 모델 가중치: `best_srnet_finetuned.pt`

### 설치

```bash
git clone https://github.com/etc-true-friends/stegano-gateway
cd stegano-gateway
pip install -r requirements.txt
```

### 모델 가중치 설정

```bash
mkdir -p 4_Local_Workspace/checkpoints
# best_srnet_finetuned.pt 파일을 아래 경로에 배치
# 4_Local_Workspace/checkpoints/best_srnet_finetuned.pt
```

---

## 실행 방법

### 1. API 서버 실행

```bash
cd 2_API_Gateway
uvicorn api:app --port 8000 --reload
```

### 2. 대시보드 실행

```bash
cd 3_Web_Dashboard
streamlit run dashboard.py
```

### 3. 시연 자동화

```bash
cd 3_Web_Dashboard
python demo.py
```

정상 이미지 통과 → 은닉 이미지 AI 탐지 → 물리 격리 → CDR 무해화 증명까지 전 과정 자동 시연

### API 엔드포인트

| 메서드 | 경로 | 설명 |
| :--- | :--- | :--- |
| `GET` | `/health` | 게이트웨이 서버 및 DB 상태 체크 |
| `GET` | `/stats` | 관제 대시보드용 위협 통계 데이터 산출 |
| `POST` | `/scan` | 인라인 파일 스캔 및 무해화 자동 처리 |
| `GET` | `/audit` | 전체 시스템 감사 로그 조회 |

---

## 개발 로드맵

```
Phase 1 (현재 완료)
  ✅ SRNet AI 탐지 파이프라인
  ✅ CDR 5단계 무해화 엔진
  ✅ FastAPI 백엔드
  ✅ Streamlit 관제 대시보드
  ✅ SQLite3 감사 로그
  ✅ Quarantine 격리 시스템
  ✅ MIME 시그니처 검증

Phase 2 (6/8~6/22)
  → 프록시 서버 구현 (mitmproxy)
  → 네트워크 트래픽 자동 가로채기
  → 양방향 자동 방어 연동

Phase 3 (6/23~7/9)
  → Docker 컨테이너화
  → AWS EC2 배포
  → 대시보드 실시간 고도화

Phase 4 (7/14 최종 발표)
  → 실제 시연 데모
  → 트러블슈팅 보고서
```

---

## 라이선스

본 프로젝트는 구름 정보보호 부트캠프 17기 교육 목적으로 제작되었습니다.
