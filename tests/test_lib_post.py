from lib.normalize import parse_salary


def test_range_lak():
    assert parse_salary("3,000,000 - 5,000,000 LAK") == (3_000_000, 5_000_000)


def test_single_kip():
    assert parse_salary("5000000 kip") == (5_000_000, None)


def test_usd_rejected():
    assert parse_salary("$500 - $800") == (None, None)


def test_thb_rejected():
    assert parse_salary("฿15,000") == (None, None)


def test_empty():
    assert parse_salary("") == (None, None)


def test_below_minimum():
    # values below 500k LAK sanity threshold are dropped
    assert parse_salary("100 kip") == (None, None)


def test_range_swapped():
    # always returns (low, high) regardless of input order
    lo, hi = parse_salary("5,000,000 - 3,000,000 LAK")
    assert lo == 3_000_000
    assert hi == 5_000_000
