"""
openai_service.py — Capa de IA con GROQ (Whisper + Mixtral).

Reemplaza OpenAI por GROQ:
  - Whisper-large-v3: transcripción (1-2 seg)
  - Mixtral 8x7B: traducción (0.5-1 seg)
  - Total latencia: 1-2 seg (más rápido que OpenAI)
  - Costo: $0.15/hora (vs $0.32/hora con OpenAI)
"""
import io
import os
import requests

def _get_key(): return os.getenv("GROQ_API_KEY", "")
GROQ_BASE = "https://api.groq.com/openai/v1"

TRANSLATION_PROMPT = """Translate the following text to {target_lang}.

STRICT RULES:
1. Output ONLY the translation. No explanations, no notes, no original text.
2. The output language MUST be {target_lang}. This is non-negotiable.
3. Medical terms: use precise clinical terminology. Example: "infarto" → "myocardial infarction".
4. Legal terms: use precise legal terminology. Example: "tutela" → "guardianship".
5. Keep proper names, medical acronyms (EKG, ICU, CT), legal articles, and numbers unchanged.
6. If the text is incomplete, translate it as-is without completing it.
7. If the text is unintelligible noise, respond with empty string only.
8. DO NOT respond in the same language as the input under any circumstances."""


def transcribe_audio(wav_bytes: bytes, source_lang: str | None = None) -> str:
    """Transcribe audio WAV usando GROQ Whisper-large-v3."""
    if not _get_key():
        raise RuntimeError("GROQ_API_KEY no esta configurada")

    files = {"file": ("chunk.wav", wav_bytes, "audio/wav")}
    data = {
        "model": "whisper-large-v3",
        "response_format": "text",
        "prompt": "This is a conversation in Spanish or English only.",
        "temperature": 0,
        "language": source_lang if source_lang else None,
    }
    # Eliminar claves None
    data = {k: v for k, v in data.items() if v is not None}

    r = requests.post(
        f"{GROQ_BASE}/audio/transcriptions",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {_get_key()}"},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Whisper GROQ error {r.status_code}: {r.text[:200]}")
    
    text = r.text.strip()
    
    # Filtrar alucinaciones comunes de Whisper en silencio
    alucinaciones = [
        "gracias", "thank you", "thanks for watching", "suscríbete",
        "subtitulado por", "transcripción por", "...", ". . .",
        "you", "the", "[música]", "[music]", "[silencio]",
    ]
    if text.lower().strip(" .") in alucinaciones or len(text) < 3:
        return ""
    
    return text


def translate_text(text: str, target_lang: str, context: str = "") -> str:
    """Traduce texto usando GROQ Mixtral 8x7B."""
    if not text.strip():
        return ""
    if not _get_key():
        raise RuntimeError("GROQ_API_KEY no esta configurada")

    lang_names = {"es": "Spanish", "en": "English", "fr": "French",
                  "de": "German", "pt": "Portuguese", "it": "Italian",
                  "español": "Spanish", "inglés": "English", "frances": "French"}
    lang_display = lang_names.get(target_lang, target_lang)
    system = TRANSLATION_PROMPT.format(target_lang=lang_display)
    user = (
        f"Contexto previo:\n{context}\n\n---\nFragmento:\n{text}"
        if context else f"Fragmento:\n{text}"
    )

    r = requests.post(
        f"{GROQ_BASE}/chat/completions",
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 400,
        },
        headers={"Authorization": f"Bearer {_get_key()}"},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Mixtral GROQ error {r.status_code}: {r.text[:200]}")
    result = (r.json()["choices"][0]["message"]["content"] or "").strip()
    # Si devolvió exactamente el mismo texto, forzar reintento con instrucción más directa
    if result.lower().strip() == text.lower().strip():
        retry = requests.post(
            f"{GROQ_BASE}/chat/completions",
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": f"You are a translator. Translate to {lang_display} only."},
                    {"role": "user", "content": f"Translate this to {lang_display}: {text}"},
                ],
                "temperature": 0,
                "max_tokens": 400,
            },
            headers={"Authorization": f"Bearer {_get_key()}"},
            timeout=30,
        )
        if retry.status_code == 200:
            result = (retry.json()["choices"][0]["message"]["content"] or "").strip()
    return result
