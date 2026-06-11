"""
PaddleOCR HTTP Microservice
Accepts image uploads, returns recognized license plate text.
Loads the OCR model once at startup (singleton pattern).
"""
import logging
import os
import re
import time
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

# OCR confusion corrections — ONLY characters NEVER used on Chinese plates:
#   O → 0  (letter O is never used on plates, to avoid confusion with digit 0)
#   I → 1  (letter I is never used on plates, to avoid confusion with digit 1)
# All other corrections (B→8, D→0, S→5, Z→2, L→1, Q→0, V→0) are REMOVED
# because B/D/S/Z/L are valid city codes and alphanumeric plate characters.
OCR_SAFE_CORRECTIONS = str.maketrans({"O": "0", "I": "1"})


def is_valid_plate(text: str) -> bool:
    """Check if text matches Chinese license plate format."""
    cleaned = text.replace(" ", "").replace("-", "").replace(".", "").upper()
    return bool(
        PATTERN_NORMAL.match(cleaned)
        or PATTERN_NEW_ENERGY.match(cleaned)
        or PATTERN_POLICE.match(cleaned)
    )


def normalize_plate(plate: str) -> str:
    """Fix common OCR errors on license plates.

    Only corrects O→0 and I→1. These are the ONLY letters never used
    on Chinese plates (to avoid visual confusion with digits).
    Other characters (B, D, S, Z, L) are VALID city codes and left alone.
    """
    if not plate:
        return ""
    cleaned = plate.replace(" ", "").replace("-", "").replace(".", "").upper()
    cleaned = cleaned.translate(OCR_SAFE_CORRECTIONS)
    return cleaned


def find_best_plate(results) -> tuple:
    """From all OCR results, find the one most likely to be a license plate.

    Priority: valid-format plate with highest confidence.
    Fallback: any text ≥5 chars if no valid plate found (for manual review).
    """
    if not results or not results[0]:
        return "", 0.0

    best_valid_plate = ""
    best_valid_conf = 0.0
    best_fallback_text = ""
    best_fallback_conf = 0.0

    for line in results[0]:
        box, (text, confidence) = line
        text = text.strip()
        if confidence > 0.7 and 6 <= len(text) <= 9:
            if is_valid_plate(text):
                if confidence > best_valid_conf:
                    best_valid_conf = confidence
                    best_valid_plate = text
            elif len(text) >= 5 and confidence > best_fallback_conf:
                best_fallback_conf = confidence
                best_fallback_text = text

    # Always prefer a valid plate, even if a fallback had higher confidence
    if best_valid_plate:
        return normalize_plate(best_valid_plate), best_valid_conf
    if best_fallback_text:
        return normalize_plate(best_fallback_text), best_fallback_conf
    return "", 0.0


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
