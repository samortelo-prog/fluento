"""
gui_client.py — v6: diseño oscuro, paneles iguales, botones legibles,
ventana flotante, mejor detección de idioma, términos médicos/legales.
"""
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import sys

from .api_client import ApiClient, AccessExpiredError
from .audio_capture import AudioCapture, list_input_devices
from .tts_engine import TTSEngine

# ── PALETA ────────────────────────────────────────────────────────────────────
BG      = "#0F1117"
SURFACE = "#1A1D2B"
BORDER  = "#2C3050"
ACCENT  = "#5B9BF8"     # azul botones principales
ACCENT2 = "#3DD68C"     # verde éxito / inglés
WARN    = "#F5A623"     # naranja canjear
DANGER  = "#F05C5C"     # rojo detener
TXT     = "#DDE1EE"     # texto principal (suficiente contraste)
TXT2    = "#6B7299"     # texto secundario
TXT_ES  = "#7EC8F7"     # panel español
TXT_EN  = "#5CDBA0"     # panel inglés

# Botones: texto SIEMPRE blanco o negro claro según fondo
BTN_TXT_DARK  = "#0F1117"   # texto sobre fondos claros (verde, azul claro)
BTN_TXT_LIGHT = "#DDE1EE"   # texto sobre fondos oscuros (rojo, borde)

if sys.platform == "darwin":
    FH = ("SF Pro Display", 14, "bold")
    FB = ("SF Pro Text",    11)
    FM = ("Menlo",          11)
    FS = ("SF Pro Text",     9)
else:
    FH = ("Segoe UI", 14, "bold")
    FB = ("Segoe UI", 11)
    FM = ("Consolas", 11)
    FS = ("Segoe UI",  9)


def _btn(parent, text, cmd, bg=ACCENT, fg=BTN_TXT_DARK, px=18, py=8, **kw):
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                     font=FB, relief=tk.FLAT, bd=0, padx=px, pady=py,
                     cursor="hand2", **kw)

def _entry(parent, w=34, show=""):
    return tk.Entry(parent, width=w, show=show, bg=BORDER, fg=TXT,
                    insertbackground=TXT, relief=tk.FLAT, font=FB,
                    highlightthickness=1, highlightcolor=ACCENT,
                    highlightbackground=BORDER)

def _lbl(parent, text, fg=TXT2, font=None, bg=SURFACE):
    return tk.Label(parent, text=text, bg=bg, fg=fg, font=font or FS)


class FloatingWindow:
    """Ventana flotante que acumula todo el historial de traducción."""
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.title("Fluento — En vivo")
        self.win.geometry("560x400+20+20")
        self.win.attributes("-topmost", True)
        self.win.configure(bg=SURFACE)
        self.win.resizable(True, True)

        # Header
        hdr = tk.Frame(self.win, bg=BORDER, pady=6)
        hdr.pack(fill=tk.X)
        # Logo pequeño en ventana flotante
        try:
            from assets import LOGO_SIDEBAR_GIF
            _logo_fl = tk.PhotoImage(data=LOGO_SIDEBAR_GIF)
            # Escalar a 24px aproximado usando subsample
            _logo_fl_small = _logo_fl.subsample(2, 2)
            tk.Label(hdr, image=_logo_fl_small, bg=BORDER).pack(side=tk.LEFT, padx=(8,4))
            hdr._logo = _logo_fl_small  # evitar garbage collection
        except Exception:
            pass
        tk.Label(hdr, text="Fluento — Traducción en vivo", bg=BORDER, fg=TXT, font=FB).pack(side=tk.LEFT, padx=4)
        tk.Button(hdr, text="🗑 Limpiar", command=self.clear, bg=BORDER, fg=TXT2,
                  relief=tk.FLAT, font=FS, cursor="hand2").pack(side=tk.RIGHT, padx=4)
        tk.Button(hdr, text="✕", command=self.hide, bg=BORDER, fg=TXT2,
                  relief=tk.FLAT, font=FB, cursor="hand2").pack(side=tk.RIGHT, padx=4)

        # Área de historial con scroll
        self.txt = scrolledtext.ScrolledText(
            self.win, wrap=tk.WORD, font=(FM[0], 11),
            bg="#0F1117", fg="#DDE1EE", bd=0, relief=tk.FLAT,
            padx=12, pady=8, state=tk.DISABLED
        )
        self.txt.pack(fill=tk.BOTH, expand=True)
        self.txt.tag_config("es",   foreground=TXT_ES, font=(FM[0], 11, "bold"))
        self.txt.tag_config("en",   foreground=TXT_EN, font=(FM[0], 11, "bold"))
        self.txt.tag_config("time", foreground=TXT2,   font=(FM[0],  9))

        self.win.withdraw()

    def update(self, es="", en=""):
        import time as _time
        self.txt.config(state=tk.NORMAL)
        ts = _time.strftime("%H:%M:%S")
        self.txt.insert(tk.END, f"[{ts}]\n", "time")
        if es:
            self.txt.insert(tk.END, f"\U0001f1ea\U0001f1f8 {es}\n", "es")
        if en:
            self.txt.insert(tk.END, f"\U0001f1fa\U0001f1f8 {en}\n\n", "en")
        self.txt.see(tk.END)
        self.txt.config(state=tk.DISABLED)

    def clear(self):
        self.txt.config(state=tk.NORMAL)
        self.txt.delete(1.0, tk.END)
        self.txt.config(state=tk.DISABLED)

    def show(self):
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        self.win.withdraw()


class App:
    def __init__(self, root, server_url="http://127.0.0.1:8000", groq_key=""):
        self.root = root
        self.root.title("Fluento — Traducción en Tiempo Real")
        self.root.configure(bg=BG)
        self.root.geometry("1340x860")
        self.root.minsize(900, 640)

        self.api = ApiClient(server_url, groq_key=groq_key)
        self.capture = None
        self.running = False
        self.user_status = None
        self._devices = []
        self.device_var = tk.StringVar()

        self._last_es = ""
        self._last_en = ""

        self._build()
        self._refresh_devices()

        # Auto-login si hay sesión guardada
        self.root.after(500, self._load_session)

        # Ventana flotante (se crea aquí para que exista siempre)
        self.floating = FloatingWindow(self.root)

        # Al minimizar → mostrar flotante
        self.root.bind("<Unmap>", self._on_minimize)
        self.root.bind("<Map>",   self._on_restore)

    # ── CONSTRUCCIÓN ─────────────────────────────────────────────────────────
    def _build(self):
        # SIDEBAR
        self.sidebar = tk.Frame(self.root, bg="#F0F0F0", width=210)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        self._build_sidebar()

        # MAIN
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.pages = {}
        for n in ("cuenta", "traductor", "admin"):
            self.pages[n] = tk.Frame(self.main, bg=BG)

        self._build_cuenta()
        self._build_traductor()
        self._build_admin()
        self._show("cuenta")

    def _build_sidebar(self):
        s = self.sidebar
        tk.Frame(s, bg=SURFACE, height=20).pack()
        # Logo Fluento en sidebar
        try:
            from assets import LOGO_SIDEBAR_GIF
            _logo_sb = tk.PhotoImage(data=LOGO_SIDEBAR_GIF)
            lbl_sb = tk.Label(s, image=_logo_sb, bg="#F0F0F0")
            lbl_sb.image = _logo_sb
            lbl_sb.pack(pady=(8,0))
        except Exception:
            tk.Label(s, text="F", bg="#5B9BF8", fg="white",
                     font=("Helvetica", 28, "bold"), width=2).pack(pady=(8,0))
        tk.Label(s, text="Fluento", bg="#F0F0F0", fg="#0A2463",
                 font=FH, justify=tk.CENTER).pack(pady=(4,0))
        tk.Label(s, text="Translate. Communicate. Connect.", bg="#F0F0F0", fg="#5B9BF8",
                 font=(FS[0], 8), justify=tk.CENTER).pack(pady=(0, 16))
        tk.Frame(s, bg="#CCCCCC", height=1).pack(fill=tk.X, padx=14, pady=4)

        self._nav = {}
        for key, lbl in [("cuenta","👤  Mi Cuenta"),("traductor","💬  Traductor"),("admin","🔑  Admin")]:
            b = tk.Button(s, text=lbl, bg="#F0F0F0", fg="#111111",
                          activebackground="#DDDDDD", activeforeground="#111111",
                          font=FB, relief=tk.FLAT, bd=0, padx=18, pady=10,
                          anchor=tk.W, cursor="hand2",
                          command=lambda k=key: self._show(k))
            b.pack(fill=tk.X, padx=6, pady=2)
            self._nav[key] = b
        self._nav["admin"].pack_forget()

        tk.Frame(s, bg="#CCCCCC", height=1).pack(fill=tk.X, padx=14, pady=10)
        self.lbl_session = tk.Label(s, text="Sin sesión", bg="#F0F0F0", fg="#555555",
                                    font=FS, wraplength=180, justify=tk.CENTER)
        self.lbl_session.pack(padx=10, pady=(4,0))
        tk.Button(s, text="Cerrar sesión", command=self._logout,
                  bg="#F0F0F0", fg="#CC3333", font=FS, relief=tk.FLAT,
                  cursor="hand2").pack(pady=(2,8))

    def _show(self, name):
        for f in self.pages.values(): f.pack_forget()
        self.pages[name].pack(fill=tk.BOTH, expand=True)
        for k, b in self._nav.items():
            b.config(bg="#DDDDDD" if k==name else "#F0F0F0",
                     fg="#111111")

    # ── CUENTA ───────────────────────────────────────────────────────────────
    def _build_cuenta(self):
        p = self.pages["cuenta"]
        tk.Label(p, text="Mi Cuenta", bg=BG, fg=TXT, font=FH).pack(anchor=tk.W, padx=30, pady=(24,16))

        body = tk.Frame(p, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=30)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # LOGIN (col 0)
        col0 = tk.Frame(body, bg=BG)
        col0.grid(row=0, column=0, sticky="nsew", padx=(0,12))
        self._card_login(col0)
        tk.Frame(col0, bg=BG, height=12).pack()
        self._card_redeem(col0)

        # REGISTRO (col 1)
        col1 = tk.Frame(body, bg=BG)
        col1.grid(row=0, column=1, sticky="nsew", padx=(12,0))
        self._card_register(col1)

    def _card(self, parent, title):
        f = tk.Frame(parent, bg=SURFACE, padx=20, pady=16)
        f.pack(fill=tk.X)
        tk.Label(f, text=title, bg=SURFACE, fg=TXT, font=FH).pack(anchor=tk.W, pady=(0,12))
        return f

    def _row(self, card, label, show=""):
        _lbl(card, label).pack(anchor=tk.W)
        e = _entry(card, show=show)
        e.pack(fill=tk.X, pady=(3,10))
        return e

    def _card_login(self, parent):
        c = self._card(parent, "Iniciar sesión")
        self.e_email = self._row(c, "Correo electrónico")
        self.e_pass  = self._row(c, "Contraseña", show="•")
        _btn(c, "Entrar →", self._login, bg=ACCENT, fg=BTN_TXT_DARK).pack(anchor=tk.W, pady=(4,0))

    def _card_redeem(self, parent):
        c = self._card(parent, "Renovar acceso")
        self.e_redeem = self._row(c, "Código de cupón")
        _btn(c, "Canjear", self._redeem, bg=WARN, fg=BTN_TXT_DARK).pack(anchor=tk.W, pady=(4,0))

    def _card_register(self, parent):
        c = self._card(parent, "Crear cuenta nueva")
        self.e_nombre = self._row(c, "Nombre completo")
        self.e_remail = self._row(c, "Correo electrónico")
        self.e_rpass  = self._row(c, "Contraseña (mín. 8 caracteres)", show="•")
        self.e_coupon = self._row(c, "Cupón de acceso")
        _lbl(c, "El correo admin no necesita cupón").pack(anchor=tk.W, pady=(0,8))
        _btn(c, "Crear cuenta →", self._register, bg=ACCENT2, fg=BTN_TXT_DARK).pack(anchor=tk.W)

    # ── TRADUCTOR ─────────────────────────────────────────────────────────────
    def _build_traductor(self):
        p = self.pages["traductor"]

        # Header
        hdr = tk.Frame(p, bg=BG)
        hdr.pack(fill=tk.X, padx=28, pady=(20,8))
        tk.Label(hdr, text="Fluento — Traducción en vivo", bg=BG, fg=TXT, font=FH).pack(side=tk.LEFT)
        self.lbl_ind = tk.Label(hdr, text="● Detenido", bg=BG, fg=TXT2, font=FB)
        self.lbl_ind.pack(side=tk.RIGHT)

        # Dispositivo
        dev = tk.Frame(p, bg=SURFACE, pady=8)
        dev.pack(fill=tk.X, padx=28)
        _lbl(dev, "Fuente de audio:", fg=TXT2, bg=SURFACE).pack(side=tk.LEFT, padx=(12,6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("D.TCombobox", fieldbackground=BORDER, background=BORDER,
                        foreground=TXT, selectbackground=BORDER, selectforeground=TXT)
        self.cmb = ttk.Combobox(dev, textvariable=self.device_var,
                                 width=42, state="readonly", style="D.TCombobox")
        self.cmb.pack(side=tk.LEFT, padx=6)
        _btn(dev, "↺", self._refresh_devices, bg="#4A5080", fg="#000000", px=10, py=4).pack(side=tk.LEFT, padx=4)
        _btn(dev, "📱 Celular como mic", self._ayuda_cel, bg="#4A5080", fg="#000000", px=10, py=4).pack(side=tk.LEFT, padx=4)


        # Controles
        ctrl = tk.Frame(p, bg=BG, pady=8)
        ctrl.pack(fill=tk.X, padx=28)
        self.btn_start = _btn(ctrl, "▶  Iniciar", self._start, bg=ACCENT2, fg=BTN_TXT_DARK, px=22, py=10)
        self.btn_start.pack(side=tk.LEFT, padx=(0,8))
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop = _btn(ctrl, "■  Detener", self._stop, bg=DANGER, fg=BTN_TXT_LIGHT, px=22, py=10)
        self.btn_stop.pack(side=tk.LEFT)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_lat = tk.Label(ctrl, text="", bg=BG, fg=TXT2, font=FS)
        self.lbl_lat.pack(side=tk.LEFT, padx=16)

        # Botón ventana flotante
        _btn(ctrl, "⧉ Ventana flotante", self._toggle_float,
             bg=BORDER, fg="#000000", px=14, py=10).pack(side=tk.RIGHT)

        # ── DOS PANELES DE IGUAL TAMAÑO ──
        panels = tk.PanedWindow(p, orient=tk.HORIZONTAL, bg=BG,
                                 sashwidth=6, sashrelief=tk.FLAT,
                                 handlesize=0)
        panels.pack(fill=tk.BOTH, expand=True, padx=28, pady=(8,20))

        # Panel ES
        frm_es = tk.Frame(panels, bg=SURFACE, width=500)
        panels.add(frm_es, stretch="always", minsize=300)
        tk.Label(frm_es, text="🇪🇸  ESPAÑOL", bg=SURFACE, fg=TXT_ES, font=FH).pack(anchor=tk.W, padx=14, pady=(10,6))
        self.txt_es = scrolledtext.ScrolledText(frm_es, wrap=tk.WORD, font=FM,
                                                 bg="#0F1117", fg="#DDE1EE", bd=0, relief=tk.FLAT,
                                                 padx=10, pady=8, insertbackground="#DDE1EE")
        self.txt_es.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,8))
        self.txt_es.tag_config("orig", foreground=TXT2)
        self.txt_es.tag_config("trad", foreground=TXT_ES, font=(FM[0], FM[1], "bold"))
        self.txt_es.tag_config("err",  foreground=DANGER)

        # Panel EN  (mismo peso → mismo tamaño)
        frm_en = tk.Frame(panels, bg=SURFACE, width=500)
        panels.add(frm_en, stretch="always", minsize=300)
        tk.Label(frm_en, text="🇺🇸  ENGLISH", bg=SURFACE, fg=TXT_EN, font=FH).pack(anchor=tk.W, padx=14, pady=(10,6))
        self.txt_en = scrolledtext.ScrolledText(frm_en, wrap=tk.WORD, font=FM,
                                                 bg="#0F1117", fg="#DDE1EE", bd=0, relief=tk.FLAT,
                                                 padx=10, pady=8, insertbackground="#DDE1EE")
        self.txt_en.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0,8))
        self.txt_en.tag_config("orig", foreground=TXT2)
        self.txt_en.tag_config("trad", foreground=TXT_EN, font=(FM[0], FM[1], "bold"))
        self.txt_en.tag_config("err",  foreground=DANGER)

    # ── ADMIN ─────────────────────────────────────────────────────────────────
    def _build_admin(self):
        p = self.pages["admin"]
        tk.Label(p, text="Panel Admin", bg=BG, fg=TXT, font=FH).pack(anchor=tk.W, padx=30, pady=(24,16))

        box = tk.Frame(p, bg=SURFACE, padx=20, pady=16)
        box.pack(fill=tk.X, padx=30)
        tk.Label(box, text="Generar cupones de acceso", bg=SURFACE, fg=TXT, font=FH).pack(anchor=tk.W, pady=(0,12))

        row = tk.Frame(box, bg=SURFACE)
        row.pack(fill=tk.X, pady=(0,12))

        # Cantidad
        tk.Label(row, text="Cantidad", bg=SURFACE, fg=TXT2, font=FS).grid(row=0,column=0,sticky=tk.W)
        self.spn_qty = ttk.Spinbox(row, from_=1, to=100, width=7, font=FB)
        self.spn_qty.set(1)
        self.spn_qty.grid(row=1,column=0,padx=(0,24),pady=(4,0))

        # Días
        tk.Label(row, text="Días de acceso", bg=SURFACE, fg=TXT2, font=FS).grid(row=0,column=1,sticky=tk.W)
        self.spn_days = ttk.Spinbox(row, from_=1, to=365, width=7, font=FB)
        self.spn_days.set(30)
        self.spn_days.grid(row=1,column=1,padx=(0,24),pady=(4,0))

        # Botones (texto claro sobre fondo oscuro/acento)
        brow = tk.Frame(box, bg=SURFACE)
        brow.pack(fill=tk.X, pady=(4,16))
        _btn(brow, "Generar cupones", self._admin_gen, bg=ACCENT, fg=BTN_TXT_DARK, px=20, py=9).pack(side=tk.LEFT)
        _btn(brow, "Copiar todos",    self._admin_copy, bg=BORDER, fg=TXT, px=16, py=9).pack(side=tk.LEFT, padx=(10,0))

        tk.Label(box, text="Cupones generados", bg=SURFACE, fg=TXT2, font=FS).pack(anchor=tk.W)
        self.txt_admin = scrolledtext.ScrolledText(box, height=18, font=FM,
                                                    bg="#0F1117", fg="#3DD68C", bd=0,
                                                    relief=tk.FLAT, padx=8, pady=8)
        self.txt_admin.pack(fill=tk.BOTH, expand=True, pady=(4,0))
        self.txt_admin.insert(tk.END, "# Los cupones aparecerán aquí.\n")

    # ── DISPOSITIVOS ──────────────────────────────────────────────────────────
    def _refresh_devices(self):
        self._devices = list_input_devices()
        names = [f"[{i}] {n}" for i, n in self._devices]
        self.cmb["values"] = names
        # Prioridad: MacBook Microphone > primer dispositivo
        mac_mic = next((s for s in names if "macbook pro microphone" in s.lower()), None)
        self.device_var.set(mac_mic or (names[0] if names else ""))

    def _selected_device(self):
        val = self.device_var.get()
        if val.startswith("["):
            try: return int(val.split("]")[0][1:])
            except: pass
        return None

    def _activar_modo_llamada(self):
        """Configura AirPods + BlackHole automáticamente con un clic."""
        import subprocess

        # Buscar dispositivos
        self._refresh_devices()
        airpods_name = next((n for _, n in self._devices
                             if any(k in n.lower() for k in ["airpod","air pod"])), None)
        blackhole_entry = next((f"[{i}] {n}" for i, n in self._devices
                                if "blackhole 2" in n.lower()), None)

        # Validar AirPods
        if not airpods_name:
            messagebox.showwarning("AirPods no encontrados",
                "No veo tus AirPods conectados.\n\n"
                "1. Abre Centro de control (esquina superior derecha)\n"
                "2. Haz clic en el icono de audio\n"
                "3. Selecciona tus AirPods\n\n"
                "Luego pulsa este boton de nuevo.")
            return

        # Seleccionar AirPods como fuente en la app
        airpods_entry = next((f"[{i}] {n}" for i, n in self._devices
                              if "airpod" in n.lower()), None)
        if airpods_entry:
            self.device_var.set(airpods_entry)

        # Confirmar e iniciar
        ok = messagebox.askokcancel("🎧 Modo llamada listo",
            "AirPods seleccionados como fuente de audio.\n\n"
            "La app capturara el audio de la llamada\n"
            "directamente desde tus AirPods.\n\n"
            "Iniciar traduccion ahora?")
        if ok:
            self._start()

    def _ayuda_cel(self):
        messagebox.showinfo("Celular como micrófono",
            "OPCIÓN 1 — iPhone (Continuity Mic, sin instalar nada):\n"
            "  1. iPhone y Mac en el mismo Wi-Fi + Bluetooth activado\n"
            "  2. Mismo Apple ID en ambos\n"
            "  3. Desbloquea tu iPhone y acércalo al Mac\n"
            "  4. Pulsa ↺ en la app → busca 'iPhone Microphone'\n"
            "  Requiere macOS 13+ y iOS 16+\n\n"
            "OPCIÓN 2 — Cualquier Android o iPhone:\n"
            "  Instala 'Microphone Live' (iOS) o 'WO Mic' (Android/iOS)\n"
            "  Conecta por Wi-Fi → aparece como dispositivo de audio\n"
            "  Pulsa ↺ para actualizar la lista\n\n"
            "OPCIÓN 3 — Llamadas Zoom/Meet:\n"
            "  Usa BlackHole para capturar el audio de la llamada\n"
            "  (pulsa el botón 'Zoom / YouTube' para más info)")

    def _ayuda_audio(self):
        messagebox.showinfo("Capturar audio del sistema",
            "Para traducir Zoom, Meet, Teams o YouTube:\n\n"
            "1. Descarga BlackHole 2ch (gratis):\n"
            "   https://existential.audio/blackhole/\n"
            "2. Instala y reinicia el Mac\n"
            "3. Spotlight → 'Audio MIDI Setup'\n"
            "4. '+' → 'Crear dispositivo de salida múltiple'\n"
            "5. Marca: tus altavoces + BlackHole 2ch\n"
            "6. Ajustes del sistema → Sonido → Salida → ese dispositivo\n"
            "7. En la app ↺ → selecciona 'BlackHole 2ch'\n\n"
            "Windows: VB-Audio Virtual Cable (gratis)\n"
            "https://vb-audio.com/Cable/")

    # ── AUTH ──────────────────────────────────────────────────────────────────
    def _login(self):
        email = self.e_email.get().strip()
        pw    = self.e_pass.get()
        if not email or not pw:
            messagebox.showerror("Error", "Correo y contraseña obligatorios"); return
        try:
            self.api.login(email, pw)
            self.user_status = self.api.me()
            self._save_session(email, pw)
            self._after_auth()
        except Exception as e:
            messagebox.showerror("Login fallido", str(e))

    def _register(self):
        nombre = self.e_nombre.get().strip()
        email  = self.e_remail.get().strip()
        pw     = self.e_rpass.get()
        coupon = self.e_coupon.get().strip()
        if not nombre or not email or not pw:
            messagebox.showerror("Error", "Nombre, correo y contraseña obligatorios"); return
        if len(pw) < 8:
            messagebox.showerror("Error", "Contraseña mínimo 8 caracteres"); return
        try:
            self.api.register(nombre, email, pw, coupon)
            self.user_status = self.api.me()
            self._save_session(email, pw)
            messagebox.showinfo("¡Bienvenido!", f"Cuenta creada para {nombre}.")
            self._after_auth()
        except Exception as e:
            messagebox.showerror("Registro fallido", str(e))

    def _redeem(self):
        code = self.e_redeem.get().strip()
        if not code: return
        try:
            self.api.redeem(code)
            self.user_status = self.api.me()
            messagebox.showinfo("OK", "Acceso extendido.")
            self._after_auth()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _save_session(self, email, password):
        """Guarda credenciales en .session para auto-login."""
        import json, pathlib
        session_file = pathlib.Path(__file__).parent.parent / ".session"
        session_file.write_text(json.dumps({"email": email, "password": password}))

    def _load_session(self):
        """Carga sesión guardada al arrancar."""
        import json, pathlib
        session_file = pathlib.Path(__file__).parent.parent / ".session"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                self.api.login(data["email"], data["password"])
                self.user_status = self.api.me()
                self._after_auth()
                return True
            except Exception:
                session_file.unlink(missing_ok=True)
        return False

    def _logout(self):
        """Cierra sesión y borra la sesión guardada."""
        import pathlib
        session_file = pathlib.Path(__file__).parent.parent / ".session"
        session_file.unlink(missing_ok=True)
        self.user_status = None
        self.btn_start.config(state=tk.DISABLED)
        self.lbl_session.config(text="Sin sesión", fg="#555555")
        self._show("cuenta")

    def _after_auth(self):
        st = self.user_status
        extra = " · Admin" if st.get("is_admin") else ""
        if st["has_active_access"]:
            self.lbl_session.config(text=f"✓ {st['nombre']}{extra}", fg=ACCENT2)
            self.btn_start.config(state=tk.NORMAL)
        else:
            self.lbl_session.config(text="⛔ Acceso expirado", fg=DANGER)
            self.btn_start.config(state=tk.DISABLED)
        if st.get("is_admin") and st.get("email", "").lower() == "samortelo@gmail.com":
            self._nav["admin"].pack(fill=tk.X, padx=6, pady=2)
        self._show("traductor")

    # ── ADMIN ─────────────────────────────────────────────────────────────────
    def _admin_gen(self):
        try:
            qty  = int(self.spn_qty.get())
            days = int(self.spn_days.get())
            cups = self.api.generate_coupons(qty, days)
            self._last_codes = [c["code"] for c in cups]
            self.txt_admin.insert(tk.END,
                f"\n# {time.strftime('%H:%M:%S')} — {qty} cupón(es) · {days} días\n")
            for code in self._last_codes:
                self.txt_admin.insert(tk.END, code + "\n")
            self.txt_admin.see(tk.END)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _admin_gen_trial(self):
        """Genera cupones de prueba de 7 días para intérpretes."""
        try:
            qty = int(self.spn_trial.get())
            cups = self.api.generate_coupons(qty, 7)
            self._last_codes = [c["code"] for c in cups]
            self.txt_admin.insert(tk.END,
                f"\n# {time.strftime('%H:%M:%S')} — {qty} cupón(es) PRUEBA GRATUITA · 7 días\n")
            for code in self._last_codes:
                self.txt_admin.insert(tk.END, code + "\n")
            self.txt_admin.see(tk.END)
            messagebox.showinfo("Cupones generados",
                f"{qty} cupón(es) de prueba generados (7 días).\n\n"
                "Envíalos a los intérpretes para que prueben la app gratis.\n"
                "Haz clic en 'Copiar' para copiarlos al portapapeles.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _admin_copy(self):
        codes = getattr(self, "_last_codes", [])
        if codes:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(codes))
            messagebox.showinfo("Copiado", f"{len(codes)} cupón(es) en el portapapeles.")

    # ── TRADUCCIÓN ────────────────────────────────────────────────────────────
    def _start(self):
        if not self.user_status or not self.user_status["has_active_access"]:
            messagebox.showerror("Error", "Inicia sesión primero"); return
        self.running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_ind.config(text="● Escuchando…", fg=ACCENT2)
        self.txt_es.delete(1.0, tk.END)
        self.txt_en.delete(1.0, tk.END)

        self.capture = AudioCapture(device=self._selected_device())
        try:
            self.capture.start()
        except Exception as e:
            messagebox.showerror("Audio", f"No pude abrir el dispositivo:\n{e}")
            self._stop(); return

        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        ctx_es = ctx_en = ""
        while self.running:
            chunk = self.capture.get_chunk(timeout=0.5)
            if chunk is None: continue
            t0 = time.time()
            self._lat("⏱ procesando…")
            try:
                wav = ApiClient._to_wav_bytes(chunk)
                transcript = self.api.transcribe_with_groq(wav)
            except Exception as e:
                self._we(f"❌ {e}\n", "err"); continue

            if not transcript: continue

            # Detección de idioma más robusta
            es_markers = set("áéíóúñü¿¡àèìòùâêîôûäëïöü")
            es_words = {"el","la","los","las","de","que","en","un","una",
                        "es","son","con","por","para","del","al","se","le"}
            words_lower = set(transcript.lower().split())
            es_score = sum(1 for c in transcript.lower() if c in es_markers)
            es_score += sum(2 for w in words_lower if w in es_words)
            is_es = es_score > 2

            try:
                def _es_misma(a, b):
                    return a.lower().strip() == b.lower().strip()

                if is_es:
                    trad = self.api.translate_with_groq(transcript, "en", context=ctx_en)
                    if _es_misma(trad, transcript):
                        trad = self.api.translate_with_groq(
                            "Translate to English: " + transcript, "en", context="")
                    if not trad or _es_misma(trad, transcript):
                        trad = "—"
                    self._we(f"{transcript}\n", "orig")
                    self._we(f"→ {trad}\n\n", "trad")
                    self._wen(f"{trad}\n\n", "trad")
                    ctx_es, ctx_en = transcript, trad
                    self._last_es = transcript
                    self._last_en = trad
                else:
                    trad = self.api.translate_with_groq(transcript, "es", context=ctx_es)
                    if _es_misma(trad, transcript):
                        trad = self.api.translate_with_groq(
                            "Translate to Spanish: " + transcript, "es", context="")
                    if not trad or _es_misma(trad, transcript):
                        trad = "—"
                    self._wen(f"{transcript}\n", "orig")
                    self._wen(f"→ {trad}\n\n", "trad")
                    self._we(f"{trad}\n\n", "trad")
                    ctx_en, ctx_es = transcript, trad
                    self._last_en = transcript
                    self._last_es = trad
                # Actualizar ventana flotante
                self.root.after(0, lambda: self.floating.update(self._last_es, self._last_en))
            except Exception as e:
                self._we(f"❌ {e}\n", "err"); continue

            self._lat(f"✓ {time.time()-t0:.1f}s")

    def _we(self, t, tag=""):
        self.root.after(0, lambda: (self.txt_es.insert(tk.END, t, tag), self.txt_es.see(tk.END)))

    def _wen(self, t, tag=""):
        self.root.after(0, lambda: (self.txt_en.insert(tk.END, t, tag), self.txt_en.see(tk.END)))

    def _lat(self, t):
        self.root.after(0, lambda: self.lbl_lat.config(text=t))

    def _stop(self):
        self.running = False
        if self.capture: self.capture.stop()
        self.btn_start.config(state=tk.NORMAL if self.user_status else tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_ind.config(text="● Detenido", fg=TXT2)

    # ── VENTANA FLOTANTE ──────────────────────────────────────────────────────
    def _toggle_float(self):
        if self.floating.win.winfo_viewable():
            self.floating.hide()
            self.root.deiconify()
        else:
            self.floating.show()
            self.root.iconify()  # minimiza la app grande

    def _on_minimize(self, event):
        if event.widget == self.root and self.running:
            self.floating.show()

    def _on_restore(self, event):
        if event.widget == self.root:
            self.floating.hide()

    def _on_close(self):
        self._stop()
        self.root.destroy()


ModernTranslatorGUI = App

def main():
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app._on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
