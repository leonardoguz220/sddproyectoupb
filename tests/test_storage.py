"""Pruebas de persistencia: lectura, validación y guardado atómico (RF-5.x)."""

import json
import os
from datetime import date
from pathlib import Path

import pytest
from conftest import EXAMPLE_HABITS, TODAY, write_habits

from habits import storage
from habits.core import Habit
from habits.storage import StorageError, StorageProblem, default_path, load, save

EXAMPLE_DATA = {
    "version": 1,
    "habits": [
        {"name": "Leer 20 minutos", "marks": ["2026-10-21", "2026-10-22", "2026-10-23"]},
        {"name": "Repasar álgebra", "marks": ["2026-10-19", "2026-10-22"]},
        {"name": "Escribir diario", "marks": []},
    ],
}


def _example_habits() -> tuple[Habit, ...]:
    return tuple(Habit(name, frozenset(marks)) for name, marks in EXAMPLE_HABITS.items())


# --- default_path ----------------------------------------------------------


def test_rf_5_6_default_path_is_under_user_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert default_path() == tmp_path / ".habits-cli" / "habits.json"


def test_rf_5_6_unknown_home_is_a_storage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_home() -> Path:
        raise RuntimeError("sin carpeta de usuario")

    monkeypatch.setattr(Path, "home", staticmethod(no_home))
    with pytest.raises(StorageError) as info:
        default_path()
    assert info.value.problem is StorageProblem.UNREADABLE


# --- save: camino feliz ----------------------------------------------------


def test_rf_5_1_rf_5_4_save_writes_versioned_json(data_path: Path) -> None:
    save(data_path, _example_habits())
    assert json.loads(data_path.read_text(encoding="utf-8")) == EXAMPLE_DATA


def test_rf_5_4_version_is_1() -> None:
    assert storage.FORMAT_VERSION == 1


def test_rf_5_1_save_writes_marks_in_ascending_order(data_path: Path) -> None:
    habit = Habit("Leer", frozenset({date(2026, 10, 23), date(2026, 1, 5), date(2026, 5, 9)}))
    save(data_path, (habit,))
    marks = json.loads(data_path.read_text(encoding="utf-8"))["habits"][0]["marks"]
    assert marks == ["2026-01-05", "2026-05-09", "2026-10-23"]


def test_rf_1_4_save_keeps_accents_and_emoji_unescaped(data_path: Path) -> None:
    save(data_path, (Habit("Álgebra ☕", frozenset()),))
    assert "Álgebra ☕" in data_path.read_text(encoding="utf-8")


def test_rf_5_5_save_creates_missing_folder(tmp_path: Path) -> None:
    path = tmp_path / "a" / "b" / "habits.json"
    save(path, ())
    assert load(path) == ()


def test_rf_5_5_save_leaves_no_temporary_file(data_path: Path) -> None:
    save(data_path, _example_habits())
    assert [item.name for item in data_path.parent.iterdir()] == ["habits.json"]


# --- load: camino feliz ----------------------------------------------------


def test_rf_5_2_cl_9_missing_file_is_empty_and_creates_nothing(tmp_path: Path) -> None:
    path = tmp_path / "nueva" / "habits.json"
    assert load(path) == ()
    assert not path.parent.exists()


def test_rf_5_1_save_then_load_round_trip(data_path: Path) -> None:
    save(data_path, _example_habits())
    assert load(data_path) == _example_habits()


def test_rf_5_1_example_from_plan_loads_in_order(data_path: Path) -> None:
    write_habits(data_path, EXAMPLE_HABITS)
    assert [habit.name for habit in load(data_path)] == list(EXAMPLE_HABITS)


def test_rf_5_3_unsorted_marks_are_accepted(data_path: Path) -> None:
    data_path.write_text(
        '{"version": 1, "habits": [{"name": "Leer", "marks": ["2026-10-23", "2026-10-01"]}]}',
        encoding="utf-8",
    )
    assert load(data_path)[0].marks == {date(2026, 10, 1), date(2026, 10, 23)}


def test_rf_4_6_future_marks_are_kept(data_path: Path) -> None:
    future = date(TODAY.year + 1, 1, 1)
    write_habits(data_path, {"Leer": [future]})
    assert load(data_path)[0].marks == {future}


# --- load: datos dañados ---------------------------------------------------

_VALID_NAME = '"name": "Leer", "marks": []'


def _doc(habits: str = "[]", version: str = "1", extra: str = "") -> bytes:
    return f'{{"version": {version}, "habits": {habits}{extra}}}'.encode()


def _habit_json(name: str = "Leer", marks: str = "[]", extra: str = "") -> str:
    return f'[{{"name": {json.dumps(name)}, "marks": {marks}{extra}}}]'


DAMAGED_CASES = [
    # (contenido, problema esperado)
    (b"", StorageProblem.EMPTY),
    (b"\xff\xfe\x00bad", StorageProblem.UNREADABLE),
    (b"{not json", StorageProblem.UNREADABLE),
    (b"\xef\xbb\xbf" + _doc(), StorageProblem.UNREADABLE),
    (b'{"habits": []}', StorageProblem.UNKNOWN_VERSION),
    (_doc(version="2"), StorageProblem.UNKNOWN_VERSION),
    (_doc(version='"1"'), StorageProblem.UNKNOWN_VERSION),
    (_doc(version="true"), StorageProblem.UNKNOWN_VERSION),
    (_doc(version="1.0"), StorageProblem.UNKNOWN_VERSION),
    (b"[]", StorageProblem.INVALID_STRUCTURE),
    (b'"texto"', StorageProblem.INVALID_STRUCTURE),
    (b'{"version": 1}', StorageProblem.INVALID_STRUCTURE),
    (_doc(extra=', "extra": 1'), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits="{}"), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits='["Leer"]'), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits=_habit_json(extra=', "color": "rojo"')), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits='[{"name": "Leer"}]'), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits='[{"name": 5, "marks": []}]'), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits='[{"name": "Leer", "marks": "2026-10-23"}]'), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits='[{"name": "Leer", "marks": [20261023]}]'), StorageProblem.INVALID_STRUCTURE),
    (_doc(habits=_habit_json(marks='["2026-02-30"]')), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(marks='["20261023"]')), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(marks='["2026-W43-5"]')), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(marks='["2026-10-3"]')), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(marks='[""]')), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(marks='["2026-10-23", "2026-10-23"]')), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(name="")), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(name="Leer  mucho")), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(name="-x")), StorageProblem.INCOHERENT),
    (_doc(habits=_habit_json(name="a\nb")), StorageProblem.INCOHERENT),
    (
        _doc(habits='[{"name": "Leer", "marks": []}, {"name": "leer", "marks": []}]'),
        StorageProblem.INCOHERENT,
    ),
]


@pytest.mark.parametrize(("content", "problem"), DAMAGED_CASES)
def test_rf_5_3_cl_10_cl_23_damaged_data_is_rejected_untouched(
    data_path: Path, content: bytes, problem: StorageProblem
) -> None:
    data_path.write_bytes(content)
    with pytest.raises(StorageError) as info:
        load(data_path)
    assert info.value.problem is problem
    assert data_path.read_bytes() == content


def test_rf_5_3_cl_10_a_folder_instead_of_a_file_is_unreadable(data_path: Path) -> None:
    data_path.mkdir()
    with pytest.raises(StorageError) as info:
        load(data_path)
    assert info.value.problem is StorageProblem.UNREADABLE


# --- save: fallos del sistema ----------------------------------------------


def _saved_file(data_path: Path) -> bytes:
    save(data_path, _example_habits())
    return data_path.read_bytes()


def _assert_failed_save_left_everything_intact(data_path: Path, original: bytes) -> None:
    assert data_path.read_bytes() == original
    assert [item.name for item in data_path.parent.iterdir()] == ["habits.json"]


def _fail(*args: object, **kwargs: object) -> None:
    raise OSError("fallo simulado")


@pytest.mark.parametrize("target", ["replace", "fsync"])
def test_rf_5_5_cl_22_os_failures_become_save_failed(
    data_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    original = _saved_file(data_path)
    monkeypatch.setattr(os, target, _fail)
    with pytest.raises(StorageError) as info:
        save(data_path, ())
    assert info.value.problem is StorageProblem.SAVE_FAILED
    assert "fallo simulado" in info.value.detail
    monkeypatch.undo()
    _assert_failed_save_left_everything_intact(data_path, original)


def test_rf_5_5_cl_22_folder_that_cannot_be_created(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sin_permiso" / "habits.json"
    monkeypatch.setattr(Path, "mkdir", _fail)
    with pytest.raises(StorageError) as info:
        save(path, ())
    assert info.value.problem is StorageProblem.SAVE_FAILED
    monkeypatch.undo()
    assert not path.parent.exists()


def test_rf_5_5_cl_22_read_only_data_file(data_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = _saved_file(data_path)
    monkeypatch.setattr(os, "access", lambda *args, **kwargs: False)
    with pytest.raises(StorageError) as info:
        save(data_path, ())
    assert info.value.problem is StorageProblem.SAVE_FAILED
    monkeypatch.undo()
    _assert_failed_save_left_everything_intact(data_path, original)


def test_rnf_5_keyboard_interrupt_leaves_original_and_no_temporary(
    data_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _saved_file(data_path)

    def interrupt(*args: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "fsync", interrupt)
    with pytest.raises(KeyboardInterrupt):
        save(data_path, ())
    monkeypatch.undo()
    _assert_failed_save_left_everything_intact(data_path, original)


def test_rnf_5_stale_temporary_is_overwritten_and_never_read(data_path: Path) -> None:
    stale = data_path.with_name(data_path.name + ".tmp")
    stale.write_text("basura", encoding="utf-8")
    assert load(data_path) == ()
    save(data_path, _example_habits())
    assert not stale.exists()
    assert load(data_path) == _example_habits()
