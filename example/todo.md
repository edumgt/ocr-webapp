# FastAPI에 Tesseract OCR 엔드포인트 추가하기 (동일 컨테이너 방식)

이 문서는 **기존 FastAPI 게시판 API(main.py)** 에 **Tesseract OCR** 기능을 가장 단순/안정적인 방식으로 추가하는 방법을 정리합니다.

- 방식: **같은 컨테이너 안에서 Tesseract 설치 + FastAPI가 subprocess로 OCR 실행**
- 장점: 구성 단순, 운영 안정적, 의존성 명확
- 단점: OCR 부하가 커지면 API 컨테이너 스케일/분리가 필요할 수 있음

---

## 1) `requirements.txt`에 의존성 추가

파일 업로드를 받으려면 `python-multipart`가 필요합니다. (`UploadFile` / `File` 사용 시)

`requirements.txt`에 아래를 추가하세요.

```txt
python-multipart==0.0.9
```

---

## 2) `Dockerfile`에 Tesseract(한글 포함) 설치 추가

기존 `Dockerfile`의 `apt-get install` 부분에 `tesseract` 패키지를 추가하세요.

```dockerfile
RUN apt-get update  && apt-get install -y --no-install-recommends       curl       tesseract-ocr       tesseract-ocr-kor  && rm -rf /var/lib/apt/lists/*
```

- `tesseract-ocr-kor` : **한글 학습데이터** 패키지
- 컨테이너 내부에서 언어 목록 확인:

```bash
tesseract --list-langs
```

---

## 3) `main.py`에 OCR API 추가

### (1) import 추가

`main.py` 상단의 FastAPI import에 `UploadFile`, `File`을 추가하세요.

```py
from fastapi import FastAPI, HTTPException, Query, Path, Body, status, UploadFile, File
```

그리고 아래 import들도 추가합니다.

```py
import shutil
import subprocess
import tempfile
from pathlib import Path as P
```

---

### (2) Swagger 태그에 `OCR` 추가

`openapi_tags`에 아래 한 줄을 추가하세요.

```py
openapi_tags = [
    {"name": "Health", "description": "서버 상태/헬스체크"},
    {"name": "Posts", "description": "게시글 CRUD 및 검색/정렬/페이징"},
    {"name": "OCR", "description": "이미지 OCR (Tesseract)"},
]
```

---

### (3) 응답 모델 + 엔드포인트 추가

파일 하단(예: `delete_post()` 아래)에 아래 코드를 붙여넣으세요.

```py
class OcrResponse(BaseModel):
    text: str = Field(..., description="추출된 텍스트")
    lang: str = Field(..., description="사용한 언어 코드 (예: kor+eng)")
    psm: int = Field(..., description="Tesseract Page Segmentation Mode")


@app.post(
    "/api/ocr",
    tags=["OCR"],
    summary="이미지 OCR (Tesseract)",
    description="이미지(PNG/JPG 등)를 업로드하면 OCR로 텍스트를 추출합니다.",
    response_model=OcrResponse,
)
def ocr_image(
    file: UploadFile = File(..., description="OCR 대상 이미지 파일"),
    lang: str = Query("kor+eng", description="Tesseract 언어 코드 (예: kor, eng, kor+eng)"),
    psm: int = Query(6, ge=0, le=13, description="Tesseract PSM (기본 6: 단일 블록 텍스트)"),
):
    # 간단한 타입 체크(원하면 더 엄격히)
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    suffix = P(file.filename or "").suffix or ".png"

    with tempfile.TemporaryDirectory() as td:
        td_path = P(td)
        in_path = td_path / f"input{suffix}"
        out_base = td_path / "out"

        # 업로드 파일 저장
        with open(in_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # tesseract 실행
        cmd = [
            "tesseract",
            str(in_path),
            str(out_base),
            "-l",
            lang,
            "--psm",
            str(psm),
        ]
        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.returncode != 0:
            raise HTTPException(status_code=500, detail=(p.stderr or "tesseract failed"))

        txt_path = out_base.with_suffix(".txt")
        text = txt_path.read_text(encoding="utf-8", errors="ignore")

        return OcrResponse(text=text, lang=lang, psm=psm)
```

---

## 4) 실행

이미지 빌드부터 다시 하려면:

```bash
docker compose up --build
```

---

## 5) 테스트 (PowerShell)

아래 예시는 `image.png` 파일을 업로드하여 OCR 실행합니다.

```powershell
curl -X POST "http://localhost:8000/api/ocr?lang=kor%2Beng&psm=6" `
  -F "file=@.\image.png"
```

---

## 참고: OCR 엔진을 **별도 컨테이너**로 분리하고 싶다면

부하/확장/운영 분리를 고려하면 OCR을 별도 서비스로 분리하는 게 더 좋을 수 있습니다.

예) 구조

- FastAPI: 업로드 수신 + 인증/권한 + 요청 라우팅
- OCR 서비스 컨테이너(예: rapid-ocr-api): OCR 처리 전담
- FastAPI가 OCR 컨테이너를 **HTTP로 호출**

장점:
- OCR 워커만 독립적으로 스케일 가능
- API 서버가 OCR CPU 부하에 덜 영향 받음
- 장애 격리/관측성 향상

---

## 운영 팁 (선택)

- OCR 처리 시간이 길어질 수 있으니 요청 타임아웃/리트라이 정책을 고려하세요.
- 이미지가 크면 처리 시간이 늘어납니다. 필요 시 업로드 크기 제한 또는 리사이즈 전처리를 추가하세요.
- `psm` 값에 따라 인식 성능이 달라질 수 있습니다.
  - 6: 단일 블록 텍스트(기본)
  - 3: 자동 페이지 분할(문서 형태에 따라 유리)

