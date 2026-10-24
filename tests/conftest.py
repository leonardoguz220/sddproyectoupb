"""Constantes y fixtures compartidos por las pruebas."""

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

TODAY = date(2026, 10, 23)

# Datos del ejemplo del plan (sección 3.3); con TODAY dan rachas 3, 1 y 0.
EXAMPLE_HABITS: dict[str, list[date]] = {
    "Leer 20 minutos": [date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)],
    "Repasar álgebra": [date(2026, 10, 19), date(2026, 10, 22)],
    "Escribir diario": [],
}


def write_habits(path: Path, habits: dict[str, list[date]]) -> None:
    """Escribe un archivo de datos válido (versión 1) con los hábitos dados."""
    payload = {
        "version": 1,
        "habits": [
            {"name": name, "marks": [day.isoformat() for day in marks]}
            for name, marks in habits.items()
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def data_path(tmp_path: Path) -> Path:
    return tmp_path / "habits.json"


@pytest.fixture
def write_data(data_path: Path) -> Callable[[str], Path]:
    def write(text: str) -> Path:
        data_path.write_text(text, encoding="utf-8")
        return data_path

    return write
