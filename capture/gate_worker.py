#!/usr/bin/env python3
"""
Main gate worker — the event loop that ties everything together.
Runs as a standalone process:
  1. Wait for motion detection (vehicle approaching)
  2. Capture frame → OCR recognize plate
  3. Determine entry/exit → call backend API
  4. Control barrier gate (open/close)
  5. Handle payment flow at exit

Usage:
    python gate_worker.py                        # with simulated gate
    GATE_TYPE=network_relay python gate_worker.py  # with real relay
"""
import logging
import os
import signal
import sys
import time
from datetime import datetime

import requests

# Add backend to path for importing modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from config import Config
from gate_controller import create_gate_controller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] gate_worker: %(message)s",
)
logger = logging.getLogger("gate_worker")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000")

# ---- Direction Detection ----
# Simple heuristic: if vehicle has been seen entering without exiting,
# it's an exit event. Otherwise, it's an entry event.
# In production, this is determined by which gate (entry vs exit lane).


class GateWorker:
    def __init__(self):
        self.gate_type = os.environ.get("GATE_TYPE", "simulated")
        self.gate = create_gate_controller(self.gate_type)
        self.entry_gate_id = os.environ.get("ENTRY_GATE_ID", "entry_gate")
        self.exit_gate_id = os.environ.get("EXIT_GATE_ID", "exit_gate")
        self.running = True
        logger.info("Gate worker started (type=%s, backend=%s)", self.gate_type, BACKEND_URL)

    def stop(self):
        self.running = False

    def run_once(self, direction: str, image_path: str):
        """
        Process one vehicle pass.
        direction: 'entry' or 'exit'
        image_path: path to the captured plate image
        """
        logger.info("Vehicle detected at %s gate, image=%s", direction, image_path)

        # Step 1: OCR recognition
        ocr_result = self._call_ocr(image_path)
        if not ocr_result.get("success"):
            logger.warning("OCR failed: %s", ocr_result.get("error", "unknown"))
            # In production, save image for manual review
            return False

        plate = ocr_result["plate"]
        confidence = ocr_result["confidence"]
        need_review = ocr_result.get("need_review", confidence < 0.85)

        logger.info("Recognized: %s (confidence=%.2f, review=%s)", plate, confidence, need_review)

        # Step 2: Record entry or exit
        if direction == "entry":
            return self._handle_entry(plate, confidence, need_review, image_path)
        else:
            return self._handle_exit(plate, image_path)

    def _handle_entry(self, plate: str, confidence: float, need_review: bool, image_path: str) -> bool:
        """Record vehicle entry and open gate."""
        resp = self._call_api("/api/entry", {
            "plate": plate,
            "confidence": confidence,
            "need_review": need_review,
            "image_path": image_path,
            "location": self.entry_gate_id,
        })

        if resp.get("success"):
            logger.info("Entry recorded: %s", plate)
            # Check blacklist
            if resp.get("blacklisted"):
                logger.warning("Blacklisted vehicle %s — gate stays closed", plate)
                return False

            # Open the entry gate
            self.gate.open(self.entry_gate_id)
            # Wait for vehicle to pass
            time.sleep(3)
            self.gate.close(self.entry_gate_id)
            return True
        else:
            logger.warning("Entry failed for %s: %s", plate, resp.get("error", ""))
            return False

    def _handle_exit(self, plate: str, image_path: str) -> bool:
        """Record vehicle exit, calculate fee, handle payment, open gate."""
        resp = self._call_api("/api/exit", {
            "plate": plate,
            "location": self.exit_gate_id,
        })

        if not resp.get("success"):
            logger.warning("Exit failed for %s: %s", plate, resp.get("error", ""))
            return False

        fee = resp.get("fee", 0)
        need_payment = resp.get("need_payment", False)

        logger.info("Exit: %s fee=%.2f need_payment=%s", plate, fee, need_payment)

        if not need_payment:
            # No fee (free tier or monthly pass) — open gate immediately
            self.gate.open(self.exit_gate_id)
            time.sleep(3)
            self.gate.close(self.exit_gate_id)
            return True

        # Fee required — wait for payment before opening
        # In production, this would integrate with a payment terminal or
        # the WeChat mini-program where the user pays on their phone.
        # For now, we log and wait.
        logger.info("Fee ¥%.2f required for %s — waiting for payment...", fee, plate)
        # The gate should open when payment is confirmed via API
        return True

    def _call_ocr(self, image_path: str) -> dict:
        """Send image to OCR service, return result."""
        try:
            with open(image_path, "rb") as f:
                resp = requests.post(
                    Config.OCR_SERVICE_URL,
                    files={"image": f},
                    timeout=15,
                )
            return resp.json()
        except Exception as e:
            logger.error("OCR service error: %s", e)
            return {"success": False, "error": str(e)}

    def _call_api(self, endpoint: str, data: dict) -> dict:
        """Call backend API endpoint."""
        try:
            resp = requests.post(
                f"{BACKEND_URL}{endpoint}",
                json=data,
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            logger.error("Backend API error (%s): %s", endpoint, e)
            return {"success": False, "error": str(e)}

    def run_demo(self):
        """
        Demo mode — uses simulated captures for testing without real camera.
        Calls the backend's /api/recognize with a test flow.
        """
        logger.info("Demo mode — testing full entry→exit flow without camera")
        test_plate = "粤B12345"

        # Simulate entry
        logger.info("=== Simulating ENTRY ===")
        entry_resp = self._call_api("/api/entry", {
            "plate": test_plate,
            "confidence": 0.95,
            "need_review": False,
            "location": "main_gate",
        })
        logger.info("Entry response: %s", entry_resp)
        self.gate.open(self.entry_gate_id)
        time.sleep(1)
        self.gate.close(self.entry_gate_id)

        # Simulate some parking time
        logger.info("Vehicle parked for 1.5 hours...")
        time.sleep(2)

        # Simulate exit
        logger.info("=== Simulating EXIT ===")
        exit_resp = self._call_api("/api/exit", {
            "plate": test_plate,
            "location": "main_gate",
        })
        logger.info("Exit response: %s", exit_resp)

        if exit_resp.get("need_payment"):
            # Simulate payment
            logger.info("Creating payment for ¥%.2f...", exit_resp["fee"])
            pay_resp = self._call_api("/api/payment/create", {
                "record_id": 1,
                "openid": "test_openid",
            })
            logger.info("Payment response: %s", pay_resp)

        self.gate.open(self.exit_gate_id)
        time.sleep(1)
        self.gate.close(self.exit_gate_id)
        logger.info("=== Demo complete ===")


# ---- Signal handling ----
_worker = None


def _signal_handler(signum, frame):
    logger.info("Shutting down...")
    if _worker:
        _worker.stop()


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ---- Entry Point ----
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parking Gate Worker")
    parser.add_argument("--demo", action="store_true", help="Run demo mode (no camera needed)")
    parser.add_argument("--direction", choices=["entry", "exit"], default="entry",
                        help="Gate direction for single-capture mode")
    args = parser.parse_args()

    _worker = GateWorker()

    if args.demo:
        _worker.run_demo()
    else:
        # Production mode: continuous monitoring with camera
        gate_type = os.environ.get("GATE_TYPE", "simulated")

        if gate_type == "simulated":
            logger.warning("Running in SIMULATED gate mode — no real hardware control")
            logger.info("Use --demo for a quick test of the full pipeline")
            # In simulated mode, just run demo
            _worker.run_demo()
        else:
            # Real camera + gate mode
            from camera import CameraCapture
            camera = CameraCapture()
            direction = os.environ.get("GATE_DIRECTION", args.direction)

            logger.info("Starting continuous monitoring at %s gate...", direction)
            try:
                while _worker.running:
                    filepath = camera.wait_for_vehicle(timeout=30.0)
                    if filepath:
                        _worker.run_once(direction, filepath)
            finally:
                camera.release()

    logger.info("Gate worker stopped")
