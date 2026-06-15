"""
schemas.py — Esquemas Pydantic (validación de entrada y formato de salida).
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- Autenticación ----------

class RegisterRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, description="Mínimo 8 caracteres")
    coupon_code: str | None = Field(default=None, description="Cupón (no requerido para el admin)")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    access_expires_at: datetime | None  # fin del acceso por cupón


class UserStatus(BaseModel):
    nombre: str
    email: EmailStr
    has_active_access: bool
    access_expires_at: datetime | None
    is_admin: bool = False


# ---------- Cupones ----------

class CouponCreateRequest(BaseModel):
    quantity: int = Field(default=1, ge=1, le=100)
    duration_days: int = Field(default=30, ge=1, le=365)


class CouponInfo(BaseModel):
    code: str
    duration_days: int
    used: bool
    revoked: bool


class RedeemRequest(BaseModel):
    coupon_code: str


# ---------- Traducción ----------

class TranslationResult(BaseModel):
    transcript: str    # texto original transcrito por Whisper
    translation: str   # texto traducido por GPT
