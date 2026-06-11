"""Entry and exit recording APIs."""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from config import Config
from database import get_conn, upsert_vehicle, is_blacklisted
from payment import calculate_fee

logger = logging.getLogger(__name__)
api_entry_exit = Blueprint("api_entry_exit", __name__)


@api_entry_exit.route("/api/entry", methods=["POST"])
def vehicle_entry():
    """
    Record vehicle entry.
    POST /api/entry
    JSON: {"plate": "粤B12345", "location": "main_gate", "confidence": 0.95, "image_path": "..."}
    """
    data = request.get_json(silent=True) or {}
    plate = data.get("plate", "").strip().upper()
    location = data.get("location", "main_gate")
    confidence = data.get("confidence", 1.0)
    image_path = data.get("image_path", "")
    need_review = 1 if data.get("need_review", False) or confidence < 0.85 else 0

    if not plate:
        return jsonify({"success": False, "error": "车牌号不能为空"}), 400

    # Check blacklist
    if is_blacklisted(plate):
        logger.warning("Blacklisted vehicle attempted entry: %s", plate)
        return jsonify({
            "success": False,
            "error": f"黑名单车辆: {plate}",
            "blacklisted": True,
        }), 403

    # Check if already inside
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id FROM records r1
           WHERE plate_number = ? AND event_type = 'enter'
           AND NOT EXISTS (
               SELECT 1 FROM records r2
               WHERE r2.plate_number = r1.plate_number
               AND r2.event_type = 'exit'
               AND r2.created_at >= r1.created_at
           )""",
        (plate,),
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({"success": False, "error": f"{plate} 已在场内，请勿重复入场"}), 400

    # Ensure vehicle record exists
    upsert_vehicle(plate)

    # Insert entry record
    cursor.execute(
        """INSERT INTO records (plate_number, event_type, image_path, confidence, need_review, location)
           VALUES (?, 'enter', ?, ?, ?, ?)""",
        (plate, image_path, confidence, need_review, location),
    )
    conn.commit()
    conn.close()

    logger.info("Vehicle entry: %s at %s", plate, location)
    return jsonify({
        "success": True,
        "message": f"{plate} 入场成功",
        "plate": plate,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "need_review": bool(need_review),
    })


@api_entry_exit.route("/api/exit", methods=["POST"])
def vehicle_exit():
    """
    Record vehicle exit with automatic fee calculation.
    POST /api/exit
    JSON: {"plate": "粤B12345", "location": "main_gate"}
    """
    data = request.get_json(silent=True) or {}
    plate = data.get("plate", "").strip().upper()
    location = data.get("location", "main_gate")

    if not plate:
        return jsonify({"success": False, "error": "车牌号不能为空"}), 400

    conn = get_conn()
    cursor = conn.cursor()

    # Find the unpaid entry record
    cursor.execute(
        """SELECT id, created_at FROM records
           WHERE plate_number = ? AND event_type = 'enter'
           AND NOT EXISTS (
               SELECT 1 FROM records r2
               WHERE r2.plate_number = records.plate_number
               AND r2.event_type = 'exit'
               AND r2.created_at > records.created_at
           )
           ORDER BY created_at DESC LIMIT 1""",
        (plate,),
    )
    entry_record = cursor.fetchone()

    if not entry_record:
        conn.close()
        return jsonify({"success": False, "error": f"未找到 {plate} 的入场记录"}), 404

    entry_time = datetime.strptime(entry_record["created_at"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    duration_seconds = int((now - entry_time).total_seconds())
    duration_minutes = duration_seconds / 60

    # Check vehicle type for fee calculation
    cursor.execute("SELECT vehicle_type FROM vehicles WHERE plate_number = ?", (plate,))
    veh = cursor.fetchone()
    vehicle_type = veh["vehicle_type"] if veh else "normal"

    fee = calculate_fee(duration_minutes, plate, vehicle_type)

    # Insert exit record
    cursor.execute(
        """INSERT INTO records (plate_number, event_type, parking_duration, fee, location)
           VALUES (?, 'exit', ?, ?, ?)""",
        (plate, duration_seconds, fee, location),
    )
    conn.commit()
    conn.close()

    logger.info("Vehicle exit: %s duration=%ds fee=%.2f", plate, duration_seconds, fee)

    return jsonify({
        "success": True,
        "plate": plate,
        "duration_seconds": duration_seconds,
        "duration_text": _format_duration(duration_seconds),
        "fee": round(fee, 2),
        "exit_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "need_payment": fee > 0,
    })


def _format_duration(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}小时{minutes}分钟"
    return f"{minutes}分钟"
