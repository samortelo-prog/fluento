"""
main.py — Punto de entrada del servidor (FastAPI).

Ejecutar:
    uvicorn server.main:app --host 0.0.0.0 --port 8000

Documentación interactiva automática en http://localhost:8000/docs
"""
import logging

from dotenv import load_dotenv

# Cargar .env ANTES de importar módulos que leen variables de entorno.
load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from .database import Base, engine  # noqa: E402
from .routes import auth_routes, coupon_routes, translate_routes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Crear tablas si no existen (suficiente para prototipo; en producción
# usar migraciones con Alembic).
Base.metadata.create_all(bind=engine)

# Migración ligera: añadir is_admin si la BD ya existía sin esa columna.
try:
    from sqlalchemy import text
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(users)"))]
        if "is_admin" not in cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
            conn.commit()
except Exception:
    pass

app = FastAPI(
    title="Traductor en Tiempo Real",
    description="Whisper + GPT con registro de usuarios y acceso por cupones de 30 días",
    version="1.0.0",
)

# CORS abierto para el prototipo; en producción restringir allow_origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(coupon_routes.router)
app.include_router(translate_routes.router)


@app.get("/health", tags=["Sistema"])
def health():
    """Comprobación de vida; el cliente la usa para reconexión."""
    return {"status": "ok"}
