# OCR Web App

FastAPI + Tesseract + Nginx 기반의 OCR 웹 애플리케이션입니다.  
이미지를 업로드하면 OCR 결과 텍스트를 웹에서 바로 확인하고, AI로 추가 보완할 수 있습니다.

## 1. 기술 스택

| 영역 | 기술 |
|------|------|
| **Frontend** | Vanilla JS, Nginx 1.27-alpine |
| **Backend** | Python 3.11, FastAPI 0.115, Uvicorn |
| **OCR 엔진** | Tesseract 5 (한국어·영어), jitesoft/tesseract-ocr |
| **AI 보완** | Ollama (llama3.2 등 로컬 모델), OpenAI API (gpt-4o-mini 등) |
| **HTTP 클라이언트** | httpx 0.27 (비동기 AI 연동) |
| **컨테이너** | Docker, Docker Compose |
| **모니터링** | psutil, ApexCharts (관리자 대시보드) |

## 2. 구성

- `frontend` (Nginx, port `5173`): 업로드 UI + 관리자 대시보드
- `backend` (FastAPI, port `8000`): OCR 게이트웨이 + AI 보완 API
- `ocr-engine` (Tesseract, on-demand): 요청마다 Docker 컨테이너로 실행 후 자동 소멸

```text
Browser (5173)
  └─ POST /api/ocr       → Backend (8000) → docker run ocr-engine → Tesseract
  └─ POST /api/ai/enhance → Backend (8000) → Ollama | OpenAI API
```

## 3. 빠른 시작

사전 준비:
- Docker
- Docker Compose

실행:

```bash
cd <project-directory>
docker compose up --build -d
```

접속:
- Web App: http://localhost:5173
- Backend API 문서: http://localhost:8000/docs
- Backend health: http://localhost:8000/health

중지:

```bash
docker compose down
```

## 4. 웹 사용법

### OCR

1. `설정` 패널에서 Backend URL 확인 (기본값: `http://localhost:8000`)
2. 이미지 파일 업로드 — 드래그 앤 드롭 또는 파일 선택 (최대 10MB)
3. 인식 언어 선택 (`한국어+영어` / `한국어만` / `영어만`)
4. `OCR 실행` 클릭 → 결과 텍스트 확인 후 `복사` 가능

### AI 보완

OCR 완료 후 결과 카드의 **AI 보완** 버튼을 클릭합니다.

1. `설정` 패널 → **AI 보완** 섹션에서 제공자 선택
   - **Ollama (로컬)**: Ollama URL, 모델명 입력 (기본 `llama3.2`)
   - **OpenAI**: API Key, 모델명 입력 (기본 `gpt-4o-mini`)
2. OCR 결과 화면에서 **AI 보완** 버튼 클릭
3. AI가 오인식 문자·띄어쓰기·줄바꿈을 교정한 텍스트를 표시
4. 원본 OCR 결과는 **원본 OCR 결과 보기** 를 펼쳐 확인 가능

#### Ollama 로컬 사용 예시

```bash
ollama pull llama3.2
```

Docker 컨테이너에서 호스트 Ollama에 접근할 때는 `docker-compose.yml`의 `OLLAMA_BASE_URL`을 `http://host.docker.internal:11434`로 설정합니다.

## 5. API

### OCR

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 헬스 체크 |
| `POST` | `/api/ocr?lang=kor+eng` | OCR 실행 (multipart `file`) |
| `GET` | `/api/metrics` | 관리자 대시보드용 메트릭 |

`POST /api/ocr` 응답:

```json
{
  "text": "인식된 텍스트",
  "lang": "kor+eng",
  "filename": "sample.png",
  "size_bytes": 31245
}
```

### AI 보완

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/ai/config` | 현재 AI 설정 조회 (API 키 미포함) |
| `POST` | `/api/ai/enhance` | OCR 텍스트 AI 보완 |

`POST /api/ai/enhance` 요청 (Ollama):

```json
{
  "text": "OCR 결과 텍스트",
  "lang": "kor+eng",
  "provider": "ollama",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "llama3.2"
}
```

`POST /api/ai/enhance` 요청 (OpenAI):

```json
{
  "text": "OCR 결과 텍스트",
  "lang": "kor+eng",
  "provider": "openai",
  "openai_api_key": "sk-...",
  "openai_model": "gpt-4o-mini"
}
```

응답:

```json
{
  "enhanced_text": "교정된 텍스트",
  "provider": "ollama"
}
```

> `provider` 및 모든 설정 필드는 선택사항입니다. 미입력 시 서버 환경변수 값이 사용됩니다.

## 6. 환경변수 (AI 보완)

`docker-compose.yml`의 `backend` 서비스에서 설정합니다.

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `AI_PROVIDER` | `ollama` | 기본 AI 제공자 (`ollama` \| `openai`) |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama 서버 URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama 모델명 |
| `OPENAI_API_KEY` | _(빈값)_ | OpenAI API 키 |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI 모델명 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI 호환 Base URL |

## 7. 디렉터리 요약

| 경로 | 설명 |
|------|------|
| `frontend/` | OCR 웹 UI 정적 파일 (Nginx) |
| `backend/` | OCR 게이트웨이 + AI 보완 API (FastAPI) |
| `backend/ai_enhancer.py` | Ollama / OpenAI AI 보완 모듈 |
| `ocr-service/` | Tesseract OCR 엔진 (on-demand 컨테이너) |
| `scripts/` | 부하 테스트·모니터링 유틸리티 |
| `docker-compose.yml` | 전체 스택 실행 정의 |

> `docker-compose.cicd.yml`, `jenkins/`, `ansible/`, `docker-sample/`, `example/`, `yaml_bkp/` 는 CI/CD·인프라 부가 자료입니다.

## 8. 트러블슈팅

- OCR API 오류 시:
  ```bash
  docker compose logs -f backend
  ```
- AI 보완 연결 오류 시:
  - Ollama: `ollama list` 로 모델 설치 여부 확인
  - OpenAI: API 키·모델명 확인, 잔액 확인
- 프론트 접속 오류 시:
  ```bash
  docker compose logs -f frontend
  ```
