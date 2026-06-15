"""
models.py — Tablas de la base de datos.

User   : usuarios registrados. La contraseña se guarda SOLO como hash
         bcrypt (con salt automático). access_expires_at marca hasta
         cuándo el usuario puede usar el traductor.
Coupon : cupones de acceso. Cada cupón es de un solo uso y otorga
         duration_days (30 por defecto) de acceso al canjearlo.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from .database import Base


def utcnow():
    """Hora actual en UTC (naive, consistente en toda la app)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)   # bcrypt(hash+salt)
    created_at = Column(DateTime, default=utcnow)
    # Fecha-hora hasta la cual el usuario tiene acceso al traductor.
    # NULL = nunca canjeó cupón. Se extiende al canjear nuevos cupones.
    access_expires_at = Column(DateTime, nullable=True)
    # Administrador: puede generar cupones desde la app y tiene acceso sin cupón.
    is_admin = Column(Boolean, default=False, nullable=False)

    @property
    def has_active_access(self) -> bool:
        """True si el usuario tiene un cupón vigente."""
        return self.access_expires_at is not None and self.access_expires_at > utcnow()


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, index=True, nullable=False)
    duration_days = Column(Integer, default=30, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    revoked = Column(Boolean, default=False)               # el admin puede anularlo
    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime, nullable=True)

    @property
    def is_available(self) -> bool:
        """Un cupón sirve si no fue revocado ni canjeado antes."""
        return (not self.revoked) and self.used_by_user_id is None
