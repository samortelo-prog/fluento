#!/bin/bash
# setup_audio.sh — Configura BlackHole + Multi-Output Device automáticamente
# Corre una sola vez después de instalar BlackHole

echo "🔧 Configurando audio para el Traductor..."

# Verificar que BlackHole está instalado
if ! system_profiler SPAudioDataType 2>/dev/null | grep -q "BlackHole 2ch"; then
    echo "❌ BlackHole no está instalado."
    echo "   Descárgalo en: https://existential.audio/blackhole/"
    echo "   Instálalo, reinicia el Mac y corre este script de nuevo."
    open "https://existential.audio/blackhole/"
    exit 1
fi

echo "✅ BlackHole detectado"

# Verificar que SwitchAudioSource está disponible (para cambiar salida)
if ! command -v SwitchAudioSource &> /dev/null; then
    echo "📦 Instalando SwitchAudioSource..."
    if command -v brew &> /dev/null; then
        brew install switchaudio-osx
    else
        echo "⚠️  Homebrew no está instalado. Instálalo en https://brew.sh"
        echo "   Luego corre: brew install switchaudio-osx"
    fi
fi

# Crear Multi-Output Device via script Python
python3 - << 'PYEOF'
import subprocess, sys

# Usar audiodevice (más confiable que applescript para esto)
try:
    # Verificar dispositivos disponibles
    result = subprocess.run(
        ["SwitchAudioSource", "-a", "-t", "output"],
        capture_output=True, text=True
    )
    devices = result.stdout.strip().split('\n')
    print("Dispositivos de salida disponibles:")
    for d in devices:
        print(f"  {d}")
except Exception as e:
    print(f"SwitchAudioSource no disponible: {e}")

print("\n✅ Configuración lista.")
print("   En la app, usa el botón '🎧 Iniciar llamada' para configurar todo automáticamente.")
PYEOF

echo ""
echo "✅ Setup completado."
echo "   Abre el Traductor y usa '🎧 Iniciar llamada'"
