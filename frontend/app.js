// ── 엘리먼트 참조 ─────────────────────────────────────────────
const fileInput    = document.getElementById('file-input');
const dropZone     = document.getElementById('drop-zone');
const fileBadge    = document.getElementById('file-badge');
const fileNameEl   = document.getElementById('file-name');
const fileSizeEl   = document.getElementById('file-size');
const ocrBtn       = document.getElementById('ocr-btn');
const btnText      = document.getElementById('btn-text');
const btnSpinner   = document.getElementById('btn-spinner');
const copyBtn      = document.getElementById('copy-btn');
const resultEl     = document.getElementById('result');
const resultMeta   = document.getElementById('result-meta');
const langDisplay  = document.getElementById('lang-display');
const overlay      = document.getElementById('overlay');

// 오프캔버스
const ocSettings   = document.getElementById('oc-settings');
const ocHelp       = document.getElementById('oc-help');
const backendInput = document.getElementById('backend-url-input');
const langGroup    = document.getElementById('lang-group');
const langBtns     = langGroup.querySelectorAll('.lang-btn');

// ── 상태 ─────────────────────────────────────────────────────
let currentLang = 'kor+eng';
let currentFile = null;

const LANG_LABELS = { 'kor+eng': '한국어 + 영어', kor: '한국어만', eng: '영어만' };

// ── 오프캔버스 헬퍼 ──────────────────────────────────────────
let activeOc = null;

function openOc(el) {
  if (activeOc && activeOc !== el) closeOc(activeOc);
  el.classList.add('open');
  overlay.classList.add('open');
  activeOc = el;
  el.querySelector('.oc-close')?.focus();
}

function closeOc(el) {
  el?.classList.remove('open');
  overlay.classList.remove('open');
  activeOc = null;
}

document.getElementById('btn-settings').addEventListener('click', () => openOc(ocSettings));
document.getElementById('btn-help').addEventListener('click',     () => openOc(ocHelp));
overlay.addEventListener('click', () => closeOc(activeOc));
document.querySelectorAll('.oc-close').forEach((btn) => {
  btn.addEventListener('click', () => closeOc(activeOc));
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeOc(activeOc); });

// 언어 선택
langBtns.forEach((btn) => {
  btn.addEventListener('click', () => {
    langBtns.forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    currentLang = btn.dataset.lang;
  });
});

// 설정 저장
document.getElementById('oc-save').addEventListener('click', () => {
  langDisplay.textContent = LANG_LABELS[currentLang] ?? currentLang;
  closeOc(activeOc);
});

// ── 파일 업로드 ──────────────────────────────────────────────
function formatSize(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function applyFile(file) {
  if (!file) return;
  currentFile          = file;
  fileNameEl.textContent = file.name;
  fileSizeEl.textContent = formatSize(file.size);
  fileBadge.classList.remove('hidden');
  ocrBtn.disabled = false;
}

dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => applyFile(fileInput.files?.[0]));

dropZone.addEventListener('dragover',  (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', ()  => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files?.[0];
  if (f?.type.startsWith('image/')) applyFile(f);
});

// ── OCR 실행 ─────────────────────────────────────────────────
ocrBtn.addEventListener('click', async () => {
  if (!currentFile) return;
  const backendUrl = (backendInput.value || 'http://localhost:8000').replace(/\/+$/, '');

  ocrBtn.disabled = true;
  btnText.textContent = '처리 중...';
  btnSpinner.classList.remove('hidden');
  copyBtn.disabled = true;
  resultEl.textContent = 'OCR 처리 중입니다. 잠시 기다려 주세요.';
  resultMeta.classList.add('hidden');

  try {
    const fd = new FormData();
    fd.append('file', currentFile);
    const res = await fetch(
      `${backendUrl}/api/ocr?lang=${encodeURIComponent(currentLang)}`,
      { method: 'POST', body: fd },
    );
    const data = await res.json().catch(() => { throw new Error(`파싱 실패 (status ${res.status})`); });
    if (!res.ok) throw new Error(data.detail || '요청 실패');

    resultEl.textContent = data.text?.trim() || '(인식된 텍스트가 없습니다.)';
    copyBtn.disabled = false;
    resultMeta.innerHTML = `
      <span>파일명: <strong>${data.filename ?? currentFile.name}</strong></span>
      <span>언어: <strong>${data.lang ?? currentLang}</strong></span>
      <span>크기: <strong>${formatSize(data.size_bytes ?? currentFile.size)}</strong></span>`;
    resultMeta.classList.remove('hidden');
  } catch (err) {
    resultEl.textContent = `오류: ${err.message}`;
    resultMeta.classList.add('hidden');
  } finally {
    ocrBtn.disabled = false;
    btnText.textContent = 'OCR 실행';
    btnSpinner.classList.add('hidden');
  }
});

// ── 복사 ─────────────────────────────────────────────────────
copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(resultEl.textContent || '');
    const prev = copyBtn.innerHTML;
    copyBtn.textContent = '복사 완료!';
    setTimeout(() => { copyBtn.innerHTML = prev; }, 1400);
  } catch (err) {
    alert(`복사 실패: ${err.message}`);
  }
});
