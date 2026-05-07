"""Camera streaming blueprint"""
from flask import Blueprint, Response, current_app, render_template
from flask_login import login_required
from app.services.camera import get_camera

camera_bp = Blueprint("camera", __name__)

@camera_bp.route("/feed")
@login_required
def feed():
    source = current_app.config.get("CAMERA_SOURCE", "0")
    fps = current_app.config.get("CAMERA_FPS", 15)
    cam = get_camera(source=source, fps=fps)
    return Response(
        cam.mjpeg_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@camera_bp.route("/view")
@login_required
def view():
    return render_template("dashboard/camera.html")
