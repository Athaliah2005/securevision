"""
Camera Service — OpenCV-based CCTV / webcam streaming module.
Supports: USB webcam (index 0), RTSP streams (IP cameras), video files.
"""
import logging
import threading
import time
from typing import Generator, Optional

import cv2

logger = logging.getLogger(__name__)


class CameraStream:
    """
    Thread-safe camera wrapper with auto-reconnect.
    Uses a background thread to continuously read frames so the
    MJPEG endpoint never blocks waiting for the hardware.
    """

    def __init__(self, source: str | int = 0, fps: int = 15) -> None:
        self.source = int(source) if str(source).isdigit() else source
        self.fps = fps
        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[bytes] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("Camera stream started: source=%s fps=%s", self.source, self.fps)

    def stop(self) -> None:
        self._running = False
        if self._cap:
            self._cap.release()
        logger.info("Camera stream stopped.")

    # ── Internal capture loop ─────────────────────────────────────────────────

    def _open_capture(self) -> bool:
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            logger.warning("Cannot open camera source: %s", self.source)
            return False
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)
        return True

    def _capture_loop(self) -> None:
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                if not self._open_capture():
                    time.sleep(3)   # Back-off before retry
                    continue

            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Frame read failed — reconnecting…")
                self._cap.release()
                self._cap = None
                time.sleep(2)
                continue

            # Overlay timestamp on frame
            ts = time.strftime("%Y-%m-%d  %H:%M:%S")
            cv2.putText(
                frame, ts, (10, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 120), 1, cv2.LINE_AA,
            )

            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with self._lock:
                self._frame = jpeg.tobytes()

            time.sleep(1 / self.fps)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_frame(self) -> Optional[bytes]:
        with self._lock:
            return self._frame

    def mjpeg_generator(self) -> Generator[bytes, None, None]:
        """Yield MJPEG multipart frames suitable for a Flask streaming response."""
        while True:
            frame = self.get_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            time.sleep(1 / self.fps)


# Singleton instance — initialised lazily by the camera blueprint
_camera: Optional[CameraStream] = None


def get_camera(source: str = "0", fps: int = 15) -> CameraStream:
    global _camera
    if _camera is None:
        _camera = CameraStream(source=source, fps=fps)
        _camera.start()
    return _camera
