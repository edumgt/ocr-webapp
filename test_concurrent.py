#!/usr/bin/env python3
"""
10명 동시 접속 OCR 부하 테스트
- 10개의 텍스트 이미지 자동 생성
- 동시에 /api/ocr 요청 발송
- 실행 중인 ocr-engine 컨테이너 수 실시간 모니터링
"""
import asyncio
import io
import subprocess
import time
from datetime import datetime

import httpx
from PIL import Image, ImageDraw, ImageFont

BACKEND_URL = "http://localhost:8000/api/ocr"
NUM_USERS = 10
LANG = "kor+eng"

TEXTS = [
    "안녕하세요! OCR 동시성 테스트입니다.\nUser 1 - Hello World",
    "파이썬 비동기 처리 테스트\nAsyncio concurrent test User 2",
    "도커 온디맨드 컨테이너 실행 확인\nDocker on-demand container User 3",
    "동시에 10개의 OCR 엔진이 실행됩니다\nTen engines running at once User 4",
    "자원 효율화 테스트 진행 중\nResource optimization test User 5",
    "Tesseract OCR 한국어 인식 테스트\nKorean recognition test User 6",
    "컨테이너는 처리 후 자동 소멸됩니다\nContainer auto-removed User 7",
    "FastAPI 게이트웨이 부하 테스트\nFastAPI gateway load test User 8",
    "10명 동시 요청 처리 성능 측정\n10 concurrent requests User 9",
    "OCR 웹앱 스트레스 테스트 완료\nOCR webapp stress test User 10",
]


def make_image(text: str, user_id: int) -> bytes:
    """텍스트가 담긴 PNG 이미지를 생성하여 bytes로 반환"""
    img = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    draw.multiline_text((20, 30), text, fill=(20, 20, 20), font=font, spacing=12)
    draw.rectangle([0, 0, 599, 199], outline=(100, 100, 200), width=3)
    draw.text((20, 170), f"[USER-{user_id:02d}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]}", fill=(150, 0, 0), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def count_ocr_containers() -> int:
    """현재 실행 중인 ocr-engine 컨테이너 수 반환"""
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--filter", "ancestor=ocr-engine:latest", "--format", "{{.ID}}"],
            text=True,
        )
        return len([l for l in out.strip().splitlines() if l])
    except Exception:
        return -1


async def monitor_containers(stop_event: asyncio.Event):
    """테스트 중 컨테이너 수를 0.3초마다 출력"""
    max_seen = 0
    while not stop_event.is_set():
        n = count_ocr_containers()
        if n > max_seen:
            max_seen = n
        bar = "█" * n + "░" * (NUM_USERS - max(n, 0))
        print(f"\r  [모니터] 실행 중 ocr-engine: {n:2d}개  최대: {max_seen:2d}개  [{bar}]", end="", flush=True)
        await asyncio.sleep(0.3)
    print()  # 줄바꿈


async def send_request(client: httpx.AsyncClient, user_id: int, image_bytes: bytes) -> dict:
    """단일 OCR 요청 전송"""
    start = time.perf_counter()
    try:
        resp = await client.post(
            BACKEND_URL,
            params={"lang": LANG},
            files={"file": (f"user{user_id:02d}.png", image_bytes, "image/png")},
            timeout=90.0,
        )
        elapsed = time.perf_counter() - start
        if resp.status_code == 200:
            data = resp.json()
            preview = data.get("text", "")[:40].replace("\n", " ")
            return {"user": user_id, "ok": True, "elapsed": elapsed, "preview": preview}
        else:
            return {"user": user_id, "ok": False, "elapsed": elapsed, "error": resp.text[:80]}
    except Exception as exc:
        return {"user": user_id, "ok": False, "elapsed": time.perf_counter() - start, "error": str(exc)}


async def main():
    print("=" * 60)
    print(f"  OCR 동시 10명 부하 테스트")
    print(f"  대상: {BACKEND_URL}")
    print(f"  언어: {LANG}  |  요청 수: {NUM_USERS}")
    print("=" * 60)

    print("\n[1] 테스트 이미지 10장 생성 중...")
    images = [(i + 1, make_image(TEXTS[i], i + 1)) for i in range(NUM_USERS)]
    print(f"    완료: {sum(len(b) for _, b in images) // 1024} KB 총 생성")

    print("\n[2] 10개 요청 동시 발송 시작...\n")
    stop_event = asyncio.Event()

    async with httpx.AsyncClient() as client:
        monitor_task = asyncio.create_task(monitor_containers(stop_event))
        wall_start = time.perf_counter()

        tasks = [send_request(client, uid, img) for uid, img in images]
        results = await asyncio.gather(*tasks)

        wall_elapsed = time.perf_counter() - wall_start
        stop_event.set()
        await monitor_task

    print("\n[3] 결과 요약")
    print("-" * 60)
    ok = [r for r in results if r["ok"]]
    fail = [r for r in results if not r["ok"]]

    for r in sorted(results, key=lambda x: x["user"]):
        if r["ok"]:
            print(f"  USER-{r['user']:02d}  ✓  {r['elapsed']:.2f}s  →  \"{r['preview']}...\"")
        else:
            print(f"  USER-{r['user']:02d}  ✗  {r['elapsed']:.2f}s  →  ERROR: {r.get('error','')}")

    print("-" * 60)
    if ok:
        times = [r["elapsed"] for r in ok]
        print(f"  성공: {len(ok)}/{NUM_USERS}  |  실패: {len(fail)}/{NUM_USERS}")
        print(f"  개별 최소: {min(times):.2f}s  최대: {max(times):.2f}s  평균: {sum(times)/len(times):.2f}s")
    print(f"  전체 소요 (wall time): {wall_elapsed:.2f}s")
    print(f"\n  ※ ocr-engine 컨테이너는 처리 후 전부 --rm 자동 소멸됨")
    remaining = count_ocr_containers()
    print(f"  ※ 테스트 종료 후 잔여 컨테이너: {remaining}개")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
