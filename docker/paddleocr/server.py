"""
PaddleOCR HTTP Microservice
Accepts image uploads, returns recognized license plate text.
Loads the OCR model once at startup (singleton pattern).
"""
import logging
import os
import re
import time
from io import BytesIO

from flask import Flask, jsonify, request
from paddleocr import PaddleOCR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---- OCR Singleton ----
_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        logger.info("Loading PaddleOCR model (this may take a minute on first run)...")
        _ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        logger.info("PaddleOCR model loaded successfully.")
    return _ocr


# ---- Plate Validation & Normalization ----

PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"

PATTERN_NORMAL = re.compile(rf"^[{PROVINCES}][A-Z][A-Z0-9]{{5}}$")
PATTERN_NEW_ENERGY = re.compile(rf"^[{PROVINCES}][A-Z][A-Z0-9]{{6}}$")
PATTERN_POLICE = re.compile(rf"^\d{{2,5}}[{PROVINCES}]警$")

# Characters OCR commonly confuses on plates
CHAR_CORRECTIONS = str.maketrans({
    "O": "0", "D": "0", "Q": "0", "V": "0",
    "I": "1", "L": "1",
    "Z": "2",
    "S": "5", "B": "8",
})


def is_valid_plate(text: str) -> bool:
    """Check if text matches Chinese license plate format."""
    cleaned = text.replace(" ", "").replace("-", "").replace(".", "").upper()
    return bool(
        PATTERN_NORMAL.match(cleaned)
        or PATTERN_NEW_ENERGY.match(cleaned)
        or PATTERN_POLICE.match(cleaned)
    )


def normalize_plate(plate: str) -> str:
    """Fix common OCR errors on license plates."""
    if not plate:
        return ""
    prefix = plate[0]
    suffix = plate[1:]
    suffix = suffix.translate(CHAR_CORRECTIONS)
    return (prefix + suffix).replace(" ", "").replace("-", "").upper()


def find_best_plate(results) -> tuple:
    """From all OCR results, find the one most likely to be a license plate."""
    if not results or not results[0]:
        return "", 0.0

    best_plate = ""
    best_confidence = 0.0

    for line in results[0]:
        box, (text, confidence) = line
        text = text.strip()
        if confidence > 0.7 and 6 <= len(text) <= 9:
            if is_valid_plate(text):
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_plate = text
            # Also keep best even if invalid format
            elif confidence > best_confidence and len(text) >= 5:
                best_confidence = confidence
                best_plate = text

    return normalize_plate(best_plate), best_confidence


# ---- Routes ----

@app.route("/ocr", methods=["POST"])
def ocr_recognize():
    """
    Recognize license plate from uploaded image.
    POST /ocr
    multipart/form-data: image=<file>
    Returns: {"plate": "粤B12345", "confidence": 0.95, "need_review": false}
    """
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    try:
        img_bytes = file.read()
        # PaddleOCR can read from file path or bytes via numpy
        import numpy as np
        import cv2

        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"success": False, "error": "Cannot decode image"}), 400

        ocr = get_ocr()
        start = time.time()
        results = ocr.ocr(img, cls=True)
        elapsed = time.time() - start

        plate, confidence = find_best_plate(results)
        need_review = confidence < 0.85 if confidence > 0 else True

        logger.info(
            "OCR result: plate=%s confidence=%.2f need_review=%s elapsed=%.2fs",
            plate, confidence, need_review, elapsed,
        )

        if not plate:
            return jsonify({
                "success": False,
                "error": "No plate recognized",
                "confidence": 0.0,
                "need_review": True,
                "elapsed_ms": int(elapsed * 1000),
            })

        return jsonify({
            "success": True,
            "plate": plate,
            "confidence": round(confidence, 4),
            "need_review": need_review,
            "elapsed_ms": int(elapsed * 1000),
        })

    except Exception as e:
        logger.error("OCR error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    ocr = get_ocr()
    return jsonify({
        "status": "ok",
        "model_loaded": ocr is not None,
    })


if __name__ == "__main__":
    # Warm up the model
    get_ocr()
    app.run(host="0.0.0.0", port=5001, debug=False)
