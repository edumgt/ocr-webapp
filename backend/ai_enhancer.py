from __future__ import annotations

import os

import httpx

AI_TIMEOUT = 120.0

_LANG_NAMES = {"kor": "Korean", "eng": "English"}


def _lang_hint(lang: str) -> str:
    return _LANG_NAMES.get(lang, "Korean and English mixed")


def _build_prompt(text: str, lang: str) -> str:
    return (
        "You are an OCR post-correction assistant. "
        "The text below was extracted from an image by Tesseract OCR and may contain "
        "recognition errors (wrong characters, broken spacing, garbled words). "
        f"Language hint: {_lang_hint(lang)}.\n\n"
        "Rules:\n"
        "1. Fix character recognition errors (e.g. 0↔O, 1↔l, rn↔m, ㅁ↔口).\n"
        "2. Restore natural word spacing and line breaks.\n"
        "3. Preserve the original structure, layout, and meaning exactly.\n"
        "4. Do NOT add any explanation, commentary, or preamble — return ONLY the corrected text.\n\n"
        f"OCR output:\n{text}"
    )


async def enhance_ollama(text: str, lang: str, base_url: str, model: str) -> str:
    async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={"model": model, "prompt": _build_prompt(text, lang), "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()


async def enhance_openai(
    text: str,
    lang: str,
    api_key: str,
    model: str,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    async with httpx.AsyncClient(timeout=AI_TIMEOUT) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": _build_prompt(text, lang)}],
                "temperature": 0.1,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


# ── 환경변수 기본값 ─────────────────────────────────────────────────────────
DEFAULT_PROVIDER     = os.getenv("AI_PROVIDER",      "ollama")
DEFAULT_OLLAMA_URL   = os.getenv("OLLAMA_BASE_URL",  "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL",     "llama3.2")
DEFAULT_OPENAI_KEY   = os.getenv("OPENAI_API_KEY",   "")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL",     "gpt-4o-mini")
DEFAULT_OPENAI_URL   = os.getenv("OPENAI_BASE_URL",  "https://api.openai.com/v1")
