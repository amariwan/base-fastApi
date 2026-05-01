import pytest

from app.shared.utils.text import normalize_german_text


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("ä", "ae", "ae"),
        ("Ä", "AE", "ae"),
        ("A\u0308RZTIN_ẞ", "AErztin_SS", "aerztin_ss"),
        ("ö", "oe", "oe"),
        ("Ö", "OE", "oe"),
        ("GRO\u0308SSE", "Groesse", "groesse"),
        ("ü", "ue", "ue"),
        ("Ü", "UE", "ue"),
        ("GrÜßE", "gruesse", "gruesse"),
        ("ß", "ss", "ss"),
        ("ẞ", "SS", "ss"),
        ("Fuß", "FUSS", "fuss"),
    ],
)
def test_normalize_german_text_matches_ascii_digraphs_and_umlauts(left: str, right: str, expected: str) -> None:
    assert normalize_german_text(left) == expected
    assert normalize_german_text(right) == expected
