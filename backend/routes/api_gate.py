"""Gate control and manual review APIs."""
import logging

from flask import Blueprint, jsonify, request, session

from database import get_conn
from gate_controller import create_gate_controller

logger = logging.getLogger(__name__)
api_gate = Blueprint("api_gate", __name__)

# Default to simulated gate controller
_gate = create_gate_controller("simulated")


@api_gate.route("/api/gate/open", methods=["POST"])
def open_gate():
    """Manually open a barrier gate."""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "请先登录"}), 401

    data = request.get_json(silent=True) or {}
    gate_id = data.get("gate_id", "entry_gate")
    ok = _gate.open(gate_id)
    return jsonify({"success": ok, "gate_id": gate_id, "action": "open"})


@api_gate.route("/api/gate/close", methods=["POST"])
def close_gate():
    """Manually close a barrier gate."""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "请先登录"}), 401

    data = request.get_json(silent=True) or {}
    gate_id = data.get("gate_id", "entry_gate")
    ok = _gate.close(gate_id)
    return jsonify({"success": ok, "gate_id": gate_id, "action": "close"})


@api_gate.route("/api/gate/status", methods=["GET"])
def gate_status():
    """Get current status of all gates."""
    conn = get_conn()
    gates = [dict(r) for r in conn.execute("SELECT * FROM gates").fetchall()]
    conn.close()

    result = []
    for g in gates:
        status = _gate.get_status(g["name"])
        result.append({
            **g,
            "is_open": status.is_open,
            "updated_at": status.updated_at,
        })
    return jsonify({"success": True, "gates": result})


@api_gate.route("/api/review/confirm", methods=["POST"])
def confirm_review():
    """Confirm or correct a low-confidence OCR result."""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "请先登录"}), 401

    data = request.get_json(silent=True) or {}
    record_id = data.get("record_id")
    correct_plate = data.get("plate", "").strip().upper()

    if not record_id or not correct_plate:
        return jsonify({"success": False, "error": "record_id and plate required"}), 400

    conn = get_conn()
    conn.execute(
        "UPDATE records SET plate_number = ?, need_review = 0 WHERE id = ?",
        (correct_plate, record_id),
    )
    conn.commit()
    conn.close()

    logger.info("Manual review confirmed: record=%d plate=%s", record_id, correct_plate)
    return jsonify({"success": True, "message": f"已确认为 {correct_plate}"})
