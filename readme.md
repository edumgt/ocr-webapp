# OCR Web App

FastAPI + Tesseract + Nginx 기반의 OCR 웹 애플리케이션입니다.  
이미지를 업로드하면 OCR 결과 텍스트를 웹에서 바로 확인할 수 있습니다.

## 1. 구성

- `frontend` (Nginx, port `5173`): 업로드 UI
- `backend` (FastAPI, port `8000`): 업로드 파일 검증 및 OCR 서비스 게이트웨이
- `ocr-service` (FastAPI + Tesseract, internal `8001`): 실제 OCR 실행

```text
Browser (5173) -> Backend /api/ocr (8000) -> OCR Service /ocr (8001) -> Tesseract
```

## 2. 빠른 시작

사전 준비:
- Docker
- Docker Compose

실행:

```bash
cd /home/runner/work/ocr-webapp/ocr-webapp
docker compose up --build -d
```

접속:
- Web App: http://localhost:5173
- Backend docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health

중지:

```bash
docker compose down
```

## 3. 웹 사용법

1. `Backend URL` 확인 (기본값: `http://localhost:8000`)
2. 이미지 파일 업로드 (`image/*`)
3. OCR 언어 입력 (기본값: `kor+eng`)
4. `OCR 실행` 클릭
5. 결과 텍스트 확인 후 `결과 복사` 가능

## 4. API

### Backend

- `GET /health`
- `POST /api/ocr?lang=kor+eng`
  - form-data: `file`
  - 파일 크기 제한: 10MB
  - 지원 타입: `image/*`

응답 예시:

```json
{
  "text": "인식된 텍스트",
  "lang": "kor+eng",
  "filename": "sample.png",
  "size_bytes": 31245
}
```

### OCR Service

- `GET /health`
- `POST /ocr?lang=kor+eng`
  - `lang` 패턴: `xxx` 또는 `xxx+yyy`
  - OCR 타임아웃: 30초

## 5. 디렉터리 요약

- `frontend/`: OCR 웹 UI 정적 파일
- `backend/`: OCR API 게이트웨이
- `ocr-service/`: Tesseract 실행 서비스
- `docker-compose.yml`: OCR 앱 실행 스택

아래 경로는 OCR 앱 핵심 기능과는 분리된 부가 자료입니다.
- `docker-compose.cicd.yml`, `jenkins/`, `ansible/`, `docker-sample/`, `example/`, `yaml_bkp/`

## 6. 트러블슈팅

- OCR API 오류 시:
  ```bash
  docker compose logs -f backend
  docker compose logs -f ocr-service
  ```
- 프론트 접속 오류 시:
  ```bash
  docker compose logs -f frontend
  ```
