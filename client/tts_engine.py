"""
tts_engine.py — Texto a voz (TTS) local con pyttsx3.

Corre en su propio hilo con una cola: la síntesis de voz NUNCA bloquea
el pipeline de captura/traducción (clave para mantener la latencia baja).
pyttsx3 funciona offline (usa las voces del sistema operativo), por lo
que no añade latencia de red ni costo de API.
"""
import queue
import threading

import pyttsx3


class TTSEngine:
    def __init__(self, rate: int = 185):
        """rate: palabras por minuto (ligeramente rápido para 'simultaneidad')."""
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._rate = rate
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self):
        # El motor debe crearse en el MISMO hilo que lo usa (limitación pyttsx3).
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        while True:
            text = self._queue.get()
            if text is None:  # señal de apagado
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"[tts] error: {e}")

    def speak(self, text: str):
        """Encola texto para hablar (no bloquea)."""
        if text.strip():
            self._queue.put(text)

    def stop(self):
        self._queue.put(None)
