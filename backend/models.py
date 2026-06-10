"""Data models as dataclasses for type-safe DB row handling."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    role: str = "operator"
    created_at: Optional[str] = None


@dataclass
class Vehicle:
    id: Optional[int] = None
    plate_number: str = ""
    owner_name: str = ""
    phone: str = ""
    vehicle_type: str = "normal"
    monthly_fee: float = 0.0
    monthly_expire: Optional[str] = None
    wechat_openid: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Record:
    id: Optional[int] = None
    plate_number: str = ""
    event_type: str = ""          # enter / exit
    image_path: Optional[str] = None
    confidence: float = 0.0
    need_review: int = 0
    location: str = "main_gate"
    parking_duration: int = 0     # seconds
    fee: float = 0.0
    created_at: Optional[str] = None


@dataclass
class Payment:
    id: Optional[int] = None
    record_id: int = 0
    plate_number: str = ""
    amount: float = 0.0
    method: str = "wechat"
    transaction_id: Optional[str] = None
    status: str = "pending"
    paid_at: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Gate:
    id: Optional[int] = None
    name: str = ""
    location: str = ""
    direction: str = "entry"
    control_type: str = "network_relay"
    control_address: str = ""
    status: str = "offline"
    last_heartbeat: Optional[str] = None


@dataclass
class Blacklist:
    id: Optional[int] = None
    plate_number: str = ""
    reason: str = ""
    created_at: Optional[str] = None
