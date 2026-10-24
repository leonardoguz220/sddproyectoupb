"""Lógica pura: nombres, hábitos y cálculo de la racha."""

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import Enum

MAX_NAME_LENGTH = 100

_ONE_DAY = timedelta(days=1)
_LINE_BREAK_CATEGORIES = frozenset({"Cc", "Zl", "Zp"})


class NameProblem(Enum):
    EMPTY = "empty"
    CONTROL_CHARS = "control_chars"
    LEADING_DASH = "leading_dash"
    TOO_LONG = "too_long"


@dataclass(frozen=True)
class Habit:
    name: str
    marks: frozenset[date]


HabitList = tuple[Habit, ...]


@dataclass(frozen=True)
class HabitStatus:
    name: str
    streak: int
    done_today: bool
    has_future_marks: bool


@dataclass(frozen=True)
class MarkResult:
    habits: HabitList
    habit_name: str
    already_marked: bool
    streak: int
    has_future_marks: bool


class HabitError(Exception):
    """Base de los errores del núcleo; llevan datos, el texto lo pone la interfaz."""


class InvalidNameError(HabitError):
    def __init__(self, problem: NameProblem, length: int | None = None) -> None:
        super().__init__(problem.value)
        self.problem = problem
        self.length = length


class DuplicateHabitError(HabitError):
    def __init__(self, existing_name: str) -> None:
        super().__init__(existing_name)
        self.existing_name = existing_name


class HabitNotFoundError(HabitError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name


class IncoherentDataError(HabitError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _is_space(char: str) -> bool:
    return char == "\t" or unicodedata.category(char) == "Zs"


def normalize_name(raw: str) -> str:
    """Quita los espacios de los bordes y reduce los internos a uno solo."""
    words: list[str] = []
    current: list[str] = []
    for char in raw:
        if _is_space(char):
            if current:
                words.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        words.append("".join(current))
    return " ".join(words)


def validate_name(raw: str) -> str:
    """Devuelve el nombre normalizado o lanza InvalidNameError con el primer problema."""
    name = normalize_name(raw)
    if not name:
        raise InvalidNameError(NameProblem.EMPTY)
    if any(unicodedata.category(char) in _LINE_BREAK_CATEGORIES for char in name):
        raise InvalidNameError(NameProblem.CONTROL_CHARS)
    if name.startswith("-"):
        raise InvalidNameError(NameProblem.LEADING_DASH)
    if len(name) > MAX_NAME_LENGTH:
        raise InvalidNameError(NameProblem.TOO_LONG, len(name))
    return name


def name_key(name: str) -> str:
    """Clave de equivalencia: ignora mayúsculas y forma Unicode, pero no los acentos."""
    decomposed = unicodedata.normalize("NFD", normalize_name(name))
    return unicodedata.normalize("NFD", decomposed.casefold())


def find_habit(habits: HabitList, raw_name: str) -> Habit | None:
    key = name_key(raw_name)
    for habit in habits:
        if name_key(habit.name) == key:
            return habit
    return None


def add_habit(habits: HabitList, raw_name: str) -> HabitList:
    name = validate_name(raw_name)
    existing = find_habit(habits, name)
    if existing is not None:
        raise DuplicateHabitError(existing.name)
    return habits + (Habit(name, frozenset()),)


def compute_streak(marks: Iterable[date], today: date) -> int:
    """Días naturales consecutivos con marca que terminan hoy o, si no, ayer."""
    # Solo se consultan hoy y días anteriores, así que las marcas futuras no cuentan (RF-4.6).
    days = marks if isinstance(marks, (set, frozenset)) else frozenset(marks)
    if today in days:
        cursor = today
    elif today > date.min and today - _ONE_DAY in days:
        cursor = today - _ONE_DAY
    else:
        return 0
    streak = 0
    while cursor in days:
        streak += 1
        if cursor == date.min:
            break
        cursor -= _ONE_DAY
    return streak


def has_future_marks(marks: Iterable[date], today: date) -> bool:
    return max(marks, default=date.min) > today


def mark_done(habits: HabitList, raw_name: str, today: date) -> MarkResult:
    name = normalize_name(raw_name)
    if not name:
        raise InvalidNameError(NameProblem.EMPTY)
    habit = find_habit(habits, name)
    if habit is None:
        raise HabitNotFoundError(name)
    already_marked = today in habit.marks
    if already_marked:
        updated, new_habits = habit, habits
    else:
        updated = replace(habit, marks=habit.marks | {today})
        new_habits = tuple(updated if item is habit else item for item in habits)
    return MarkResult(
        new_habits,
        updated.name,
        already_marked,
        compute_streak(updated.marks, today),
        has_future_marks(updated.marks, today),
    )


def summarize(habits: HabitList, today: date) -> tuple[HabitStatus, ...]:
    return tuple(
        HabitStatus(
            habit.name,
            compute_streak(habit.marks, today),
            today in habit.marks,
            has_future_marks(habit.marks, today),
        )
        for habit in habits
    )


def check_integrity(habits: HabitList) -> None:
    """Lanza IncoherentDataError si hay nombres no válidos, sin normalizar o equivalentes."""
    seen: dict[str, str] = {}
    for habit in habits:
        try:
            valid = validate_name(habit.name)
        except InvalidNameError as error:
            raise IncoherentDataError(f"el nombre «{habit.name}» no es válido") from error
        if valid != habit.name:
            raise IncoherentDataError(f"el nombre «{habit.name}» no está normalizado")
        key = name_key(habit.name)
        if key in seen:
            raise IncoherentDataError(
                f"los nombres «{seen[key]}» y «{habit.name}» son equivalentes"
            )
        seen[key] = habit.name
