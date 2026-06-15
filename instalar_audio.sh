#!/bin/bash
# instalar_audio.sh — Instala BlackHole + SwitchAudioSource automáticamente
# Corre UNA SOLA VEZ antes de usar el Traductor

echo "================================================"
echo "  Configuración de Audio — Traductor Bilingüe"
echo "================================================"
echo ""

# 1. Verificar Homebrew
if ! command -v brew &> /dev/null; then
    echo "📦 Instalando Homebrew (gestor de paquetes para Mac)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✅ Homebrew ya instalado"
fi

# 2. Instalar SwitchAudioSource
if ! command -v SwitchAudioSource &> /dev/null; then
    echo "📦 Instalando SwitchAudioSource..."
    brew install switchaudio-osx
else
    echo "✅ SwitchAudioSource ya instalado"
fi

# 3. Verificar BlackHole
if system_profiler SPAudioDataType 2>/dev/null | grep -q "BlackHole 2ch"; then
    echo "✅ BlackHole 2ch ya instalado"
else
    echo ""
    echo "📦 BlackHole no está instalado."
    echo "   Abriendo página de descarga..."
    open "https://existential.audio/blackhole/"
    echo ""
    echo "   Instala BlackHole 2ch y REINICIA el Mac."
    echo "   Después de reiniciar, corre este script de nuevo."
    exit 1
fi

# 4. Crear Multi-Output Device automáticamente con Python
echo ""
echo "🔧 Configurando Multi-Output Device..."

python3 - << 'PYEOF'
import subprocess, time

# Obtener lista de dispositivos de salida
result = subprocess.run(
    ["SwitchAudioSource", "-a", "-t", "output"],
    capture_output=True, text=True
)
outputs = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
print("Dispositivos de salida encontrados:")
for d in outputs:
    print(f"  - {d}")

# Verificar que existe Multi-Output Device
if "Multi-Output Device" in outputs:
    print("\n✅ Multi-Output Device ya existe")
else:
    print("\n⚠️  Multi-Output Device no encontrado.")
    print("   Créalo manualmente:")
    print("   1. Spotlight → 'Audio MIDI Setup'")
    print("   2. Botón '+' → 'Crear dispositivo de salida múltiple'")
    print("   3. Marca: tus altavoces/AirPods + BlackHole 2ch")

PYEOF

echo ""
echo "================================================"
echo "✅ Configuración completada."
echo ""
echo "Para usar el Traductor en llamadas:"
echo "  1. Conecta tus AirPods"
echo "  2. Abre el Traductor"
echo "  3. Pulsa '🎧 Iniciar llamada'"
echo "  4. La app configura todo automáticamente"
echo "================================================"
