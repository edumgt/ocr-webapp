from __future__ import annotations

import logging
from collections.abc import Mapping

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import httpx

OCR_SERVICE_URL = "http://ocr-service:8001/ocr"
TIMEOUT_SECONDS = 60.0
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPE_PREFIXES = ("image/",)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OCR Gateway API",
    version="1.0.0",
    description="Vanilla JS frontend가 업로드한 이미지를 OCR 컨테이너로 전달하는 FastAPI 게이트웨이",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/ocr")
async def run_ocr(
    file: UploadFile = File(...),
    lang: str = Query("kor+eng", description="Tesseract language code (ex: kor+eng)"),
) -> dict[str, str | int]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="업로드된 파일이 비어 있습니다.")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"업로드 파일은 {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB 이하여야 합니다.",
        )

    content_type = file.content_type or "application/octet-stream"
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_CONTENT_TYPE_PREFIXES):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다: {content_type}")

    files = {"file": (file.filename or "upload.png", content, content_type)}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(OCR_SERVICE_URL, params={"lang": lang}, files=files)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"OCR 서비스 연결 실패: {exc}") from exc

    if resp.status_code >= 400:
        detail: str = resp.text
        try:
            payload = resp.json()
            if isinstance(payload, Mapping):
                detail_value = payload.get("detail")
                if detail_value is not None:
                    detail = str(detail_value)
        except ValueError as exc:
            logger.warning("OCR 서비스 오류 응답 JSON 파싱 실패: %s", exc)
        raise HTTPException(status_code=resp.status_code, detail=detail)

    payload = resp.json()
    payload.setdefault("filename", file.filename or "upload")
    payload.setdefault("size_bytes", len(content))
    return payload
