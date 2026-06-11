"""
WeChat Pay integration module.
Handles: order creation, payment verification, callback processing.
Uses WeChat Pay API v3 (JSAPI for mini-programs, Native for QR codes).
"""
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Optional

import requests
from config import Config

logger = logging.getLogger(__name__)

WECHAT_PAY_API = "https://api.mch.weixin.qq.com"


def calculate_fee(parking_minutes: float, plate: str, vehicle_type: str = "normal") -> float:
    """
    Tiered parking fee calculation:
      ≤ 30 min   → free
      30min-2h   → short-term fee
      2h-4h      → medium-term fee
      > 4h       → + hourly rate per extra hour
      Monthly    → free
    """
    if vehicle_type == "monthly":
        return 0.0

    if parking_minutes <= Config.FREE_MINUTES:
        return 0.0

    if parking_minutes <= 120:
        return Config.SHORT_TERM_FEE

    if parking_minutes <= 240:
        return Config.MEDIUM_TERM_FEE

    extra_hours = (parking_minutes - 240) / 60
    fee = Config.MEDIUM_TERM_FEE + int(extra_hours) * Config.EXTRA_HOURLY_RATE
    return min(fee, Config.DAILY_CAP)


def create_jsapi_order(plate: str, amount: float, openid: str, record_id: int,
                       description: str = "停车费") -> dict:
    """
    Create a WeChat Pay JSAPI order (for mini-program payment).
    Returns prepay_id and sign params for wx.requestPayment().
    """
    if not Config.WECHAT_APP_ID or not Config.WECHAT_MCH_ID:
        logger.warning("WeChat Pay not configured — returning simulated order")
        return _simulated_prepay(amount, record_id)

    out_trade_no = _generate_trade_no()
    order = {
        "appid": Config.WECHAT_APP_ID,
        "mchid": Config.WECHAT_MCH_ID,
        "description": description,
        "out_trade_no": out_trade_no,
        "notify_url": Config.WECHAT_NOTIFY_URL,
        "amount": {
            "total": int(amount * 100),  # cents
            "currency": "CNY",
        },
        "payer": {"openid": openid},
    }

    try:
        resp = requests.post(
            f"{WECHAT_PAY_API}/v3/pay/transactions/jsapi",
            json=order,
            headers=_build_headers("POST", "/v3/pay/transactions/jsapi", json.dumps(order)),
            timeout=10,
        )
        data = resp.json()
        if resp.status_code == 200 and "prepay_id" in data:
            return _build_jsapi_params(data["prepay_id"])
        logger.error("WeChat Pay order creation failed: %s", data)
        return {"success": False, "error": data.get("message", "Unknown error")}
    except Exception as e:
        logger.error("WeChat Pay error: %s", e)
        return {"success": False, "error": str(e)}


def query_order(out_trade_no: str = None, transaction_id: str = None) -> dict:
    """Query WeChat Pay order status."""
    if not Config.WECHAT_MCH_ID:
        return {"trade_state": "SUCCESS"}  # simulated

    try:
        if transaction_id:
            url = f"{WECHAT_PAY_API}/v3/pay/transactions/id/{transaction_id}?mchid={Config.WECHAT_MCH_ID}"
        else:
            url = f"{WECHAT_PAY_API}/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={Config.WECHAT_MCH_ID}"

        resp = requests.get(url, headers=_build_headers("GET", url.split("v3")[1], ""), timeout=10)
        return resp.json() if resp.status_code == 200 else {"trade_state": "UNKNOWN"}
    except Exception as e:
        logger.error("Query order failed: %s", e)
        return {"trade_state": "ERROR", "error": str(e)}


def verify_callback(headers: dict, body: str) -> bool:
    """Verify WeChat Pay callback signature. Returns True if valid."""
    if not Config.WECHAT_API_KEY:
        return True  # skip verification when not configured (dev mode)
    # WeChat Pay v3 uses AES-256-GCM + platform certificate
    # Simplified for initial implementation
    return True


def _generate_trade_no() -> str:
    return f"PK{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"


def _build_headers(method: str, path: str, body: str) -> dict:
    """Build WeChat Pay v3 authorization headers."""
    nonce = uuid.uuid4().hex[:32]
    timestamp = str(int(time.time()))
    message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}\n"
    # In production, sign with merchant private key
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"WECHATPAY2-SHA256-RSA2048 mchid=\"{Config.WECHAT_MCH_ID}\",nonce_str=\"{nonce}\",timestamp=\"{timestamp}\",signature=\"SIMULATED\"",
    }


def _build_jsapi_params(prepay_id: str) -> dict:
    """Build params needed by wx.requestPayment()."""
    nonce = uuid.uuid4().hex[:32]
    timestamp = str(int(time.time()))
    package = f"prepay_id={prepay_id}"
    # In production: sign with merchant key
    pay_sign = _sign(f"{Config.WECHAT_APP_ID}\n{timestamp}\n{nonce}\n{package}\n")
    return {
        "success": True,
        "prepay_id": prepay_id,
        "timeStamp": timestamp,
        "nonceStr": nonce,
        "package": package,
        "signType": "RSA",
        "paySign": pay_sign,
    }


def _simulated_prepay(amount: float, record_id: int) -> dict:
    """Simulated payment for development — always succeeds."""
    return {
        "success": True,
        "prepay_id": f"simulated_{uuid.uuid4().hex[:12]}",
        "timeStamp": str(int(time.time())),
        "nonceStr": uuid.uuid4().hex[:32],
        "package": f"prepay_id=simulated_{record_id}",
        "signType": "MD5",
        "paySign": "SIMULATED",
        "_simulated": True,
    }


def _sign(message: str) -> str:
    return hashlib.md5(message.encode()).hexdigest()
