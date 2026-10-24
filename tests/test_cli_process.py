"""Pruebas con el punto de entrada real: `python -m habits` en un proceso aparte."""

import json
import os
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_HABITS = 100
REFERENCE_MARKS = 5 * 365 + 1  # 5 años de marcas


def _data_file(home: Path) -> Path:
    return home / ".habits-cli" / "habits.json"


def _run(
    *args: str,
    home: Path,
    cwd: Path | None = None,
    io_encoding: str = "utf-8",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        HOME=str(home),
        USERPROFILE=str(home),
        PYTHONPATH=str(ROOT),
        PYTHONIOENCODING=io_encoding,
    )
    env.pop("PYTHONUTF8", None)
    return subprocess.run(
        [sys.executable, "-m", "habits", *args],
        cwd=cwd or ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding=io_encoding,
        timeout=30,
    )


@pytest.fixture
def home(tmp_path: Path) -> Path:
    folder = tmp_path / "home"
    folder.mkdir()
    return folder


def test_rf_6_2_entry_point_shows_help(home: Path) -> None:
    result = _run("--ayuda", home=home)
    assert result.returncode == 0
    assert "crear <nombre>" in result.stdout
    assert result.stderr == ""


def test_rf_5_1_data_persists_between_executions(home: Path) -> None:
    assert _run("crear", "Leer 20 minutos", home=home).returncode == 0
    assert _run("marcar", "Leer 20 minutos", home=home).returncode == 0
    result = _run("listar", home=home)
    assert result.returncode == 0
    assert "- Leer 20 minutos | racha: 1 día | hoy: sí" in result.stdout
    assert _data_file(home).exists()


def test_rf_5_6_cl_30_same_habits_from_different_working_folders(home: Path, tmp_path: Path) -> None:
    folder_a, folder_b = tmp_path / "a", tmp_path / "b"
    folder_a.mkdir()
    folder_b.mkdir()
    assert _run("crear", "Leer", home=home, cwd=folder_a).returncode == 0
    listing_a = _run("listar", home=home, cwd=folder_a).stdout
    listing_b = _run("listar", home=home, cwd=folder_b).stdout
    assert "- Leer |" in listing_b
    assert listing_a == listing_b
    assert list(folder_a.iterdir()) == [] and list(folder_b.iterdir()) == []


def test_rf_6_6_cl_31_errors_go_to_stderr_and_stdout_stays_clean(home: Path) -> None:
    result = _run("marcar", "inexistente", home=home)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("Error: no existe ningún hábito llamado «inexistente».")


def test_rf_6_6_cl_31_future_marks_warning_goes_to_stderr_only(home: Path) -> None:
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    data = {"version": 1, "habits": [{"name": "Leer", "marks": [tomorrow]}]}
    _data_file(home).parent.mkdir()
    _data_file(home).write_text(json.dumps(data), encoding="utf-8")
    result = _run("listar", home=home)
    assert result.returncode == 0
    assert "Aviso" not in result.stdout
    assert result.stdout == "Tus hábitos:\n- Leer | racha: 0 días | hoy: no\n"
    assert f"última marca: {tomorrow}" in result.stderr


def test_rf_6_5_cl_28_console_that_cannot_show_a_character_does_not_fail(home: Path) -> None:
    created = _run("crear", "Estudio 🚀", home=home, io_encoding="cp1252")
    listing = _run("listar", home=home, io_encoding="cp1252")
    assert (created.returncode, listing.returncode) == (0, 0)
    assert "Traceback" not in created.stderr + listing.stderr
    assert "Hábito «Estudio ?» creado." in created.stdout
    assert "- Estudio ? |" in listing.stdout
    saved = json.loads(_data_file(home).read_text(encoding="utf-8"))
    assert saved["habits"][0]["name"] == "Estudio 🚀"


def _write_reference_data(home: Path) -> None:
    today = date.today()
    habits = [
        {
            "name": f"Hábito {index:03d}",
            "marks": [
                (today - timedelta(days=offset)).isoformat()
                for offset in range(REFERENCE_MARKS, 0, -1)
            ],
        }
        for index in range(REFERENCE_HABITS)
    ]
    _data_file(home).parent.mkdir()
    _data_file(home).write_text(json.dumps({"version": 1, "habits": habits}), encoding="utf-8")


@pytest.mark.parametrize("args", [["listar"], ["marcar", "Hábito 000"], ["crear", "Hábito 101"]])
def test_rnf_2_cl_27_commands_finish_under_one_second_with_reference_load(
    tmp_path: Path, args: list[str]
) -> None:
    """Mejor de 3 intentos, cada uno con datos nuevos: descarta el ruido puntual del equipo."""
    timings: list[float] = []
    for attempt in range(3):
        home = tmp_path / f"home{attempt}"
        home.mkdir()
        _write_reference_data(home)
        start = time.perf_counter()
        result = _run(*args, home=home)
        timings.append(time.perf_counter() - start)
        assert result.returncode == 0, result.stderr
    assert min(timings) < 1.0, f"{args[0]} tardó {[round(t, 2) for t in timings]} s"
