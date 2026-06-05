"""
Tests for lib/normalize.py — canonical province slugs, category inference,
and job type inference.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.normalize import canonicalize_province, infer_category, infer_type


# ---------------------------------------------------------------------------
# Province slug tests
# ---------------------------------------------------------------------------

def test_province_lao_vientiane_capital():
    assert canonicalize_province("ນະຄອນຫຼວງວຽງຈັນ") == "vientiane-capital"


def test_province_lao_vientiane_city_defaults_capital():
    assert canonicalize_province("ວຽງຈັນ") == "vientiane-capital"


def test_province_english_vientiane_capital():
    assert canonicalize_province("Vientiane Capital") == "vientiane-capital"


def test_province_english_vientiane_prefecture():
    assert canonicalize_province("Vientiane Prefecture") == "vientiane-capital"


def test_province_english_vientiane_province():
    assert canonicalize_province("Vientiane Province") == "vientiane"


def test_province_savannakhet_english():
    assert canonicalize_province("Savannakhet") == "savannakhet"


def test_province_savannakhet_variant_spelling():
    assert canonicalize_province("Savanaket") == "savannakhet"


def test_province_luang_prabang():
    assert canonicalize_province("Luang Prabang") == "luang-prabang"


def test_province_champasak():
    assert canonicalize_province("Champasak") == "champasak"


def test_province_pakse_maps_champasak():
    assert canonicalize_province("Pakse") == "champasak"


def test_province_lao_script_savannakhet():
    assert canonicalize_province("ສະຫວັນນະເຂດ") == "savannakhet"


def test_province_lao_script_luang_prabang():
    assert canonicalize_province("ຫຼວງພະບາງ") == "luang-prabang"


def test_province_lao_script_champasak():
    assert canonicalize_province("ຈຳປາສັກ") == "champasak"


def test_province_lao_script_khammouane():
    assert canonicalize_province("ຄຳມ່ວນ") == "khammouane"


def test_province_bolikhamsai_variant():
    assert canonicalize_province("Bolikhamxai") == "bolikhamsai"


def test_province_salavan_variant():
    assert canonicalize_province("Saravane") == "salavan"


def test_province_luang_namtha():
    assert canonicalize_province("Luang Namtha") == "luang-namtha"


def test_province_houaphanh():
    assert canonicalize_province("Houaphanh") == "houaphanh"


def test_province_oudomxay_variant():
    assert canonicalize_province("Oudomsai") == "oudomxay"


def test_province_xieng_khouang():
    assert canonicalize_province("Xieng Khouang") == "xieng-khouang"


def test_province_phongsaly():
    assert canonicalize_province("Phongsaly") == "phongsaly"


def test_province_sekong():
    assert canonicalize_province("Sekong") == "sekong"


def test_province_attapeu():
    assert canonicalize_province("Attapeu") == "attapeu"


def test_province_xaysomboun():
    assert canonicalize_province("Xaisomboun") == "xaisomboun"


def test_province_partial_match_in_longer_string():
    # province name embedded in a location string
    assert canonicalize_province("Sisattanak District, Vientiane Capital") == "vientiane-capital"


def test_province_remote_returns_none():
    assert canonicalize_province("Online / Remote") is None


def test_province_empty_returns_none():
    assert canonicalize_province("") is None


# ---------------------------------------------------------------------------
# Category inference tests
# ---------------------------------------------------------------------------

def test_category_software_developer():
    assert infer_category("Software Developer") == "Engineering & IT"


def test_category_it_support():
    assert infer_category("IT Support Officer") == "Engineering & IT"


def test_category_engineer():
    assert infer_category("Civil Engineer") == "Engineering & IT"


def test_category_accounting():
    assert infer_category("Accounting Officer") == "Banking & Finance"


def test_category_banking():
    assert infer_category("Loan Officer — Banking Department") == "Banking & Finance"


def test_category_finance():
    assert infer_category("Finance Manager") == "Banking & Finance"


def test_category_marketing():
    assert infer_category("Marketing Manager") == "Sales & Marketing"


def test_category_digital_marketing_beats_marketing():
    # More specific rule should match first
    assert infer_category("Digital Marketing Specialist") == "Sales & Marketing"


def test_category_sales():
    assert infer_category("Sales Representative") == "Sales & Marketing"


def test_category_human_resource():
    assert infer_category("Human Resource Manager") == "Admin & HR"


def test_category_admin():
    assert infer_category("Administrative Officer") == "Admin & HR"


def test_category_manufacturing():
    assert infer_category("Production Supervisor") == "Manufacturing"


def test_category_hotel():
    assert infer_category("Hotel Manager") == "Hospitality & Tourism"


def test_category_tourism():
    assert infer_category("Tourism Development Officer") == "Hospitality & Tourism"


def test_category_nurse():
    assert infer_category("Nurse Practitioner") == "Healthcare"


def test_category_medical():
    assert infer_category("Medical Officer") == "Healthcare"


def test_category_programme_officer():
    assert infer_category("Programme Officer") == "NGO & Development"


def test_category_ngo():
    assert infer_category("NGO Project Coordinator") == "NGO & Development"


def test_category_teacher():
    assert infer_category("English Teacher") == "Education & Training"


def test_category_logistics():
    assert infer_category("Logistics Manager") == "Logistics & Supply Chain"


def test_category_supply_chain():
    assert infer_category("Supply Chain Analyst") == "Logistics & Supply Chain"


def test_category_none_for_generic():
    assert infer_category("Staff") is None


def test_category_none_for_empty():
    assert infer_category("") is None


# ---------------------------------------------------------------------------
# Job type inference tests
# ---------------------------------------------------------------------------

def test_type_full_time():
    assert infer_type("Full Time") == "FULL_TIME"


def test_type_full_time_hyphen():
    assert infer_type("Full-Time Employment") == "FULL_TIME"


def test_type_lao_script_full_time():
    assert infer_type("ເຕັມເວລາ") == "FULL_TIME"


def test_type_part_time():
    assert infer_type("Part-Time Position") == "PART_TIME"


def test_type_contract():
    assert infer_type("Contract Position") == "CONTRACT"


def test_type_internship():
    assert infer_type("Internship Program") == "INTERNSHIP"


def test_type_intern():
    assert infer_type("Intern — 3 months") == "INTERNSHIP"


def test_type_lao_script_internship():
    assert infer_type("ຝຶກງານ 6 ເດືອນ") == "INTERNSHIP"


def test_type_none_for_unrecognised():
    assert infer_type("Apply Now") is None


def test_type_none_for_empty():
    assert infer_type("") is None
