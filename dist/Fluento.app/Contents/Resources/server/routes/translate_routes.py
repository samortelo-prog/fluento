"""
routes/translate_routes.py — Endpoint de traducción en tiempo real.

Recibe fragmentos WAV del cliente, los transcribe con Whisper y los
traduce con GPT. Protegido por require_active_access: SOLO usuarios
con sesión válida Y cupón vigente pueden usarlo.
"""
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..auth import require_active_access
from ..models import User
from ..schemas import TranslationResult
from ..openai_service import transcribe_audio, translate_text

logger = logging.getLogger("translator")

router = APIRouter(prefix="/translate", tags=["Traducción"])

# Límite de tamaño por fragmento: 16 kHz * 2 bytes * ~10 s + cabecera WAV
MAX_CHUNK_BYTES = 16000 * 2 * 12


@router.post("/audio", response_model=TranslationResult)
async def translate_audio_chunk(
    file: UploadFile = File(..., description="Fragmento WAV 16 kHz mono int16"),
    target_lang: str = Form(..., description="Idioma destino, ej. 'español' o 'inglés'"),
    source_lang: str = Form(default="", description="ISO-639-1 origen opcional, ej. 'en'"),
    context: str = Form(default="", description="Últimas frases para coherencia"),
    user: User = Depends(require_active_access),  # ← control de acceso por cupón
):
    """Pipeline por fragmento: WAV → Whisper (ASR) → GPT (traducción)."""
    wav_bytes = await file.read()

    if len(wav_bytes) > MAX_CHUNK_BYTES:
        raise HTTPException(status_code=413, detail="Fragmento de audio demasiado grande (máx ~10 s)")
    if len(wav_bytes) < 1000:  # WAV vacío o corrupto
        return TranslationResult(transcript="", translation="")

    try:
        transcript = transcribe_audio(wav_bytes, source_lang or None)
    except Exception as e:
        logger.exception("Error en Whisper")
        raise HTTPException(status_code=502, detail=f"Error de transcripción: {e}")

    if not transcript:
        return TranslationResult(transcript="", translation="")

    try:
        translation = translate_text(transcript, target_lang, context)
    except Exception as e:
        logger.exception("Error en GPT")
        raise HTTPException(status_code=502, detail=f"Error de traducción: {e}")

    return TranslationResult(transcript=transcript, translation=translation)
