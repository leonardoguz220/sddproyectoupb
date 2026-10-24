"""Persistencia: lectura y escritura del archivo JSON de datos."""

import json
import os
from datetime import date
from enum import Enum
from pathlib import Path

from habits.core import Habit, HabitList, IncoherentDataError, check_integrity

FORMAT_VERSION = 1

_ROOT_KEYS = {"version", "habits"}
_HABIT_KEYS = {"name", "marks"}


class StorageProblem(Enum):
    EMPTY = "empty"
    UNREADABLE = "unreadable"
    UNKNOWN_VERSION = "unknown_version"
    INVALID_STRUCTURE = "invalid_structure"
    INCOHERENT = "incoherent"
    SAVE_FAILED = "save_failed"


class StorageError(Exception):
    def __init__(self, problem: StorageProblem, detail: str) -> None:
        super().__init__(detail)
        self.problem = problem
        self.detail = detail


def default_path() -> Path:
    try:
        return Path.home() / ".habits-cli" / "habits.json"
    except RuntimeError as error:
        raise StorageError(
            StorageProblem.UNREADABLE, "no se puede determinar la carpeta del usuario"
        ) from error


def _invalid(detail: str) -> StorageError:
    return StorageError(StorageProblem.INVALID_STRUCTURE, detail)


def _parse_date(text: str) -> date:
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise StorageError(StorageProblem.INCOHERENT, f"fecha no válida «{text}»") from error
    if parsed.isoformat() != text:
        raise StorageError(StorageProblem.INCOHERENT, f"fecha no canónica «{text}»")
    return parsed


def _parse_habit(item: object) -> Habit:
    if not isinstance(item, dict) or set(item) != _HABIT_KEYS:
        raise _invalid("cada hábito debe tener solo «name» y «marks»")
    name, marks = item["name"], item["marks"]
    if not isinstance(name, str):
        raise _invalid("«name» debe ser texto")
    if not isinstance(marks, list) or not all(isinstance(mark, str) for mark in marks):
        raise _invalid("«marks» debe ser una lista de textos")
    parsed = [_parse_date(mark) for mark in marks]
    if len(set(parsed)) != len(parsed):
        raise StorageError(StorageProblem.INCOHERENT, f"«{name}» repite una fecha")
    return Habit(name, frozenset(parsed))


def load(path: Path) -> HabitList:
    """Lee los hábitos; un archivo ausente equivale a no tener hábitos."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return ()
    except OSError as error:
        raise StorageError(StorageProblem.UNREADABLE, str(error)) from error
    if not raw:
        raise StorageError(StorageProblem.EMPTY, "el archivo está vacío")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError) as error:
        raise StorageError(StorageProblem.UNREADABLE, "no es un JSON UTF-8 válido") from error
    if not isinstance(data, dict):
        raise _invalid("la raíz debe ser un objeto")
    version = data.get("version")
    if type(version) is not int or version != FORMAT_VERSION:
        raise StorageError(StorageProblem.UNKNOWN_VERSION, f"versión {version!r}")
    if set(data) != _ROOT_KEYS or not isinstance(data["habits"], list):
        raise _invalid("la raíz debe tener solo «version» y «habits» (lista)")
    habits = tuple(_parse_habit(item) for item in data["habits"])
    try:
        check_integrity(habits)
    except IncoherentDataError as error:
        raise StorageError(StorageProblem.INCOHERENT, error.detail) from error
    return habits


def _to_dict(habits: HabitList) -> dict[str, object]:
    return {
        "version": FORMAT_VERSION,
        "habits": [
            {"name": habit.name, "marks": [day.isoformat() for day in sorted(habit.marks)]}
            for habit in habits
        ],
    }


def save(path: Path, habits: HabitList) -> None:
    """Guarda de forma atómica: escribe un temporal y lo reemplaza al final."""
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not os.access(path, os.W_OK):
            raise PermissionError(f"el archivo de datos es de solo lectura: {path}")
        try:
            with open(temporary, "w", encoding="utf-8", newline="\n") as file:
                json.dump(_to_dict(habits), file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except OSError as error:
        raise StorageError(StorageProblem.SAVE_FAILED, str(error)) from error
