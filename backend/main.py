from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

import docker as docker_sdk
import httpx
import psutil
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import ai_enhancer

# ── 설정 ─────────────────────────────────────────────────────────────────────
OCR_IMAGE   = os.getenv("OCR_IMAGE",  "ocr-engine:latest")
OCR_VOLUME  = os.getenv("OCR_VOLUME", "ocr-inbox")
OCR_INBOX   = os.getenv("OCR_INBOX",  "/ocr-inbox")
TIMEOUT_SECONDS          = 60.0
MAX_UPLOAD_SIZE_BYTES    = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPE_PREFIXES = ("image/",)
SUPPORTED_LANG_CHOICES   = ("kor", "eng", "kor+eng", "eng+kor")

logger = logging.getLogger(__name__)

# ── 메트릭 저장소 ─────────────────────────────────────────────────────────────
_lock           = threading.Lock()
_cpu_hist:  deque = deque(maxlen=60)   # 2s 간격 × 60 = 2분
_mem_hist:  deque = deque(maxlen=60)
_ocr_hist:  deque = deque(maxlen=60)   # 동시 OCR 컨테이너 수
_req_hist:  deque = deque(maxlen=60)   # 2s 윈도우 요청 수

_active_ocr   = 0    # 현재 처리 중인 OCR 요청
_total_req    = 0
_success_req  = 0
_failed_req   = 0
_resp_times: deque = deque(maxlen=200)  # 응답시간 히스토리 (초)
_prev_total   = 0


def _count_ocr_containers() -> int:
    try:
        client = docker_sdk.DockerClient(base_url="unix:///var/run/docker.sock")
        return len(client.containers.list(filters={"ancestor": OCR_IMAGE}))
    except Exception:
        return 0


def _collect_metrics():
    """백그라운드 스레드: 2초마다 시스템 메트릭 수집."""
    global _prev_total
    while True:
        ts = int(time.time() * 1000)
        cpu  = psutil.cpu_percent()
        mem  = psutil.virtual_memory()
        ocr_n = _count_ocr_containers()
        with _lock:
            req_delta = _total_req - _prev_total
            _prev_total = _total_req
            _cpu_hist.append([ts, round(cpu, 1)])
            _mem_hist.append([ts, round(mem.used / 1024 ** 2, 1)])
            _ocr_hist.append([ts, ocr_n])
            _req_hist.append([ts, req_delta])
        time.sleep(2)


# ── 앱 수명주기 ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    t = threading.Thread(target=_collect_metrics, daemon=True)
    t.start()
    yield


app = FastAPI(
    title="OCR Gateway API",
    version="3.0.0",
    description="on-demand OCR 컨테이너 게이트웨이 + 시스템 메트릭 API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── OCR 헬퍼 ─────────────────────────────────────────────────────────────────
def _ocr_sync(content: bytes, lang: str, suffix: str) -> str:
    fname       = f"{uuid.uuid4().hex}{suffix}"
    host_file   = Path(OCR_INBOX) / fname
    container_file = f"/inbox/{fname}"
    host_file.write_bytes(content)
    try:
        client = docker_sdk.DockerClient(base_url="unix:///var/run/docker.sock")
        stdout = client.containers.run(
            OCR_IMAGE,
            command=[lang, container_file],
            volumes={OCR_VOLUME: {"bind": "/inbox", "mode": "ro"}},
            remove=True,
            stdout=True,
            stderr=False,
        )
        return stdout.decode(errors="replace").strip()
    finally:
        host_file.unlink(missing_ok=True)


# ── 엔드포인트 ────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/ocr")
async def run_ocr(
    file: UploadFile = File(...),
    lang: str = Query("kor+eng"),
) -> dict[str, str | int]:
    global _active_ocr, _total_req, _success_req, _failed_req

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="업로드된 파일이 비어 있습니다.")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"파일은 {MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB 이하여야 합니다.")

    ct = file.content_type or "application/octet-stream"
    if not any(ct.startswith(p) for p in ALLOWED_CONTENT_TYPE_PREFIXES):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 형식: {ct}")
    if lang not in SUPPORTED_LANG_CHOICES:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 lang: {lang}")

    suffix = Path(file.filename or "upload.png").suffix or ".png"
    t0 = time.perf_counter()

    with _lock:
        _total_req  += 1
        _active_ocr += 1

    try:
        loop = asyncio.get_event_loop()
        text = await asyncio.wait_for(
            loop.run_in_executor(None, _ocr_sync, content, lang, suffix),
            timeout=TIMEOUT_SECONDS,
        )
        with _lock:
            _success_req += 1
            _resp_times.append(round(time.perf_counter() - t0, 3))
    except asyncio.TimeoutError:
        with _lock:
            _failed_req += 1
        raise HTTPException(status_code=504, detail="OCR 처리 시간 초과.")
    except docker_sdk.errors.ContainerError as exc:
        with _lock:
            _failed_req += 1
        detail = exc.stderr.decode(errors="replace").strip() if exc.stderr else "OCR 실패"
        raise HTTPException(status_code=400, detail=detail)
    except Exception as exc:
        with _lock:
            _failed_req += 1
        logger.exception("OCR 컨테이너 실행 실패")
        raise HTTPException(status_code=502, detail=f"OCR 컨테이너 실행 실패: {exc}")
    finally:
        with _lock:
            _active_ocr -= 1

    return {
        "text":       text,
        "lang":       lang,
        "filename":   file.filename or "upload",
        "size_bytes": len(content),
    }


@app.get("/api/metrics")
def get_metrics():
    """관리자 대시보드용 시스템 메트릭."""
    mem  = psutil.virtual_memory()
    cpu  = psutil.cpu_percent()
    with _lock:
        rt = list(_resp_times)
        return {
            "current": {
                "cpu_pct":    round(cpu, 1),
                "mem_used_mb": round(mem.used  / 1024**2, 1),
                "mem_total_mb": round(mem.total / 1024**2, 1),
                "mem_pct":    round(mem.percent, 1),
                "active_ocr": _active_ocr,
                "total_req":  _total_req,
                "success_req":_success_req,
                "failed_req": _failed_req,
                "success_pct": round(_success_req / _total_req * 100, 1) if _total_req else 100.0,
                "avg_resp_s": round(sum(rt) / len(rt), 2) if rt else 0,
            },
            "series": {
                "cpu":  list(_cpu_hist),
                "mem":  list(_mem_hist),
                "ocr":  list(_ocr_hist),
                "req":  list(_req_hist),
            },
            "resp_dist": _resp_time_buckets(rt),
        }


def _resp_time_buckets(times: list[float]) -> dict:
    """응답시간 분포 (히스토그램 버킷)."""
    buckets = {"0-5s": 0, "5-10s": 0, "10-20s": 0, "20s+": 0}
    for t in times:
        if t < 5:      buckets["0-5s"]   += 1
        elif t < 10:   buckets["5-10s"]  += 1
        elif t < 20:   buckets["10-20s"] += 1
        else:          buckets["20s+"]   += 1
    return buckets


# ── AI 보완 ───────────────────────────────────────────────────────────────────
class EnhanceRequest(BaseModel):
    text: str
    lang: str = "kor+eng"
    provider: str | None = None          # "ollama" | "openai", 미지정 시 환경변수 사용
    ollama_url: str | None = None
    ollama_model: str | None = None
    openai_api_key: str | None = None    # 클라이언트가 직접 전달 가능
    openai_model: str | None = None
    openai_base_url: str | None = None


@app.get("/api/ai/config")
def get_ai_config() -> dict:
    """현재 AI 보완 설정 정보 (API 키 노출 없이 반환)."""
    return {
        "provider":        ai_enhancer.DEFAULT_PROVIDER,
        "ollama_url":      ai_enhancer.DEFAULT_OLLAMA_URL,
        "ollama_model":    ai_enhancer.DEFAULT_OLLAMA_MODEL,
        "openai_model":    ai_enhancer.DEFAULT_OPENAI_MODEL,
        "openai_base_url": ai_enhancer.DEFAULT_OPENAI_URL,
        "openai_key_set":  bool(ai_enhancer.DEFAULT_OPENAI_KEY),
    }


@app.post("/api/ai/enhance")
async def enhance_ocr(req: EnhanceRequest) -> dict[str, str]:
    """OCR 결과 텍스트를 AI로 보완."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text가 비어 있습니다.")

    provider = (req.provider or ai_enhancer.DEFAULT_PROVIDER).lower()

    try:
        if provider == "ollama":
            enhanced = await ai_enhancer.enhance_ollama(
                text=req.text,
                lang=req.lang,
                base_url=req.ollama_url or ai_enhancer.DEFAULT_OLLAMA_URL,
                model=req.ollama_model or ai_enhancer.DEFAULT_OLLAMA_MODEL,
            )
        elif provider == "openai":
            api_key = req.openai_api_key or ai_enhancer.DEFAULT_OPENAI_KEY
            if not api_key:
                raise HTTPException(status_code=400, detail="OpenAI API 키가 설정되지 않았습니다.")
            enhanced = await ai_enhancer.enhance_openai(
                text=req.text,
                lang=req.lang,
                api_key=api_key,
                model=req.openai_model or ai_enhancer.DEFAULT_OPENAI_MODEL,
                base_url=req.openai_base_url or ai_enhancer.DEFAULT_OPENAI_URL,
            )
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 제공자: {provider}")
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"AI 서비스 오류: {exc.response.text[:300]}")
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail=f"{provider} 서버에 연결할 수 없습니다.")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과.")
    except Exception as exc:
        logger.exception("AI enhance 실패")
        raise HTTPException(status_code=500, detail=f"AI 처리 오류: {exc}")

    return {"enhanced_text": enhanced, "provider": provider}
