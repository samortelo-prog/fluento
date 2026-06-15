"""
translator.py — Cliente principal de traducción en tiempo real.

Uso:
    python -m client.translator --server http://localhost:8000 \
        --target "español" --source en --tts

Flujo:
    micrófono/loopback → fragmentos (1.5-4 s) → servidor (Whisper+GPT)
    → impresión en pantalla (+ TTS opcional)

El acceso lo controla el servidor: si el cupón del usuario expira a
mitad de sesión, el bucle termina con un mensaje claro.
"""
import argparse
import getpass
import sys
import time

import sounddevice as sd

from .audio_capture import AudioCapture
from .api_client import ApiClient, AccessExpiredError
from .tts_engine import TTSEngine


def parse_args():
    p = argparse.ArgumentParser(description="Traductor en tiempo real (Whisper + GPT)")
    p.add_argument("--server", default="http://localhost:8000", help="URL del servidor backend")
    p.add_argument("--target", default="español", help="Idioma destino (ej. 'español', 'inglés')")
    p.add_argument("--source", default="", help="Idioma origen ISO-639-1 opcional (ej. 'en'); vacío = autodetectar")
    p.add_argument("--device", default=None, help="Índice o nombre del dispositivo de entrada (ver --list-devices)")
    p.add_argument("--tts", action="store_true", help="Leer la traducción en voz alta (pyttsx3)")
    p.add_argument("--list-devices", action="store_true", help="Listar dispositivos de audio y salir")
    return p.parse_args()


def main():
    args = parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    # ---------- 1) Login ----------
    api = ApiClient(args.server)
    print(f"Conectando a {args.server}")
    email = input("Correo: ").strip()
    password = getpass.getpass("Contraseña: ")
    try:
        api.login(email, password)
    except Exception as e:
        print(f"Login fallido: {e}")
        sys.exit(1)

    status = api.me()
    if not status["has_active_access"]:
        print("Tu cupón ha expirado. Canjea uno nuevo (POST /coupons/redeem) para continuar.")
        sys.exit(1)
    print(f"Bienvenido, {status['nombre']}. Acceso activo hasta: {status['access_expires_at']}")

    # ---------- 2) Audio + TTS ----------
    device = int(args.device) if args.device and str(args.device).isdigit() else args.device
    capture = AudioCapture(device=device)
    tts = TTSEngine() if args.tts else None

    capture.start()
    print(f"\nEscuchando... traduciendo a «{args.target}». Ctrl+C para salir.\n" + "-" * 60)

    # Ventana de contexto: últimas frases originales, para que GPT
    # mantenga coherencia (pronombres, terminología) entre fragmentos.
    context_window: list[str] = []

    # ---------- 3) Bucle principal ----------
    try:
        while True:
            chunk = capture.get_chunk(timeout=1.0)
            if chunk is None:
                continue  # silencio: seguir escuchando

            t0 = time.time()
            try:
                result = api.translate_chunk(
                    chunk,
                    target_lang=args.target,
                    source_lang=args.source,
                    context=" ".join(context_window[-2:]),  # últimas 2 frases
                )
            except AccessExpiredError as e:
                print(f"\n⛔ {e}")
                break

            if not result or not result["transcript"]:
                continue

            latency = time.time() - t0
            print(f"\n🎙  {result['transcript']}")
            print(f"🌐  {result['translation']}   ({latency:.1f} s)")

            context_window.append(result["transcript"])
            context_window = context_window[-4:]  # acotar memoria

            if tts:
                tts.speak(result["translation"])

    except KeyboardInterrupt:
        print("\nSaliendo...")
    finally:
        capture.stop()
        if tts:
            tts.stop()


if __name__ == "__main__":
    main()
