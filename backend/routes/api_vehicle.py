"""Vehicle management APIs (CRUD)."""
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from database import get_conn, upsert_vehicle

api_vehicle = Blueprint("api_vehicle", __name__)


def _require_admin():
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "请先登录"}), 401
    return None


@api_vehicle.route("/api/vehicles", methods=["GET"])
def list_vehicles():
    """List all registered vehicles with optional search."""
    plate = request.args.get("plate", "").strip()
    vtype = request.args.get("type", "").strip()
    conn = get_conn()
    cursor = conn.cursor()

    query = "SELECT * FROM vehicles WHERE 1=1"
    params = []
    if plate:
        query += " AND plate_number LIKE ?"
        params.append(f"%{plate}%")
    if vtype:
        query += " AND vehicle_type = ?"
        params.append(vtype)

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "vehicles": rows, "total": len(rows)})


@api_vehicle.route("/api/vehicles", methods=["POST"])
def create_vehicle():
    """Register a new vehicle or update existing."""
    err = _require_admin()
    if err: return err

    data = request.get_json(silent=True) or {}
    plate = data.get("plate_number", "").strip().upper()
    if not plate:
        return jsonify({"success": False, "error": "车牌号不能为空"}), 400

    vid = upsert_vehicle(
        plate=plate,
        owner_name=data.get("owner_name", ""),
        phone=data.get("phone", ""),
        vehicle_type=data.get("vehicle_type", "normal"),
        monthly_fee=data.get("monthly_fee", 0),
        wechat_openid=data.get("wechat_openid"),
    )
    return jsonify({"success": True, "id": vid, "message": f"车辆 {plate} 已保存"})


@api_vehicle.route("/api/vehicles/<int:vehicle_id>", methods=["PUT"])
def update_vehicle(vehicle_id):
    """Update vehicle information."""
    err = _require_admin()
    if err: return err

    data = request.get_json(silent=True) or {}
    conn = get_conn()
    conn.execute(
        """UPDATE vehicles SET owner_name=?, phone=?, vehicle_type=?,
           monthly_fee=?, monthly_expire=?, wechat_openid=? WHERE id=?""",
        (
            data.get("owner_name", ""),
            data.get("phone", ""),
            data.get("vehicle_type", "normal"),
            data.get("monthly_fee", 0),
            data.get("monthly_expire"),
            data.get("wechat_openid"),
            vehicle_id,
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "车辆信息已更新"})


@api_vehicle.route("/api/blacklist", methods=["GET"])
def list_blacklist():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM blacklist ORDER BY created_at DESC").fetchall()]
    conn.close()
    return jsonify({"success": True, "blacklist": rows})


@api_vehicle.route("/api/blacklist", methods=["POST"])
def add_blacklist():
    err = _require_admin()
    if err: return err

    data = request.get_json(silent=True) or {}
    plate = data.get("plate_number", "").strip().upper()
    if not plate:
        return jsonify({"success": False, "error": "车牌号不能为空"}), 400

    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO blacklist (plate_number, reason) VALUES (?, ?)",
        (plate, data.get("reason", "")),
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": f"{plate} 已加入黑名单"})


@api_vehicle.route("/api/blacklist/<int:item_id>", methods=["DELETE"])
def remove_blacklist(item_id):
    err = _require_admin()
    if err: return err

    conn = get_conn()
    conn.execute("DELETE FROM blacklist WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "已移出黑名单"})
