const form = document.getElementById('ocr-form');
const backendUrlInput = document.getElementById('backend-url-input');
const fileInput = document.getElementById('file-input');
const langInput = document.getElementById('lang-input');
const fileMetaEl = document.getElementById('file-meta');
const copyButton = document.getElementById('copy-btn');
const resultEl = document.getElementById('result');

function normalizeBackendUrl(rawValue) {
  const value = (rawValue || '').trim();
  if (!value) {
    return 'http://localhost:8000';
  }
  return value.replace(/\/+$/, '');
}

function setPreview(file) {
  if (!file) {
    fileMetaEl.textContent = '선택된 파일이 없습니다.';
    return;
  }

  fileMetaEl.textContent = `파일명: ${file.name} / 크기: ${(file.size / 1024).toFixed(1)}KB / 타입: ${file.type || 'unknown'}`;
}

fileInput.addEventListener('change', () => {
  setPreview(fileInput.files?.[0]);
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];
  const backendUrl = normalizeBackendUrl(backendUrlInput.value);
  copyButton.disabled = true;

  if (!file) {
    resultEl.textContent = '파일을 선택해 주세요.';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  resultEl.textContent = 'OCR 처리 중...';

  try {
    const res = await fetch(`${backendUrl}/api/ocr?lang=${encodeURIComponent(langInput.value || 'kor+eng')}`, {
      method: 'POST',
      body: formData,
    });

    const payload = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(payload.detail || '요청 실패');
    }

    const lines = [
      payload.text || '(텍스트가 비어 있습니다.)',
      '',
      `filename: ${payload.filename || file.name}`,
      `lang: ${payload.lang || langInput.value || 'kor+eng'}`,
      `size_bytes: ${payload.size_bytes ?? file.size}`,
    ];
    resultEl.textContent = lines.join('\n');
    copyButton.disabled = false;
  } catch (error) {
    resultEl.textContent = `오류: ${error.message}`;
  }
});

copyButton.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(resultEl.textContent || '');
    copyButton.textContent = '복사 완료';
    setTimeout(() => {
      copyButton.textContent = '결과 복사';
    }, 1200);
  } catch (error) {
    resultEl.textContent = `오류: 복사 실패 (${error.message})`;
  }
});
