"""
routes/coupon_routes.py — Generación (solo admin) y canje de cupones.

La generación está protegida por el header X-Admin-Key, comparado en
tiempo constante contra ADMIN_API_KEY del .env. Solo el dueño del
sistema (quien posee esa clave) puede crear cupones.
"""
import os
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Coupon, User, utcnow
from ..schemas import CouponCreateRequest, CouponInfo, RedeemRequest, UserStatus
from ..auth import get_current_user

router = APIRouter(prefix="/coupons", tags=["Cupones"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")


def require_admin(x_admin_key: str = Header(default="")):
    """Verifica la clave de administrador en tiempo constante."""
    if not ADMIN_API_KEY or not secrets.compare_digest(x_admin_key, ADMIN_API_KEY):
        raise HTTPException(status_code=403, detail="Clave de administrador inválida")


def require_admin_user(user: User = Depends(get_current_user)) -> User:
    """Verifica que el usuario autenticado (JWT) sea administrador."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo el administrador puede generar cupones")
    return user


@router.post("/generate", response_model=list[CouponInfo])
def generate_coupons_as_admin(
    data: CouponCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_user),
):
    """[ADMIN por JWT] Genera N cupones desde la app, sin clave extra."""
    coupons = []
    for _ in range(data.quantity):
        coupon = Coupon(code=f"LM-{secrets.token_urlsafe(12)}", duration_days=data.duration_days)
        db.add(coupon)
        coupons.append(coupon)
    db.commit()
    return [CouponInfo(code=c.code, duration_days=c.duration_days, used=False, revoked=False) for c in coupons]


@router.post("/admin/generate", response_model=list[CouponInfo], dependencies=[Depends(require_admin)])
def generate_coupons(data: CouponCreateRequest, db: Session = Depends(get_db)):
    """[ADMIN] Genera N cupones aleatorios de un solo uso."""
    coupons = []
    for _ in range(data.quantity):
        # token_urlsafe(12) ≈ 16 caracteres aleatorios criptográficos
        coupon = Coupon(code=f"LM-{secrets.token_urlsafe(12)}", duration_days=data.duration_days)
        db.add(coupon)
        coupons.append(coupon)
    db.commit()
    return [CouponInfo(code=c.code, duration_days=c.duration_days, used=False, revoked=False) for c in coupons]


@router.get("/admin/list", response_model=list[CouponInfo], dependencies=[Depends(require_admin)])
def list_coupons(db: Session = Depends(get_db)):
    """[ADMIN] Lista todos los cupones y su estado."""
    return [
        CouponInfo(
            code=c.code,
            duration_days=c.duration_days,
            used=c.used_by_user_id is not None,
            revoked=c.revoked,
        )
        for c in db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    ]


@router.post("/admin/revoke/{code}", dependencies=[Depends(require_admin)])
def revoke_coupon(code: str, db: Session = Depends(get_db)):
    """[ADMIN] Revoca un cupón no usado para que ya no pueda canjearse."""
    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if coupon is None:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    coupon.revoked = True
    db.commit()
    return {"detail": f"Cupón {code} revocado"}


@router.post("/redeem", response_model=UserStatus)
def redeem_coupon(data: RedeemRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Canjea un cupón en una cuenta existente (renovación).
    Si el acceso sigue vigente, los días se SUMAN al final del periodo;
    si ya expiró, el nuevo periodo arranca desde ahora.
    """
    coupon = db.query(Coupon).filter(Coupon.code == data.coupon_code.strip()).first()
    if coupon is None or not coupon.is_available:
        raise HTTPException(status_code=400, detail="Cupón inválido, usado o revocado")

    base = user.access_expires_at if user.has_active_access else utcnow()
    user.access_expires_at = base + timedelta(days=coupon.duration_days)

    coupon.used_by_user_id = user.id
    coupon.used_at = utcnow()
    db.commit()
    db.refresh(user)

    return UserStatus(
        nombre=user.nombre,
        email=user.email,
        has_active_access=user.has_active_access,
        access_expires_at=user.access_expires_at,
    )
