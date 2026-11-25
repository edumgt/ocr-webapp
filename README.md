# OCR Web App

> 🌐 **Language**: **English** | [한국어 (Korean)](./README.kr.md)

An OCR web application built with **FastAPI + Tesseract + Nginx**.  
Upload or paste an image in the browser to extract text with Tesseract OCR, compare side-by-side, edit or export results, and optionally post-process the text with AI (Ollama or OpenAI).

---

## 1. Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Vanilla JS, HTML5/CSS3, Nginx 1.27-alpine |
| **Backend** | Python 3.11+, FastAPI 0.115, Uvicorn |
| **OCR Engine** | Tesseract 5 (Korean & English), `jitesoft/tesseract-ocr` |
| **AI Post-Processing** | Ollama (local models e.g. `llama3.2`), OpenAI API (e.g. `gpt-4o-mini`) |
| **HTTP Client** | `httpx` 0.27 (async AI integration) |
| **Containers** | Docker, Docker Compose |
| **Monitoring & Testing** | `psutil`, ApexCharts (Admin Dashboard), `pytest` |

---

## 2. Architecture

- **`frontend`** (Nginx, port `5173`): Upload UI, side-by-side comparison, inline editor, history, and Admin Dashboard (`admin.html`)
- **`backend`** (FastAPI, port `8000`): OCR gateway (magic-byte validation + concurrency semaphore), AI enhancement API, and metrics API
- **`ocr-engine`** (Tesseract, on-demand): Spawned per request via Docker and automatically removed (`--rm`)

```text
Browser (5173)
  ├─ POST /api/ocr        → Backend (8000) → docker run ocr-engine → Tesseract
  └─ POST /api/ai/enhance → Backend (8000) → Ollama | OpenAI API
```

---

## 3. Quick Start

### Prerequisites
- Docker & Docker Compose

### Run
```bash
cd ocr-webapp
docker compose --profile build build ocr-engine
docker compose up --build -d
```

### Endpoints
- **Web App**: http://localhost:5173
- **Admin Dashboard**: http://localhost:5173/admin.html
- **Backend API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Stop
```bash
docker compose down
```

---

## 4. Key Features

### OCR & Workspace UX
- **Drag & Drop, File Picker, and Clipboard Paste (`Ctrl+V`)**: Supports PNG, JPG, WEBP, BMP, TIFF, GIF (up to 10MB) with instant image preview.
- **Language Selection**: `kor+eng` (Korean + English), `kor` (Korean only), `eng` (English only).
- **Side-by-Side Comparison**: Toggle `비교` (Compare) to inspect the uploaded image alongside the extracted text.
- **Inline Result Editor**: Toggle `편집` (Edit) to fix or refine extracted text directly before copying, exporting, or running AI enhancement.
- **Export & Copy**: One-click clipboard copy and download as `.txt` or `.md`.
- **Persistent Settings & History**: Saves settings (`Backend URL`, language, AI provider/model — excluding API keys) and the last 10 OCR results in `localStorage`.

### AI Enhancement
1. Open **Settings** (`설정`) and choose a provider:
   - **Ollama (Local)**: Configure Ollama URL and model (default: `llama3.2`).
   - **OpenAI**: Provide your API Key, model (default: `gpt-4o-mini`), and Base URL.
2. Click **AI 보완** (AI Enhance) on the result card to fix OCR character errors, spacing, and line breaks.
3. Expand **원본 OCR 결과 보기** to compare against the original OCR output.

> When running Ollama on the host machine, set `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `docker-compose.yml`.

---

## 5. API Reference

### OCR & Metrics

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/ocr?lang=kor+eng` | Run OCR (`multipart/form-data` `file`, validated by magic bytes) |
| `GET` | `/api/metrics` | System & request metrics for the Admin Dashboard |

Sample `POST /api/ocr` response:
```json
{
  "text": "Extracted text",
  "lang": "kor+eng",
  "filename": "sample.png",
  "size_bytes": 31245,
  "duration_ms": 1420,
  "char_count": 14,
  "line_count": 1
}
```

### AI Enhancement

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/ai/config` | Get current AI configuration (without exposing API keys) |
| `POST` | `/api/ai/enhance` | Post-process OCR text using Ollama or OpenAI |

---

## 6. Environment Variables

Configured under `backend.environment` in `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| `OCR_TIMEOUT_SECONDS` | `60.0` | Timeout per OCR request (seconds) |
| `MAX_CONCURRENT_OCR` | `4` | Max concurrent `ocr-engine` containers |
| `AI_PROVIDER` | `ollama` | Default AI provider (`ollama` \| `openai`) |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Default Ollama model |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | Default OpenAI model |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible Base URL |

---

## 7. Testing

```bash
python3 -m pytest backend/tests/test_main.py -v
```

---

## 8. Directory Structure

| Path | Description |
|---|---|
| `frontend/` | Static web UI & Admin Dashboard (Nginx) |
| `backend/` | OCR gateway, magic-byte validation, metrics & AI enhancement API (FastAPI) |
| `backend/tests/` | Unit tests for `/health` and `/api/ocr` validation/error handling |
| `ocr-service/` | On-demand Tesseract OCR container |
| `scripts/` | Load testing and monitoring utilities |
| `docker-compose.yml` | Full stack definition |
