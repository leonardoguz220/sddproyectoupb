"""Interfaz de línea de comandos: argumentos, textos y códigos de salida."""

import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from habits import core, storage
from habits.core import (
    DuplicateHabitError,
    HabitError,
    HabitList,
    HabitNotFoundError,
    InvalidNameError,
    NameProblem,
)
from habits.storage import StorageError, StorageProblem

_HELP_OPTIONS = {"-h", "--ayuda"}
_COMMANDS_WITH_NAME = ("crear", "marcar")
_UNKNOWN_PATH = "~/.habits-cli/habits.json"

_DAMAGED_REASONS = {
    StorageProblem.EMPTY: "el archivo está vacío",
    StorageProblem.UNREADABLE: "no se puede leer",
    StorageProblem.UNKNOWN_VERSION: "versión de formato desconocida",
    StorageProblem.INVALID_STRUCTURE: "estructura no válida",
}


class UsageError(Exception):
    """Uso incorrecto de la herramienta; el mensaje va en español."""


@dataclass(frozen=True)
class Command:
    kind: Literal["crear", "marcar", "listar", "ayuda"]
    argument: str | None = None


def help_text() -> str:
    return (
        "Uso: python -m habits <comando> [argumentos]\n"
        "\n"
        "Comandos:\n"
        "  crear <nombre>    Crea un hábito nuevo.\n"
        "  marcar <nombre>   Marca un hábito como hecho hoy.\n"
        "  listar            Muestra tus hábitos con su racha.\n"
        "\n"
        "Opciones:\n"
        "  -h, --ayuda       Muestra esta ayuda.\n"
        "\n"
        "Si el nombre tiene espacios, escríbelo entre comillas."
    )


def parse_args(argv: list[str]) -> Command:
    if any(arg in _HELP_OPTIONS for arg in argv):
        return Command("ayuda")
    if not argv:
        raise UsageError("falta el comando.")
    command, *rest = argv
    if command == "listar":
        if rest:
            raise UsageError("el comando «listar» no admite argumentos.")
        return Command("listar")
    if command in _COMMANDS_WITH_NAME:
        if not rest:
            raise UsageError(f"el comando «{command}» necesita un nombre.")
        if len(rest) > 1:
            extra = ", ".join(f"«{arg}»" for arg in rest[1:])
            raise UsageError(
                f"el comando «{command}» recibió argumentos de más: {extra}. "
                "Si el nombre tiene espacios, escríbelo entre comillas."
            )
        return Command(command, rest[0])  # type: ignore[arg-type]
    raise UsageError(f"comando desconocido «{command}».")


def configure_output() -> None:
    """Hace que la consola sustituya, en vez de fallar, lo que no puede mostrar."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def _read_today() -> date:
    return date.today()


def _days(count: int) -> str:
    return f"{count} día" if count == 1 else f"{count} días"


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


def _habit_error_message(error: HabitError) -> str:
    if isinstance(error, InvalidNameError):
        if error.problem is NameProblem.EMPTY:
            return (
                "Error: el nombre del hábito está vacío. "
                'Escribe al menos un carácter, por ejemplo: crear "Leer".'
            )
        if error.problem is NameProblem.CONTROL_CHARS:
            return (
                "Error: el nombre contiene caracteres de control (como saltos de línea). "
                "Escríbelo en una sola línea."
            )
        if error.problem is NameProblem.LEADING_DASH:
            return "Error: el nombre no puede empezar por «-». Empieza por una letra o un número."
        return (
            f"Error: el nombre tiene {error.length} caracteres y el máximo es "
            f"{core.MAX_NAME_LENGTH}. Acórtalo."
        )
    if isinstance(error, DuplicateHabitError):
        return (
            f"Error: ya existe el hábito «{error.existing_name}» "
            "(los nombres no distinguen mayúsculas ni espacios de más). Elige otro nombre."
        )
    if isinstance(error, HabitNotFoundError):
        return (
            f"Error: no existe ningún hábito llamado «{error.name}». "
            "Usa «listar» para ver tus hábitos."
        )
    return f"Error: {error}"


def _storage_error_message(error: StorageError, path: Path | None) -> str:
    shown = str(path) if path is not None else _UNKNOWN_PATH
    if error.problem is StorageProblem.SAVE_FAILED:
        return (
            f"Error: no se pudo guardar ({error.detail}). Tus datos anteriores siguen intactos. "
            f"Revisa el espacio en disco y los permisos de «{shown}»."
        )
    if error.problem is StorageProblem.INCOHERENT:
        reason = f"contenido incoherente: {error.detail}"
    else:
        reason = _DAMAGED_REASONS[error.problem]
    return (
        f"Error: los datos guardados están dañados ({reason}). No se ha modificado nada. "
        f"Repara o aparta manualmente el archivo «{shown}» y vuelve a intentarlo."
    )


def _warn_future_marks(habits: HabitList, name: str) -> None:
    habit = core.find_habit(habits, name)
    latest = max(habit.marks).isoformat() if habit is not None else "?"
    _print_error(
        f"Aviso: la fecha del equipo parece anterior a alguna marca de «{name}» "
        f"(última marca: {latest}). Esas marcas se ignoran hasta que la fecha del equipo las alcance."
    )


def _create(habits: HabitList, name: str, path: Path) -> None:
    updated = core.add_habit(habits, name)
    storage.save(path, updated)
    print(f"Hábito «{updated[-1].name}» creado.")


def _mark(habits: HabitList, name: str, path: Path, today: date) -> None:
    result = core.mark_done(habits, name, today)
    if not result.already_marked:
        storage.save(path, result.habits)
        print(f"Hábito «{result.habit_name}» marcado hoy. Racha: {_days(result.streak)}.")
    else:
        print(f"El hábito «{result.habit_name}» ya estaba marcado hoy. Racha: {_days(result.streak)}.")
    if result.has_future_marks:
        _warn_future_marks(result.habits, result.habit_name)


def _list(habits: HabitList, today: date) -> None:
    statuses = core.summarize(habits, today)
    if not statuses:
        print('Aún no tienes hábitos. Crea el primero con: python -m habits crear "Leer 20 minutos"')
        return
    print("Tus hábitos:")
    for status in statuses:
        done = "sí" if status.done_today else "no"
        print(f"- {status.name} | racha: {_days(status.streak)} | hoy: {done}")
    for status in statuses:
        if status.has_future_marks:
            _warn_future_marks(habits, status.name)


def main(argv: list[str], *, today: date | None = None, path: Path | None = None) -> int:
    """Ejecuta un comando y devuelve el código de salida (0 éxito, 1 error, 2 uso incorrecto)."""
    try:
        command = parse_args(argv)
    except UsageError as error:
        _print_error(f"Error: {error}")
        _print_error(help_text())
        return 2
    if command.kind == "ayuda":
        print(help_text())
        return 0
    today = today if today is not None else _read_today()
    data_path: Path | None = path
    try:
        if data_path is None:
            data_path = storage.default_path()
        habits = storage.load(data_path)
        argument = command.argument or ""
        if command.kind == "crear":
            _create(habits, argument, data_path)
        elif command.kind == "marcar":
            _mark(habits, argument, data_path, today)
        else:
            _list(habits, today)
    except StorageError as error:
        _print_error(_storage_error_message(error, data_path))
        return 1
    except HabitError as error:
        _print_error(_habit_error_message(error))
        return 1
    return 0
