"""Payment APIs — WeChat Pay order creation, callback, status query."""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from database import get_conn
from payment import create_jsapi_order, query_order, verify_callback

logger = logging.getLogger(__name__)
api_payment = Blueprint("api_payment", __name__)


@api_payment.route("/api/payment/create", methods=["POST"])
def create_payment():
    """
    Create a WeChat Pay order for a parking record.
    POST /api/payment/create
    JSON: {"record_id": 123, "openid": "oXXXX"}
    """
    data = request.get_json(silent=True) or {}
    record_id = data.get("record_id")
    openid = data.get("openid", "")

    if not record_id:
        return jsonify({"success": False, "error": "record_id is required"}), 400

    conn = get_conn()
    row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Record not found"}), 404

    record = dict(row)
    if record["fee"] <= 0:
        conn.close()
        return jsonify({"success": False, "error": "No fee required"}), 400

    # Check for existing payment
    existing = conn.execute(
        "SELECT * FROM payments WHERE record_id = ? AND status = 'success'", (record_id,)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({"success": False, "error": "Already paid"}), 400

    # Create WeChat Pay order
    result = create_jsapi_order(
        plate=record["plate_number"],
        amount=record["fee"],
        openid=openid,
        record_id=record_id,
    )

    if not result.get("success"):
        conn.close()
        return jsonify({"success": False, "error": result.get("error", "Payment creation failed")}), 500

    # Insert payment record
    conn.execute(
        """INSERT INTO payments (record_id, plate_number, amount, transaction_id, status)
           VALUES (?, ?, ?, ?, 'pending')""",
        (record_id, record["plate_number"], record["fee"], result.get("prepay_id", "")),
    )
    conn.commit()
    conn.close()

    return jsonify(result)


@api_payment.route("/api/payment/callback", methods=["POST"])
def payment_callback():
    """WeChat Pay callback endpoint."""
    body = request.get_data(as_text=True)
    if not verify_callback(dict(request.headers), body):
        logger.warning("Invalid payment callback signature")
        return jsonify({"code": "FAIL", "message": "Invalid signature"}), 400

    # Parse WeChat Pay v3 callback JSON
    import json
    try:
        cb = json.loads(body)
        transaction_id = cb.get("transaction_id", "")
        out_trade_no = cb.get("out_trade_no", "")
        trade_state = cb.get("trade_state", "")

        if trade_state == "SUCCESS":
            conn = get_conn()
            conn.execute(
                """UPDATE payments SET status = 'success', transaction_id = ?, paid_at = ?
                   WHERE transaction_id = ?""",
                (transaction_id, datetime.now().isoformat(), out_trade_no),
            )
            conn.commit()
            conn.close()
            logger.info("Payment confirmed: txn=%s", transaction_id)
    except Exception as e:
        logger.error("Callback parse error: %s", e)

    return jsonify({"code": "SUCCESS", "message": "OK"})


@api_payment.route("/api/payment/status", methods=["GET"])
def payment_status():
    """Query payment status by record_id or prepay_id."""
    record_id = request.args.get("record_id")
    prepay_id = request.args.get("prepay_id")

    conn = get_conn()
    if record_id:
        row = conn.execute(
            "SELECT * FROM payments WHERE record_id = ? ORDER BY created_at DESC LIMIT 1",
            (record_id,),
        ).fetchone()
    elif prepay_id:
        row = conn.execute(
            "SELECT * FROM payments WHERE transaction_id = ?", (prepay_id,)
        ).fetchone()
    else:
        conn.close()
        return jsonify({"success": False, "error": "record_id or prepay_id required"}), 400

    conn.close()
    if not row:
        return jsonify({"success": False, "error": "Payment not found"}), 404

    return jsonify({"success": True, "payment": dict(row)})
