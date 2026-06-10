"""Page routes — dashboard, records, vehicles, review, login."""
import os
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, session

from database import get_conn

web = Blueprint("web", __name__)


@web.route("/")
def index():
    """Dashboard page with real-time stats."""
    conn = get_conn()
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    # Today's entry count
    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE DATE(created_at) = ? AND event_type = 'enter'",
        (today,),
    )
    today_in = cursor.fetchone()[0]

    # Today's exit count
    cursor.execute(
        "SELECT COUNT(*) FROM records WHERE DATE(created_at) = ? AND event_type = 'exit'",
        (today,),
    )
    today_out = cursor.fetchone()[0]

    # Currently parked vehicles
    cursor.execute(
        """SELECT COUNT(DISTINCT plate_number) FROM records r1
           WHERE event_type = 'enter'
           AND NOT EXISTS (
               SELECT 1 FROM records r2
               WHERE r2.plate_number = r1.plate_number
               AND r2.event_type = 'exit'
               AND r2.created_at > r1.created_at
               AND DATE(r2.created_at) = ?
           )""",
        (today,),
    )
    current_parked = cursor.fetchone()[0]

    # Today's revenue
    cursor.execute(
        "SELECT COALESCE(SUM(fee), 0) FROM records WHERE DATE(created_at) = ? AND fee > 0",
        (today,),
    )
    today_revenue = cursor.fetchone()[0]

    # Recent records (last 20)
    cursor.execute("SELECT * FROM records ORDER BY created_at DESC LIMIT 20")
    recent_records = [dict(row) for row in cursor.fetchall()]

    # Pending reviews
    cursor.execute("SELECT COUNT(*) FROM records WHERE need_review = 1")
    pending_reviews = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        today_in=today_in,
        today_out=today_out,
        current_parked=current_parked,
        today_revenue=today_revenue,
        pending_reviews=pending_reviews,
        recent_records=recent_records,
    )


@web.route("/records")
def records():
    """Record search page with date and plate filter."""
    plate = request.args.get("plate", "").strip()
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    page = request.args.get("page", 1, type=int)
    per_page = 20

    conn = get_conn()
    cursor = conn.cursor()

    base_query = "FROM records WHERE DATE(created_at) = ?"
    params = [date]

    if plate:
        base_query += " AND plate_number LIKE ?"
        params.append(f"%{plate}%")

    # Total count
    cursor.execute(f"SELECT COUNT(*) {base_query}", params)
    total = cursor.fetchone()[0]

    # Paginated results
    cursor.execute(
        f"SELECT * {base_query} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page],
    )
    records_list = [dict(row) for row in cursor.fetchall()]
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "records.html",
        records=records_list,
        plate=plate,
        date=date,
        page=page,
        total=total,
        per_page=per_page,
        total_pages=total_pages,
    )


@web.route("/vehicles")
def vehicles_page():
    """Vehicle management page."""
    if not session.get("logged_in"):
        return redirect(url_for("web.login_page"))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
    vehicles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template("vehicles.html", vehicles=vehicles)


@web.route("/review")
def review_page():
    """Manual plate review page for low-confidence OCR results."""
    if not session.get("logged_in"):
        return redirect(url_for("web.login_page"))

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM records WHERE need_review = 1 ORDER BY created_at DESC LIMIT 50"
    )
    pending = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return render_template("review.html", pending=pending)


@web.route("/login")
def login_page():
    return render_template("login.html")
