"""
api_client.py — Cliente HTTP con GROQ (sin OpenAI, sin TOGETHER.AI).

GROQ:
  - Whisper para ASR (transcripción): $0.10/hora
  - LLaMA/Mixtral para traducción: $0.05/hora
  - Total: $0.15/hora (más rápido que TOGETHER.AI)
  - Latencia: 1–2 segundos (más rápido)
  - Gratis: $5 de crédito inicial

Endpoints:
  - Transcripción: audio/transcriptions
  - Traducción: chat.completions (Mixtral 8x7B)
"""
import io
import json
import time
from typing import Optional

import numpy as np
import requests
import soundfile as sf


class AccessExpiredError(Exception):
    """El cupón del usuario expiró durante la sesión."""
    pass


class ApiClient:
    BASE_URL = "http://127.0.0.1:8000"
    GROQ_API_KEY = None  # Se obtiene del .env en launcher
    GROQ_BASE = "https://api.groq.com/openai/v1"

    def __init__(self, base_url: str, groq_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self._email = None
        self._password = None
        ApiClient.GROQ_API_KEY = groq_key

    def login(self, email: str, password: str) -> dict:
        """Login contra el servidor local (usuarios + cupones)."""
        r = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=15,
        )
        if r.status_code != 200:
            detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
            raise RuntimeError(detail)
        data = r.json()
        self.token = data["access_token"]
        self._email, self._password = email, password
        return data

    def register(self, nombre: str, email: str, password: str, coupon_code: str = "") -> dict:
        """Registrar usuario (cupón obligatorio excepto admin)."""
        payload = {"nombre": nombre, "email": email, "password": password}
        if coupon_code.strip():
            payload["coupon_code"] = coupon_code.strip()
        r = requests.post(f"{self.base_url}/auth/register", json=payload, timeout=15)
        if r.status_code != 201:
            detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
            raise RuntimeError(detail)
        data = r.json()
        self.token = data["access_token"]
        self._email, self._password = email, password
        return data

    def generate_coupons(self, quantity: int = 1, duration_days: int = 30) -> list[dict]:
        """[Admin] Genera cupones ilimitados."""
        r = requests.post(
            f"{self.base_url}/coupons/generate",
            json={"quantity": quantity, "duration_days": duration_days},
            headers=self._headers(),
            timeout=15,
        )
        if r.status_code != 200:
            detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
            raise RuntimeError(detail)
        return r.json()

    def redeem(self, coupon_code: str) -> dict:
        """Renovar acceso con cupón."""
        r = requests.post(
            f"{self.base_url}/coupons/redeem",
            json={"coupon_code": coupon_code.strip()},
            headers=self._headers(),
            timeout=15,
        )
        if r.status_code != 200:
            detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
            raise RuntimeError(detail)
        return r.json()

    def me(self) -> dict:
        """Estado de la cuenta."""
        r = requests.get(f"{self.base_url}/auth/me", headers=self._headers(), timeout=15)
        if r.status_code == 401:
            self._relogin()
            return self.me()
        if r.status_code != 200:
            raise RuntimeError(f"No pude obtener info de la cuenta: {r.text}")
        return r.json()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _relogin(self):
        """Re-login automático si el JWT expiró."""
        if self._email and self._password:
            try:
                self.login(self._email, self._password)
            except Exception:
                pass

    @staticmethod
    def _to_wav_bytes(chunk: np.ndarray) -> bytes:
        """Convierte array numpy a WAV bytes."""
        buf = io.BytesIO()
        sf.write(buf, chunk, 16000, format="WAV")
        return buf.getvalue()

    def transcribe_with_groq(self, audio_bytes: bytes) -> str:
        """Transcribe usando GROQ Whisper (rápido: 0.5-1 seg)."""
        text, _ = self.transcribe_with_lang(audio_bytes)
        return text

    def transcribe_with_lang(self, audio_bytes: bytes):
        """Transcribe y devuelve (texto, idioma_detectado). idioma = 'es', 'en', etc."""
        if not self.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY no configurada")

        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        headers = {"Authorization": f"Bearer {self.GROQ_API_KEY}"}

        # verbose_json devuelve el idioma detectado por Whisper (muy confiable)
        r = requests.post(
            f"{self.GROQ_BASE}/audio/transcriptions",
            files=files,
            data={"model": "whisper-large-v3", "response_format": "verbose_json"},
            headers=headers,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Transcripción falló: {r.text}")
        data = r.json()
        text = data.get("text", "")
        lang = data.get("language", "")
        # Whisper devuelve idioma como nombre completo o código; normalizar
        lang_norm = {
            "spanish": "es", "español": "es", "es": "es",
            "english": "en", "inglés": "en", "en": "en",
        }.get(lang.lower().strip(), lang.lower().strip()[:2])
        return text, lang_norm

    def translate_with_groq(
        self, text: str, target_lang: str, source_lang: str = "", context: str = ""
    ) -> str:
        """Traduce usando GROQ Mixtral 8x7B (muy rápido: 0.5-0.8 seg)."""
        if not self.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY no configurada")

        # Mapeo de idiomas
        lang_map = {
            "es": "español",
            "en": "inglés",
            "fr": "francés",
            "de": "alemán",
            "pt": "portugués",
            "it": "italiano",
            "zh": "chino",
            "ja": "japonés",
        }
        target_name = {"en": "English", "es": "Spanish", "inglés": "English",
                       "español": "Spanish"}.get(target_lang,
                       lang_map.get(target_lang, target_lang))

        system = (
            f"You are a professional simultaneous interpreter. "
            f"Translate the following text to {target_name}. "
            f"STRICT RULES — no exceptions: "
            f"(1) Output ONLY the translated text in {target_name}. "
            f"(2) Do NOT explain, do NOT add notes, do NOT say 'this translates as'. "
            f"(3) Do NOT repeat the original text. "
            f"(4) If the text is a fragment or incomplete sentence, translate it as-is. "
            f"(5) Use precise medical and legal terminology. "
            f"(6) Keep proper names, numbers and acronyms unchanged. "
            f"Example — input: 'me fui a venir' — correct output: 'I ended up coming' "
            f"Example — input: 'No, mi amor' — correct output: 'No, my love'"
        )
        user_msg = text
        if context:
            user_msg = f"Context: {context[:100]}\nTranslate: {text}"

        headers = {"Authorization": f"Bearer {self.GROQ_API_KEY}"}
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }

        r = requests.post(
            f"{self.GROQ_BASE}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Traducción falló: {r.text}")

        result = r.json()
        return result["choices"][0]["message"]["content"].strip()

    def translate_chunk(
        self,
        chunk: np.ndarray,
        target_lang: str = "español",
        source_lang: str = "",
        context: str = "",
    ) -> dict:
        """Flujo completo: transcribir + traducir (con GROQ)."""
        wav_bytes = self._to_wav_bytes(chunk)

        # Transcribir
        try:
            transcript = self.transcribe_with_groq(wav_bytes)
        except Exception as e:
            raise RuntimeError(f"Transcripción: {e}")

        if not transcript or not transcript.strip():
            return {"transcript": "", "translation": ""}

        # Traducir
        try:
            translation = self.translate_with_groq(
                transcript, target_lang=target_lang, source_lang=source_lang, context=context
            )
        except Exception as e:
            raise RuntimeError(f"Traducción: {e}")

        return {"transcript": transcript, "translation": translation}
