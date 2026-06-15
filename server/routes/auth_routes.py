"""
routes/auth_routes.py — Registro (cupón obligatorio salvo admin), login y estado.

ADMIN_EMAIL (en .env): ese correo se registra SIN cupón, queda marcado
como administrador y recibe acceso de 10 años. Desde la app puede generar
cupones ilimitados para otros usuarios.
"""
import os
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Coupon, utcnow
from ..schemas import RegisterRequest, LoginRequest, TokenResponse, UserStatus
from ..auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registra un usuario nuevo. Exige un cupón válido (no usado, no
    revocado). Al registrarse, el cupón se consume y la cuenta queda
    activa por duration_days (30 por defecto).
    """
    # 1) Email único
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    is_admin = bool(admin_email) and data.email.lower() == admin_email

    if is_admin:
        # 2a) El admin no necesita cupón: acceso de 10 años.
        user = User(
            nombre=data.nombre.strip(),
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            access_expires_at=utcnow() + timedelta(days=3650),
            is_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # 2b) Usuario normal: cupón obligatorio y válido.
        code = (data.coupon_code or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="Cupón obligatorio para registrarse")
        coupon = db.query(Coupon).filter(Coupon.code == code).first()
        if coupon is None or not coupon.is_available:
            raise HTTPException(status_code=400, detail="Cupón inválido, usado o revocado")

        user = User(
            nombre=data.nombre.strip(),
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            access_expires_at=utcnow() + timedelta(days=coupon.duration_days),
        )
        db.add(user)
        db.flush()
        coupon.used_by_user_id = user.id
        coupon.used_at = utcnow()
        db.commit()
        db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id),
        access_expires_at=user.access_expires_at,
    )


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Login con email + contraseña. Devuelve JWT de sesión (12 h)."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    # Mensaje genérico: no revelar si falló el email o la contraseña.
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    return TokenResponse(
        access_token=create_access_token(user.id),
        access_expires_at=user.access_expires_at,
    )


@router.get("/me", response_model=UserStatus)
def me(user: User = Depends(get_current_user)):
    """Estado de la cuenta: el cliente lo consulta para saber si el cupón sigue vigente."""
    return UserStatus(
        nombre=user.nombre,
        email=user.email,
        has_active_access=user.has_active_access,
        access_expires_at=user.access_expires_at,
        is_admin=bool(user.is_admin),
    )
