"""
Authentication Blueprint  ◄── SECURITY LOGIC: IP allow-list gate at login.
"""
from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template,
    request, url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app import db, limiter
from app.models import User
from app.services.security import (
    get_client_ip, is_ip_allowed, log_access, send_alert,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")   # Brute-force protection
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        client_ip = get_client_ip()

        # ── 1. IP Allow-list Gate  ◄── SECURITY LOGIC ────────────────────────
        if not is_ip_allowed(client_ip):
            alert_sent = send_alert(username, client_ip, "Blocked IP address")
            log_access(username, client_ip, "blocked_ip", alert_sent=alert_sent)
            flash(
                "Access denied. Your network is not authorised to use this system. "
                "The system administrator has been notified.",
                "error",
            )
            return render_template("auth/login.html"), 403

        # ── 2. User lookup ────────────────────────────────────────────────────
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            alert_sent = False
            if user is None:
                alert_sent = send_alert(username, client_ip, "Unknown username")
            log_access(
                username, client_ip, "fail_pw",
                user=user, alert_sent=alert_sent,
            )
            flash("Invalid username or password. Please try again.", "error")
            return render_template("auth/login.html"), 401

        if not user.is_active:
            log_access(username, client_ip, "blocked_user", user=user)
            flash("Your account has been disabled. Contact the administrator.", "error")
            return render_template("auth/login.html"), 403

        # ── 3. Successful login ───────────────────────────────────────────────
        login_user(user, remember=False)
        user.last_login = datetime.utcnow()
        db.session.commit()
        log_access(username, client_ip, "success", user=user)

        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out securely.", "info")
    return redirect(url_for("auth.login"))
