from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import httpx

OCR_SERVICE_URL = "http://ocr-service:8001/ocr"
TIMEOUT_SECONDS = 60.0

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
) -> dict[str, str]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="업로드된 파일이 비어 있습니다.")

    files = {"file": (file.filename or "upload.png", content, file.content_type or "application/octet-stream")}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            resp = await client.post(OCR_SERVICE_URL, params={"lang": lang}, files=files)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"OCR 서비스 연결 실패: {exc}") from exc

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    payload = resp.json()
    payload.setdefault("filename", file.filename or "upload")
    return payload
