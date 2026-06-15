# Traductor en Tiempo Real — Whisper + GPT con acceso por cupones

Prototipo completo: captura de audio (micrófono o audio del sistema) → transcripción con **Whisper** → traducción con **GPT** → texto en pantalla + **TTS opcional**, con **registro/login de usuarios** y **cupones de acceso de 30 días** generados solo por el administrador.

## Dos opciones de uso

### Para usuarios finales (sin programación)

Descarga el archivo ejecutable y ejecuta:
- **Windows**: `Traductor.exe` (un solo clic)
- **macOS**: `Traductor.app` (un solo clic)

Ver [BUILD_GUIDE.md](BUILD_GUIDE.md) para compilar o descargar ejecutables precompilados.

### Para desarrolladores

Clona el repo, instala dependencias y ejecuta:
```bash
python launcher.py                                          # Inicia GUI + servidor
# O en modo desarrollo puro:
uvicorn server.main:app --port 8000                       # Terminal 1: servidor
python -m client.translator --target español --tts        # Terminal 2: cliente CLI
```

## Arquitectura

```
CLIENTE (escritorio)                      SERVIDOR (FastAPI)              OPENAI
┌─────────────────────┐    WAV 1.5-4s    ┌──────────────────┐
│ GUI o CLI           │  ─────────────▶ │ JWT + cupón OK?  │──▶ Whisper (ASR)
│ sounddevice         │   HTTPS + JWT   │ /translate/audio │──▶ GPT (traducción)
│ buffer + corte      │  ◀───────────── │ SQLite/Postgres  │
│ pantalla + TTS      │  texto traducido│ users + cupones  │
└─────────────────────┘                  └──────────────────┘
```

La **API key de OpenAI vive solo en el servidor**. El cliente nunca la conoce: se autentica con email/contraseña, recibe un JWT y solo puede traducir mientras su cupón esté vigente.

## Estructura

```
server/     → FastAPI: auth, cupones, endpoint de traducción, capa OpenAI
client/     → captura de audio, cliente HTTP, TTS, GUI (tkinter), CLI
scripts/    → gen_coupons.py (admin) y demo_5s.py (prueba end-to-end)
launcher.py → Punto de entrada único: levanta servidor + abre GUI
```

## Instalación (modo desarrollo)

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Editar .env: OPENAI_API_KEY, JWT_SECRET, ADMIN_API_KEY
python -c "import secrets; print(secrets.token_hex(32))"   # para generar secretos
```

> macOS: si pyttsx3 falla, `pip install pyobjc`. Linux: `sudo apt install espeak libespeak1 portaudio19-dev`.

## Puesta en marcha

### Opción A: Con GUI (recomendado para usuarios)

```bash
python launcher.py
```

Se abrirá automáticamente:
1. Ventana de login (email + contraseña)
2. Configuración: idioma destino, opciones de TTS
3. Botón "Iniciar escucha" → captura y traduce en vivo

### Opción B: Modo desarrollo puro (CLI sin GUI)

```bash
# Terminal 1: Servidor
uvicorn server.main:app --host 0.0.0.0 --port 8000
# Docs: http://localhost:8000/docs

# Terminal 2: Generar cupón (admin)
python scripts/gen_coupons.py -n 1 --days 30
#   → LM-xxxxxxxxxxxxxxxx

# Terminal 2: Registrar usuario
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Samuel","email":"s@test.com","password":"ClaveSegura123","coupon_code":"LM-..."}'

# Terminal 2: Demo de 5 segundos
python -m scripts.demo_5s --target inglés --tts

# Terminal 2: Traducción continua (CLI)
python -m client.translator --target español --source en --tts
```

## Capturar el audio del sistema (Zoom, Teams, Meet, etc.)

Para capturar cualquier audio que sale de tu computador:

| SO | Herramienta | Pasos |
|---|---|---|
| **macOS** | [BlackHole 2ch](https://existential.audio/blackhole/) | 1. Instalar BlackHole<br>2. En Audio MIDI Setup: crear Multi-Output Device (altavoces + BlackHole)<br>3. En GUI: seleccionar BlackHole como dispositivo de entrada |
| **Windows** | VB-Audio Virtual Cable | 1. Instalar VBCABLE<br>2. Salida de app → CABLE Input<br>3. Cliente escucha CABLE Output |
| **Linux** | PulseAudio/PipeWire | Usar dispositivo "Monitor of ..." como entrada |

```bash
python -m client.translator --list-devices        # listar índices disponibles
python -m client.translator --device 3 --target español
```

Funciona con **cualquier plataforma** (Zoom, Teams, Skype, etc.) porque se captura a nivel de SO.

## Renovar acceso (canjear cupón)

En la GUI: botón "Canjear cupón" (automático cuando falta poco para expirar)

O con curl:
```bash
curl -X POST http://localhost:8000/coupons/redeem \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"coupon_code":"LM-..."}'
```

## Seguridad

- Contraseñas: **bcrypt** (hash + salt), nunca en claro
- Sesiones: **JWT HS256** de 12 h con re-login automático
- Cupones: un solo uso, criptográficos, creables solo con `X-Admin-Key`
- Endpoint de traducción: exige JWT + cupón vigente en cada petición
- API keys: confinadas al servidor (cliente nunca las ve)

## Compilación a ejecutables (.exe y .app)

Para usuarios finales sin Python instalado:

```bash
# Windows
build_windows.bat
# → dist/Traductor.exe

# macOS
chmod +x build_macos.sh && ./build_macos.sh
# → dist/Traductor.app
```

Ver [BUILD_GUIDE.md](BUILD_GUIDE.md) para instrucciones detalladas y distribución profesional.

## Producción

- HTTPS obligatorio (Railway por defecto; Hetzner: Nginx + Let's Encrypt)
- PostgreSQL en lugar de SQLite
- Migraciones con Alembic
- Rate-limiting por usuario (slowapi)
- Múltiples workers: `uvicorn server.main:app --workers 4`
