"""
demo_5s.py — Prueba de extremo a extremo con 5 segundos de audio.

Graba 5 s del micrófono, los envía al servidor (Whisper → GPT) y
muestra transcripción + traducción; con --tts también la reproduce.

Uso:
    python -m scripts.demo_5s --server http://localhost:8000 --target inglés --tts
"""
import argparse
import getpass
import sys
import time

import numpy as np
import sounddevice as sd

sys.path.insert(0, ".")  # permitir ejecutar desde la raíz del proyecto
from client.api_client import ApiClient          # noqa: E402
from client.audio_capture import SAMPLE_RATE     # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--server", default="http://localhost:8000")
    p.add_argument("--target", default="inglés")
    p.add_argument("--source", default="")
    p.add_argument("--tts", action="store_true")
    args = p.parse_args()

    api = ApiClient(args.server)
    api.login(input("Correo: ").strip(), getpass.getpass("Contraseña: "))
    print("Login OK. Estado:", api.me())

    print("\n🎙  Grabando 5 segundos... habla ahora.")
    audio = sd.rec(int(5 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    audio = audio[:, 0]
    print("Grabación lista, enviando al servidor...")

    t0 = time.time()
    result = api.translate_chunk(audio, target_lang=args.target, source_lang=args.source)
    print(f"\nTiempo total: {time.time() - t0:.1f} s")
    print(f"Transcripción : {result['transcript']}")
    print(f"Traducción    : {result['translation']}")

    if args.tts and result["translation"]:
        from client.tts_engine import TTSEngine
        tts = TTSEngine()
        tts.speak(result["translation"])
        time.sleep(8)  # dar tiempo a que termine de hablar
        tts.stop()


if __name__ == "__main__":
    main()
