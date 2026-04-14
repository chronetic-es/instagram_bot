import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


def _load_env_no_interpolation() -> None:
    """Pre-load .env into os.environ without $VAR interpolation (preserves bcrypt hashes)."""
    try:
        from dotenv import dotenv_values
        env_file = Path(__file__).parent.parent / ".env"
        for key, value in dotenv_values(env_file, interpolate=False).items():
            if value is not None and key not in os.environ:
                os.environ[key] = value
    except Exception:
        pass


_load_env_no_interpolation()


class Settings(BaseSettings):
    # Instagram / Meta
    meta_verify_token: str = "default_verify_token"
    meta_page_access_token: str = ""
    meta_app_secret: str = ""
    instagram_account_id: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/gym_dm_bot"

    # Web Push (VAPID)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_claim_email: str = "mailto:dueno@gimnasio.com"

    # Auth
    admin_username: str = "admin"
    admin_password_hash: str = ""
    jwt_secret: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    # App
    frontend_url: str = "http://localhost:5173"

    class Config:
        pass


@lru_cache()
def get_settings() -> Settings:
    return Settings()
