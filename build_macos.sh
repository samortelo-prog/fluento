#!/bin/bash
# build_macos.sh — Compila el traductor a .app (aplicación macOS nativa)
# Uso: chmod +x build_macos.sh && ./build_macos.sh

set -e  # Salir si hay error

echo ""
echo "============================================================"
echo "Compilador: Traductor en Tiempo Real (.app)"
echo "============================================================"
echo ""

# 1) Verificar que Python está disponible
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no encontrado. Instálalo desde python.org"
    exit 1
fi

# 2) Verificar/instalar PyInstaller
if ! python3 -m pip list | grep -q PyInstaller; then
    echo "Instalando PyInstaller..."
    python3 -m pip install PyInstaller --break-system-packages
fi

# 3) Limpiar compilaciones previas
echo "Limpiando compilaciones previas..."
rm -rf build dist *.spec

# 4) Compilar a .app
echo ""
echo "Compilando a .app (esto tarda ~1 minuto)..."
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name "Traductor" \
    --add-data "server:server" \
    --add-data ".env.example:.env.example" \
    --icon "icon.icns" 2>/dev/null || true \
    --hidden-import=passlib.handlers.bcrypt \
    --hidden-import=sqlalchemy.dialects.sqlite \
    --hidden-import=uvicorn.logging \
    --hidden-import=pydantic.json \
    --collect-all openai \
    --collect-all sounddevice \
    --osx-bundle-identifier "com.libertymedialabs.traductor" \
    launcher.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Error en la compilación. Verifica los mensajes arriba."
    exit 1
fi

echo ""
echo "============================================================"
echo "✓ Compilación exitosa"
echo "============================================================"
echo ""
echo "La aplicación está en: dist/Traductor.app"
echo ""
echo "Para usar:"
echo "  1. Abre dist/Traductor.app (o muévelo a /Applications)"
echo "  2. Se abrirá la aplicación y creará .env automáticamente"
echo "  3. Edita .env con tu OPENAI_API_KEY (misma carpeta que .app)"
echo ""
echo "Nota: en el primer lanzamiento, macOS pedirá autorización"
echo "      para acceder al micrófono. Aprueba para que funcione."
echo ""
