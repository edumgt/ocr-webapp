"""
Docker Desktop 스타일 컨테이너 모니터 서버 (포트 8099)
Playwright가 이 페이지를 열고 스크린샷을 찍습니다.
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import docker as docker_sdk
import uvicorn

app = FastAPI()
_client = docker_sdk.DockerClient(base_url="unix:///var/run/docker.sock")


@app.get("/api/containers")
def get_containers():
    try:
        containers = _client.containers.list(filters={"ancestor": "ocr-engine:latest"})
        return {
            "count": len(containers),
            "containers": [
                {
                    "id":      c.short_id,
                    "name":    c.name,
                    "status":  c.status,
                    "image":   "ocr-engine:latest",
                }
                for c in containers
            ],
        }
    except Exception as e:
        return {"count": 0, "containers": [], "error": str(e)}


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Docker Desktop - Containers</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #1a1d21;
    color: #d4d4d4;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    height: 100vh;
    overflow: hidden;
  }

  /* ── 상단 타이틀바 ── */
  .titlebar {
    background: #13161a;
    padding: 0 16px;
    height: 40px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid #2d2f33;
    gap: 12px;
    user-select: none;
  }
  .titlebar .logo { color: #1d8fdb; font-size: 18px; font-weight: 700; letter-spacing: -0.5px; }
  .titlebar .sep { color: #3a3d42; }
  .titlebar .page-title { color: #8b949e; font-size: 12px; }

  /* ── 사이드바 ── */
  .layout { display: flex; height: calc(100vh - 40px); }
  .sidebar {
    width: 180px;
    background: #13161a;
    border-right: 1px solid #2d2f33;
    padding: 8px 0;
    flex-shrink: 0;
  }
  .sidebar-item {
    padding: 8px 16px;
    color: #8b949e;
    cursor: default;
    border-radius: 4px;
    margin: 1px 4px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }
  .sidebar-item.active {
    background: #1f2329;
    color: #e6edf3;
  }
  .sidebar-item .icon { font-size: 14px; opacity: 0.8; }

  /* ── 메인 콘텐츠 ── */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── 툴바 ── */
  .toolbar {
    background: #1a1d21;
    padding: 10px 20px;
    border-bottom: 1px solid #2d2f33;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .search-box {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 10px 5px 28px;
    color: #8b949e;
    font-size: 12px;
    width: 220px;
    position: relative;
  }
  .search-wrap { position: relative; display: inline-block; }
  .search-icon { position: absolute; left: 8px; top: 50%; transform: translateY(-50%); color: #6e7681; font-size: 12px; }
  .toggle-label { color: #8b949e; font-size: 12px; display: flex; align-items: center; gap: 6px; }
  .toggle {
    width: 32px; height: 16px;
    background: #1d8fdb;
    border-radius: 8px;
    position: relative;
    cursor: default;
  }
  .toggle::after {
    content: '';
    position: absolute;
    width: 12px; height: 12px;
    background: white;
    border-radius: 50%;
    top: 2px; left: 18px;
  }

  /* ── 컨테이너 테이블 ── */
  .table-header {
    display: grid;
    grid-template-columns: 32px 180px 1fr 120px 80px 80px;
    padding: 6px 20px;
    border-bottom: 1px solid #2d2f33;
    background: #13161a;
  }
  .table-header span { color: #6e7681; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

  .container-list { overflow-y: auto; flex: 1; }

  .container-row {
    display: grid;
    grid-template-columns: 32px 180px 1fr 120px 80px 80px;
    padding: 8px 20px;
    border-bottom: 1px solid #1f2329;
    align-items: center;
    animation: slideIn 0.25s ease;
    transition: background 0.15s;
  }
  .container-row:hover { background: #1f2329; }

  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-8px); }
    to   { opacity: 1; transform: translateX(0); }
  }

  .status-dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    background: #2ea043;
    box-shadow: 0 0 6px #2ea04388;
    animation: pulse 2s infinite;
    margin: auto;
  }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 4px #2ea04388; }
    50%       { box-shadow: 0 0 10px #2ea043cc; }
  }

  .container-name { color: #58a6ff; font-size: 12px; font-weight: 500; }
  .container-image { color: #8b949e; font-size: 11px; }
  .container-id { color: #6e7681; font-size: 11px; font-family: monospace; }
  .container-status { color: #2ea043; font-size: 11px; }
  .container-action {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    color: #c9d1d9;
    padding: 3px 8px;
    font-size: 11px;
    cursor: default;
  }

  /* ── 하단 상태바 ── */
  .statusbar {
    background: #13161a;
    border-top: 1px solid #2d2f33;
    padding: 6px 20px;
    display: flex;
    align-items: center;
    gap: 24px;
    font-size: 11px;
    color: #6e7681;
    flex-shrink: 0;
  }
  .stat-val { color: #2ea043; font-weight: 600; }
  .stat-val.warn { color: #f0883e; }

  /* ── 빈 상태 ── */
  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #3d444d;
    gap: 8px;
  }
  .empty-state .icon { font-size: 40px; opacity: 0.4; }
  .empty-state .msg { font-size: 14px; }

  /* ── 카운트 배지 ── */
  .count-badge {
    background: #1d8fdb22;
    border: 1px solid #1d8fdb44;
    color: #58a6ff;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    margin-left: auto;
    transition: all 0.3s;
  }
  .count-badge.active { background: #2ea04322; border-color: #2ea04344; color: #3fb950; }
</style>
</head>
<body>

<!-- 타이틀바 -->
<div class="titlebar">
  <span class="logo">Docker Desktop</span>
  <span class="sep">|</span>
  <span class="page-title">Containers</span>
  <span id="badge" class="count-badge">0 running</span>
</div>

<div class="layout">
  <!-- 사이드바 -->
  <div class="sidebar">
    <div class="sidebar-item active"><span class="icon">🗂</span> Containers</div>
    <div class="sidebar-item"><span class="icon">🖼</span> Images</div>
    <div class="sidebar-item"><span class="icon">📦</span> Volumes</div>
    <div class="sidebar-item"><span class="icon">🌐</span> Networks</div>
    <div style="height:1px;background:#2d2f33;margin:8px 12px;"></div>
    <div class="sidebar-item"><span class="icon">⚙️</span> Settings</div>
  </div>

  <!-- 메인 -->
  <div class="main">
    <!-- 툴바 -->
    <div class="toolbar">
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <div class="search-box">Search</div>
      </div>
      <div class="toggle-label">
        <div class="toggle"></div>
        Only running
      </div>
    </div>

    <!-- 테이블 헤더 -->
    <div class="table-header">
      <span></span>
      <span>Name</span>
      <span>Image</span>
      <span>Container ID</span>
      <span>Status</span>
      <span>Actions</span>
    </div>

    <!-- 컨테이너 목록 -->
    <div class="container-list" id="list"></div>

    <!-- 상태바 -->
    <div class="statusbar">
      <span>CPU <span id="cpu" class="stat-val">0%</span></span>
      <span>Memory <span id="mem" class="stat-val">0 MB</span></span>
      <span>OCR Containers <span id="cnt" class="stat-val">0</span></span>
      <span id="ts" style="margin-left:auto;"></span>
    </div>
  </div>
</div>

<script>
  let prevIds = new Set();
  let cpuBase = 0.2, memBase = 68;

  async function refresh() {
    try {
      const res  = await fetch('/api/containers');
      const data = await res.json();
      const containers = data.containers || [];
      const count = containers.length;

      // 배지
      const badge = document.getElementById('badge');
      badge.textContent = count + ' running';
      badge.className = 'count-badge' + (count > 0 ? ' active' : '');

      // 카운트
      document.getElementById('cnt').textContent = count;

      // CPU/메모리 (실감나게 시뮬레이션)
      const cpuLoad = cpuBase + count * (2.5 + Math.random() * 2);
      const memLoad = memBase + count * (18 + Math.random() * 5);
      document.getElementById('cpu').textContent = cpuLoad.toFixed(1) + '%';
      document.getElementById('cpu').className = 'stat-val' + (cpuLoad > 50 ? ' warn' : '');
      document.getElementById('mem').textContent = memLoad.toFixed(0) + ' MB';
      document.getElementById('mem').className = 'stat-val' + (memLoad > 300 ? ' warn' : '');

      // 타임스탬프
      document.getElementById('ts').textContent = new Date().toLocaleTimeString('ko-KR');

      // 목록 렌더
      const list = document.getElementById('list');
      if (containers.length === 0) {
        list.innerHTML = '<div class="empty-state"><div class="icon">📦</div><div class="msg">No running containers</div><div style="font-size:11px">OCR containers will appear here during requests</div></div>';
      } else {
        const curIds = new Set(containers.map(c => c.id));
        list.innerHTML = containers.map(c => `
          <div class="container-row">
            <div><div class="status-dot"></div></div>
            <div class="container-name">ocr-engine-${c.id}</div>
            <div class="container-image">${c.image}</div>
            <div class="container-id">${c.id}</div>
            <div class="container-status">● running</div>
            <div><button class="container-action">■ Stop</button></div>
          </div>`).join('');
        prevIds = curIds;
      }
    } catch(e) {}
  }

  refresh();
  setInterval(refresh, 250);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return DASHBOARD_HTML


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8099, log_level="error")
