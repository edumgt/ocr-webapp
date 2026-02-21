const form = document.getElementById('ocr-form');
const fileInput = document.getElementById('file-input');
const langInput = document.getElementById('lang-input');
const resultEl = document.getElementById('result');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const file = fileInput.files?.[0];

  if (!file) {
    resultEl.textContent = '파일을 선택해 주세요.';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  resultEl.textContent = 'OCR 처리 중...';

  try {
    const res = await fetch(`http://localhost:8000/api/ocr?lang=${encodeURIComponent(langInput.value || 'kor+eng')}`, {
      method: 'POST',
      body: formData,
    });

    const payload = await res.json();

    if (!res.ok) {
      throw new Error(payload.detail || '요청 실패');
    }

    resultEl.textContent = payload.text || '(텍스트가 비어 있습니다.)';
  } catch (error) {
    resultEl.textContent = `오류: ${error.message}`;
  }
});
