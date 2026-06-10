"""Mini-program specific API routes."""
import logging
import time

import requests
from flask import Blueprint, jsonify, request

from config import Config
from database import get_conn, upsert_vehicle, get_vehicle_by_openid, find_active_entry
from payment import calculate_fee

logger = logging.getLogger(__name__)
api_miniapp = Blueprint("api_miniapp", __name__)


def _get_openid() -> str:
    """Extract openid from request (header or query param)."""
    # In production: validate JWT token from WeChat login
    openid = request.headers.get("X-WeChat-OpenID", "")
    if not openid:
        openid = request.args.get("openid", "")
    if not openid:
        data = request.get_json(silent=True) or {}
        openid = data.get("openid", "")
    return openid


@api_miniapp.route("/api/miniapp/login", methods=["POST"])
def miniapp_login():
    """
    Exchange WeChat login code for openid.
    POST /api/miniapp/login
    JSON: {"code": "wx_login_code"}
    """
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")

    if not code or not Config.WECHAT_APP_ID or not Config.WECHAT_APP_SECRET:
        # Dev mode: return simulated openid
        return jsonify({"success": True, "openid": f"simulated_{int(time.time())}"})

    try:
        resp = requests.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": Config.WECHAT_APP_ID,
                "secret": Config.WECHAT_APP_SECRET,
                "js_code": code,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        wx_data = resp.json()
        if "openid" in wx_data:
            return jsonify({"success": True, "openid": wx_data["openid"]})
        return jsonify({"success": False, "error": wx_data.get("errmsg", "Login failed")}), 400
    except Exception as e:
        logger.error("WeChat login error: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


@api_miniapp.route("/api/miniapp/vehicle", methods=["GET"])
def miniapp_get_vehicle():
    """Get the vehicle bound to a WeChat openid."""
    openid = _get_openid()
    if not openid:
        return jsonify({"success": False, "error": "openid required"}), 400

    vehicle = get_vehicle_by_openid(openid)
    if vehicle:
        return jsonify({"success": True, **vehicle})
    return jsonify({"success": True, "plate_number": None})


@api_miniapp.route("/api/miniapp/bind", methods=["POST"])
def miniapp_bind_plate():
    """Bind a license plate to a WeChat openid."""
    data = request.get_json(silent=True) or {}
    plate = data.get("plate_number", "").strip().upper()
    openid = data.get("openid", "") or _get_openid()

    if not plate:
        return jsonify({"success": False, "error": "plate_number required"}), 400
    if not openid:
        return jsonify({"success": False, "error": "openid required"}), 400

    # Unbind: if plate is empty, remove binding
    if plate == "":
        conn = get_conn()
        conn.execute("UPDATE vehicles SET wechat_openid = NULL WHERE wechat_openid = ?", (openid,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "已解绑"})

    # Check if plate is already bound to another user
    conn = get_conn()
    existing = conn.execute(
        "SELECT wechat_openid FROM vehicles WHERE plate_number = ?", (plate,)
    ).fetchone()
    if existing and existing["wechat_openid"] and existing["wechat_openid"] != openid:
        conn.close()
        return jsonify({"success": False, "error": "该车牌已被其他用户绑定"}), 409
    conn.close()

    upsert_vehicle(
        plate=plate,
        owner_name=data.get("owner_name", ""),
        phone=data.get("phone", ""),
        wechat_openid=openid,
    )
    return jsonify({"success": True, "message": f"已绑定 {plate}"})


@api_miniapp.route("/api/miniapp/records", methods=["GET"])
def miniapp_records():
    """Get parking records for a user."""
    openid = _get_openid()
    if not openid:
        return jsonify({"success": False, "error": "openid required"}), 400

    vehicle = get_vehicle_by_openid(openid)
    if not vehicle:
        return jsonify({"success": True, "records": [], "total": 0})

    page = request.args.get("page", 1, type=int)
    per_page = 20

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE plate_number = ?",
        (vehicle["plate_number"],),
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT * FROM records WHERE plate_number = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (vehicle["plate_number"], per_page, (page - 1) * per_page),
    )
    records = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({"success": True, "records": records, "total": total})


@api_miniapp.route("/api/miniapp/current", methods=["GET"])
def miniapp_current():
    """Get current parking status for a user."""
    openid = _get_openid()
    if not openid:
        return jsonify({"success": False, "error": "openid required"}), 400

    vehicle = get_vehicle_by_openid(openid)
    if not vehicle:
        return jsonify({"success": True, "current": None})

    entry = find_active_entry(vehicle["plate_number"])
    if not entry:
        return jsonify({"success": True, "current": None})

    from datetime import datetime
    entry_time = datetime.strptime(entry["created_at"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    duration_seconds = int((now - entry_time).total_seconds())
    duration_minutes = duration_seconds / 60

    fee = calculate_fee(duration_minutes, vehicle["plate_number"], vehicle.get("vehicle_type", "normal"))

    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    duration_text = f"{hours}小时{minutes}分钟" if hours > 0 else f"{minutes}分钟"

    return jsonify({
        "success": True,
        "current": {
            "record_id": entry["id"],
            "plate_number": vehicle["plate_number"],
            "entry_time": entry["created_at"],
            "duration_seconds": duration_seconds,
            "duration_text": duration_text,
            "fee": round(fee, 2),
        },
    })


@api_miniapp.route("/api/miniapp/stats", methods=["GET"])
def miniapp_stats():
    """Get user parking stats."""
    openid = _get_openid()
    if not openid:
        return jsonify({"success": False, "error": "openid required"}), 400

    vehicle = get_vehicle_by_openid(openid)
    if not vehicle:
        return jsonify({"success": True, "stats": {"today_count": 0, "total_fee": 0}})

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE plate_number = ? AND DATE(created_at) = ?",
        (vehicle["plate_number"], today),
    )
    today_count = cursor.fetchone()[0]
    cursor.execute(
        "SELECT COALESCE(SUM(fee), 0) FROM records WHERE plate_number = ?",
        (vehicle["plate_number"],),
    )
    total_fee = cursor.fetchone()[0]
    conn.close()

    return jsonify({
        "success": True,
        "stats": {"today_count": today_count, "total_fee": round(total_fee, 2)},
    })
