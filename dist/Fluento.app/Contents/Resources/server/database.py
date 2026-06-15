"""
database.py — Conexión y sesión de base de datos (SQLAlchemy).

Por defecto usa SQLite (archivo translator.db) para el prototipo.
Para producción basta cambiar DATABASE_URL a PostgreSQL, sin tocar código.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# URL de conexión; viene del .env (cargado en main.py)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./translator.db")

# check_same_thread=False es necesario solo en SQLite porque FastAPI
# atiende peticiones en varios hilos.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# Fábrica de sesiones: cada petición HTTP abre y cierra la suya.
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Clase base de la que heredan todos los modelos ORM.
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
