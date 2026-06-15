@echo off
REM Traductor.bat - Doble clic para iniciar (Windows)

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python no esta instalado. Descargalo de python.org
    pause
    exit /b 1
)

python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias (primera vez, ~1 min)...
    pip install -q -r requirements.txt
)

python launcher.py
