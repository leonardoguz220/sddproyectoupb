"""Pruebas de normalización, validación y equivalencia de nombres (RF-1.x, RF-2.2)."""

import pytest

from habits.core import InvalidNameError, NameProblem, name_key, normalize_name, validate_name

COMPOUND_EMOJI = "\U0001f468‍\U0001f469‍\U0001f467"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Leer", "Leer"),
        ("  Leer  ", "Leer"),
        ("Leer   20    minutos", "Leer 20 minutos"),
        ("\tLeer\t20\t", "Leer 20"),
        (" Leer  20 ", "Leer 20"),
        ("   ", ""),
        ("", ""),
        ("Ñandú ☕ ÁLGEBRA", "Ñandú ☕ ÁLGEBRA"),
    ],
)
def test_rf_1_1_rf_1_4_normalize_name(raw: str, expected: str) -> None:
    assert normalize_name(raw) == expected


def test_rf_1_1_line_breaks_are_not_spaces() -> None:
    assert normalize_name("a\nb") == "a\nb"
    assert normalize_name("  a \n b  ") == "a \n b"


def test_rf_1_1_validate_name_returns_normalized() -> None:
    assert validate_name("  Leer   mucho ") == "Leer mucho"


@pytest.mark.parametrize("raw", ["", "   ", "\t  "])
def test_rf_1_2_cl_2_empty_name_rejected(raw: str) -> None:
    with pytest.raises(InvalidNameError) as info:
        validate_name(raw)
    assert info.value.problem is NameProblem.EMPTY


@pytest.mark.parametrize("raw", ["a\nb", "\x00", "a b", "a b", "a\r"])
def test_rf_1_6_cl_18_control_chars_rejected(raw: str) -> None:
    with pytest.raises(InvalidNameError) as info:
        validate_name(raw)
    assert info.value.problem is NameProblem.CONTROL_CHARS


@pytest.mark.parametrize("raw", ["-x", "   -x", "--ayuda", "-"])
def test_rf_1_6_cl_18_leading_dash_rejected(raw: str) -> None:
    with pytest.raises(InvalidNameError) as info:
        validate_name(raw)
    assert info.value.problem is NameProblem.LEADING_DASH


def test_rf_1_6_dash_inside_name_is_allowed() -> None:
    assert validate_name("Lectura - capítulo 1") == "Lectura - capítulo 1"


def test_rf_1_5_cl_13_exactly_100_characters_accepted() -> None:
    assert validate_name("a" * 100) == "a" * 100


def test_rf_1_5_cl_13_101_characters_rejected() -> None:
    with pytest.raises(InvalidNameError) as info:
        validate_name("a" * 101)
    assert info.value.problem is NameProblem.TOO_LONG
    assert info.value.length == 101


def test_rf_1_5_cl_13_border_spaces_do_not_count() -> None:
    assert validate_name("     " + "a" * 100 + "     ") == "a" * 100


def test_rf_1_5_length_is_measured_after_normalizing() -> None:
    raw = "a" * 50 + " " * 40 + "b" * 49
    assert len(raw) > 100
    assert len(validate_name(raw)) == 100


def test_cl_12_accents_enye_and_compound_emoji_accepted() -> None:
    for name in ("Ñandú árbol", "Estudio 🚀", f"Familia {COMPOUND_EMOJI}"):
        assert validate_name(name) == name


def test_rf_1_6_validation_order_control_before_dash_before_length() -> None:
    with pytest.raises(InvalidNameError) as info:
        validate_name("-\n")
    assert info.value.problem is NameProblem.CONTROL_CHARS
    with pytest.raises(InvalidNameError) as info:
        validate_name("-" + "a" * 120)
    assert info.value.problem is NameProblem.LEADING_DASH


@pytest.mark.parametrize("other", ["leer", " LEER ", "Leer  ", "lEEr"])
def test_rf_1_3_cl_1_name_key_ignores_case_and_border_spaces(other: str) -> None:
    assert name_key(other) == name_key("Leer")


def test_cl_14_internal_spaces_are_equivalent() -> None:
    assert name_key("Leer  mucho") == name_key("Leer mucho")


def test_cl_14_accents_distinguish() -> None:
    assert name_key("Leer") != name_key("Léer")


def test_cl_19_composed_and_combined_accent_are_equivalent() -> None:
    assert name_key("é") == name_key("é")


def test_rf_2_2_special_letters_use_casefold() -> None:
    assert name_key("Straße") == name_key("STRASSE")
