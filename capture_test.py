#!/usr/bin/env python3
"""
20명 동시 OCR 부하 테스트 + Playwright 스크린샷 캡처
실행: python3 capture_test.py
결과: captures/ 디렉터리에 PNG 저장
"""
import asyncio
import io
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

# ── 설정 ─────────────────────────────────────────────────────────────────────
BACKEND_URL  = "http://localhost:8000/api/ocr"
MONITOR_URL  = "http://127.0.0.1:8099"
NUM_USERS    = 20
LANG         = "kor+eng"
CAPTURE_DIR  = Path("captures")
CAPTURE_INT  = 0.6   # 스크린샷 간격 (초)

TEXTS = [
    f"안녕하세요! OCR 부하 테스트입니다.\nUser {i:02d} - Hello World Docker"
    for i in range(1, NUM_USERS + 1)
]


# ── 이미지 생성 ───────────────────────────────────────────────────────────────
def make_image(text: str, uid: int) -> bytes:
    img  = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font = font_s = ImageFont.load_default()
    draw.multiline_text((20, 30), text, fill=(20, 20, 20), font=font, spacing=12)
    draw.rectangle([0, 0, 599, 199], outline=(80, 120, 200), width=3)
    draw.text((20, 175), f"[USER-{uid:02d}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]}",
              fill=(160, 30, 30), font=font_s)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def count_containers() -> int:
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--filter", "ancestor=ocr-engine:latest", "--format", "{{.ID}}"],
            text=True, stderr=subprocess.DEVNULL,
        )
        return len([l for l in out.strip().splitlines() if l])
    except Exception:
        return 0


# ── OCR 요청 ─────────────────────────────────────────────────────────────────
results: dict = {}

async def send(client: httpx.AsyncClient, uid: int, img: bytes):
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            BACKEND_URL, params={"lang": LANG},
            files={"file": (f"user{uid:02d}.png", img, "image/png")},
            timeout=120.0,
        )
        elapsed = time.perf_counter() - t0
        ok = resp.status_code == 200
        results[uid] = {"ok": ok, "elapsed": elapsed,
                        "preview": resp.json().get("text", "")[:40].replace("\n", " ") if ok else resp.text[:40]}
    except Exception as exc:
        results[uid] = {"ok": False, "elapsed": time.perf_counter() - t0, "preview": str(exc)[:40]}


# ── 메인 ─────────────────────────────────────────────────────────────────────
async def main():
    CAPTURE_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print(f"  OCR 20명 동시 테스트 + Playwright 캡처")
    print("=" * 60)

    # 모니터 서버 시작
    print("[1] 모니터 서버 시작 (port 8099)...")
    subprocess.run(["fuser", "-k", "8099/tcp"], capture_output=True)
    await asyncio.sleep(0.5)
    server = subprocess.Popen(
        [sys.executable, "monitor_server.py"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # 서버 준비 대기
    for _ in range(20):
        await asyncio.sleep(0.5)
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{MONITOR_URL}/api/containers", timeout=1.0)
                if r.status_code == 200:
                    print("    서버 준비 완료")
                    break
        except Exception:
            pass
    else:
        print("    서버 시작 실패")
        server.terminate()
        return

    # 이미지 생성
    print("[2] 테스트 이미지 20장 생성...")
    images = [(i + 1, make_image(TEXTS[i], i + 1)) for i in range(NUM_USERS)]
    print(f"    완료: {sum(len(b) for _, b in images) // 1024} KB")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 780})
        await page.goto(MONITOR_URL, wait_until="domcontentloaded", timeout=15000)
        print("[3] 브라우저 열림:", MONITOR_URL)

        # 초기 상태 캡처 (0개)
        shot_idx = 0
        async def capture(label: str = ""):
            nonlocal shot_idx
            fname = CAPTURE_DIR / f"capture_{shot_idx:02d}_{label}.png"
            await page.screenshot(path=str(fname), full_page=False)
            n = count_containers()
            print(f"    📷 {fname.name}  (컨테이너 {n}개)")
            shot_idx += 1

        await capture("00_before")

        print("[4] 20개 요청 동시 발송 시작...")
        wall_start = time.perf_counter()

        # 부하 테스트 비동기 실행
        async with httpx.AsyncClient() as client:
            async def run_all():
                await asyncio.gather(*[send(client, uid, img) for uid, img in images])
            test_task = asyncio.create_task(run_all())

            # 테스트 진행 중 주기적 캡처
            prev_n = -1
            while not test_task.done():
                n = count_containers()
                label = f"n{n:02d}"
                # 컨테이너 수가 바뀌거나 일정 간격마다 캡처
                if n != prev_n or shot_idx % 3 == 0:
                    await capture(label)
                    prev_n = n
                await asyncio.sleep(CAPTURE_INT)

            await test_task

        # 완료 직후 + 소멸 후 캡처
        await asyncio.sleep(0.5)
        await capture("after_done")
        await asyncio.sleep(2.0)
        await capture("99_after_cleanup")

        wall = time.perf_counter() - wall_start
        await browser.close()

    server.terminate()

    # 결과 요약
    ok_list = [r for r in results.values() if r["ok"]]
    fail_list = [r for r in results.values() if not r["ok"]]
    times = [r["elapsed"] for r in ok_list]

    print()
    print("=" * 60)
    print(f"  캡처 저장: {CAPTURE_DIR}/  ({shot_idx}장)")
    print(f"  성공: {len(ok_list)}/{NUM_USERS}  실패: {len(fail_list)}")
    if times:
        print(f"  처리시간  최소 {min(times):.2f}s  최대 {max(times):.2f}s  평균 {sum(times)/len(times):.2f}s")
    print(f"  wall time: {wall:.2f}s")
    print("=" * 60)

    # 캡처 이미지를 세로로 이어붙인 리포트 생성
    print("\n[5] 타임라인 합성 이미지 생성...")
    shots = sorted(CAPTURE_DIR.glob("capture_*.png"))
    if shots:
        frames = [Image.open(s) for s in shots]
        w = max(f.width for f in frames)
        total_h = sum(f.height for f in frames) + (len(frames) - 1) * 4
        report = Image.new("RGB", (w, total_h), color=(20, 20, 25))
        y = 0
        for frame in frames:
            report.paste(frame, (0, y))
            y += frame.height + 4
        report_path = CAPTURE_DIR / "timeline_report.png"
        report.save(report_path)
        print(f"    저장: {report_path}  ({w}×{total_h}px)")

    print("\n완료!")


if __name__ == "__main__":
    asyncio.run(main())
