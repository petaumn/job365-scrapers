"""
lib/normalize.py — canonical normalization helpers shared across all scrapers.

Province slugs and the 10-value category set must match the Job365 platform
contract. See docs/scrapers-contract.md for the authoritative reference.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Province slugs
# ---------------------------------------------------------------------------
# Keys: lowercase Lao script or lowercase English (various spellings).
# Values: canonical platform slug used in the `province` field of POST requests.

PROVINCE_SLUGS: dict[str, str] = {
    # Lao script
    "ນະຄອນຫຼວງວຽງຈັນ": "vientiane-capital",
    "ວຽງຈັນ": "vientiane-capital",  # city name -> capital province
    "ແຂວງວຽງຈັນ": "vientiane",
    "ສະຫວັນນະເຂດ": "savannakhet",
    "ຫຼວງພະບາງ": "luang-prabang",
    "ຈຳປາສັກ": "champasak",
    "ປາກເຊ": "champasak",
    "ຄຳມ່ວນ": "khammouane",
    "ບໍລິຄຳໄຊ": "bolikhamsai",
    "ສາລະວັນ": "salavan",
    "ໄຊຍະບູລີ": "xayaboury",
    "ຫຼວງນ້ຳທາ": "luang-namtha",
    "ຫົວພັນ": "houaphanh",
    "ອຸດົມໄຊ": "oudomxay",
    "ບໍ່ແກ້ວ": "bokeo",
    "ຊຽງຂວາງ": "xieng-khouang",
    "ຜົ້ງສາລີ": "phongsaly",
    "ອັດຕະປື": "attapeu",
    "ເຊກອງ": "sekong",
    "ໄຊສົມບູນ": "xaisomboun",
    # English — canonical and variant spellings
    "vientiane capital": "vientiane-capital",
    "vientiane prefecture": "vientiane-capital",
    "nakhone luang vientiane": "vientiane-capital",
    "vientiane province": "vientiane",
    "vientiane (province)": "vientiane",
    "savannakhet": "savannakhet",
    "savanaket": "savannakhet",
    "luang prabang": "luang-prabang",
    "luang phrabang": "luang-prabang",
    "champasak": "champasak",
    "pakse": "champasak",
    "khammouane": "khammouane",
    "khammuan": "khammouane",
    "bolikhamsai": "bolikhamsai",
    "bolikhamxai": "bolikhamsai",
    "salavan": "salavan",
    "saravane": "salavan",
    "xayaboury": "xayaboury",
    "sayaboury": "xayaboury",
    "luang namtha": "luang-namtha",
    "luangnamtha": "luang-namtha",
    "houaphanh": "houaphanh",
    "huaphanh": "houaphanh",
    "oudomxay": "oudomxay",
    "oudomsai": "oudomxay",
    "bokeo": "bokeo",
    "xieng khouang": "xieng-khouang",
    "xiengkhouang": "xieng-khouang",
    "phongsaly": "phongsaly",
    "attapeu": "attapeu",
    "sekong": "sekong",
    "xaisomboun": "xaisomboun",
}

# ---------------------------------------------------------------------------
# Category rules — 10-value canonical set
# ---------------------------------------------------------------------------
# Ordered list of (keyword, canonical_value) tuples.
# Specific terms appear BEFORE broad ones to avoid false matches.
# Omit `category` rather than guessing when no rule matches — the server
# classifies from title + description, which is better than a wrong value.

CATEGORY_RULES: list[tuple[str, str]] = [
    # Engineering & IT — specific before broad
    ("software developer", "Engineering & IT"),
    ("web developer", "Engineering & IT"),
    ("it support", "Engineering & IT"),
    ("it officer", "Engineering & IT"),
    ("network engineer", "Engineering & IT"),
    ("data engineer", "Engineering & IT"),
    ("data analyst", "Engineering & IT"),
    ("system admin", "Engineering & IT"),
    ("systems analyst", "Engineering & IT"),
    ("database", "Engineering & IT"),
    ("devops", "Engineering & IT"),
    ("cybersecurity", "Engineering & IT"),
    ("information technology", "Engineering & IT"),
    ("software", "Engineering & IT"),
    ("developer", "Engineering & IT"),
    ("programmer", "Engineering & IT"),
    ("civil engineer", "Engineering & IT"),
    ("mechanical engineer", "Engineering & IT"),
    ("electrical engineer", "Engineering & IT"),
    ("engineer", "Engineering & IT"),
    # Banking & Finance
    ("loan officer", "Banking & Finance"),
    ("credit analyst", "Banking & Finance"),
    ("treasury", "Banking & Finance"),
    ("investment analyst", "Banking & Finance"),
    ("banking", "Banking & Finance"),
    ("accountant", "Banking & Finance"),
    ("accounting", "Banking & Finance"),
    ("audit", "Banking & Finance"),
    ("finance", "Banking & Finance"),
    ("tax", "Banking & Finance"),
    # Sales & Marketing
    ("digital marketing", "Sales & Marketing"),
    ("brand manager", "Sales & Marketing"),
    ("marketing manager", "Sales & Marketing"),
    ("marketing officer", "Sales & Marketing"),
    ("marketing", "Sales & Marketing"),
    ("sales manager", "Sales & Marketing"),
    ("business development", "Sales & Marketing"),
    ("account manager", "Sales & Marketing"),
    ("sales", "Sales & Marketing"),
    # Admin & HR
    ("human resource", "Admin & HR"),
    ("hr manager", "Admin & HR"),
    ("hr officer", "Admin & HR"),
    ("recruitment", "Admin & HR"),
    ("administrative officer", "Admin & HR"),
    ("office manager", "Admin & HR"),
    ("executive assistant", "Admin & HR"),
    ("personal assistant", "Admin & HR"),
    ("secretary", "Admin & HR"),
    ("legal officer", "Admin & HR"),
    ("compliance officer", "Admin & HR"),
    ("administration", "Admin & HR"),
    ("admin", "Admin & HR"),
    ("legal", "Admin & HR"),
    # Manufacturing
    ("quality control", "Manufacturing"),
    ("quality assurance", "Manufacturing"),
    ("production supervisor", "Manufacturing"),
    ("construction", "Manufacturing"),
    ("manufacturing", "Manufacturing"),
    ("factory", "Manufacturing"),
    # Hospitality & Tourism
    ("food and beverage", "Hospitality & Tourism"),
    ("f&b", "Hospitality & Tourism"),
    ("chef", "Hospitality & Tourism"),
    ("hotel", "Hospitality & Tourism"),
    ("hospitality", "Hospitality & Tourism"),
    ("tourism", "Hospitality & Tourism"),
    ("restaurant", "Hospitality & Tourism"),
    # Healthcare
    ("medical officer", "Healthcare"),
    ("nurse", "Healthcare"),
    ("physician", "Healthcare"),
    ("pharmacist", "Healthcare"),
    ("health officer", "Healthcare"),
    ("public health", "Healthcare"),
    ("doctor", "Healthcare"),
    ("healthcare", "Healthcare"),
    ("medical", "Healthcare"),
    ("hospital", "Healthcare"),
    # NGO & Development
    ("programme officer", "NGO & Development"),
    ("project coordinator", "NGO & Development"),
    ("monitoring and evaluation", "NGO & Development"),
    ("m&e officer", "NGO & Development"),
    ("ngo", "NGO & Development"),
    ("ingo", "NGO & Development"),
    ("development officer", "NGO & Development"),
    ("humanitarian", "NGO & Development"),
    ("international organization", "NGO & Development"),
    ("development", "NGO & Development"),
    # Education & Training
    ("teacher", "Education & Training"),
    ("lecturer", "Education & Training"),
    ("trainer", "Education & Training"),
    ("curriculum", "Education & Training"),
    ("school principal", "Education & Training"),
    ("education", "Education & Training"),
    ("training", "Education & Training"),
    # Logistics & Supply Chain
    ("logistics manager", "Logistics & Supply Chain"),
    ("supply chain", "Logistics & Supply Chain"),
    ("warehouse", "Logistics & Supply Chain"),
    ("procurement officer", "Logistics & Supply Chain"),
    ("procurement", "Logistics & Supply Chain"),
    ("import export", "Logistics & Supply Chain"),
    ("customs", "Logistics & Supply Chain"),
    ("delivery", "Logistics & Supply Chain"),
    ("driver", "Logistics & Supply Chain"),
    ("logistics", "Logistics & Supply Chain"),
]

# ---------------------------------------------------------------------------
# Job type map — includes Lao script keys
# ---------------------------------------------------------------------------

TYPE_MAP: dict[str, str] = {
    "full time": "FULL_TIME",
    "fulltime": "FULL_TIME",
    "full-time": "FULL_TIME",
    "ເຕັມເວລາ": "FULL_TIME",
    "part time": "PART_TIME",
    "parttime": "PART_TIME",
    "part-time": "PART_TIME",
    "ເຄິ່ງເວລາ": "PART_TIME",
    "contract": "CONTRACT",
    "ສັນຍາ": "CONTRACT",
    "internship": "INTERNSHIP",
    "intern": "INTERNSHIP",
    "ຝຶກງານ": "INTERNSHIP",
    "freelance": "FREELANCE",
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def canonicalize_province(raw: str) -> str | None:
    """Return canonical province slug for *raw*, or None if unmappable."""
    if not raw:
        return None
    low = raw.strip().lower()
    if low in PROVINCE_SLUGS:
        return PROVINCE_SLUGS[low]
    for key, slug in PROVINCE_SLUGS.items():
        if key in low:
            return slug
    return None


def infer_category(text: str) -> str | None:
    """Return first matching canonical category, or None."""
    low = text.lower()
    for keyword, cat in CATEGORY_RULES:
        if keyword in low:
            return cat
    return None


def infer_type(text: str) -> str | None:
    """Return canonical job type from text, or None."""
    low = text.lower()
    for keyword, jtype in TYPE_MAP.items():
        if keyword in low:
            return jtype
    return None
