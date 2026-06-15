
import base64
import io
import tkinter as tk

def load_logo(size=64):
    """Carga el logo de Fluento desde los assets."""
    try:
        from assets import LOGO_64_B64, LOGO_128_B64
        b64 = LOGO_128_B64 if size > 64 else LOGO_64_B64
        img_data = base64.b64decode(b64)
        from PIL import Image, ImageTk
        img = Image.open(io.BytesIO(img_data))
        img = img.resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None
