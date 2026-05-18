from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

app = FastAPI(title="OCR Service", version="1.0.0")
LANG_PATTERN = re.compile(r"^[a-z]{3}(?:\+[a-z]{3})*$")
ALLOWED_LANGS = {"kor", "eng"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
OCR_TIMEOUT_SECONDS = 30


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...), lang: str = Query("kor+eng")) -> dict[str, str]:
    if not LANG_PATTERN.fullmatch(lang):
        raise HTTPException(status_code=400, detail="lang 형식이 올바르지 않습니다. 예: kor+eng")
    lang_codes = lang.split("+")
    if any(code not in ALLOWED_LANGS for code in lang_codes):
        raise HTTPException(status_code=400, detail=f"지원하지 않는 lang입니다. 지원값: {','.join(sorted(ALLOWED_LANGS))}")
    normalized_lang = "+".join(lang_codes)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="빈 파일은 OCR 할 수 없습니다.")
    if len(data) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"업로드 파일은 {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB 이하여야 합니다.",
        )

    suffix = Path(file.filename or "upload.png").suffix or ".png"

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(data)
        tmp.flush()

        cmd = ["tesseract", tmp.name, "stdout", "-l", normalized_lang]
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=OCR_TIMEOUT_SECONDS,
            )
        except subprocess.CalledProcessError as exc:
            raise HTTPException(status_code=400, detail=exc.stderr.strip() or "OCR 실패") from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail=f"OCR 처리 시간이 초과되었습니다: {exc}") from exc

    return {"text": result.stdout.strip(), "lang": normalized_lang}
