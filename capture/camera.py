"""
IP Camera (RTSP) capture module with motion detection.
Supports Hikvision, Dahua, and generic RTSP cameras.
"""
import logging
import os
import time
from datetime import datetime

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Common RTSP URL formats:
# Hikvision: rtsp://admin:password@192.168.1.64:554/h264/ch1/main/av_stream
# Dahua:     rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0
# Generic:   rtsp://username:password@ip:port/stream

DEFAULT_RTSP_URL = os.environ.get(
    "RTSP_URL", "rtsp://admin:admin123@192.168.1.100:554/h264/ch1/main/av_stream"
)
CAPTURE_DIR = os.environ.get("CAPTURE_DIR", "uploads")


class MotionDetector:
    """Detects motion by comparing consecutive frames with absdiff."""

    def __init__(self, threshold: int = 25, min_area: int = 5000, cooldown_sec: float = 2.0):
        self.threshold = threshold
        self.min_area = min_area
        self.cooldown_sec = cooldown_sec
        self._prev_frame: np.ndarray | None = None
        self._last_trigger_time: float = 0.0

    def is_motion(self, frame: np.ndarray) -> bool:
        """Check if there's significant motion in the frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._prev_frame is None:
            self._prev_frame = gray
            return False

        diff = cv2.absdiff(self._prev_frame, gray)
        _, thresh = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        self._prev_frame = gray

        for c in contours:
            if cv2.contourArea(c) > self.min_area:
                now = time.time()
                if now - self._last_trigger_time > self.cooldown_sec:
                    self._last_trigger_time = now
                    return True
        return False


class CameraCapture:
    """RTSP camera stream capture with auto-reconnect."""

    def __init__(self, rtsp_url: str = None):
        self.rtsp_url = rtsp_url or DEFAULT_RTSP_URL
        self.cap: cv2.VideoCapture | None = None
        self.motion = MotionDetector()
        self._connect()

    def _connect(self):
        """Connect to RTSP stream with retry."""
        max_retries = 5
        for i in range(max_retries):
            self.cap = cv2.VideoCapture(self.rtsp_url)
            # Optimize for network stream
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 15)
            if self.cap.isOpened():
                logger.info("Camera connected: %s", self.rtsp_url[:50] + "...")
                return
            logger.warning("Camera connect attempt %d/%d failed", i + 1, max_retries)
            time.sleep(2)
        raise ConnectionError(f"Cannot connect to camera: {self.rtsp_url}")

    def read(self) -> np.ndarray | None:
        """Read a single frame. Returns None on failure."""
        if self.cap is None:
            return None
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Frame read failed, reconnecting...")
            self._connect()
            ret, frame = self.cap.read() if self.cap else (False, None)
        return frame if ret else None

    def wait_for_vehicle(self, timeout: float = 60.0) -> str | None:
        """
        Wait for a vehicle (motion detected), then capture and save a frame.
        Returns the file path of the captured image, or None on timeout.
        """
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        start = time.time()

        while time.time() - start < timeout:
            frame = self.read()
            if frame is None:
                time.sleep(1)
                continue

            if self.motion.is_motion(frame):
                timestamp = int(time.time() * 1000)
                filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{timestamp}.jpg"
                filepath = os.path.join(CAPTURE_DIR, filename)
                cv2.imwrite(filepath, frame)
                logger.info("Motion detected → captured: %s", filepath)
                return filepath

            # Small sleep to control CPU usage
            time.sleep(0.1)

        logger.info("No motion detected within timeout")
        return None

    def capture_snapshot(self) -> str:
        """Immediately capture a single frame (no motion detection)."""
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        frame = self.read()
        if frame is None:
            raise RuntimeError("Cannot capture frame from camera")
        timestamp = int(time.time() * 1000)
        filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{timestamp}.jpg"
        filepath = os.path.join(CAPTURE_DIR, filename)
        cv2.imwrite(filepath, frame)
        return filepath

    def release(self):
        if self.cap:
            self.cap.release()


class USBCameraCapture(CameraCapture):
    """For USB webcam (dev/test fallback)."""

    def __init__(self, device_id: int = 0):
        self.rtsp_url = f"usb://{device_id}"
        self.motion = MotionDetector()
        self.cap = cv2.VideoCapture(device_id)
        if not self.cap.isOpened():
            raise ConnectionError(f"Cannot open USB camera device {device_id}")
        logger.info("USB camera connected: device %d", device_id)
