"""
launcher.py — Punto de entrada único con ventana de bienvenida mejorada.
"""
import os
import secrets
import subprocess
import sys
import time
import urllib.request
import webbrowser
import tkinter as tk
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.absolute()
ENV_PATH = PROJECT_ROOT / ".env"
ADMIN_EMAIL_DEFAULT = "samortelo@gmail.com"

BG     = "#0F1117"
SURF   = "#1A1D2B"
BORDER = "#2C3050"
ACCENT = "#5B9BF8"
GREEN  = "#3DD68C"
TXT    = "#DDE1EE"
TXT2   = "#7B8099"


def read_env() -> dict:
    data = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                data[k.strip()] = v.strip()
    return data


def write_env(values: dict):
    lines = ["# Configuración del Traductor (generada automáticamente)"]
    for k, v in values.items():
        lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n")


def ask_groq_key() -> str | None:
    """Ventana de bienvenida con info de horas gratis y video tutorial."""
    from tkinter import messagebox

    result = {"key": None}

    win = tk.Tk()
    win.title("Fluento — Configuración inicial")
    win.geometry("640x520")
    win.resizable(False, False)
    win.configure(bg=BG)

    # Título
    # Logo Fluento — GIF base64, sin Pillow
    try:
        from assets import LOGO_LAUNCHER_GIF
        _logo = tk.PhotoImage(data=LOGO_LAUNCHER_GIF)
        lbl = tk.Label(win, image=_logo, bg=BG)
        lbl.image = _logo
        lbl.pack(pady=(20,4))
    except Exception:
        tk.Label(win, text="", bg=BG).pack(pady=(20,4))
    tk.Label(win, text="Fluento",
             bg=BG, fg="#5B9BF8", font=("Helvetica", 22, "bold")).pack(pady=(0,2))
    tk.Label(win, text="Translate. Communicate. Connect.",
             bg=BG, fg=TXT2, font=("Helvetica", 10)).pack(pady=(0, 2))
    tk.Label(win, text="Configuración inicial (solo una vez)",
             bg=BG, fg=TXT2, font=("Helvetica", 10)).pack(pady=(0, 12))

    # Caja verde — horas gratis
    box = tk.Frame(win, bg=SURF, padx=20, pady=16)
    box.pack(fill=tk.X, padx=30, pady=(0, 14))
    tk.Label(box, text="🎁  Con tu API key de GROQ obtienes GRATIS:",
             bg=SURF, fg=GREEN,
             font=("Helvetica", 11, "bold")).pack(anchor=tk.W)
    for line in [
        "✓   $5 USD de crédito al registrarte",
        "✓   20–30 horas de traducción en tiempo real sin costo",
        "✓   Después: solo $0.15 / hora (muy económico)",
    ]:
        tk.Label(box, text=line, bg=SURF, fg=TXT,
                 font=("Helvetica", 10)).pack(anchor=tk.W, pady=1)

    # Video tutorial
    vid = tk.Frame(win, bg=BG)
    vid.pack(pady=(0, 10))
    tk.Label(vid, text="¿No sabes cómo obtener tu API key?",
             bg=BG, fg=TXT2, font=("Helvetica", 10)).pack(side=tk.LEFT)
    tk.Button(vid, text="▶  Ver video tutorial",
              command=lambda: webbrowser.open("https://www.youtube.com/watch?v=HmTkthAuenU"),
              bg="#FF0000", fg="#000000",
              font=("Helvetica", 10, "bold"),
              relief=tk.FLAT, padx=12, pady=5,
              cursor="hand2").pack(side=tk.LEFT, padx=(10, 0))

    # Enlace consola
    tk.Button(win,
              text="Ir a console.groq.com para obtener tu clave →",
              command=lambda: webbrowser.open("https://console.groq.com/keys"),
              bg=BG, fg=ACCENT,
              font=("Helvetica", 9, "underline"),
              relief=tk.FLAT, cursor="hand2").pack(pady=(0, 8))

    # Campo key
    tk.Label(win, text="Pega aquí tu GROQ API Key:",
             bg=BG, fg=TXT, font=("Helvetica", 10)).pack(anchor=tk.W, padx=30)

    entry_frame = tk.Frame(win, bg=BORDER, padx=1, pady=1)
    entry_frame.pack(fill=tk.X, padx=30, pady=(4, 2))
    entry = tk.Entry(entry_frame, show="•", bg=SURF, fg=TXT,
                     insertbackground=TXT, font=("Helvetica", 11),
                     relief=tk.FLAT, bd=0)
    entry.pack(fill=tk.X, ipady=8, padx=8)
    entry.focus()

    # Mostrar / ocultar
    show_var = tk.BooleanVar(value=False)
    def toggle():
        entry.config(show="" if show_var.get() else "•")
    tk.Checkbutton(win, text="Mostrar clave", variable=show_var,
                   command=toggle, bg=BG, fg=TXT2,
                   selectcolor=SURF,
                   font=("Helvetica", 9)).pack(anchor=tk.W, padx=30, pady=(2, 10))

    # Botón guardar
    def save():
        key = entry.get().strip()
        if not key or len(key) < 10:
            messagebox.showerror("Clave inválida",
                "Pega una clave válida de GROQ.\n"
                "Si no tienes una, mira el video tutorial.")
            return
        result["key"] = key
        win.destroy()

    tk.Button(win, text="  Guardar y comenzar →  ",
              command=save,
              bg=ACCENT, fg=BG,
              font=("Helvetica", 12, "bold"),
              relief=tk.FLAT, padx=20, pady=10,
              cursor="hand2").pack(pady=4)

    tk.Label(win,
             text="Tu clave se guarda solo en tu computadora y nunca se comparte.",
             bg=BG, fg=TXT2, font=("Helvetica", 9)).pack(pady=(6, 0))

    win.bind("<Return>", lambda e: save())
    win.mainloop()
    return result["key"]


def ensure_env() -> dict:
    env = read_env()
    env.setdefault("JWT_SECRET", secrets.token_hex(32))
    env.setdefault("ADMIN_API_KEY", secrets.token_hex(32))
    env.setdefault("DATABASE_URL", "sqlite:///./translator.db")
    env.setdefault("TRANSLATION_MODEL", "llama-3.3-70b-versatile")
    env.setdefault("ADMIN_EMAIL", ADMIN_EMAIL_DEFAULT)

    if not env.get("GROQ_API_KEY", "").strip():
        key = ask_groq_key()
        if not key:
            return {}
        env["GROQ_API_KEY"] = key

    write_env(env)
    return env


def start_server(env: dict) -> subprocess.Popen | None:
    full_env = {**os.environ, **env}
    cmd = [sys.executable, "-m", "uvicorn", "server.main:app",
           "--host", "127.0.0.1", "--port", "8000"]
    try:
        proc = subprocess.Popen(
            cmd, cwd=PROJECT_ROOT, env=full_env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        print(f"Error iniciando servidor: {e}")
        return None

    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1):
                return proc
        except Exception:
            time.sleep(0.5)
    return proc


def main():
    os.chdir(PROJECT_ROOT)

    env = ensure_env()
    if not env:
        return

    for k, v in env.items():
        os.environ[k] = v

    server = start_server(env)
    if server is None:
        from tkinter import messagebox
        messagebox.showerror("Error", "No se pudo iniciar el servidor.")
        return

    try:
        from client.gui_client import App
        root = tk.Tk()
        app = App(root, server_url="http://127.0.0.1:8000",
                  groq_key=env.get("GROQ_API_KEY", ""))
        root.protocol("WM_DELETE_WINDOW", app._on_close)
        root.mainloop()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
