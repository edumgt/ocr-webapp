// ── 엘리먼트 참조 ─────────────────────────────────────────────
const fileInput       = document.getElementById('file-input');
const dropZone        = document.getElementById('drop-zone');
const dropPlaceholder = document.getElementById('drop-placeholder');
const previewWrap     = document.getElementById('preview-wrap');
const imagePreview    = document.getElementById('image-preview');
const clearFileBtn    = document.getElementById('clear-file-btn');
const fileBadge       = document.getElementById('file-badge');
const fileNameEl      = document.getElementById('file-name');
const fileSizeEl      = document.getElementById('file-size');

const ocrBtn          = document.getElementById('ocr-btn');
const btnText         = document.getElementById('btn-text');
const btnSpinner      = document.getElementById('btn-spinner');
const copyBtn         = document.getElementById('copy-btn');
const compareBtn      = document.getElementById('compare-btn');
const editBtn         = document.getElementById('edit-btn');
const downloadTxtBtn  = document.getElementById('download-txt-btn');
const downloadMdBtn   = document.getElementById('download-md-btn');

const resultWorkspace = document.getElementById('result-workspace');
const comparePane     = document.getElementById('compare-pane');
const compareImage    = document.getElementById('compare-image');
const resultEl        = document.getElementById('result');
const resultEditor    = document.getElementById('result-editor');
const resultMeta      = document.getElementById('result-meta');
const langDisplay     = document.getElementById('lang-display');
const overlay         = document.getElementById('overlay');
const toastContainer  = document.getElementById('toast-container');

// 히스토리
const historyCard     = document.getElementById('history-card');
const historyList     = document.getElementById('history-list');
const clearHistoryBtn = document.getElementById('clear-history-btn');

// AI 보완
const aiBtn           = document.getElementById('ai-btn');
const aiBtnText       = document.getElementById('ai-btn-text');
const aiBtnSpinner    = document.getElementById('ai-btn-spinner');
const originalSection = document.getElementById('original-section');
const originalResult  = document.getElementById('original-result');
const aiProviderGroup = document.getElementById('ai-provider-group');
const aiProviderBtns  = aiProviderGroup.querySelectorAll('.lang-btn');
const ollamaSettings  = document.getElementById('ollama-settings');
const openaiSettings  = document.getElementById('openai-settings');

// 오프캔버스
const ocSettings      = document.getElementById('oc-settings');
const ocHelp          = document.getElementById('oc-help');
const backendInput    = document.getElementById('backend-url-input');
const ollamaUrlInput  = document.getElementById('ollama-url-input');
const ollamaModelInput = document.getElementById('ollama-model-input');
const openaiKeyInput  = document.getElementById('openai-key-input');
const openaiModelInput = document.getElementById('openai-model-input');
const openaiUrlInput  = document.getElementById('openai-url-input');
const langGroup       = document.getElementById('lang-group');
const langBtns        = langGroup.querySelectorAll('.lang-btn');

// ── 상수 & 상태 ──────────────────────────────────────────────
const SETTINGS_KEY = 'ocr_webapp_settings_v1';
const HISTORY_KEY  = 'ocr_webapp_history_v1';
const MAX_HISTORY  = 10;
const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const LANG_LABELS  = { 'kor+eng': '한국어 + 영어', kor: '한국어만', eng: '영어만' };

let currentLang = 'kor+eng';
let currentFile = null;
let currentPreviewUrl = null;
let currentAIProvider = 'ollama';
let lastOcrText = null;
let currentFilename = 'ocr-result';
let isEditing = false;
let isComparing = false;

// ── Toast 알림 ───────────────────────────────────────────────
function showToast(message, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  toastContainer.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 220);
  }, 2400);
}

// ── 설정 영속화 ──────────────────────────────────────────────
function applyLangSelection(lang) {
  currentLang = LANG_LABELS[lang] ? lang : 'kor+eng';
  langBtns.forEach((b) => b.classList.toggle('active', b.dataset.lang === currentLang));
  langDisplay.textContent = LANG_LABELS[currentLang] ?? currentLang;
}

function applyProviderSelection(provider) {
  currentAIProvider = provider === 'openai' ? 'openai' : 'ollama';
  aiProviderBtns.forEach((b) => b.classList.toggle('active', b.dataset.provider === currentAIProvider));
  ollamaSettings.classList.toggle('hidden', currentAIProvider !== 'ollama');
  openaiSettings.classList.toggle('hidden', currentAIProvider !== 'openai');
}

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (saved.backendUrl) backendInput.value = saved.backendUrl;
    if (saved.lang) applyLangSelection(saved.lang);
    if (saved.aiProvider) applyProviderSelection(saved.aiProvider);
    if (saved.ollamaUrl) ollamaUrlInput.value = saved.ollamaUrl;
    if (saved.ollamaModel) ollamaModelInput.value = saved.ollamaModel;
    if (saved.openaiModel) openaiModelInput.value = saved.openaiModel;
    if (saved.openaiUrl) openaiUrlInput.value = saved.openaiUrl;
  } catch {
    // 손상된 설정 무시
  }
}

function saveSettings() {
  const data = {
    backendUrl: backendInput.value.trim() || 'http://localhost:8000',
    lang: currentLang,
    aiProvider: currentAIProvider,
    ollamaUrl: ollamaUrlInput.value.trim() || 'http://localhost:11434',
    ollamaModel: ollamaModelInput.value.trim() || 'llama3.2',
    openaiModel: openaiModelInput.value.trim() || 'gpt-4o-mini',
    openaiUrl: openaiUrlInput.value.trim() || 'https://api.openai.com/v1',
  };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(data));
}

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
document.getElementById('btn-help').addEventListener('click', () => openOc(ocHelp));
overlay.addEventListener('click', () => closeOc(activeOc));
document.querySelectorAll('.oc-close').forEach((btn) => {
  btn.addEventListener('click', () => closeOc(activeOc));
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeOc(activeOc); });

langBtns.forEach((btn) => {
  btn.addEventListener('click', () => applyLangSelection(btn.dataset.lang));
});

aiProviderBtns.forEach((btn) => {
  btn.addEventListener('click', () => applyProviderSelection(btn.dataset.provider));
});

document.getElementById('oc-save').addEventListener('click', () => {
  saveSettings();
  closeOc(activeOc);
  showToast('설정이 저장되었습니다.', 'success');
});

// ── 유틸 & 결과 렌더링 ───────────────────────────────────────
function formatSize(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function getActiveResultText() {
  return isEditing ? resultEditor.value : (resultEl.textContent || '');
}

function setResultActionsEnabled(enabled) {
  copyBtn.disabled = !enabled;
  aiBtn.disabled = !enabled;
  editBtn.disabled = !enabled;
  downloadTxtBtn.disabled = !enabled;
  downloadMdBtn.disabled = !enabled;
  compareBtn.disabled = !currentPreviewUrl || !enabled;
}

function renderMeta(items, aiLabel = null) {
  resultMeta.replaceChildren();
  items.forEach(([label, value]) => {
    const span = document.createElement('span');
    span.textContent = `${label}: `;
    const strong = document.createElement('strong');
    strong.textContent = String(value);
    span.appendChild(strong);
    resultMeta.appendChild(span);
  });
  if (aiLabel) {
    const badge = document.createElement('span');
    badge.className = 'ai-badge';
    const icon = document.createElement('i');
    icon.className = 'fa-solid fa-wand-magic-sparkles';
    badge.appendChild(icon);
    badge.append(` ${aiLabel} 보완됨`);
    resultMeta.appendChild(badge);
  }
  resultMeta.classList.remove('hidden');
}

// ── 파일 업로드 & 미리보기 ───────────────────────────────────
function clearFileSelection() {
  if (currentPreviewUrl) {
    URL.revokeObjectURL(currentPreviewUrl);
    currentPreviewUrl = null;
  }
  currentFile = null;
  fileInput.value = '';
  previewWrap.classList.add('hidden');
  dropPlaceholder.classList.remove('hidden');
  fileBadge.classList.add('hidden');
  ocrBtn.disabled = true;
  if (isComparing) toggleCompare(false);
  compareBtn.disabled = true;
}

function applyFile(file) {
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    showToast('이미지 파일만 업로드할 수 있습니다.', 'error');
    return;
  }
  if (file.size > MAX_SIZE_BYTES) {
    showToast('파일 크기는 10MB 이하여야 합니다.', 'error');
    return;
  }

  if (currentPreviewUrl) URL.revokeObjectURL(currentPreviewUrl);
  currentPreviewUrl = URL.createObjectURL(file);
  currentFile = file;
  currentFilename = file.name || 'clipboard-image.png';

  imagePreview.src = currentPreviewUrl;
  compareImage.src = currentPreviewUrl;
  fileNameEl.textContent = currentFilename;
  fileSizeEl.textContent = formatSize(file.size);
  fileBadge.classList.remove('hidden');
  dropPlaceholder.classList.add('hidden');
  previewWrap.classList.remove('hidden');
  ocrBtn.disabled = false;
  compareBtn.disabled = !lastOcrText;
}

dropZone.addEventListener('click', (e) => {
  if (e.target.closest('#clear-file-btn')) return;
  fileInput.click();
});
clearFileBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  clearFileSelection();
});
fileInput.addEventListener('change', () => applyFile(fileInput.files?.[0]));

dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  applyFile(e.dataTransfer.files?.[0]);
});

document.addEventListener('paste', (e) => {
  const items = e.clipboardData?.items;
  if (!items) return;
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile();
      if (file) {
        applyFile(file);
        showToast('클립보드 이미지를 불러왔습니다.', 'success');
      }
      break;
    }
  }
});

// ── 비교 & 편집 모드 ─────────────────────────────────────────
function toggleCompare(force) {
  isComparing = typeof force === 'boolean' ? force : !isComparing;
  compareBtn.classList.toggle('active', isComparing);
  comparePane.classList.toggle('hidden', !isComparing);
  resultWorkspace.classList.toggle('compare-mode', isComparing);
}

compareBtn.addEventListener('click', () => {
  if (!currentPreviewUrl) return;
  toggleCompare();
});

function setEditMode(enable) {
  isEditing = enable;
  editBtn.classList.toggle('active', isEditing);
  if (isEditing) {
    resultEditor.value = resultEl.textContent || '';
    resultEl.classList.add('hidden');
    resultEditor.classList.remove('hidden');
    resultEditor.focus();
  } else {
    const edited = resultEditor.value;
    resultEl.textContent = edited || '(인식된 텍스트가 없습니다.)';
    lastOcrText = edited.trim() || null;
    resultEditor.classList.add('hidden');
    resultEl.classList.remove('hidden');
  }
}

editBtn.addEventListener('click', () => setEditMode(!isEditing));

// ── 히스토리 관리 ────────────────────────────────────────────
function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveHistoryItem(entry) {
  const list = loadHistory().filter((item) => item.id !== entry.id);
  list.unshift(entry);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, MAX_HISTORY)));
  renderHistory();
}

function deleteHistoryItem(id) {
  const list = loadHistory().filter((item) => item.id !== id);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
  renderHistory();
}

function renderHistory() {
  const list = loadHistory();
  historyList.replaceChildren();
  if (!list.length) {
    historyCard.classList.add('hidden');
    return;
  }
  historyCard.classList.remove('hidden');

  list.forEach((item) => {
    const li = document.createElement('li');
    li.className = 'history-item';

    const main = document.createElement('div');
    main.className = 'history-main';
    const title = document.createElement('div');
    title.className = 'history-title';
    title.textContent = item.filename;
    const snippet = document.createElement('div');
    snippet.className = 'history-snippet';
    snippet.textContent = item.text.replace(/\s+/g, ' ').slice(0, 90);
    main.append(title, snippet);

    const meta = document.createElement('div');
    meta.className = 'history-meta';
    const info = document.createElement('span');
    info.textContent = `${item.lang} · ${item.time}`;
    const delBtn = document.createElement('button');
    delBtn.className = 'history-del';
    delBtn.type = 'button';
    delBtn.title = '삭제';
    const delIcon = document.createElement('i');
    delIcon.className = 'fa-solid fa-xmark';
    delBtn.appendChild(delIcon);
    delBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      deleteHistoryItem(item.id);
    });
    meta.append(info, delBtn);

    li.append(main, meta);
    li.addEventListener('click', () => {
      if (isEditing) setEditMode(false);
      lastOcrText = item.text;
      currentFilename = item.filename;
      resultEl.textContent = item.text;
      originalSection.classList.add('hidden');
      setResultActionsEnabled(Boolean(item.text));
      renderMeta([
        ['파일명', item.filename],
        ['언어', item.lang],
        ['글자 수', `${item.text.length}자`],
      ]);
      showToast('이전 OCR 기록을 불러왔습니다.', 'info');
    });

    historyList.appendChild(li);
  });
}

clearHistoryBtn.addEventListener('click', () => {
  localStorage.removeItem(HISTORY_KEY);
  renderHistory();
  showToast('최근 기록을 모두 삭제했습니다.', 'info');
});

// ── OCR 실행 ─────────────────────────────────────────────────
ocrBtn.addEventListener('click', async () => {
  if (!currentFile) return;
  const backendUrl = (backendInput.value || 'http://localhost:8000').replace(/\/+$/, '');

  if (isEditing) setEditMode(false);
  ocrBtn.disabled = true;
  btnText.textContent = '처리 중...';
  btnSpinner.classList.remove('hidden');
  setResultActionsEnabled(false);
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

    const ocrText = data.text?.trim() || '';
    resultEl.textContent = ocrText || '(인식된 텍스트가 없습니다.)';
    lastOcrText = ocrText || null;
    currentFilename = data.filename ?? currentFile.name;
    originalSection.classList.add('hidden');
    setResultActionsEnabled(Boolean(ocrText));

    const metaItems = [
      ['파일명', currentFilename],
      ['언어', data.lang ?? currentLang],
      ['크기', formatSize(data.size_bytes ?? currentFile.size)],
    ];
    if (typeof data.duration_ms === 'number') {
      metaItems.push(['소요', `${(data.duration_ms / 1000).toFixed(2)}s`]);
    }
    if (typeof data.char_count === 'number') {
      metaItems.push(['글자 수', `${data.char_count}자`]);
    }
    renderMeta(metaItems);

    if (ocrText) {
      const now = new Date();
      saveHistoryItem({
        id: `${Date.now()}-${Math.random().toString(16).slice(2, 6)}`,
        filename: currentFilename,
        lang: data.lang ?? currentLang,
        text: ocrText,
        time: now.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
      });
      showToast('OCR 추출이 완료되었습니다.', 'success');
    }
  } catch (err) {
    resultEl.textContent = `오류: ${err.message}`;
    resultMeta.classList.add('hidden');
    showToast(`OCR 실패: ${err.message}`, 'error');
  } finally {
    ocrBtn.disabled = false;
    btnText.textContent = 'OCR 실행';
    btnSpinner.classList.add('hidden');
  }
});

// ── 복사 & 다운로드 ──────────────────────────────────────────
copyBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(getActiveResultText());
    showToast('클립보드에 복사되었습니다.', 'success');
  } catch (err) {
    showToast(`복사 실패: ${err.message}`, 'error');
  }
});

function downloadText(ext) {
  const text = getActiveResultText().trim();
  if (!text) return;
  const base = currentFilename.replace(/\.[^.]+$/, '') || 'ocr-result';
  const content = ext === 'md' ? `# ${base}\n\n${text}\n` : `${text}\n`;
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${base}.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

downloadTxtBtn.addEventListener('click', () => downloadText('txt'));
downloadMdBtn.addEventListener('click', () => downloadText('md'));

// ── AI 보완 ──────────────────────────────────────────────────
aiBtn.addEventListener('click', async () => {
  const sourceText = getActiveResultText().trim();
  if (!sourceText) return;
  const backendUrl = (backendInput.value || 'http://localhost:8000').replace(/\/+$/, '');

  if (isEditing) setEditMode(false);
  aiBtn.disabled = true;
  aiBtnText.textContent = '처리 중...';
  aiBtnSpinner.classList.remove('hidden');

  const body = { text: sourceText, lang: currentLang, provider: currentAIProvider };
  if (currentAIProvider === 'ollama') {
    if (ollamaUrlInput.value) body.ollama_url = ollamaUrlInput.value;
    if (ollamaModelInput.value) body.ollama_model = ollamaModelInput.value;
  } else {
    if (openaiKeyInput.value) body.openai_api_key = openaiKeyInput.value;
    if (openaiModelInput.value) body.openai_model = openaiModelInput.value;
    if (openaiUrlInput.value) body.openai_base_url = openaiUrlInput.value;
  }

  try {
    const res = await fetch(`${backendUrl}/api/ai/enhance`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => { throw new Error(`파싱 실패 (status ${res.status})`); });
    if (!res.ok) throw new Error(data.detail || '요청 실패');

    originalResult.textContent = sourceText;
    originalSection.classList.remove('hidden');
    const enhanced = data.enhanced_text?.trim() || '';
    resultEl.textContent = enhanced || '(AI 보완 결과 없음)';
    lastOcrText = enhanced || sourceText;

    const providerLabel = currentAIProvider === 'ollama' ? 'Ollama' : 'OpenAI';
    renderMeta(
      [
        ['파일명', currentFilename],
        ['언어', currentLang],
        ['글자 수', `${lastOcrText.length}자`],
      ],
      providerLabel,
    );
    showToast(`${providerLabel} AI 보완이 완료되었습니다.`, 'success');
  } catch (err) {
    resultEl.textContent = `AI 오류: ${err.message}`;
    showToast(`AI 보완 실패: ${err.message}`, 'error');
  } finally {
    aiBtn.disabled = false;
    aiBtnText.textContent = 'AI 보완';
    aiBtnSpinner.classList.add('hidden');
  }
});

// ── 초기화 ───────────────────────────────────────────────────
loadSettings();
renderHistory();
