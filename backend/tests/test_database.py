"""Tests for database operations."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database


class TestDatabase:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "test.db")
        database.DB_PATH = self.db_path
        database.init_db()

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_init_creates_tables(self):
        conn = database.get_conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        for expected in ["users", "vehicles", "records", "payments", "gates", "blacklist"]:
            assert expected in table_names

    def test_default_admin_created(self):
        conn = database.get_conn()
        row = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
        assert row is not None
        assert row["role"] == "admin"

    def test_default_gates_created(self):
        conn = database.get_conn()
        gates = conn.execute("SELECT * FROM gates").fetchall()
        assert len(gates) == 2

    def test_upsert_vehicle_insert(self):
        vid = database.upsert_vehicle("粤B12345", "张三", "13800138000", "normal")
        assert vid > 0
        v = database.get_vehicle("粤B12345")
        assert v["plate_number"] == "粤B12345"
        assert v["owner_name"] == "张三"

    def test_upsert_vehicle_update(self):
        database.upsert_vehicle("粤B12345", "张三", "13800138000")
        database.upsert_vehicle("粤B12345", "李四", "13900139000", "monthly")
        v = database.get_vehicle("粤B12345")
        assert v["owner_name"] == "李四"
        assert v["vehicle_type"] == "monthly"

    def test_blacklist_check(self):
        assert not database.is_blacklisted("粤B99999")
        conn = database.get_conn()
        conn.execute("INSERT INTO blacklist (plate_number, reason) VALUES ('粤B99999', 'Test')")
        conn.commit()
        conn.close()
        assert database.is_blacklisted("粤B99999")

    def test_find_active_entry(self):
        # No entry yet
        assert database.find_active_entry("粤B12345") is None

        # Create vehicle first (FK constraint)
        database.upsert_vehicle("粤B12345")

        # Insert entry
        conn = database.get_conn()
        conn.execute(
            "INSERT INTO records (plate_number, event_type) VALUES ('粤B12345', 'enter')"
        )
        conn.commit()
        conn.close()

        entry = database.find_active_entry("粤B12345")
        assert entry is not None
        assert entry["plate_number"] == "粤B12345"
        assert entry["event_type"] == "enter"

    def test_vehicle_by_openid(self):
        database.upsert_vehicle("粤B88888", "王五", "", "normal", wechat_openid="oTest123")
        v = database.get_vehicle_by_openid("oTest123")
        assert v is not None
        assert v["plate_number"] == "粤B88888"

        # Non-existent openid
        assert database.get_vehicle_by_openid("oNonexistent") is None

    def test_upsert_with_monthly_expire(self):
        """Verify Bug #3 fix: monthly_expire is saved correctly."""
        database.upsert_vehicle(
            "粤B99999", "赵六", "13900000000",
            vehicle_type="monthly", monthly_fee=300.0,
            monthly_expire="2026-12-31"
        )
        v = database.get_vehicle("粤B99999")
        assert v["monthly_expire"] == "2026-12-31"
        assert v["monthly_fee"] == 300.0
        assert v["vehicle_type"] == "monthly"

    def test_upsert_update_preserves_monthly_expire(self):
        """Updating a vehicle should keep monthly_expire if provided."""
        database.upsert_vehicle("粤B77777", monthly_expire="2026-06-30")
        v = database.get_vehicle("粤B77777")
        assert v["monthly_expire"] == "2026-06-30"

        # Update with new expiry
        database.upsert_vehicle("粤B77777", owner_name="钱七", monthly_expire="2027-01-01")
        v = database.get_vehicle("粤B77777")
        assert v["owner_name"] == "钱七"
        assert v["monthly_expire"] == "2027-01-01"
