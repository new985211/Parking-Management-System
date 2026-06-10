"""HTTP client to the PaddleOCR Docker microservice."""
import logging
import time
import requests
from config import Config

logger = logging.getLogger(__name__)


def recognize(image_path: str) -> dict:
    """
    Send image to OCR service and return recognition result.
    Returns: {"success": bool, "plate": str, "confidence": float, "need_review": bool}
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with open(image_path, "rb") as f:
                resp = requests.post(
                    Config.OCR_SERVICE_URL,
                    files={"image": f},
                    timeout=15,
                )
            resp.raise_for_status()
            data = resp.json()
            logger.info(
                "OCR: plate=%s confidence=%.2f need_review=%s",
                data.get("plate", ""), data.get("confidence", 0), data.get("need_review", True),
            )
            return data
        except requests.ConnectionError:
            logger.warning("OCR service unreachable, attempt %d/%d", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.error("OCR client error: %s", e)
            return {"success": False, "error": str(e), "plate": "", "confidence": 0, "need_review": True}

    return {"success": False, "error": "OCR service unavailable", "plate": "", "confidence": 0, "need_review": True}
