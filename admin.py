"""Admin Blueprint — IP allow-list and user management"""
from functools import wraps
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app import db
from app.models import AllowedIP, AccessLog, User

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@login_required
@admin_required
def index():
    ips = AllowedIP.query.order_by(AllowedIP.added_at.desc()).all()
    users = User.query.order_by(User.created_at.desc()).all()
    logs = AccessLog.query.order_by(AccessLog.timestamp.desc()).limit(50).all()
    return render_template("dashboard/admin.html", ips=ips, users=users, logs=logs)


@admin_bp.route("/ip/add", methods=["POST"])
@login_required
@admin_required
def add_ip():
    ip = request.form.get("ip_address", "").strip()
    label = request.form.get("label", "").strip()
    if ip:
        existing = AllowedIP.query.filter_by(ip_address=ip).first()
        if existing:
            existing.is_active = True
            flash(f"IP {ip} re-activated.", "info")
        else:
            entry = AllowedIP(ip_address=ip, label=label, added_by=current_user.username)
            db.session.add(entry)
            flash(f"IP {ip} added to allow-list.", "success")
        db.session.commit()
    return redirect(url_for("admin.index"))


@admin_bp.route("/ip/<int:ip_id>/remove", methods=["POST"])
@login_required
@admin_required
def remove_ip(ip_id: int):
    entry = AllowedIP.query.get_or_404(ip_id)
    entry.is_active = False
    db.session.commit()
    flash(f"IP {entry.ip_address} removed from allow-list.", "warning")
    return redirect(url_for("admin.index"))


@admin_bp.route("/user/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id: int):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("admin.index"))
    user.is_active = not user.is_active
    db.session.commit()
    state = "activated" if user.is_active else "deactivated"
    flash(f"User {user.username} {state}.", "info")
    return redirect(url_for("admin.index"))
