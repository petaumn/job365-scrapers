"""
lib/normalize.py — shared data-normalization helpers for all Job365 scrapers.

Provides:
  parse_salary(raw)           — parse salary strings to (min_lak, max_lak) or (None, None)
  canonicalize_province(raw)  — map raw location strings to canonical Lao province names
  infer_category(text)        — classify job text into one of the 10 canonical categories
  infer_type(text)            — map employment-type strings to the API enum
"""
import re

_NUM_RE = re.compile(r"[\d,]+")


def _clean_num(s: str) -> int | None:
    s = s.replace(",", "").strip()
    try:
        return int(s)
    except ValueError:
        return None


def parse_salary(raw: str) -> tuple[int | None, int | None]:
    """
    Parse a raw salary string into (salary_min, salary_max) in LAK/month.

    Handles:
      "3,000,000 - 5,000,000 LAK"  -> (3000000, 5000000)
      "5000000 kip"                 -> (5000000, None)
      "$500 - $800"                 -> (None, None)  # foreign currency — skip
      ""                            -> (None, None)
    """
    if not raw:
        return None, None

    if re.search(r"[$€\xa3฿]|USD|THB|EUR", raw, re.I):
        return None, None

    nums = _NUM_RE.findall(raw)
    if not nums:
        return None, None

    values = [_clean_num(n) for n in nums if _clean_num(n) is not None]
    # LAK monthly salary sanity: 500k – 500M
    values = [v for v in values if 500_000 <= v <= 500_000_000]

    if not values:
        return None, None
    if len(values) == 1:
        return values[0], None

    low, high = min(values[0], values[1]), max(values[0], values[1])
    return low, high


# ---------------------------------------------------------------------------
# Province canonicalization
# ---------------------------------------------------------------------------

# Maps lowercase fragments (Lao script + English) to canonical province names
PROVINCE_MAP: dict[str, str] = {
    "ວີວງຈັນ": "Vientiane",
    "vientiane capital": "Vientiane",
    "vientiane prefecture": "Vientiane",
    "vientiane": "Vientiane",
    "ສາວັນນະເຂດ": "Savannakhet",
    "savannakhet": "Savannakhet",
    "ຫຼວງພະບາງ": "Luang Prabang",
    "luang prabang": "Luang Prabang",
    "ຈຳປາສັກ": "Champasak",
    "champasak": "Champasak",
    "ປາກເສ": "Champasak",
    "pakse": "Champasak",
    "ຄຳມ່ວນ": "Khammouane",
    "khammouane": "Khammouane",
    "ບອລິຄຳໄສ": "Bolikhamxai",
    "bolikhamxai": "Bolikhamxai",
    "ຫອວພັນ": "Houaphanh",
    "houaphanh": "Houaphanh",
    "ຫວ້ານ": "Houaphanh",
    "ອຸດົມໄສ": "Oudomxay",
    "oudomxay": "Oudomxay",
    "ໂຂງ": "Champasak",
    "luang namtha": "Luang Namtha",
    "bokeo": "Bokeo",
    "phongsaly": "Phongsaly",
    "saravane": "Saravane",
    "sekong": "Sekong",
    "xaisomboun": "Xaisomboun",
    "xayaboury": "Xayaboury",
    "xiengkhouang": "Xieng Khouang",
    "xieng khouang": "Xieng Khouang",
}


def canonicalize_province(raw: str) -> str | None:
    """Return a canonical Lao province name for a raw location string, or None."""
    low = raw.lower()
    for key, prov in PROVINCE_MAP.items():
        if key in low:
            return prov
    return None


# ---------------------------------------------------------------------------
# Job category inference
# ---------------------------------------------------------------------------

# Maps keyword fragments to the 10 canonical categories from docs/scrapers-contract.md:
# Engineering & IT, Hospitality & Tourism, Banking & Finance, Sales & Marketing,
# Logistics & Supply Chain, Manufacturing, Healthcare, NGO & Development,
# Education & Training, Admin & HR
CATEGORY_MAP: dict[str, str] = {
    # Engineering & IT
    "information technology": "Engineering & IT",
    "software": "Engineering & IT",
    "developer": "Engineering & IT",
    "programmer": "Engineering & IT",
    "it support": "Engineering & IT",
    "network engineer": "Engineering & IT",
    "data analyst": "Engineering & IT",
    "data engineer": "Engineering & IT",
    "civil engineer": "Engineering & IT",
    "electrical engineer": "Engineering & IT",
    "mechanical engineer": "Engineering & IT",
    # Banking & Finance
    "accounting": "Banking & Finance",
    "finance": "Banking & Finance",
    "audit": "Banking & Finance",
    "banking": "Banking & Finance",
    "loan officer": "Banking & Finance",
    "credit": "Banking & Finance",
    # Sales & Marketing
    "marketing": "Sales & Marketing",
    "digital marketing": "Sales & Marketing",
    "brand": "Sales & Marketing",
    "sales": "Sales & Marketing",
    "business development": "Sales & Marketing",
    # Admin & HR
    "human resource": "Admin & HR",
    "hr ": "Admin & HR",
    "recruitment": "Admin & HR",
    "administration": "Admin & HR",
    "admin": "Admin & HR",
    "secretary": "Admin & HR",
    # Education & Training
    "education": "Education & Training",
    "teacher": "Education & Training",
    "training": "Education & Training",
    # Healthcare
    "healthcare": "Healthcare",
    "nurse": "Healthcare",
    "doctor": "Healthcare",
    "medical": "Healthcare",
    # Hospitality & Tourism
    "hospitality": "Hospitality & Tourism",
    "hotel": "Hospitality & Tourism",
    "tourism": "Hospitality & Tourism",
    "restaurant": "Hospitality & Tourism",
    # Logistics & Supply Chain
    "logistics": "Logistics & Supply Chain",
    "supply chain": "Logistics & Supply Chain",
    "warehouse": "Logistics & Supply Chain",
    "driver": "Logistics & Supply Chain",
    # Manufacturing
    "manufacturing": "Manufacturing",
    "factory": "Manufacturing",
    "production": "Manufacturing",
    # NGO & Development
    "ngo": "NGO & Development",
    "ingo": "NGO & Development",
    "development officer": "NGO & Development",
    "programme officer": "NGO & Development",
    "project officer": "NGO & Development",
}


def infer_category(text: str) -> str | None:
    """Infer a canonical category from job title or description text, or None."""
    low = text.lower()
    for keyword, cat in CATEGORY_MAP.items():
        if keyword in low:
            return cat
    return None


# ---------------------------------------------------------------------------
# Employment type normalization
# ---------------------------------------------------------------------------

TYPE_MAP: dict[str, str] = {
    "full time": "FULL_TIME",
    "fulltime": "FULL_TIME",
    "full-time": "FULL_TIME",
    "part time": "PART_TIME",
    "parttime": "PART_TIME",
    "part-time": "PART_TIME",
    "contract": "CONTRACT",
    "temporary": "TEMPORARY",
    "internship": "INTERNSHIP",
    "intern ": "INTERNSHIP",
    "freelance": "FREELANCE",
}

VALID_TYPES: frozenset[str] = frozenset(TYPE_MAP.values())


def infer_type(text: str) -> str | None:
    """Map a raw employment-type string to the API enum value, or None."""
    low = text.lower()
    for keyword, jtype in TYPE_MAP.items():
        if keyword in low:
            return jtype
    return None
