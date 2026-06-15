"""
auth.py — Seguridad: hashing de contraseñas (bcrypt) y tokens JWT.

- hash_password / verify_password: bcrypt genera y verifica el salt
  automáticamente; nunca se guarda la contraseña en claro.
- create_access_token: JWT firmado con HS256, expira en 12 horas.
- get_current_user: dependencia que valida el token en cada petición.
- require_active_access: además exige cupón vigente; es la puerta de
  entrada al endpoint de traducción.
"""
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

JWT_SECRET = os.getenv("JWT_SECRET", "INSEGURO-cambiar-en-.env")
JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()  # espera header: Authorization: Bearer <token>


def hash_password(plain: str) -> str:
    """Devuelve el hash bcrypt (incluye salt aleatorio interno)."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Compara en tiempo constante la contraseña con su hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    """Genera un JWT de sesión para el usuario."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_LIFETIME_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Valida el JWT y devuelve el usuario; 401 si es inválido/expirado."""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sesión expirada, inicia sesión de nuevo")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


def require_active_access(user: User = Depends(get_current_user)) -> User:
    """Bloquea (403) a usuarios sin cupón vigente. Protege la traducción."""
    if not user.has_active_access:
        raise HTTPException(
            status_code=403,
            detail="Tu acceso ha expirado. Canjea un cupón para reactivar tu cuenta.",
        )
    return user
