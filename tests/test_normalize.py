"""
Tests for lib/normalize.py — salary parsing, province canonicalization,
category inference, and employment-type normalization.
"""
from lib.normalize import (
    parse_salary,
    canonicalize_province,
    infer_category,
    infer_type,
)


# ---------------------------------------------------------------------------
# parse_salary
# ---------------------------------------------------------------------------

def test_salary_range_lak():
    assert parse_salary("3,000,000 - 5,000,000 LAK") == (3_000_000, 5_000_000)


def test_salary_single_kip():
    assert parse_salary("5000000 kip") == (5_000_000, None)


def test_salary_usd_rejected():
    assert parse_salary("$500 - $800") == (None, None)


def test_salary_thb_rejected():
    assert parse_salary("฿15,000") == (None, None)


def test_salary_empty():
    assert parse_salary("") == (None, None)


def test_salary_below_minimum():
    # Values below 500k LAK sanity threshold are dropped
    assert parse_salary("100 kip") == (None, None)


def test_salary_range_normalised():
    # Always returns (low, high) regardless of input order
    lo, hi = parse_salary("5,000,000 - 3,000,000 LAK")
    assert lo == 3_000_000
    assert hi == 5_000_000


# ---------------------------------------------------------------------------
# canonicalize_province
# ---------------------------------------------------------------------------

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


def test_province_unknown_returns_none():
    assert canonicalize_province("Bangkok") is None


# ---------------------------------------------------------------------------
# infer_category
# ---------------------------------------------------------------------------

def test_category_software():
    assert infer_category("Software Developer") == "Engineering & IT"


def test_category_it_support():
    assert infer_category("IT Support Officer") == "Engineering & IT"


def test_category_accounting():
    assert infer_category("Accounting Officer") == "Banking & Finance"


def test_category_loan_officer():
    assert infer_category("Loan Officer Banking") == "Banking & Finance"


def test_category_hr():
    assert infer_category("Human Resource Manager") == "Admin & HR"


def test_category_marketing():
    assert infer_category("Digital Marketing Executive") == "Sales & Marketing"


def test_category_logistics():
    assert infer_category("Logistics Coordinator") == "Logistics & Supply Chain"


def test_category_ngo():
    assert infer_category("NGO Programme Officer") == "NGO & Development"


def test_category_none_for_generic():
    assert infer_category("Staff") is None


# ---------------------------------------------------------------------------
# infer_type
# ---------------------------------------------------------------------------

def test_type_full_time():
    assert infer_type("Full Time") == "FULL_TIME"


def test_type_full_time_hyphen():
    assert infer_type("Full-Time Employment") == "FULL_TIME"


def test_type_internship():
    assert infer_type("Internship Program") == "INTERNSHIP"


def test_type_contract():
    assert infer_type("Contract Position") == "CONTRACT"


def test_type_part_time():
    assert infer_type("Part-Time Job") == "PART_TIME"


def test_type_none():
    assert infer_type("Apply Now") is None
