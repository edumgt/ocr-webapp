#!/usr/bin/env python3
"""
OCR 엔진 동시 부하 테스트 - 실시간 시각화 대시보드
  실행: python3 test_visual.py
"""
import asyncio
import io
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

import httpx
from PIL import Image, ImageDraw, ImageFont
from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ── 설정 ─────────────────────────────────────────────────────────────────────
BACKEND_URL     = "http://localhost:8000/api/ocr"
NUM_USERS       = 100
LANG            = "kor+eng"
SAMPLE_INTERVAL = 0.2

def make_text(uid: int) -> str:
    samples = [
        f"안녕하세요! OCR 동시성 테스트입니다.\nUser {uid:03d} - Hello World",
        f"파이썬 비동기 처리 검증 테스트\nAsyncio concurrent test User {uid:03d}",
        f"도커 온디맨드 컨테이너 실행 확인\nDocker on-demand container User {uid:03d}",
        f"OCR 엔진 동시 인스턴스 실행 중\n100 engines running at once User {uid:03d}",
        f"자원 효율화 부하 테스트 진행 중\nResource optimization test User {uid:03d}",
        f"Tesseract OCR 한국어 인식 테스트\nKorean recognition test User {uid:03d}",
        f"컨테이너는 처리 후 자동 소멸됩니다\nContainer auto-removed User {uid:03d}",
        f"FastAPI 게이트웨이 부하 테스트\nFastAPI gateway load test User {uid:03d}",
        f"100명 동시 요청 처리 성능 측정\n100 concurrent requests User {uid:03d}",
        f"OCR 웹앱 스트레스 테스트 완료\nOCR webapp stress test User {uid:03d}",
    ]
    return samples[(uid - 1) % len(samples)]


# ── 공유 상태 ──────────────────────────────────────────────────────────────────
@dataclass
class UserState:
    user_id: int
    status: str   = "대기"   # 대기 | 전송중 | 완료 | 실패
    elapsed: float = 0.0
    preview: str  = ""

@dataclass
class AppState:
    users: list       = field(default_factory=list)
    history: list     = field(default_factory=list)
    current: int      = 0
    peak: int         = 0
    done: int         = 0
    failed: int       = 0
    wall_start: float = 0.0
    _lock: Lock       = field(default_factory=Lock)

    def record(self, n: int):
        with self._lock:
            self.current = n
            self.history.append((time.perf_counter() - self.wall_start, n))
            if n > self.peak:
                self.peak = n

    def complete(self, uid: int, ok: bool, elapsed: float, preview: str = ""):
        with self._lock:
            u = self.users[uid - 1]
            u.status  = "완료" if ok else "실패"
            u.elapsed = elapsed
            u.preview = preview
            if ok:   self.done   += 1
            else:    self.failed += 1


# ── 유틸 ─────────────────────────────────────────────────────────────────────
def make_image(text: str, uid: int) -> bytes:
    img  = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font = font_s = ImageFont.load_default()
    draw.multiline_text((20, 25), text, fill=(20, 20, 20), font=font, spacing=10)
    draw.rectangle([0, 0, 599, 199], outline=(80, 120, 200), width=3)
    draw.text((20, 175),
              f"[USER-{uid:03d}]  {datetime.now().strftime('%H:%M:%S.%f')[:-3]}",
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


# ── 대시보드 렌더 ─────────────────────────────────────────────────────────────
SPARK = " ▁▂▃▄▅▆▇█"

def _spark_char(v: int, mx: int) -> str:
    if mx == 0: return SPARK[0]
    return SPARK[round((v / mx) * (len(SPARK) - 1))]

def render(state: AppState) -> Layout:
    elapsed = time.perf_counter() - state.wall_start if state.wall_start else 0
    n       = state.current
    mx      = max(state.peak, 1)

    # ── 헤더: 게이지 바 ───────────────────────────────────────────────────────
    col  = "bright_green" if n == NUM_USERS else ("yellow" if n > 0 else "white")
    pct  = n / NUM_USERS
    BLEN = 50
    filled = int(pct * BLEN)
    bar  = Text()
    bar.append("  컨테이너  [", style="dim white")
    bar.append("█" * filled,           style=col)
    bar.append("░" * (BLEN - filled),  style="dim")
    bar.append("]  ", style="dim white")
    bar.append(f"{n:3d}/{NUM_USERS}  ", style=f"bold {col}")
    bar.append(f"최대 {state.peak}개  │  "
               f"경과 {elapsed:.1f}s  │  "
               f"완료 {state.done}  실패 {state.failed}  "
               f"진행중 {n}", style="cyan")

    # ── 10×10 컨테이너 격자 ───────────────────────────────────────────────────
    COLS = 10
    ROWS = NUM_USERS // COLS

    dot_grid = Table.grid(padding=(0, 0), expand=False)
    for _ in range(COLS):
        dot_grid.add_column(justify="center", min_width=3)

    status_dot = {
        "완료":  ("●", "bold green"),
        "실패":  ("●", "bold red"),
        "전송중":("●", "bold yellow"),
        "대기":  ("○", "dim white"),
    }
    for row in range(ROWS):
        cells = []
        for col in range(COLS):
            uid = row * COLS + col + 1
            u   = state.users[uid - 1]
            dot, style = status_dot.get(u.status, ("○", "dim white"))
            cells.append(Text(dot, style=style))
        dot_grid.add_row(*cells)

    # 범례
    legend = Text("  ○대기  ", style="dim white")
    legend.append("●전송중  ", style="bold yellow")
    legend.append("●완료  ",   style="bold green")
    legend.append("●실패",     style="bold red")

    # ── 그래프 ────────────────────────────────────────────────────────────────
    GRAPH_W = 55
    pts  = [v for _, v in state.history]
    if len(pts) > GRAPH_W:
        step = len(pts) / GRAPH_W
        pts  = [pts[int(i * step)] for i in range(GRAPH_W)]

    levels = [NUM_USERS, NUM_USERS * 3 // 4, NUM_USERS // 2, NUM_USERS // 4, 1, 0]
    graph  = Text()
    graph.append("증감 추이\n\n", style="bold white")
    for lv in levels:
        graph.append(f"{lv:3d}│", style="dim white")
        for v in pts:
            if v > lv:
                graph.append("█", style="bright_cyan")
            elif v >= lv and lv > 0:
                graph.append("▄", style="cyan")
            else:
                graph.append(" ")
        graph.append("\n")
    graph.append("   └" + "─" * len(pts) + "▶\n", style="dim white")
    spark = "".join(_spark_char(v, mx) for v in pts)
    graph.append(f"   [{spark}]\n", style="dim cyan")
    graph.append(f"   샘플 {len(state.history)}개  ·  {SAMPLE_INTERVAL}s 간격", style="dim")

    # ── 통계 ──────────────────────────────────────────────────────────────────
    done_users  = [u for u in state.users if u.status == "완료"]
    times       = [u.elapsed for u in done_users]
    stats = Text()
    stats.append(f"  완료: {state.done:3d}   실패: {state.failed:3d}   "
                 f"진행중: {n:3d}   대기: {NUM_USERS - state.done - state.failed - n:3d}\n\n",
                 style="bold white")
    if times:
        stats.append(f"  처리시간  최소 {min(times):.2f}s  "
                     f"최대 {max(times):.2f}s  "
                     f"평균 {sum(times)/len(times):.2f}s\n", style="green")
    stats.append(f"  wall time: {elapsed:.1f}s  │  최대 동시 컨테이너: {state.peak}개",
                 style="cyan")

    # ── 레이아웃 조립 ─────────────────────────────────────────────────────────
    layout = Layout()
    layout.split_column(
        Layout(Panel(bar,
                     title="[bold cyan]⚡ OCR ENGINE  100명 동시 부하 테스트[/bold cyan]",
                     border_style="cyan"), size=3, name="hdr"),
        Layout(name="mid", size=16),
        Layout(name="bot"),
    )
    layout["mid"].split_row(
        Layout(Panel(
                   Layout(dot_grid, name="dots"),
                   title=f"[yellow]컨테이너 격자  {ROWS}×{COLS}[/yellow]",
                   border_style="yellow",
                   subtitle=str(legend),
               ), ratio=2, name="grid"),
        Layout(Panel(graph,
                     title="[bright_blue]증감 추이 그래프[/bright_blue]",
                     border_style="blue"), ratio=3, name="graph"),
    )
    layout["bot"].update(Panel(stats,
                               title="[green]통계[/green]",
                               border_style="green"))
    return layout


# ── 비동기 ────────────────────────────────────────────────────────────────────
async def monitor_loop(state: AppState, stop: asyncio.Event):
    while not stop.is_set():
        state.record(count_containers())
        await asyncio.sleep(SAMPLE_INTERVAL)


async def send(client: httpx.AsyncClient, uid: int, img: bytes, state: AppState):
    state.users[uid - 1].status = "전송중"
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            BACKEND_URL, params={"lang": LANG},
            files={"file": (f"user{uid:03d}.png", img, "image/png")},
            timeout=180.0,
        )
        elapsed = time.perf_counter() - t0
        if resp.status_code == 200:
            preview = resp.json().get("text", "")[:55].replace("\n", " ")
            state.complete(uid, True, elapsed, preview)
        else:
            state.complete(uid, False, elapsed, resp.text[:40])
    except Exception as exc:
        state.complete(uid, False, time.perf_counter() - t0, str(exc)[:40])


# ── 메인 ─────────────────────────────────────────────────────────────────────
async def main():
    console = Console()
    console.print(Panel(f"[bold cyan]{NUM_USERS}장 테스트 이미지 생성 중...[/bold cyan]",
                        title="OCR 부하 테스트"))
    images = [(i + 1, make_image(make_text(i + 1), i + 1)) for i in range(NUM_USERS)]
    total_kb = sum(len(b) for _, b in images) // 1024
    console.print(f"  [green]✓[/green] {NUM_USERS}장 생성 완료 ({total_kb} KB)\n")

    state            = AppState()
    state.users      = [UserState(i + 1) for i in range(NUM_USERS)]
    state.wall_start = time.perf_counter()
    stop             = asyncio.Event()

    with Live(render(state), console=console, refresh_per_second=10, screen=True) as live:

        async def refresh():
            while not stop.is_set():
                live.update(render(state))
                await asyncio.sleep(0.1)

        mon = asyncio.create_task(monitor_loop(state, stop))
        ref = asyncio.create_task(refresh())

        async with httpx.AsyncClient() as client:
            await asyncio.gather(*[send(client, uid, img, state) for uid, img in images])

        await asyncio.sleep(2.0)   # 컨테이너 소멸 확인
        stop.set()
        await asyncio.gather(mon, ref)
        live.update(render(state))

    # ── 최종 요약 ─────────────────────────────────────────────────────────────
    wall      = time.perf_counter() - state.wall_start
    ok_users  = [u for u in state.users if u.status == "완료"]
    times     = [u.elapsed for u in ok_users]

    # 타임라인 리플레이
    console.rule("[bold cyan]증감 타임라인 리플레이[/bold cyan]")
    last_v = -1
    for ts, v in state.history:
        if v != last_v:
            pct    = v / NUM_USERS
            filled = int(pct * 40)
            bar    = "█" * filled + "░" * (40 - filled)
            col    = "bright_green" if v == NUM_USERS else ("yellow" if v > 0 else "white")
            console.print(f"  {ts:5.2f}s  [{bar}]  {v:3d}개", style=col)
            last_v = v

    console.print()
    lines = [
        f"[bold green]성공 {len(ok_users)}/{NUM_USERS}[/bold green]   [red]실패 {state.failed}[/red]",
        f"최대 동시 컨테이너: [bold cyan]{state.peak}개[/bold cyan]",
        f"처리시간  최소 [yellow]{min(times):.2f}s[/yellow]  최대 [yellow]{max(times):.2f}s[/yellow]  평균 [yellow]{sum(times)/len(times):.2f}s[/yellow]" if times else "",
        f"전체 wall time: [yellow]{wall:.2f}s[/yellow]",
        f"잔여 컨테이너: [bright_green]{count_containers()}개[/bright_green]",
    ]
    console.print(Panel("\n".join(l for l in lines if l),
                        title="[bold]최종 결과[/bold]",
                        border_style="bright_cyan"))


if __name__ == "__main__":
    asyncio.run(main())
