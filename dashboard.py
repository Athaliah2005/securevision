"""Dashboard route"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import AccessLog

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@login_required
def index():
    recent_logs = (
        AccessLog.query
        .order_by(AccessLog.timestamp.desc())
        .limit(20)
        .all()
    )
    stats = {
        "total": AccessLog.query.count(),
        "blocked": AccessLog.query.filter_by(outcome="blocked_ip").count(),
        "failed": AccessLog.query.filter(
            AccessLog.outcome.in_(["fail_pw", "blocked_user"])
        ).count(),
        "success": AccessLog.query.filter_by(outcome="success").count(),
    }
    return render_template("dashboard/index.html", logs=recent_logs, stats=stats, user=current_user)
