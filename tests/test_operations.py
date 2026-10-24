"""Pruebas de las operaciones del núcleo: crear, marcar, resumir y coherencia."""

import inspect
from dataclasses import FrozenInstanceError
from datetime import date, timedelta

import pytest
from conftest import TODAY

from habits.core import (
    DuplicateHabitError,
    Habit,
    HabitError,
    HabitNotFoundError,
    HabitStatus,
    IncoherentDataError,
    InvalidNameError,
    NameProblem,
    add_habit,
    check_integrity,
    find_habit,
    mark_done,
    summarize,
)


def _habit(name: str, *offsets: int) -> Habit:
    return Habit(name, frozenset(TODAY + timedelta(days=offset) for offset in offsets))


# --- tipos y excepciones ---------------------------------------------------


def test_habit_is_immutable() -> None:
    habit = _habit("Leer")
    with pytest.raises(FrozenInstanceError):
        habit.name = "Otro"  # type: ignore[misc]


def test_errors_keep_their_data_and_are_habit_errors() -> None:
    invalid = InvalidNameError(NameProblem.TOO_LONG, 101)
    assert (invalid.problem, invalid.length) == (NameProblem.TOO_LONG, 101)
    assert DuplicateHabitError("Leer").existing_name == "Leer"
    assert HabitNotFoundError("x").name == "x"
    assert IncoherentDataError("detalle").detail == "detalle"
    for error in (invalid, DuplicateHabitError("a"), HabitNotFoundError("a"), IncoherentDataError("a")):
        assert isinstance(error, HabitError)


# --- find_habit ------------------------------------------------------------


def test_rf_2_2_find_habit_by_equivalent_name() -> None:
    habits = (_habit("Leer"), _habit("Escribir"))
    assert find_habit(habits, " LEER ") is habits[0]
    assert find_habit(habits, "escribir") is habits[1]


def test_rf_2_2_find_habit_returns_none_when_missing_or_empty_list() -> None:
    assert find_habit((_habit("Leer"),), "Léer") is None
    assert find_habit((), "Leer") is None


# --- add_habit -------------------------------------------------------------


def test_rf_1_1_add_habit_appends_normalized_name_without_marks() -> None:
    original = (_habit("Leer"),)
    result = add_habit(original, "  Escribir   diario ")
    assert [habit.name for habit in result] == ["Leer", "Escribir diario"]
    assert result[1].marks == frozenset()
    assert len(original) == 1


def test_rf_1_4_add_habit_keeps_case_accents_and_emoji() -> None:
    assert add_habit((), "  Ñandú ☕  ")[0].name == "Ñandú ☕"


@pytest.mark.parametrize("raw", ["leer", " LEER ", "Leer  "])
def test_rf_1_3_cl_1_duplicate_equivalent_name_rejected(raw: str) -> None:
    with pytest.raises(DuplicateHabitError) as info:
        add_habit((_habit("Leer"),), raw)
    assert info.value.existing_name == "Leer"


def test_cl_14_accent_makes_a_different_habit_but_extra_spaces_do_not() -> None:
    assert len(add_habit((_habit("Leer"),), "Léer")) == 2
    with pytest.raises(DuplicateHabitError):
        add_habit((_habit("Leer mucho"),), "Leer   mucho")


@pytest.mark.parametrize(
    ("raw", "problem"),
    [
        ("   ", NameProblem.EMPTY),
        ("a\nb", NameProblem.CONTROL_CHARS),
        ("-x", NameProblem.LEADING_DASH),
        ("a" * 101, NameProblem.TOO_LONG),
    ],
)
def test_rf_1_2_rf_1_5_rf_1_6_add_habit_propagates_name_problems(raw: str, problem: NameProblem) -> None:
    with pytest.raises(InvalidNameError) as info:
        add_habit((_habit("Leer"),), raw)
    assert info.value.problem is problem


def test_cl_27_more_than_100_habits_are_accepted() -> None:
    habits: tuple[Habit, ...] = ()
    for index in range(101):
        habits = add_habit(habits, f"Hábito {index}")
    assert len(habits) == 101


# --- mark_done -------------------------------------------------------------


def test_rf_2_1_mark_done_adds_exactly_today() -> None:
    habits = (_habit("Leer", -5), _habit("Escribir"))
    result = mark_done(habits, "Leer", TODAY)
    assert result.habits[0].marks == {TODAY + timedelta(days=-5), TODAY}
    assert result.habits[1] is habits[1]
    assert (result.habit_name, result.already_marked) == ("Leer", False)


def test_rf_2_1_mark_done_streak_includes_today() -> None:
    result = mark_done((_habit("Leer", -1, -2),), "Leer", TODAY)
    assert result.streak == 3


def test_rf_2_3_cl_3_marking_twice_changes_nothing() -> None:
    habits = (_habit("Leer", 0, -1),)
    result = mark_done(habits, "Leer", TODAY)
    assert result.already_marked
    assert result.habits == habits
    assert result.streak == 2


def test_rf_2_2_mark_done_finds_equivalent_name_and_reports_stored_name() -> None:
    result = mark_done((_habit("Leer"),), " LEER ", TODAY)
    assert result.habit_name == "Leer"
    assert result.habits[0].marks == {TODAY}


def test_rf_2_4_cl_4_unknown_habit_raises_not_found_with_normalized_name() -> None:
    with pytest.raises(HabitNotFoundError) as info:
        mark_done((_habit("Leer"),), "  x    y ", TODAY)
    assert info.value.name == "x y"


@pytest.mark.parametrize("habits", [(), (_habit("Leer"),)])
def test_rf_2_6_cl_17_empty_name_is_empty_error_not_not_found(habits: tuple[Habit, ...]) -> None:
    with pytest.raises(InvalidNameError) as info:
        mark_done(habits, "   ", TODAY)
    assert info.value.problem is NameProblem.EMPTY


def test_rf_4_7_mark_done_reports_future_marks() -> None:
    assert mark_done((_habit("Leer", 3),), "Leer", TODAY).has_future_marks
    assert not mark_done((_habit("Leer", -3),), "Leer", TODAY).has_future_marks


def test_rf_2_5_mark_done_only_accepts_today_as_date() -> None:
    assert list(inspect.signature(mark_done).parameters) == ["habits", "raw_name", "today"]


# --- summarize -------------------------------------------------------------


def test_rf_3_1_summarize_example_from_plan() -> None:
    habits = (
        Habit("Leer 20 minutos", frozenset({date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)})),
        Habit("Repasar álgebra", frozenset({date(2026, 10, 19), date(2026, 10, 22)})),
        Habit("Escribir diario", frozenset()),
    )
    assert summarize(habits, TODAY) == (
        HabitStatus("Leer 20 minutos", 3, True, False),
        HabitStatus("Repasar álgebra", 1, False, False),
        HabitStatus("Escribir diario", 0, False, False),
    )


def test_rf_4_6_rf_4_7_summarize_future_marks_do_not_count_as_done_today() -> None:
    assert summarize((_habit("Leer", 1),), TODAY) == (HabitStatus("Leer", 0, False, True),)


def test_rf_3_1_summarize_empty_list() -> None:
    assert summarize((), TODAY) == ()


# --- check_integrity -------------------------------------------------------


def test_rf_5_3_valid_list_passes_integrity() -> None:
    check_integrity((_habit("Leer"), _habit("Léer"), _habit("Ñandú ☕")))
    check_integrity(())


@pytest.mark.parametrize(
    "names",
    [
        ["Leer  mucho"],
        [" Leer"],
        [""],
        ["a" * 101],
        ["a\nb"],
        ["-x"],
        ["Leer", "leer"],
        ["Leer mucho", "LEER MUCHO"],
    ],
)
def test_rf_5_3_cl_23_incoherent_names_raise(names: list[str]) -> None:
    with pytest.raises(IncoherentDataError):
        check_integrity(tuple(_habit(name) for name in names))
