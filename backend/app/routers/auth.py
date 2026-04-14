import logging
import bcrypt
from fastapi import APIRouter, HTTPException, Response, status, Depends
from app.config import get_settings
from app.deps import create_access_token, get_current_user
from app.schemas import LoginRequest, AuthMeResponse

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(request: LoginRequest, response: Response):
    # Verify username
    if request.username != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    # Verify password — support bcrypt hash (local dev) or plaintext (Easypanel/Docker)
    if settings.admin_password_hash:
        try:
            password_ok = bcrypt.checkpw(
                request.password.encode("utf-8"),
                settings.admin_password_hash.encode("utf-8"),
            )
        except Exception:
            password_ok = False
    elif settings.admin_password:
        password_ok = (request.password == settings.admin_password)
    else:
        password_ok = False

    if not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    token = create_access_token({"sub": settings.admin_username})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",  # lax for dev; use strict in production
        max_age=60 * 60 * 24 * settings.jwt_expire_days,
        path="/",
    )

    logger.info(f"Admin logged in: {settings.admin_username}")
    return {"message": "Login exitoso"}


@router.post("/logout")
async def logout(response: Response, _: str = Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    return {"message": "Sesión cerrada"}


@router.get("/me", response_model=AuthMeResponse)
async def me(current_user: str = Depends(get_current_user)):
    return AuthMeResponse(username=current_user)
