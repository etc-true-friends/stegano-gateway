# stegano-gateway

> **AI 기반 스테가노그래피 탐지 + CDR 무해화 망연계 보안 게이트웨이**<br>
> 구름 정보보호 부트캠프 17기 파이널 프로젝트 - `/etc/friends`

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=white" alt="PyTorch">
  <img src="https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=111111" alt="React">
  <img src="https://img.shields.io/badge/mitmproxy-2B2B2B?logo=python&logoColor=white" alt="mitmproxy">
  <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker">
</p>

---

## 프로젝트 소개

스테가노그래피(Steganography)는 이미지나 문서처럼 정상으로 보이는 파일 안에 메시지, 기밀 데이터, 악성 페이로드를 숨기는 은닉 기법입니다. 일반적인 확장자 검사나 육안 확인만으로는 탐지가 어렵고, 메일 첨부파일과 파일 반입/반출 흐름에서 보안 사각지대가 될 수 있습니다.

본 프로젝트는 메일 첨부파일과 프록시 트래픽을 대상으로 **정책 검사 -> AI/Aletheia 탐지 -> CDR 무해화 -> 감사 로그/관제** 흐름을 제공하는 보안 게이트웨이입니다. 탐지된 파일은 사용자에게 그대로 노출하지 않고, 안전하게 재구성한 CDR 결과물 또는 정책 대체 파일을 전달하는 것을 목표로 합니다.

> 핵심 방향: **사용자는 자연스럽게 파일을 주고받고, 게이트웨이는 뒤에서 탐지와 무해화를 수행한다.**

---

## 주요 기능

- FastAPI 기반 보안 API Gateway
- React 관제 대시보드와 React 메일 포털
- mitmproxy 기반 인라인 트래픽 인터셉트
- SRNet 계열 모델 앙상블 탐지
- LSB, AES-random LSB, Edge-adaptive LSB, DCT-mid, DWT-Haar, Fine-tuned 모델 라우팅
- Aletheia SPA 기반 보조 스테가노 분석
- 고해상도 이미지 대상 제한형 멀티크롭 추론
- 이미지 CDR 무해화 및 EXIF/픽셀 레벨 재구성
- 위험 문서/첨부파일 정책 탐지 및 안전 안내문 대체
- ZIP 내부 이미지 탐색, 개별 스캔, 무해화 ZIP 재구성
- ZIP 내부 위험 첨부파일 정책 제거 로그 기록
- SQLite 감사 로그, CDR 이력, 메일 발신/수신자 추적
- 임계값 설정, 위협 현황, CDR 검증, 무해화 이력, 일별 통계 대시보드

---

## 아키텍처

```text
stegano-gateway/
├── 1_AI_Engine/          # SRNet 모델, 앙상블 설정, 학습/평가/멀티크롭 도구
├── 2_API_Gateway/        # FastAPI, 메일 API, CDR, 정책 엔진, mitmproxy addon
├── 3_Web_Dashboard/
│   ├── react-dashboard/  # React 관제 대시보드
│   └── react-mail/       # React 메일 포털
├── 4_Local_Workspace/    # DB, 업로드/무해화 파일, 로컬 모델/리포트 저장소
├── Dockerfile
└── docker-compose.yml
```

### 처리 흐름

```text
[사용자 메일/파일 전송]
        |
        v
[mitmproxy 또는 메일 API]
        |
        v
[FastAPI Gateway]
        |
        +-- Step 1. 확장자/MIME/문서 정책 검사
        |
        +-- Step 2. SRNet 앙상블 + Aletheia 탐지
        |
        +-- Step 3. 이미지/첨부파일 CDR 무해화 또는 정책 대체
        |
        +-- Step 4. 감사 로그, CDR 로그, 메일 발신/수신자 기록
        |
        v
[사용자에게 무해화본 또는 안전 대체 파일 전달]
        |
        v
[관제 대시보드 실시간 확인]
```

### 처리 정책

| 유형 | 처리 |
| --- | --- |
| 정상 이미지 | 통과 또는 CDR 처리 후 안전 전달 |
| 스테가노 의심 이미지 | CDR 무해화 후 전달, 감사/관제 기록 |
| 실행 파일/스크립트/위장 확장자 | 안전 안내문으로 대체, 정책 로그 기록 |
| ZIP 내부 이미지 | 내부 이미지별 스캔 및 CDR 후 sanitized ZIP 재구성 |
| ZIP 내부 위험 첨부파일 | 결과 ZIP에서 제거, `POLICY_SANITIZED` 로그 기록 |

---

## AI 탐지 구성

`models_config.json` 기반으로 모델을 동적으로 로드합니다.

| 모델 | 역할 |
| --- | --- |
| `lsb` | 기본 LSB 은닉 탐지 |
| `aes_random_lsb` | AES/random LSB 계열 탐지 |
| `edge_adaptive_lsb` | 엣지 적응형 LSB 탐지 |
| `dct_mid` | DCT 주파수 영역 은닉 탐지 |
| `dwt_haar` | DWT-Haar 계열 은닉 탐지 |
| `finetuned` | 일반화 보강용 fine-tuned 모델 |

판정은 Max Router 방식으로 가장 강하게 반응한 모델을 route model로 선택합니다. 고해상도 이미지는 제한형 멀티크롭 옵션을 통해 일부 crop을 추가 평가할 수 있습니다.

---

## 기술 스택

| 분류 | 기술 |
| --- | --- |
| AI/분석 | PyTorch, SRNet, Aletheia |
| 백엔드 | FastAPI, Uvicorn, SQLite3 |
| 무해화 | CDRSanitizer, Pillow 기반 이미지 재구성 |
| 프록시 | mitmproxy |
| 프론트엔드 | React, Vite, Recharts |
| 메일 포털 | React Mail UI, FastAPI mail API |
| 배포 | Docker Compose, AWS EC2, ECR, GitHub Actions |
| 저장소 | 로컬 SQLite/파일 저장소, S3 모델 저장 연계 |

---

## 로컬 실행

### 1. Python 의존성

```bash
python -m venv venv
venv\Scripts\activate
pip install -r 2_API_Gateway/requirements.txt
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 2. 모델 파일 배치

기본 모델은 아래 경로에 둡니다.

```text
1_AI_Engine/checkpoints/
├── lsb_model.pt
├── aes_lsb_model.pt
├── edge_adaptive_lsb_model.pt
├── dct_model.pt
├── dwt_model.pt
└── finetuned_model.pt
```

`4_Local_Workspace/models_config.json` 또는 `1_AI_Engine/checkpoints/models_config.json`에서 경로와 임계값을 관리합니다.

### 3. API 서버

PowerShell:

```powershell
cd 2_API_Gateway
$env:PYTHONPATH="..\1_AI_Engine"
..\venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

Bash:

```bash
cd 2_API_Gateway
export PYTHONPATH=../1_AI_Engine
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
```

### 4. 관제 대시보드

```bash
cd 3_Web_Dashboard/react-dashboard
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

### 5. 메일 포털

```bash
cd 3_Web_Dashboard/react-mail
npm install
npm run dev -- --host 127.0.0.1 --port 3001
```

---

## Docker Compose 실행

```bash
docker compose up -d --build
docker compose ps
```

| 서비스 | 포트 | 설명 |
| --- | --- | --- |
| `api-gateway` | `8000` | FastAPI 보안 API |
| `react-dashboard` | `3000` | 관제 대시보드 |
| `react-mail` | `3001` | 메일 포털 |
| `mitmproxy` | `8080`, `9091` | 프록시/웹 콘솔 |

---

## 주요 API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/` | API 상태, 로드된 모델 목록 |
| `POST` | `/scan` | 파일 스캔 및 무해화 |
| `GET` | `/audit` | 감사 로그 조회 |
| `GET` | `/cdr/status` | CDR 처리 현황 |
| `GET` | `/dashboard/threat-overview` | 위협 현황 대시보드 데이터 |
| `GET` | `/policy/threshold` | 탐지 임계값 조회 |
| `PUT` | `/policy/threshold` | 탐지 임계값 수정 |
| `POST` | `/mails/send` | 메일 발송 및 첨부파일 보안 처리 |

---

## 배포 환경

현재 운영 기준 도메인:

| 주소 | 역할 |
| --- | --- |
| `https://stegano.app/` | 관제 대시보드 |
| `https://mail.stegano.app/` | 메일 포털 |
| `https://api.stegano.app/` | API Gateway |

배포는 GitHub Actions와 EC2 Docker Compose를 기준으로 진행합니다. `main` 머지 후 Actions가 ECR 이미지를 갱신하고 EC2에서 컨테이너를 재기동합니다.

---

## 고도화 현황

- SRNet RGB 3채널 확장
- 모델 앙상블 Max Router 구성
- Aletheia 보조 탐지 연동
- Edge-adaptive LSB 모델 추가
- 제한형 멀티크롭 탐지 옵션 추가
- 문서/첨부파일 정책 탐지 고도화
- ZIP 내부 이미지 탐색 및 sanitized ZIP 재구성
- React 관제 대시보드 고도화
- 메일 포털과 AI/CDR 파이프라인 연동
- 감사 로그에 메일 발신자/수신자 표시

---

## 라이선스

본 프로젝트는 구름 정보보호 부트캠프 17기 교육 목적의 파이널 프로젝트로 제작되었습니다.
