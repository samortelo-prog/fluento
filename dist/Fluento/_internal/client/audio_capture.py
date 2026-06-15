"""
audio_capture.py — Captura de micrófono o audio del sistema (loopback).

Estrategia de fragmentación pensada para latencia <5 s:
- El stream entrega bloques pequeños (0.25 s) a un buffer.
- Un hilo "chunker" corta fragmentos para enviar al servidor cuando:
    a) detecta una pausa (silencio) tras ≥ MIN_CHUNK_S de voz, o
    b) el fragmento alcanza MAX_CHUNK_S (corte forzado, no se espera más).
- Los fragmentos puramente silenciosos se descartan (ahorra llamadas a la API).

Para capturar el AUDIO DEL SISTEMA (Zoom/Teams/Meet/cualquier app):
- macOS  : instalar BlackHole 2ch y crear un "Multi-Output Device";
           seleccionar BlackHole como dispositivo de entrada (--device).
- Windows: instalar VB-Audio Virtual Cable; o usar WASAPI loopback.
- Linux  : usar el monitor de PulseAudio ("Monitor of ...") como entrada.
Listar dispositivos disponibles:  python -m sounddevice
"""
import queue
import threading

import numpy as np
import sounddevice as sd

# --- Parámetros de audio (óptimos para Whisper) ---
SAMPLE_RATE = 16000        # Whisper trabaja internamente a 16 kHz
CHANNELS = 1               # mono: suficiente para voz, mitad de datos
BLOCK_SECONDS = 0.2        # tamaño de bloque del stream (granularidad)
MIN_CHUNK_S = 4.0          # mínimo 4 seg — frases más completas
MAX_CHUNK_S = 10.0         # máximo 10 seg — oraciones largas
SILENCE_RMS = 0.006        # umbral RMS silencio más estricto (ignora ruido leve)
SILENCE_BLOCKS_TO_CUT = 5  # más bloques de silencio antes de cortar


def list_input_devices() -> list[tuple[int, str]]:
    """Devuelve [(índice, nombre)] de dispositivos de ENTRADA disponibles.

    Incluye dispositivos virtuales como BlackHole (macOS) o CABLE Output
    (Windows), que son los que permiten capturar el audio del sistema
    (Zoom, Teams, YouTube, cualquier sonido del computador).
    """
    devices = []
    try:
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0:
                devices.append((idx, dev["name"]))
    except Exception:
        pass
    return devices


class AudioCapture:
    """Captura continua y entrega fragmentos listos (np.float32) en una cola."""

    def __init__(self, device: int | str | None = None):
        self.device = device                  # None = dispositivo de entrada por defecto
        self.chunk_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=20)
        self._block_queue: queue.Queue[np.ndarray] = queue.Queue()
        self._running = False
        self._stream: sd.InputStream | None = None
        self._chunker_thread: threading.Thread | None = None

    # ---------- callback del stream (hilo de audio, debe ser rápido) ----------
    def _callback(self, indata, frames, time_info, status):
        if status:
            # Avisos de overflow/underflow del driver; no detienen la captura.
            print(f"[audio] aviso del driver: {status}")
        # Copiar: sounddevice reutiliza el buffer de indata.
        self._block_queue.put(indata[:, 0].copy())

    # ---------- hilo que agrupa bloques en fragmentos ----------
    def _chunker(self):
        buffer: list[np.ndarray] = []
        buffered_seconds = 0.0
        consecutive_silent = 0

        while self._running:
            try:
                block = self._block_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            buffer.append(block)
            buffered_seconds += len(block) / SAMPLE_RATE

            # RMS del bloque: medida simple de energía para detectar pausas.
            rms = float(np.sqrt(np.mean(block.astype(np.float64) ** 2)))
            consecutive_silent = consecutive_silent + 1 if rms < SILENCE_RMS else 0

            cut_on_pause = buffered_seconds >= MIN_CHUNK_S and consecutive_silent >= SILENCE_BLOCKS_TO_CUT
            cut_forced = buffered_seconds >= MAX_CHUNK_S

            if cut_on_pause or cut_forced:
                chunk = np.concatenate(buffer)
                buffer, buffered_seconds, consecutive_silent = [], 0.0, 0

                # Descartar fragmentos sin voz (RMS global muy bajo).
                if float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2))) < SILENCE_RMS:
                    continue
                try:
                    self.chunk_queue.put_nowait(chunk)
                except queue.Full:
                    # Backpressure: si el consumidor va lento, se descarta el
                    # fragmento más antiguo para no acumular latencia.
                    self.chunk_queue.get_nowait()
                    self.chunk_queue.put_nowait(chunk)

    # ---------- API pública ----------
    def start(self):
        """Abre el stream y arranca el hilo de fragmentación."""
        self._running = True
        self._stream = sd.InputStream(
            device=self.device,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=int(SAMPLE_RATE * BLOCK_SECONDS),
            callback=self._callback,
        )
        self._stream.start()
        self._chunker_thread = threading.Thread(target=self._chunker, daemon=True)
        self._chunker_thread.start()

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()

    def get_chunk(self, timeout: float = 1.0) -> np.ndarray | None:
        """Devuelve el siguiente fragmento de voz, o None si no hay."""
        try:
            return self.chunk_queue.get(timeout=timeout)
        except queue.Empty:
            return None
