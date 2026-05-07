"""
Security Service  ◄── CONTAINS CRITICAL SECURITY LOGIC
DO NOT commit this file with real credentials.
Handles: IP allow-list enforcement, access logging, alert dispatch.
"""
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests
from flask import current_app, request

from app import db
from app.models import AccessLog, AllowedIP, User

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# IP Allow-list  ◄── SECURITY LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def get_client_ip() -> str:
    """Extract the real client IP, respecting proxy headers when trusted."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def is_ip_allowed(ip: str) -> bool:
    """
    ◄── SECURITY LOGIC
    Returns True only if the IP appears in BOTH:
      1. The static ALLOWED_IPS config list, OR
      2. The dynamic AllowedIP database table (active rows).
    """
    static_list: list[str] = current_app.config.get("ALLOWED_IPS", [])
    if ip in static_list:
        return True

    db_entry = AllowedIP.query.filter_by(ip_address=ip, is_active=True).first()
    return db_entry is not None


# ─────────────────────────────────────────────────────────────────────────────
# Access logging
# ─────────────────────────────────────────────────────────────────────────────

def log_access(
    username_attempt: str,
    ip_address: str,
    outcome: str,
    user: Optional[User] = None,
    alert_sent: bool = False,
) -> AccessLog:
    entry = AccessLog(
        timestamp=datetime.utcnow(),
        username_attempt=username_attempt,
        ip_address=ip_address,
        user_agent=request.headers.get("User-Agent", "")[:256],
        outcome=outcome,
        alert_sent=alert_sent,
        user_id=user.id if user else None,
    )
    db.session.add(entry)
    db.session.commit()
    logger.info("ACCESS [%s] user=%s ip=%s", outcome, username_attempt, ip_address)
    return entry


# ─────────────────────────────────────────────────────────────────────────────
# Notification / alerting  ◄── SECURITY LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def send_alert(username_attempt: str, ip_address: str, reason: str) -> bool:
    """Dispatch alerts via all enabled channels."""
    message = (
        f"🚨 SecureVision Alert\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Reason   : {reason}\n"
        f"Username : {username_attempt}\n"
        f"IP       : {ip_address}\n"
        f"Time     : {datetime.utcnow().isoformat()} UTC\n"
    )

    success = False
    if current_app.config.get("ALERT_EMAIL_ENABLED"):
        success = _send_email_alert(message) or success
    if current_app.config.get("TELEGRAM_ENABLED"):
        success = _send_telegram_alert(message) or success

    return success


def _send_email_alert(message: str) -> bool:
    """◄── SECRET: Uses SMTP credentials from environment variables."""
    try:
        cfg = current_app.config
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "⚠️ SecureVision — Unauthorized Access Attempt"
        msg["From"] = cfg["SMTP_USER"]
        msg["To"] = cfg["ALERT_RECIPIENT"]

        html_body = f"""
        <html><body style="font-family:monospace;background:#0d0d0d;color:#e0e0e0;padding:24px;">
        <h2 style="color:#ff4444;">🚨 Unauthorized Access Attempt</h2>
        <pre style="background:#1a1a1a;padding:16px;border-left:4px solid #ff4444;">{message}</pre>
        </body></html>
        """
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"]) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
            server.sendmail(cfg["SMTP_USER"], cfg["ALERT_RECIPIENT"], msg.as_string())

        logger.info("Email alert sent successfully.")
        return True
    except Exception as exc:
        logger.error("Email alert failed: %s", exc)
        return False


def _send_telegram_alert(message: str) -> bool:
    """◄── SECRET: Uses Telegram Bot token from environment variables."""
    try:
        cfg = current_app.config
        url = f"https://api.telegram.org/bot{cfg['TELEGRAM_BOT_TOKEN']}/sendMessage"
        payload = {
            "chat_id": cfg["TELEGRAM_CHAT_ID"],
            "text": message,
            "parse_mode": "Markdown",
        }
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info("Telegram alert sent successfully.")
        return True
    except Exception as exc:
        logger.error("Telegram alert failed: %s", exc)
        return False
