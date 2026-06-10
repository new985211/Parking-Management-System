"""
Parking Lot Management System — Flask Main Application.
Entry point for the license plate recognition and parking management backend.

Usage:
    python app.py                    # Development
    gunicorn -w 4 -b 0.0.0.0:5000 app:app  # Production
"""
import logging
import os
import sys
from datetime import datetime

from flask import Flask, jsonify

from config import Config
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Init database
    init_db()

    # Register blueprints
    from routes.web import web
    from routes.api_recognize import api_recognize
    from routes.api_entry_exit import api_entry_exit
    from routes.api_vehicle import api_vehicle
    from routes.api_payment import api_payment
    from routes.api_gate import api_gate
    from routes.api_admin import api_admin
    from routes.api_miniapp import api_miniapp

    app.register_blueprint(web)
    app.register_blueprint(api_recognize)
    app.register_blueprint(api_entry_exit)
    app.register_blueprint(api_vehicle)
    app.register_blueprint(api_payment)
    app.register_blueprint(api_gate)
    app.register_blueprint(api_admin)
    app.register_blueprint(api_miniapp)

    # ---- Health Check ----
    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "service": "parking-lpr",
            "time": datetime.now().isoformat(),
        })

    # ---- Error Handlers ----
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error("Internal server error: %s", e)
        return jsonify({"success": False, "error": "Internal server error"}), 500

    logger.info("Parking LPR system initialized")
    return app


app = create_app()


if __name__ == "__main__":
    print("=" * 50)
    print("🅿️  停车场车牌识别管理系统")
    print(f"📍 Web:     http://localhost:5000")
    print(f"📍 OCR API: {Config.OCR_SERVICE_URL}")
    print(f"📍 数据库:  {os.path.abspath(Config.DB_PATH)}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
