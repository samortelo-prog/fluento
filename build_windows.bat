@echo off
REM build_windows.bat — Compila el traductor a .exe
REM Uso: abrir cmd, ir a la carpeta del proyecto, y ejecutar: build_windows.bat

echo.
echo ============================================================
echo Compilador: Traductor en Tiempo Real (.exe)
echo ============================================================
echo.

REM 1) Verificar que PyInstaller está instalado
pip list | findstr PyInstaller >nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install PyInstaller --break-system-packages
)

REM 2) Limpiar compilaciones previas
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

REM 3) Compilar a .exe con PyInstaller
echo.
echo Compilando...
REM --onefile = un único .exe
REM --windowed = sin consola (aplicación gráfica)
REM --icon = ícono (opcional, omitir si no existe)
REM --collect-all = incluir todos los datos de librerías (sounddevice, etc.)
REM --hidden-import = módulos que PyInstaller no detecta automáticamente

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Traductor" ^
    --add-data "server:server" ^
    --add-data ".env.example:.env.example" ^
    --hidden-import=passlib.handlers.bcrypt ^
    --hidden-import=sqlalchemy.dialects.sqlite ^
    --hidden-import=uvicorn.logging ^
    --hidden-import=pydantic.json ^
    --collect-all openai ^
    --collect-all sounddevice ^
    launcher.py

if errorlevel 1 (
    echo.
    echo ❌ Error en la compilación. Verifica los mensajes arriba.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo ✓ Compilación exitosa
echo ============================================================
echo.
echo El archivo ejecutable está en:
echo   dist\Traductor.exe
echo.
echo Para usar:
echo   1. Copia dist\Traductor.exe a cualquier ubicación
echo   2. Ejecuta Traductor.exe
echo   3. Se abrirá la aplicación y creará .env automáticamente
echo   4. Edita .env con tu OPENAI_API_KEY (en la misma carpeta que .exe)
echo.
pause
