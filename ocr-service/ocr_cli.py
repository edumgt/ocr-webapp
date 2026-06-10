#!/usr/bin/env python3
"""
Usage: python3 ocr_cli.py <lang> <filepath>
  lang     : kor | eng | kor+eng | eng+kor
  filepath : 처리할 이미지 파일 경로
"""
import sys
import subprocess
from pathlib import Path

SUPPORTED = ("kor", "eng", "kor+eng", "eng+kor")

lang = sys.argv[1] if len(sys.argv) > 1 else "kor+eng"
filepath = sys.argv[2] if len(sys.argv) > 2 else None

if lang not in SUPPORTED:
    sys.stderr.write(f"지원하지 않는 lang입니다. 지원값: {', '.join(SUPPORTED)}\n")
    sys.exit(1)

if not filepath:
    sys.stderr.write("파일 경로가 필요합니다.\n")
    sys.exit(1)

img_path = Path(filepath)
if not img_path.exists():
    sys.stderr.write(f"파일을 찾을 수 없습니다: {filepath}\n")
    sys.exit(1)

try:
    result = subprocess.run(
        ["tesseract", str(img_path), "stdout", "-l", lang],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    sys.stdout.write(result.stdout)
except subprocess.CalledProcessError as exc:
    sys.stderr.write(exc.stderr.strip() or "OCR 실패\n")
    sys.exit(1)
except subprocess.TimeoutExpired:
    sys.stderr.write("OCR 처리 시간이 초과되었습니다.\n")
    sys.exit(2)
