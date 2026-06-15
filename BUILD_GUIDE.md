# Compilación a Ejecutables (.exe y .app)

## Resumen

Esta guía te permite compilar el traductor a un archivo ejecutable único (.exe en Windows, .app en macOS) que cualquier usuario puede usar sin necesidad de instalar Python ni copiar código.

```
Usuario descarga → Ejecuta archivo → Automáticamente:
  1. Se crea .env si no existe
  2. Se levanta el servidor en background
  3. Se abre la interfaz gráfica (tkinter)
  4. Al cerrar, limpia automáticamente
```

---

## Para desarrolladores: Antes de compilar

```bash
# 1) Instala todas las dependencias (incluyendo PyInstaller)
pip install -r requirements.txt

# 2) Prueba que todo funciona en modo desarrollo
python launcher.py
# Debe abrirse la GUI, funcionar normalmente

# 3) Si todo OK, compilar (ver secciones abajo)
```

---

## Windows: Compilar a .exe

### Opción A: Automático (recomendado)

1. Abre **cmd** o **PowerShell** en la carpeta del proyecto
2. Ejecuta:
   ```
   build_windows.bat
   ```
3. Espera ~2 minutos. Al terminar, encontrarás el .exe en `dist/Traductor.exe`

### Opción B: Manual (si el .bat no funciona)

```bash
pip install PyInstaller
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Traductor" ^
    --add-data "server:server" ^
    --hidden-import=passlib.handlers.bcrypt ^
    --hidden-import=sqlalchemy.dialects.sqlite ^
    --collect-all openai ^
    --collect-all sounddevice ^
    launcher.py
```

### Para usar el .exe

1. Copia `dist\Traductor.exe` a una carpeta (p.ej. `C:\Programas\Traductor\`)
2. Ejecuta `Traductor.exe`
3. Se abrirá automáticamente una ventana de login y creará `.env` en la misma carpeta
4. **⚠ Importante**: Edita `.env` (con Notepad) y reemplaza `OPENAI_API_KEY` con tu clave real
5. Cierra y vuelve a abrir el .exe → Ahora sí funcionará

### Crear un acceso directo en el escritorio

- Clic derecho en `Traductor.exe` → "Crear acceso directo"
- Mueve el acceso directo al escritorio
- Doble clic para lanzar

---

## macOS: Compilar a .app

### Opción A: Automático (recomendado)

1. Abre **Terminal** en la carpeta del proyecto
2. Ejecuta:
   ```bash
   chmod +x build_macos.sh
   ./build_macos.sh
   ```
3. Espera ~2 minutos. Al terminar, encontrarás la app en `dist/Traductor.app`

### Opción B: Manual (si el script no funciona)

```bash
pip install PyInstaller
python3 -m PyInstaller \
    --onefile \
    --windowed \
    --name "Traductor" \
    --add-data "server:server" \
    --hidden-import=passlib.handlers.bcrypt \
    --collect-all openai \
    --collect-all sounddevice \
    --osx-bundle-identifier "com.libertymedialabs.traductor" \
    launcher.py
```

### Para usar la .app

1. Copia `dist/Traductor.app` a **Aplicaciones** (o déjalo donde esté)
2. Haz doble clic en `Traductor.app`
3. **Primer lanzamiento**: macOS dirá "¿Permites que Traductor acceda al micrófono?" → **Permite** (necesario para capturar audio)
4. Se abrirá la GUI, creará `.env` automáticamente en la misma carpeta que `.app`
5. **⚠ Importante**: Edita `.env` (con TextEdit) y reemplaza `OPENAI_API_KEY`
6. Cierra y vuelve a lanzar la .app

### En aplicaciones

Para una distribución más profesional:
```bash
# Crear un .dmg (disco virtual) para distribuir
hdiutil create -volname "Traductor" -srcfolder dist/Traductor.app traductor.dmg
```

---

## Estructura después de compilar

```
C:\Programas\Traductor\    (Windows)
├── Traductor.exe          ← Usuario ejecuta esto
├── .env                   ← Se crea automáticamente, editar con OPENAI_API_KEY
├── translator.db          ← Base de datos (SQLite), se crea en primer login
└── ...

/Applications/Traductor.app (macOS)
├── Contents/MacOS/launcher ← Ejecutable embebido
├── .env                   ← Se crea automáticamente
├── translator.db          ← Base de datos
└── ...
```

---

## Flujo de configuración (usuario final)

```
1. Usuario descarga Traductor.exe / Traductor.app
2. Ejecuta el archivo → Se abre ventana "Configurando..."
   - Se crea .env (con JWT_SECRET y ADMIN_API_KEY generados)
   - Se levanta servidor en puerto 8000
   - Se abre GUI de login
3. Usuario ve:
   ⚠️  AVISO: "Falta OPENAI_API_KEY"
       Edita .env y añade tu clave de OpenAI, luego reinicia la app
4. Usuario:
   - Abre .env (Bloc de notas / TextEdit)
   - Reemplaza: OPENAI_API_KEY=sk-tu-clave-aqui
   - Guarda
   - Cierra y vuelve a abrir Traductor.exe/.app
5. ✓ Ahora funciona: login → inicio de captura → traducción en vivo
```

---

## Para distribuidores: Setup completo

Si quieres vender o distribuir esto profesionalmente:

### Windows: Crear instalador .msi o .exe

Usa **NSIS** (Nullsoft Installer System) o **Inno Setup**:

```nsis
; Installer.nsi (Inno Setup)
[Setup]
AppName=Traductor
AppVersion=1.0.0
DefaultDirName={pf}\Traductor
DefaultGroupName=Traductor
OutputDir=Output
OutputBaseFilename=Traductor-Installer

[Files]
Source: "dist\Traductor.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\Traductor"; Filename: "{app}\Traductor.exe"
Name: "{userstartmenu}\Traductor"; Filename: "{app}\Traductor.exe"

[Run]
Filename: "{app}\Traductor.exe"; Description: "Ejecutar Traductor"; Flags: nowait postinstall
```

Luego compila el .nsi con Inno Setup → genera `Traductor-Installer.exe` profesional.

### macOS: Notarización (para distribución en App Store)

```bash
# Firmar la app
codesign --deep --force --verify --verbose --sign "Developer ID Application" dist/Traductor.app

# Empaquetar y enviar a Apple para notarización
ditto -c -k --sequesterRsrc dist/Traductor.app traductor.zip
xcrun altool --notarize-app --file traductor.zip --primary-bundle-id com.libertymedialabs.traductor ...
```

(Esto requiere cuenta de desarrollador Apple)

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'X'" al ejecutar .exe

Añade a `build_windows.bat` en la sección de `hidden-import`:
```batch
--hidden-import=nombre.del.modulo ^
```

### El .app no abre en macOS ("es un archivo corrupto")

```bash
# Dar permisos ejecutables
chmod +x dist/Traductor.app/Contents/MacOS/launcher
```

### El servidor no arranca desde el .exe

Verifica que `server/` esté incluido en el `--add-data`:
```
--add-data "server:server" ^
```

### "OPENAI_API_KEY no configurado"

Asegúrate de que `.env` está en la **misma carpeta** que el `.exe` o `.app`, no en una subcarpeta.

---

## Monitoreo post-compilación

Si distribuyes a muchos usuarios, considera:

1. **Telemetría**: Incluir un `health_check()` que reporta si el servidor arrancó bien
2. **Logs**: Guardar logs de server + client para debugging remoto
3. **Versionado**: Incluir un `--version` que compara con un servidor de actualizaciones

```python
# En launcher.py
import requests
latest_version_url = "https://example.com/api/latest-version"
# Comparar versión local vs remota
```

---

## Resumen: Paso a paso para usuario final

```
┌─────────────────────────────────────────────────┐
│ Usuario descarga Traductor.exe o Traductor.app  │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
         ┌──────────────────────┐
         │ Ejecuta el archivo   │
         └──────────────┬───────┘
                        │
                        ▼
         ┌──────────────────────────────────────┐
         │ launcher.py:                         │
         │ 1. Crea .env si no existe            │
         │ 2. Levanta FastAPI en background     │
         │ 3. Abre ventana de login (tkinter)   │
         └──────────────┬───────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────────────┐
         │ GUI: Login (email + contraseña)      │
         └──────────────┬───────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────────────┐
         │ GUI: Botón "Iniciar escucha"         │
         │ • Captura audio                      │
         │ • Envía fragmentos al servidor       │
         │ • Recibe traducción                  │
         │ • Muestra en pantalla + TTS          │
         └──────────────┬───────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────────────┐
         │ Usuario cierra la ventana            │
         │ launcher.py limpia (mata servidor)   │
         └──────────────────────────────────────┘
```

---

## Preguntas frecuentes

**¿Debo instalar Python?**
No, el .exe y .app incluyen Python embebido.

**¿Qué pasa si cierro la ventana sin hacer "Detener"?**
El launcher detecta que se cerró y mata el servidor automáticamente.

**¿Puedo usar el .exe en una USB?**
Sí, copia la carpeta entera (con .env) a la USB y ejecuta desde allí.

**¿Cómo hago que el servidor se levante en un puerto diferente?**
Edita `launcher.py`, línea con `--port 8000` y cambia el número.

**¿Se pueden compilar a macOS desde Windows o viceversa?**
No, necesitas compilar en la misma OS donde se ejecutará. Usa máquinas virtuales o GitHub Actions CI si necesitas ambos.
