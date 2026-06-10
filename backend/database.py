"""
Database module — SQLite connection, schema init, and CRUD helpers.
Uses sqlite3.Row so query results can be accessed by column name.
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "parking.db")


def get_conn() -> sqlite3.Connection:
    """Get a database connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables and indexes if they don't exist."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'operator',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE NOT NULL,
            owner_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            vehicle_type TEXT DEFAULT 'normal',
            monthly_fee REAL DEFAULT 0,
            monthly_expire DATE,
            wechat_openid TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            event_type TEXT NOT NULL,
            image_path TEXT,
            confidence REAL DEFAULT 0,
            need_review INTEGER DEFAULT 0,
            location TEXT DEFAULT 'main_gate',
            parking_duration INTEGER DEFAULT 0,
            fee REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plate_number) REFERENCES vehicles(plate_number)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            plate_number TEXT NOT NULL,
            amount REAL DEFAULT 0,
            method TEXT DEFAULT 'wechat',
            transaction_id TEXT,
            status TEXT DEFAULT 'pending',
            paid_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (record_id) REFERENCES records(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT DEFAULT '',
            direction TEXT DEFAULT 'entry',
            control_type TEXT DEFAULT 'network_relay',
            control_address TEXT DEFAULT '',
            status TEXT DEFAULT 'offline',
            last_heartbeat TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            reason TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_plate ON records(plate_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_time ON records(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_type ON records(event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_record ON payments(record_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_txn ON payments(transaction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_openid ON vehicles(wechat_openid)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_plate ON blacklist(plate_number)")

    # Default gate entries
    cursor.execute("SELECT COUNT(*) FROM gates")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO gates (name, location, direction, control_type, control_address) "
            "VALUES ('入口道闸', 'main_gate_entry', 'entry', 'network_relay', '192.168.1.200:1')"
        )
        cursor.execute(
            "INSERT INTO gates (name, location, direction, control_type, control_address) "
            "VALUES ('出口道闸', 'main_gate_exit', 'exit', 'network_relay', '192.168.1.200:2')"
        )

    # Default admin user (password: admin123)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin"),
        )

    conn.commit()
    conn.close()
    logger.info("Database initialized: %s", os.path.abspath(DB_PATH))


# ---- Vehicle helpers ----

def get_vehicle(plate: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM vehicles WHERE plate_number = ?", (plate,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_vehicle_by_openid(openid: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM vehicles WHERE wechat_openid = ?", (openid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_vehicle(plate: str, owner_name: str = "", phone: str = "",
                   vehicle_type: str = "normal", monthly_fee: float = 0,
                   wechat_openid: str = None) -> int:
    conn = get_conn()
    existing = conn.execute("SELECT id FROM vehicles WHERE plate_number = ?", (plate,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE vehicles SET owner_name=?, phone=?, vehicle_type=?, "
            "monthly_fee=?, wechat_openid=? WHERE plate_number=?",
            (owner_name, phone, vehicle_type, monthly_fee, wechat_openid, plate),
        )
        conn.commit()
        conn.close()
        return existing["id"]
    cursor = conn.execute(
        "INSERT INTO vehicles (plate_number, owner_name, phone, vehicle_type, monthly_fee, wechat_openid) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (plate, owner_name, phone, vehicle_type, monthly_fee, wechat_openid),
    )
    conn.commit()
    vid = cursor.lastrowid
    conn.close()
    return vid


def is_blacklisted(plate: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT id FROM blacklist WHERE plate_number = ?", (plate,)).fetchone()
    conn.close()
    return row is not None


# ---- Record helpers ----

def find_active_entry(plate: str) -> Optional[dict]:
    """Find the most recent entry record for a vehicle that has no matching exit."""
    conn = get_conn()
    row = conn.execute(
        """SELECT * FROM records
           WHERE plate_number = ? AND event_type = 'enter'
           AND id NOT IN (
               SELECT r1.id FROM records r1
               JOIN records r2 ON r1.plate_number = r2.plate_number
               WHERE r1.event_type = 'enter' AND r2.event_type = 'exit'
               AND r2.created_at > r1.created_at
           )
           ORDER BY created_at DESC LIMIT 1""",
        (plate,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
