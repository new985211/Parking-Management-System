"""Application configuration — all values can be overridden via environment variables."""
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me-in-production")
    DB_PATH = os.environ.get("DB_PATH", "parking.db")
    OCR_SERVICE_URL = os.environ.get("OCR_SERVICE_URL", "http://localhost:5001/ocr")
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # ---- WeChat Mini-Program / Pay ----
    WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")
    WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")
    WECHAT_MCH_ID = os.environ.get("WECHAT_MCH_ID", "")
    WECHAT_API_KEY = os.environ.get("WECHAT_API_KEY", "")
    WECHAT_NOTIFY_URL = os.environ.get("WECHAT_NOTIFY_URL", "")
    WECHAT_CERT_PATH = os.environ.get("WECHAT_CERT_PATH", "")
    WECHAT_KEY_PATH = os.environ.get("WECHAT_KEY_PATH", "")

    # ---- Barrier Gate ----
    GATE_RELAY_HOST = os.environ.get("GATE_RELAY_HOST", "192.168.1.200")
    GATE_RELAY_PORT = int(os.environ.get("GATE_RELAY_PORT", "80"))

    # ---- Fee Schedule ----
    FREE_MINUTES = 30
    SHORT_TERM_FEE = 5.0
    MEDIUM_TERM_FEE = 10.0
    EXTRA_HOURLY_RATE = 3.0
    DAILY_CAP = 50.0

    # ---- Pagination ----
    PER_PAGE = 20
