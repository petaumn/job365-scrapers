from sources.108jobs.scrape import _normalise_province, _infer_category, _infer_type


# --- province ---

def test_province_lao_vientiane():
    assert _normalise_province("ວຽງຈັນ") == "Vientiane"


def test_province_english_capital():
    assert _normalise_province("Vientiane Capital") == "Vientiane"


def test_province_savannakhet():
    assert _normalise_province("Savannakhet Province") == "Savannakhet"


def test_province_luang_prabang():
    assert _normalise_province("Luang Prabang") == "Luang Prabang"


def test_province_pakse_maps_champasak():
    assert _normalise_province("Pakse") == "Champasak"


def test_province_remote_returns_none():
    assert _normalise_province("Online / Remote") is None


# --- category ---

def test_category_software():
    assert _infer_category("Software Developer") == "Technology"


def test_category_it_support():
    assert _infer_category("IT Support Officer") == "Technology"


def test_category_accounting():
    assert _infer_category("Accounting Officer") == "Accounting & Finance"


def test_category_banking():
    assert _infer_category("Loan Officer – Banking") == "Banking & Finance"


def test_category_hr():
    assert _infer_category("Human Resource Manager") == "Human Resources"


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
