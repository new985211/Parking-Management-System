"""Admin APIs — auth, stats, config."""
from datetime import datetime

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

from database import get_conn

api_admin = Blueprint("api_admin", __name__)


@api_admin.route("/api/login", methods=["POST"])
def admin_login():
    """Admin login with username/password."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "error": "请输入用户名和密码"}), 400

    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()

    if row and check_password_hash(row["password_hash"], password):
        session["logged_in"] = True
        session["username"] = username
        session["role"] = row["role"]
        return jsonify({"success": True, "username": username, "role": row["role"]})

    return jsonify({"success": False, "error": "用户名或密码错误"}), 401


@api_admin.route("/api/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})


@api_admin.route("/api/stats", methods=["GET"])
def get_stats():
    """Get dashboard statistics."""
    conn = get_conn()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM records WHERE DATE(created_at) = ? AND event_type = 'enter'", (today,))
    today_in = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM records WHERE DATE(created_at) = ? AND event_type = 'exit'", (today,))
    today_out = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(fee), 0) FROM records WHERE DATE(created_at) = ?", (today,))
    today_revenue = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM records WHERE need_review = 1")
    pending_review = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type = 'monthly'")
    monthly_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "success": True,
        "date": today,
        "today_in": today_in,
        "today_out": today_out,
        "today_revenue": round(today_revenue, 2),
        "pending_review": pending_review,
        "monthly_vehicles": monthly_count,
        "total_vehicles": total_vehicles,
    })


@api_admin.route("/api/recent", methods=["GET"])
def recent_records():
    """Get recent records for AJAX refresh (no full page fetch)."""
    from database import get_conn
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records ORDER BY created_at DESC LIMIT 20")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "records": rows})


@api_admin.route("/api/stats/weekly", methods=["GET"])
def weekly_stats():
    """Get 7-day stats for chart display."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT DATE(created_at) as day,
                  SUM(CASE WHEN event_type='enter' THEN 1 ELSE 0 END) as entries,
                  SUM(CASE WHEN event_type='exit' THEN 1 ELSE 0 END) as exits,
                  COALESCE(SUM(CASE WHEN fee > 0 THEN fee ELSE 0 END), 0) as revenue
           FROM records
           WHERE created_at >= DATE('now', '-7 days')
           GROUP BY DATE(created_at)
           ORDER BY day"""
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"success": True, "weekly": rows})
