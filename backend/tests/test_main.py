import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import docker.errors
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main  # noqa: E402

client = TestClient(main.app)

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


def test_ocr_rejects_empty_file():
    res = client.post(
        "/api/ocr?lang=kor+eng",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert res.status_code == 400


def test_ocr_rejects_spoofed_image_magic_bytes():
    res = client.post(
        "/api/ocr?lang=kor+eng",
        files={"file": ("fake.png", b"not-a-real-image", "image/png")},
    )
    assert res.status_code == 400
    assert "유효한 이미지" in res.json()["detail"]


def test_ocr_rejects_unsupported_lang():
    res = client.post(
        "/api/ocr?lang=jpn",
        files={"file": ("sample.png", PNG_HEADER, "image/png")},
    )
    assert res.status_code == 400


def test_ocr_success_returns_text_and_metrics():
    with patch.object(main, "_ocr_sync", return_value="테스트 결과\n둘째 줄"):
        res = client.post(
            "/api/ocr",
            params={"lang": "kor+eng"},
            files={"file": ("sample.png", PNG_HEADER, "image/png")},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "테스트 결과\n둘째 줄"
    assert body["filename"] == "sample.png"
    assert body["char_count"] == len("테스트 결과\n둘째 줄")
    assert body["line_count"] == 2
    assert isinstance(body["duration_ms"], int)


def test_ocr_timeout_returns_504():
    async def fake_wait_for(fut, timeout):
        if hasattr(fut, "cancel"):
            fut.cancel()
        raise asyncio.TimeoutError

    with patch("main.asyncio.wait_for", side_effect=fake_wait_for):
        res = client.post(
            "/api/ocr",
            params={"lang": "kor"},
            files={"file": ("sample.png", PNG_HEADER, "image/png")},
        )
    assert res.status_code == 504


def test_ocr_container_error_returns_400():
    err = docker.errors.ContainerError(
        container=None,
        exit_status=1,
        command="tesseract",
        image="ocr-engine:latest",
        stderr=b"tesseract failed",
    )
    with patch.object(main, "_ocr_sync", side_effect=err):
        res = client.post(
            "/api/ocr?lang=eng",
            files={"file": ("sample.png", PNG_HEADER, "image/png")},
        )
    assert res.status_code == 400
    assert "tesseract failed" in res.json()["detail"]


def test_ocr_unexpected_error_returns_502():
    with patch.object(main, "_ocr_sync", side_effect=RuntimeError("docker daemon down")):
        res = client.post(
            "/api/ocr?lang=eng",
            files={"file": ("sample.png", PNG_HEADER, "image/png")},
        )
    assert res.status_code == 502
