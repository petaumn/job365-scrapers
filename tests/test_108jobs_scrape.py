"""
Tests for 108jobs source normalization.

Normalization helpers were extracted from sources/108jobs/scrape.py into
lib/normalize.py — import them from there directly.
"""
from lib.normalize import canonicalize_province, infer_category, infer_type


# --- province ---

def test_province_lao_vientiane():
    assert canonicalize_province("ວີວງຈັນ") == "Vientiane"


def test_province_english_capital():
    assert canonicalize_province("Vientiane Capital") == "Vientiane"


def test_province_savannakhet():
    assert canonicalize_province("Savannakhet Province") == "Savannakhet"


def test_province_luang_prabang():
    assert canonicalize_province("Luang Prabang") == "Luang Prabang"


def test_province_pakse_maps_champasak():
    assert canonicalize_province("Pakse") == "Champasak"


def test_province_remote_returns_none():
    assert canonicalize_province("Online / Remote") is None


# --- category (canonical contract values) ---

def test_category_software():
    assert infer_category("Software Developer") == "Engineering & IT"


def test_category_it_support():
    assert infer_category("IT Support Officer") == "Engineering & IT"


def test_category_accounting():
    assert infer_category("Accounting Officer") == "Banking & Finance"


def test_category_banking():
    assert infer_category("Loan Officer Banking") == "Banking & Finance"


def test_category_hr():
    assert infer_category("Human Resource Manager") == "Admin & HR"


def test_category_none_for_generic():
    assert infer_category("Staff") is None


# --- type ---

def test_type_full_time():
    assert infer_type("Full Time") == "FULL_TIME"


def test_type_full_time_hyphen():
    assert infer_type("Full-Time Employment") == "FULL_TIME"


def test_type_internship():
    assert infer_type("Internship Program") == "INTERNSHIP"


def test_type_contract():
    assert infer_type("Contract Position") == "CONTRACT"


def test_type_none():
    assert infer_type("Apply Now") is None
