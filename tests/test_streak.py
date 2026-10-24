"""Pruebas del cálculo de la racha (RF-4.1 a RF-4.7)."""

from datetime import date, timedelta

import pytest
from conftest import TODAY

from habits.core import compute_streak, has_future_marks


def _days(*offsets: int) -> list[date]:
    return [TODAY + timedelta(days=offset) for offset in offsets]


@pytest.mark.parametrize(
    ("offsets", "expected"),
    [
        ((), 0),  # RF-4.4
        ((0,), 1),
        ((-1,), 1),  # RF-4.2
        ((-1, -2, -3), 3),  # CL-5
        ((-3, -2), 0),  # CL-6, RF-4.3
        ((0, -2), 1),  # CL-7, RF-4.5
        ((0, -1, -3), 2),
        ((0, -1, -2, -3, -4), 5),
    ],
)
def test_rf_4_1_to_rf_4_5_streak_table(offsets: tuple[int, ...], expected: int) -> None:
    assert compute_streak(_days(*offsets), TODAY) == expected


def test_cl_5_yesterday_and_two_previous_days_give_streak_3() -> None:
    assert compute_streak(_days(-1, -2, -3), TODAY) == 3


def test_cl_6_marks_three_and_two_days_ago_give_streak_0() -> None:
    assert compute_streak(_days(-3, -2), TODAY) == 0


def test_cl_7_today_and_two_days_ago_give_streak_1() -> None:
    assert compute_streak(_days(0, -2), TODAY) == 1


def test_rf_4_2_streak_kept_when_only_yesterday_is_marked() -> None:
    assert compute_streak(_days(-1, -2), TODAY) == 2


def test_rf_4_3_no_mark_today_or_yesterday_gives_zero() -> None:
    assert compute_streak([date(2026, 10, 21), date(2026, 10, 22)], date(2026, 10, 24)) == 0


def test_rf_4_4_habit_without_marks_has_zero_streak() -> None:
    assert compute_streak([], TODAY) == 0


def test_rf_4_5_gap_cuts_the_streak() -> None:
    assert compute_streak(_days(0, -1, -3, -4, -5), TODAY) == 2


def test_cl_8_monday_and_tuesday_checked_on_wednesday() -> None:
    marks = [date(2026, 10, 19), date(2026, 10, 20)]
    assert compute_streak(marks, date(2026, 10, 21)) == 2


def test_cl_11_streak_across_month_change() -> None:
    marks = [date(2026, 2, 27), date(2026, 2, 28), date(2026, 3, 1)]
    assert compute_streak(marks, date(2026, 3, 1)) == 3


def test_cl_11_streak_across_year_change() -> None:
    marks = [date(2025, 12, 30), date(2025, 12, 31), date(2026, 1, 1)]
    assert compute_streak(marks, date(2026, 1, 1)) == 3


def test_cl_25_streak_across_leap_day() -> None:
    marks = [date(2024, 2, 28), date(2024, 2, 29), date(2024, 3, 1)]
    assert compute_streak(marks, date(2024, 3, 1)) == 3


def test_rf_4_1_streak_accepts_any_iterable() -> None:
    assert compute_streak(iter(_days(0, -1)), TODAY) == 2
    assert compute_streak(frozenset(_days(0, -1)), TODAY) == 2


def test_rf_4_6_cl_15_future_marks_are_ignored() -> None:
    assert compute_streak(_days(-1, 0, 1, 2), TODAY) == 2


def test_rf_4_6_only_future_marks_give_zero() -> None:
    assert compute_streak(_days(1, 2), TODAY) == 0


def test_cl_26_marks_made_while_clock_was_behind_count_when_date_returns() -> None:
    marks = _days(-3, -2, -1)  # marcas de días que el reloj atrasado ya había alcanzado
    assert compute_streak(marks, TODAY) == 3


def test_rf_4_1_streak_reaching_date_min_does_not_overflow() -> None:
    assert compute_streak([date.min, date.min + timedelta(days=1)], date.min + timedelta(days=1)) == 2
    assert compute_streak([date.min], date.min) == 1


def test_rf_4_7_has_future_marks() -> None:
    assert has_future_marks(_days(1), TODAY)
    assert has_future_marks(_days(-1, 0, 5), TODAY)
    assert not has_future_marks(_days(-1, 0), TODAY)
    assert not has_future_marks([], TODAY)
