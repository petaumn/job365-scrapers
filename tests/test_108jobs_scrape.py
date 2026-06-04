"""
Tests for sources/108jobs/scrape.py helper functions.

importlib is used because '108jobs' is not a valid Python identifier,
so the module cannot be imported with a normal 'from' statement.
"""
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

_spec = importlib.util.spec_from_file_location(
    "_scrape_108jobs",
    _ROOT / "sources" / "108jobs" / "scrape.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_normalise_province = _mod._normalise_province
_infer_category = _mod._infer_category
_infer_type = _mod._infer_type


# --- province (canonical slugs per docs/scrapers-contract.md) ---

def test_province_lao_vientiane():
    assert _normalise_province("ວຽງຈັນ") == "vientiane-capital"


def test_province_english_capital():
    assert _normalise_province("Vientiane Capital") == "vientiane-capital"


def test_province_savannakhet():
    assert _normalise_province("Savannakhet Province") == "savannakhet"


def test_province_luang_prabang():
    assert _normalise_province("Luang Prabang") == "luang-prabang"


def test_province_pakse_maps_champasak():
    assert _normalise_province("Pakse") == "champasak"


def test_province_remote_returns_none():
    assert _normalise_province("Online / Remote") is None


# --- category (10 canonical Job365 values) ---

def test_category_software():
    assert _infer_category("Software Developer") == "Engineering & IT"


def test_category_it_support():
    assert _infer_category("IT Support Officer") == "Engineering & IT"


def test_category_accounting():
    # "Accounting" maps to Banking & Finance per the canonical mapping
    assert _infer_category("Accounting Officer") == "Banking & Finance"


def test_category_banking():
    assert _infer_category("Loan Officer Banking") == "Banking & Finance"


def test_category_hr():
    assert _infer_category("Human Resource Manager") == "Admin & HR"


def test_category_none_for_generic():
    assert _infer_category("Staff") is None


# --- type ---

def test_type_full_time():
    assert _infer_type("Full Time") == "FULL_TIME"


def test_type_full_time_hyphen():
    assert _infer_type("Full-Time Employment") == "FULL_TIME"


def test_type_internship():
    assert _infer_type("Internship Program") == "INTERNSHIP"


def test_type_contract():
    assert _infer_type("Contract Position") == "CONTRACT"


def test_type_none():
    assert _infer_type("Apply Now") is None
