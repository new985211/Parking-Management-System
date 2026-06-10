"""OCR recognition API."""
import os
import time

from flask import Blueprint, jsonify, request

from config import Config
from ocr_client import recognize

api_recognize = Blueprint("api_recognize", __name__)


@api_recognize.route("/api/recognize", methods=["POST"])
def recognize_plate():
    """
    Upload an image and get OCR-recognized license plate.
    POST /api/recognize
    multipart/form-data: image=<file>
    """
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    timestamp = int(time.time() * 1000)
    filename = f"plate_{timestamp}.jpg"
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    result = recognize(filepath)

    return jsonify({
        "success": result.get("success", False),
        "plate": result.get("plate", ""),
        "confidence": result.get("confidence", 0),
        "need_review": result.get("need_review", True),
        "image_path": filepath if result.get("success") else None,
        "elapsed_ms": result.get("elapsed_ms", 0),
    })
