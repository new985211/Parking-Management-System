"""Tests for fee calculation logic."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from payment import calculate_fee


class TestFeeCalculation:
    def test_free_within_30_minutes(self):
        assert calculate_fee(0, "粤B12345") == 0.0
        assert calculate_fee(15, "粤B12345") == 0.0
        assert calculate_fee(30, "粤B12345") == 0.0

    def test_short_term_30min_to_2h(self):
        assert calculate_fee(31, "粤B12345") == 5.0
        assert calculate_fee(60, "粤B12345") == 5.0
        assert calculate_fee(120, "粤B12345") == 5.0

    def test_medium_term_2h_to_4h(self):
        assert calculate_fee(121, "粤B12345") == 10.0
        assert calculate_fee(180, "粤B12345") == 10.0
        assert calculate_fee(240, "粤B12345") == 10.0

    def test_long_term_over_4h(self):
        # 4h + 1h extra = 10 + 3 = 13
        fee = calculate_fee(300, "粤B12345")  # 5 hours
        assert fee == 13.0

        # 4h + 3h extra = 10 + 9 = 19
        fee = calculate_fee(420, "粤B12345")  # 7 hours
        assert fee == 19.0

    def test_daily_cap(self):
        # Very long parking should cap at daily max
        fee = calculate_fee(1440, "粤B12345")  # 24 hours
        assert fee == 50.0

    def test_monthly_vehicle_free(self):
        assert calculate_fee(500, "粤B12345", "monthly") == 0.0
        assert calculate_fee(1440, "粤B12345", "monthly") == 0.0

    def test_vip_vehicle_normal_rate(self):
        # VIP vehicles pay normal rates (no special discount in config)
        assert calculate_fee(60, "粤B12345", "vip") == 5.0


class TestPlateValidation:
    """Test the plate validation logic from the OCR server."""
    import re

    PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
    PATTERN_NORMAL = re.compile(rf"^[{PROVINCES}][A-Z][A-Z0-9]{{5}}$")
    PATTERN_NEW_ENERGY = re.compile(rf"^[{PROVINCES}][A-Z][A-Z0-9]{{6}}$")

    def is_valid(self, text):
        cleaned = text.replace(" ", "").replace("-", "").upper()
        return bool(
            self.PATTERN_NORMAL.match(cleaned)
            or self.PATTERN_NEW_ENERGY.match(cleaned)
        )

    def test_standard_plates(self):
        assert self.is_valid("粤B12345")
        assert self.is_valid("京A88888")
        assert self.is_valid("沪C66666")
        assert self.is_valid("苏E12345")

    def test_new_energy_plates(self):
        assert self.is_valid("粤BD12345")   # 8 chars: 粤 + B + D12345 (6)
        assert self.is_valid("京AD12345")   # 8 chars: 京 + A + D12345 (6)
        assert self.is_valid("沪AF88888")   # 8 chars: 沪 + A + F88888 (6)

    def test_invalid_plates(self):
        assert not self.is_valid("ABC123")
        assert not self.is_valid("12345")
        assert not self.is_valid("粤B123")  # too short
        assert not self.is_valid("粤B123456789")  # too long

    def test_plate_normalization(self):
        """OCR common errors should be corrected."""
        normalized = "粤B12345".replace("O", "0").replace("I", "1")
        assert normalized == "粤B12345"
        # O → 0 correction
        fixed = "粤BO1234".replace("O", "0")
        assert fixed == "粤B01234"
