"""
Configuration settings — KEEP THIS FILE OUT OF VERSION CONTROL.
All secrets must be set via environment variables or a .env file.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    # ── Flask core ────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = True          # Requires HTTPS in production
    SESSION_COOKIE_SAMESITE: str = "Strict"
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(hours=2)

    # ── Database ──────────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL", "sqlite:///securevision.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ── Allow-list  ◄── SECURITY LOGIC ───────────────────────────────────────
    # Comma-separated list of trusted IP addresses
    ALLOWED_IPS: list[str] = [
        ip.strip()
        for ip in os.environ.get("ALLOWED_IPS", "127.0.0.1,::1").split(",")
        if ip.strip()
    ]

    # ── Notification / alerting ───────────────────────────────────────────────
    ALERT_EMAIL_ENABLED: bool = os.environ.get("ALERT_EMAIL_ENABLED", "false").lower() == "true"
    SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER: str = os.environ.get("SMTP_USER", "")
    SMTP_PASS: str = os.environ.get("SMTP_PASS", "")          # ◄── SECRET
    ALERT_RECIPIENT: str = os.environ.get("ALERT_RECIPIENT", "")

    TELEGRAM_ENABLED: bool = os.environ.get("TELEGRAM_ENABLED", "false").lower() == "true"
    TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")   # ◄── SECRET
    TELEGRAM_CHAT_ID: str = os.environ.get("TELEGRAM_CHAT_ID", "")

    # ── Camera ────────────────────────────────────────────────────────────────
    CAMERA_SOURCE: str = os.environ.get("CAMERA_SOURCE", "0")   # 0 = webcam; RTSP URL for CCTV
    CAMERA_FPS: int = int(os.environ.get("CAMERA_FPS", 15))

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT: str = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL: str = "memory://"


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False   # Allows plain HTTP in dev


class ProductionConfig(BaseConfig):
    DEBUG: bool = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
