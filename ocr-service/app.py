from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

app = FastAPI(title="OCR Service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...), lang: str = Query("kor+eng")) -> dict[str, str]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="빈 파일은 OCR 할 수 없습니다.")

    suffix = Path(file.filename or "upload.png").suffix or ".png"

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(data)
        tmp.flush()

        cmd = ["tesseract", tmp.name, "stdout", "-l", lang]
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise HTTPException(status_code=400, detail=exc.stderr.strip() or "OCR 실패") from exc

    return {"text": result.stdout.strip(), "lang": lang}
