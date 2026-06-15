#!/bin/bash
# Traductor.command — Doble clic para iniciar (macOS)
# Todo es gráfico: la app pide tu TOGETHER_API_KEY en una ventana

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if ! command -v python3 &> /dev/null; then
    osascript -e 'tell app "System Events" to display dialog "Python 3 no está instalado. Descárgalo de python.org" buttons {"OK"}'
    exit 1
fi

if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Instalando dependencias (primera vez, ~1 min)..."
    python3 -m pip install -q -r requirements.txt --break-system-packages 2>/dev/null || python3 -m pip install -q -r requirements.txt
fi

python3 launcher.py
