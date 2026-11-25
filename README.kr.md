# OCR Web App

> 🌐 **Language**: [English](./README.md) | **한국어 (Korean)**

FastAPI + Tesseract + Nginx 기반의 OCR 웹 애플리케이션입니다.  
브라우저에서 이미지를 업로드하거나 붙여넣어 OCR 텍스트를 추출하고, 원본 이미지와 나란히 비교·편집·내보내기(TXT/MD) 및 AI 보완(Ollama / OpenAI)을 수행할 수 있습니다.

---

## 1. 기술 스택

| 영역 | 기술 |
|---|---|
| **Frontend** | Vanilla JS, HTML5/CSS3, Nginx 1.27-alpine |
| **Backend** | Python 3.11+, FastAPI 0.115, Uvicorn |
| **OCR 엔진** | Tesseract 5 (한국어·영어), `jitesoft/tesseract-ocr` |
| **AI 보완** | Ollama (로컬 모델 `llama3.2` 등), OpenAI API (`gpt-4o-mini` 등) |
| **HTTP 클라이언트** | `httpx` 0.27 (비동기 AI 연동) |
| **컨테이너** | Docker, Docker Compose |
| **모니터링 · 테스트** | `psutil`, ApexCharts (관리자 대시보드), `pytest` |

---

## 2. 아키텍처

- **`frontend`** (Nginx, port `5173`): 업로드 UI, Side-by-Side 비교, 결과 편집기, 최근 기록 및 관리자 대시보드(`admin.html`)
- **`backend`** (FastAPI, port `8000`): OCR 게이트웨이(Magic Bytes 검증 + 동시성 Semaphore 제어), AI 보완 API, 시스템 메트릭 API
- **`ocr-engine`** (Tesseract, on-demand): 요청마다 Docker 컨테이너로 실행 후 자동 소멸(`--rm`)

```text
Browser (5173)
  ├─ POST /api/ocr        → Backend (8000) → docker run ocr-engine → Tesseract
  └─ POST /api/ai/enhance → Backend (8000) → Ollama | OpenAI API
```

---

## 3. 빠른 시작

### 사전 준비
- Docker & Docker Compose

### 실행
```bash
cd ocr-webapp
docker compose --profile build build ocr-engine
docker compose up --build -d
```

### 접속 주소
- **Web App**: http://localhost:5173
- **관리자 대시보드**: http://localhost:5173/admin.html
- **Backend API 문서**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 중지
```bash
docker compose down
```

---

## 4. 주요 기능

### OCR 및 사용자 UX
- **이미지 업로드 & 미리보기**: 드래그 앤 드롭, 파일 선택, **클립보드 붙여넣기(`Ctrl+V`)** 지원 (PNG, JPG, WEBP, BMP, TIFF, GIF · 최대 10MB).
- **인식 언어 선택**: `한국어 + 영어`(`kor+eng`), `한국어만`(`kor`), `영어만`(`eng`).
- **Side-by-Side 비교**: 결과 카드의 `비교` 버튼으로 업로드한 원본 이미지와 추출 텍스트를 나란히 대조할 수 있습니다.
- **결과 직접 편집**: `편집` 버튼으로 추출된 텍스트를 바로 수정한 뒤 복사·다운로드·AI 보완에 사용할 수 있습니다.
- **내보내기 & 복사**: 원클릭 클립보드 복사 및 `.txt` / `.md` 파일 다운로드 지원.
- **설정 및 최근 기록 저장**: `localStorage`에 설정(`Backend URL`, 언어, AI 제공자/모델 — API 키 제외)과 최근 OCR 기록(최대 10건)을 저장·복원합니다.

### AI 보완
1. 우측 상단 **설정** 패널 → **AI 보완** 섹션에서 제공자 선택
   - **Ollama (로컬)**: Ollama URL, 모델명 입력 (기본 `llama3.2`)
   - **OpenAI**: API Key, 모델명 입력 (기본 `gpt-4o-mini`)
2. 결과 카드에서 **AI 보완** 버튼 클릭
3. AI가 오인식 문자·띄어쓰기·줄바꿈을 교정한 텍스트를 표시하며, **원본 OCR 결과 보기**로 이전 텍스트와 비교할 수 있습니다.

> Docker 컨테이너에서 호스트 Ollama에 접근할 때는 `docker-compose.yml`의 `OLLAMA_BASE_URL`을 `http://host.docker.internal:11434`로 설정합니다.

---

## 5. API

### OCR 및 메트릭

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/health` | 헬스 체크 |
| `POST` | `/api/ocr?lang=kor+eng` | OCR 실행 (multipart `file`, Magic Bytes 검증 포함) |
| `GET` | `/api/metrics` | 관리자 대시보드용 시스템 메트릭 |

`POST /api/ocr` 응답 예시:
```json
{
  "text": "인식된 텍스트",
  "lang": "kor+eng",
  "filename": "sample.png",
  "size_bytes": 31245,
  "duration_ms": 1420,
  "char_count": 7,
  "line_count": 1
}
```

### AI 보완

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/api/ai/config` | 현재 AI 설정 조회 (API 키 미포함) |
| `POST` | `/api/ai/enhance` | OCR 텍스트 AI 보완 (`ollama` \| `openai`) |

---

## 6. 환경변수

`docker-compose.yml`의 `backend` 서비스에서 설정합니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OCR_TIMEOUT_SECONDS` | `60.0` | OCR 요청당 타임아웃(초) |
| `MAX_CONCURRENT_OCR` | `4` | 동시 실행 가능한 최대 `ocr-engine` 컨테이너 수 |
| `AI_PROVIDER` | `ollama` | 기본 AI 제공자 (`ollama` \| `openai`) |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama 서버 URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama 모델명 |
| `OPENAI_API_KEY` | _(빈값)_ | OpenAI API 키 |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI 모델명 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI 호환 Base URL |

---

## 7. 테스트

```bash
python3 -m pytest backend/tests/test_main.py -v
```

---

## 8. 디렉터리 요약

| 경로 | 설명 |
|---|---|
| `frontend/` | OCR 웹 UI 및 관리자 대시보드 (Nginx) |
| `backend/` | OCR 게이트웨이, 이미지 시그니처 검증, 메트릭·AI 보완 API (FastAPI) |
| `backend/tests/` | `/health` 및 `/api/ocr` 검증·예외 처리 단위 테스트 |
| `ocr-service/` | Tesseract OCR 엔진 (on-demand 컨테이너) |
| `scripts/` | 부하 테스트·모니터링 유틸리티 |
| `docker-compose.yml` | 전체 스택 실행 정의 |

---

## 9. 트러블슈팅

- OCR API 오류 시:
  ```bash
  docker compose logs -f backend
  ```
- AI 보완 연결 오류 시:
  - Ollama: `ollama list`로 모델 설치 여부 확인
  - OpenAI: API 키·모델명·잔액 확인
- 프론트 접속 오류 시:
  ```bash
  docker compose logs -f frontend
  ```
