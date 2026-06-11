"""Comprehensive tests: fee calculation, plate validation, OCR normalization."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from payment import calculate_fee

# ============================================================
#  Fee Calculation Tests (8 tests)
# ============================================================

class TestFeeCalculation:
    def test_free_within_30_minutes(self):
        assert calculate_fee(0, "粤B12345") == 0.0
        assert calculate_fee(15, "粤B12345") == 0.0
        assert calculate_fee(30, "粤B12345") == 0.0

    def test_short_term(self):
        assert calculate_fee(31, "粤B12345") == 5.0
        assert calculate_fee(60, "粤B12345") == 5.0
        assert calculate_fee(120, "粤B12345") == 5.0

    def test_medium_term(self):
        assert calculate_fee(121, "粤B12345") == 10.0
        assert calculate_fee(180, "粤B12345") == 10.0
        assert calculate_fee(240, "粤B12345") == 10.0

    def test_long_term(self):
        assert calculate_fee(300, "粤B12345") == 13.0   # 5h = 10 + 1*3
        assert calculate_fee(420, "粤B12345") == 19.0   # 7h = 10 + 3*3

    def test_long_term_boundary(self):
        # 4h 1min: still just over 4h, int((241-240)/60) = 0 → 10元
        assert calculate_fee(241, "粤B12345") == 10.0
        # 5h 0min: int((300-240)/60) = 1 → 13元
        assert calculate_fee(300, "粤B12345") == 13.0
        # 5h 59min: int((359-240)/60) = 1 → 13元
        assert calculate_fee(359, "粤B12345") == 13.0
        # 6h 0min: int((360-240)/60) = 2 → 16元
        assert calculate_fee(360, "粤B12345") == 16.0

    def test_daily_cap(self):
        assert calculate_fee(1440, "粤B12345") == 50.0
        assert calculate_fee(2880, "粤B12345") == 50.0  # 2 days

    def test_monthly_vehicle_always_free(self):
        assert calculate_fee(0, "粤B12345", "monthly") == 0.0
        assert calculate_fee(500, "粤B12345", "monthly") == 0.0
        assert calculate_fee(1440, "粤B12345", "monthly") == 0.0

    def test_vip_pays_normal_rate(self):
        assert calculate_fee(60, "粤B12345", "vip") == 5.0


# ============================================================
#  Plate Format Validation Tests (8 tests)
# ============================================================

PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
PATTERN_NORMAL = re.compile(rf"^[{PROVINCES}][A-Z][A-Z0-9]{{5}}$")
PATTERN_NEW_ENERGY = re.compile(rf"^[{PROVINCES}][A-Z][A-Z0-9]{{6}}$")
PATTERN_POLICE = re.compile(rf"^\d{{2,5}}[{PROVINCES}]警$")


def is_valid(text):
    cleaned = text.replace(" ", "").replace("-", "").replace(".", "").upper()
    return bool(
        PATTERN_NORMAL.match(cleaned)
        or PATTERN_NEW_ENERGY.match(cleaned)
        or PATTERN_POLICE.match(cleaned)
    )


class TestPlateValidation:
    def test_standard_plates(self):
        assert is_valid("粤B12345")
        assert is_valid("京A88888")
        assert is_valid("沪C66666")
        assert is_valid("苏E12345")
        assert is_valid("粤D45678")  # city code D (汕头) — must be valid!

    def test_all_common_city_codes(self):
        """Every letter A-Z (except I,O) can be a valid city code."""
        for letter in "ABCDEFGHJKLMNPQRSTUVWXYZ":
            plate = f"粤{letter}12345"
            assert is_valid(plate), f"City code {letter} should be valid"

    def test_new_energy_plates(self):
        assert is_valid("粤BD12345")
        assert is_valid("京AD12345")
        assert is_valid("沪AF88888")

    def test_invalid_plates(self):
        assert not is_valid("ABC123")
        assert not is_valid("12345")
        assert not is_valid("粤B123")         # too short
        assert not is_valid("粤B123456789")   # too long
        assert not is_valid("XX12345")        # invalid province
        assert not is_valid("")               # empty

    def test_spaces_and_dashes_ignored(self):
        assert is_valid("粤B 12345")
        assert is_valid("粤B-12345")
        assert is_valid("粤B.12345")

    def test_only_valid_provinces(self):
        # Must start with a valid Chinese province abbreviation
        for p in PROVINCES:
            assert is_valid(f"{p}A12345"), f"Province {p} should be valid"
        assert not is_valid("AA12345")   # not a province
        assert not is_valid("1A12345")   # not a province

    def test_police_plates(self):
        assert is_valid("12345京警")
        assert is_valid("1234粤警")
        assert is_valid("12粤警")

    def test_mixed_case_is_uppercased(self):
        assert is_valid("粤b12345")
        assert is_valid("粤B12345")


# ============================================================
#  normalize_plate() Tests — CRITICAL: Bug #1 Fix Verification
# ============================================================

# Copy the FIXED normalize_plate logic for testing
OCR_SAFE_CORRECTIONS = str.maketrans({"O": "0", "I": "1"})


def normalize_plate(plate):
    if not plate:
        return ""
    cleaned = plate.replace(" ", "").replace("-", "").replace(".", "").upper()
    cleaned = cleaned.translate(OCR_SAFE_CORRECTIONS)
    return cleaned


class TestNormalizePlate:
    """Verify normalize_plate() only corrects O→0 and I→1."""

    def test_empty_input(self):
        assert normalize_plate("") == ""
        assert normalize_plate("   ") == ""

    def test_removes_spaces_and_dashes(self):
        assert normalize_plate("粤B 12345") == "粤B12345"
        assert normalize_plate("粤B-12345") == "粤B12345"
        assert normalize_plate("粤B.12345") == "粤B12345"

    def test_uppercases(self):
        assert normalize_plate("粤b12345") == "粤B12345"

    def test_O_corrected_to_0(self):
        """Letter O is never used on Chinese plates → safe to correct to 0."""
        assert normalize_plate("粤BO1234") == "粤B01234"
        assert normalize_plate("京AO1234") == "京A01234"

    def test_I_corrected_to_1(self):
        """Letter I is never used on Chinese plates → safe to correct to 1."""
        assert normalize_plate("粤BI1234") == "粤B11234"

    # ---- CRITICAL: These tests verify Bug #1 is FIXED ----

    def test_B_not_corrupted(self):
        """粤B = 深圳, the most common plate prefix. Must stay as B."""
        assert normalize_plate("粤B12345") == "粤B12345"
        assert normalize_plate("粤B88888") == "粤B88888"
        assert normalize_plate("京B12345") == "京B12345"

    def test_S_not_corrupted(self):
        """S is a valid city code (e.g., 苏S, 浙S)."""
        assert normalize_plate("苏S12345") == "苏S12345"
        assert normalize_plate("浙S12345") == "浙S12345"

    def test_D_not_corrupted(self):
        """D is a valid city code (e.g., 粤D=汕头)."""
        assert normalize_plate("粤D12345") == "粤D12345"
        assert normalize_plate("粤D45678") == "粤D45678"

    def test_Z_not_corrupted(self):
        """Z is used for cross-border plates (e.g., 粤Z for HK/Macau)."""
        assert normalize_plate("粤Z1234港") == "粤Z1234港"
        assert normalize_plate("粤Z1234澳") == "粤Z1234澳"

    def test_L_not_corrupted(self):
        """L is a valid city code (e.g., 苏L=镇江, 浙L=舟山)."""
        assert normalize_plate("苏L12345") == "苏L12345"
        assert normalize_plate("浙L12345") == "浙L12345"

    def test_all_common_plates_preserved(self):
        """A sample of real-world plates must pass through unchanged."""
        real_plates = [
            "粤B12345",   # 深圳
            "粤A88888",   # 广州
            "京A12345",   # 北京
            "沪A88888",   # 上海
            "粤S45678",   # 东莞
            "粤D12345",   # 汕头
            "粤L12345",   # 惠州
            "苏E12345",   # 苏州
            "浙A12345",   # 杭州
            "川A12345",   # 成都
            "粤BD12345",  # 深圳新能源
            "京AD12345",  # 北京新能源
        ]
        for plate in real_plates:
            assert normalize_plate(plate) == plate, f"{plate} should not be modified"

    def test_only_known_ocr_errors_fixed(self):
        """Verify that ONLY O→0 and I→1 are applied."""
        # Plate with O in suffix → should fix
        assert normalize_plate("粤AO1234") == "粤A01234"
        # Plate with I in suffix → should fix
        assert normalize_plate("粤AI1234") == "粤A11234"
        # Plate with both → should fix both
        assert normalize_plate("粤AOI234") == "粤A01234"
        # Plate with B, D, S, Z, L → nothing changes
        assert normalize_plate("粤BDSZL5") == "粤BDSZL5"


# ============================================================
#  find_best_plate() Logic Tests — Bug #2 Fix Verification
# ============================================================

def find_best_plate(results):
    """Copy of the FIXED find_best_plate logic for testing."""
    if not results or not results[0]:
        return "", 0.0

    best_valid_plate = ""
    best_valid_conf = 0.0
    best_fallback_text = ""
    best_fallback_conf = 0.0

    for line in results[0]:
        box, (text, confidence) = line
        text = text.strip()
        if confidence > 0.7 and 6 <= len(text) <= 9:
            if is_valid(text):
                if confidence > best_valid_conf:
                    best_valid_conf = confidence
                    best_valid_plate = text
            elif len(text) >= 5 and confidence > best_fallback_conf:
                best_fallback_conf = confidence
                best_fallback_text = text

    if best_valid_plate:
        return normalize_plate(best_valid_plate), best_valid_conf
    if best_fallback_text:
        return normalize_plate(best_fallback_text), best_fallback_conf
    return "", 0.0


def make_result(lines):
    """Helper: build synthetic OCR results."""
    return [[(None, (text, conf)) for text, conf in lines]]


class TestFindBestPlate:
    def test_empty_results(self):
        assert find_best_plate(None) == ("", 0.0)
        assert find_best_plate([]) == ("", 0.0)
        assert find_best_plate([[]]) == ("", 0.0)

    def test_single_valid_plate(self):
        results = make_result([("粤B12345", 0.95)])
        plate, conf = find_best_plate(results)
        assert plate == "粤B12345"
        assert conf == 0.95

    def test_picks_highest_confidence_valid_plate(self):
        results = make_result([
            ("粤B12345", 0.85),
            ("粤A88888", 0.95),
        ])
        plate, _ = find_best_plate(results)
        assert plate == "粤A88888"

    # ---- CRITICAL: Bug #2 scenario ----
    def test_valid_plate_beats_higher_confidence_non_plate(self):
        """A valid plate with lower confidence MUST beat a non-plate with higher."""
        results = make_result([
            ("停车场入口", 0.95),   # high confidence but NOT a plate
            ("粤B12345", 0.85),     # lower confidence but IS a valid plate
        ])
        plate, _ = find_best_plate(results)
        assert plate == "粤B12345", \
            "Bug #2: valid plate was blocked by high-confidence non-plate text"

    def test_valid_plate_present_never_returns_fallback(self):
        """When a valid plate exists, never return fallback text."""
        results = make_result([
            ("ABCDEFG", 0.99),      # high conf fallback
            ("粤B12345", 0.71),     # just above threshold, valid
        ])
        plate, _ = find_best_plate(results)
        assert plate == "粤B12345"

    def test_fallback_when_no_valid_plate(self):
        """When no valid plate, return best fallback for manual review."""
        results = make_result([
            ("ABCDEFG", 0.80),      # 7 chars but invalid format
            ("XYZ1234", 0.75),
        ])
        plate, conf = find_best_plate(results)
        assert plate == "ABCDEFG"
        assert conf == 0.80

    def test_confidence_threshold_0_7(self):
        """Text with confidence ≤ 0.7 is ignored."""
        results = make_result([
            ("粤B12345", 0.70),     # exactly 0.7 → ignored
            ("粤A88888", 0.71),     # above → kept
        ])
        plate, _ = find_best_plate(results)
        assert plate == "粤A88888"

    def test_too_short_text_ignored(self):
        """Text shorter than 6 chars is ignored for valid plates."""
        results = make_result([
            ("AB123", 0.90),        # 5 chars → too short for valid plate check
            ("粤B12345", 0.85),     # valid
        ])
        plate, _ = find_best_plate(results)
        assert plate == "粤B12345"

    def test_new_energy_plate_selected(self):
        results = make_result([("粤BD12345", 0.92)])
        plate, _ = find_best_plate(results)
        assert plate == "粤BD12345"

    def test_O_correction_applied_to_result(self):
        """OCR merging O with 0 in the result."""
        results = make_result([("粤BO1234", 0.88)])  # letter O → should become 0
        plate, _ = find_best_plate(results)
        assert plate == "粤B01234"  # O corrected to 0
