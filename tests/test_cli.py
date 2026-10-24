"""Pruebas de la interfaz de línea de comandos: argumentos, textos y códigos de salida."""

import io
import sys
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pytest
from conftest import EXAMPLE_HABITS, TODAY, write_habits

from habits import cli, storage
from habits.cli import Command, UsageError, configure_output, help_text, main, parse_args
from habits.storage import StorageError, StorageProblem

CliRunner = Callable[..., tuple[int, str, str]]


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str], data_path: Path) -> CliRunner:
    def runner(*args: str, today: date = TODAY, path: Path | None = None) -> tuple[int, str, str]:
        code = main(list(args), today=today, path=path or data_path)
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return runner


# --- parse_args ------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["crear", "Leer"], Command("crear", "Leer")),
        (["marcar", "Leer"], Command("marcar", "Leer")),
        (["listar"], Command("listar")),
        (["-h"], Command("ayuda")),
        (["--ayuda"], Command("ayuda")),
        (["crear", "Leer", "--ayuda"], Command("ayuda")),
        (["foo", "-h"], Command("ayuda")),
        (["crear", ""], Command("crear", "")),
        (["crear", "-x"], Command("crear", "-x")),
    ],
)
def test_rf_6_1_rf_6_2_rf_6_4_parse_args_valid(argv: list[str], expected: Command) -> None:
    assert parse_args(argv) == expected


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        ([], "falta el comando."),
        (["borrar"], "comando desconocido «borrar»."),
        (["crear"], "el comando «crear» necesita un nombre."),
        (["marcar"], "el comando «marcar» necesita un nombre."),
        (
            ["crear", "Leer", "mucho"],
            "el comando «crear» recibió argumentos de más: «mucho». "
            "Si el nombre tiene espacios, escríbelo entre comillas.",
        ),
        (["listar", "x"], "el comando «listar» no admite argumentos."),
    ],
)
def test_rf_6_1_cl_20_parse_args_usage_errors(argv: list[str], message: str) -> None:
    with pytest.raises(UsageError) as info:
        parse_args(argv)
    assert str(info.value) == message


# --- ayuda y uso incorrecto -------------------------------------------------


def test_rf_6_2_rf_6_3_rf_6_6_cl_21_help_goes_to_stdout_with_success(run: CliRunner) -> None:
    for option in ("--ayuda", "-h"):
        code, out, err = run(option)
        assert (code, out, err) == (0, help_text() + "\n", "")
    for command in ("crear <nombre>", "marcar <nombre>", "listar", "-h, --ayuda"):
        assert command in help_text()


@pytest.mark.parametrize(
    ("argv", "first_line"),
    [
        ([], "Error: falta el comando."),
        (["borrar"], "Error: comando desconocido «borrar»."),
        (["crear"], "Error: el comando «crear» necesita un nombre."),
        (["listar", "x"], "Error: el comando «listar» no admite argumentos."),
        (
            ["crear", "Leer", "mucho"],
            "Error: el comando «crear» recibió argumentos de más: «mucho». "
            "Si el nombre tiene espacios, escríbelo entre comillas.",
        ),
    ],
)
def test_rf_6_1_rf_6_3_rf_6_6_cl_20_cl_21_usage_error_exit_2_on_stderr(
    run: CliRunner, argv: list[str], first_line: str
) -> None:
    code, out, err = run(*argv)
    assert code == 2
    assert out == ""
    assert err == f"{first_line}\n{help_text()}\n"


# --- crear -----------------------------------------------------------------


def test_rf_1_1_rf_1_4_create_normalizes_saves_and_confirms(run: CliRunner, data_path: Path) -> None:
    code, out, err = run("crear", "  Leer   20 minutos ")
    assert (code, out, err) == (0, "Hábito «Leer 20 minutos» creado.\n", "")
    assert [habit.name for habit in storage.load(data_path)] == ["Leer 20 minutos"]


EMPTY_NAME_ERROR = 'Error: el nombre del hábito está vacío. Escribe al menos un carácter, por ejemplo: crear "Leer".'

CREATE_ERRORS = [
    ("", EMPTY_NAME_ERROR),
    ("   ", EMPTY_NAME_ERROR),
    (
        "a\nb",
        "Error: el nombre contiene caracteres de control (como saltos de línea). "
        "Escríbelo en una sola línea.",
    ),
    ("-x", "Error: el nombre no puede empezar por «-». Empieza por una letra o un número."),
    ("a" * 101, "Error: el nombre tiene 101 caracteres y el máximo es 100. Acórtalo."),
    (
        "leer",
        "Error: ya existe el hábito «Leer» (los nombres no distinguen mayúsculas ni espacios de más). "
        "Elige otro nombre.",
    ),
]


@pytest.mark.parametrize(("name", "message"), CREATE_ERRORS)
def test_rf_1_2_rf_1_3_rf_1_5_rf_1_6_cl_1_cl_2_cl_13_cl_18_create_errors(
    run: CliRunner, data_path: Path, name: str, message: str
) -> None:
    write_habits(data_path, {"Leer": []})
    before = data_path.read_bytes()
    code, out, err = run("crear", name)
    assert (code, out, err) == (1, "", message + "\n")
    assert data_path.read_bytes() == before


def test_rf_1_2_failed_create_does_not_create_the_file(run: CliRunner, data_path: Path) -> None:
    run("crear", "   ")
    assert not data_path.exists()


def test_cl_12_create_accepts_accents_and_emoji(run: CliRunner, data_path: Path) -> None:
    assert run("crear", "Ñandú 🚀")[0] == 0
    assert storage.load(data_path)[0].name == "Ñandú 🚀"


# --- marcar ----------------------------------------------------------------


def test_rf_2_1_mark_confirms_with_resulting_streak(run: CliRunner, data_path: Path) -> None:
    run("crear", "Leer")
    code, out, err = run("marcar", "Leer")
    assert (code, out, err) == (0, "Hábito «Leer» marcado hoy. Racha: 1 día.\n", "")
    assert storage.load(data_path)[0].marks == {TODAY}


def test_rf_2_1_rf_4_2_mark_streak_counts_previous_days(run: CliRunner, data_path: Path) -> None:
    write_habits(data_path, {"Leer": [TODAY - timedelta(days=1), TODAY - timedelta(days=2)]})
    assert run("marcar", "Leer")[1] == "Hábito «Leer» marcado hoy. Racha: 3 días.\n"


def test_rf_2_3_cl_3_second_mark_warns_exit_0_and_does_not_touch_the_file(
    run: CliRunner, data_path: Path
) -> None:
    run("crear", "Leer")
    run("marcar", "Leer")
    before, mtime = data_path.read_bytes(), data_path.stat().st_mtime_ns
    code, out, err = run("marcar", "Leer")
    assert (code, out, err) == (0, "El hábito «Leer» ya estaba marcado hoy. Racha: 1 día.\n", "")
    assert (data_path.read_bytes(), data_path.stat().st_mtime_ns) == (before, mtime)


def test_rf_2_2_mark_uses_equivalent_name_and_shows_stored_name(run: CliRunner) -> None:
    run("crear", "Leer")
    assert run("marcar", " LEER ")[1] == "Hábito «Leer» marcado hoy. Racha: 1 día.\n"


def test_rf_2_4_cl_4_mark_unknown_habit(run: CliRunner, data_path: Path) -> None:
    write_habits(data_path, {"Leer": []})
    before = data_path.read_bytes()
    code, out, err = run("marcar", "  x   y ")
    assert (code, out) == (1, "")
    assert err == "Error: no existe ningún hábito llamado «x y». Usa «listar» para ver tus hábitos.\n"
    assert data_path.read_bytes() == before


def test_rf_2_6_cl_17_mark_empty_name_is_not_reported_as_unknown(run: CliRunner, data_path: Path) -> None:
    write_habits(data_path, {"Leer": []})
    code, out, err = run("marcar", "   ")
    assert (code, out, err) == (1, "", EMPTY_NAME_ERROR + "\n")


def test_rf_4_7_mark_with_future_marks_warns_on_stderr(run: CliRunner, data_path: Path) -> None:
    tomorrow = TODAY + timedelta(days=1)
    write_habits(data_path, {"Leer": [tomorrow]})
    code, out, err = run("marcar", "Leer")
    assert code == 0
    assert out == "Hábito «Leer» marcado hoy. Racha: 1 día.\n"
    assert err == (
        "Aviso: la fecha del equipo parece anterior a alguna marca de «Leer» "
        "(última marca: 2026-10-24). Esas marcas se ignoran hasta que la fecha del equipo las alcance.\n"
    )


# --- listar ----------------------------------------------------------------


def test_rf_3_1_cl_8_list_example_from_plan(run: CliRunner, data_path: Path) -> None:
    write_habits(data_path, EXAMPLE_HABITS)
    code, out, err = run("listar")
    assert (code, err) == (0, "")
    assert out == (
        "Tus hábitos:\n"
        "- Leer 20 minutos | racha: 3 días | hoy: sí\n"
        "- Repasar álgebra | racha: 1 día | hoy: no\n"
        "- Escribir diario | racha: 0 días | hoy: no\n"
    )


def test_rf_3_1_list_keeps_creation_order(run: CliRunner) -> None:
    for name in ("Zeta", "Alfa", "Mu"):
        run("crear", name)
    names = [line.split(" | ")[0] for line in run("listar")[1].splitlines()[1:]]
    assert names == ["- Zeta", "- Alfa", "- Mu"]


def test_rf_3_2_cl_9_empty_list_invites_to_create_and_creates_nothing(
    run: CliRunner, tmp_path: Path
) -> None:
    path = tmp_path / "nueva" / "habits.json"
    code, out, err = run("listar", path=path)
    assert (code, err) == (0, "")
    assert out == 'Aún no tienes hábitos. Crea el primero con: python -m habits crear "Leer 20 minutos"\n'
    assert not path.parent.exists()


def test_rf_3_3_list_does_not_modify_the_file(run: CliRunner, data_path: Path) -> None:
    write_habits(data_path, EXAMPLE_HABITS)
    before, mtime = data_path.read_bytes(), data_path.stat().st_mtime_ns
    run("listar")
    assert (data_path.read_bytes(), data_path.stat().st_mtime_ns) == (before, mtime)


def test_rf_4_7_cl_15_list_warns_per_habit_with_future_marks(run: CliRunner, data_path: Path) -> None:
    write_habits(
        data_path,
        {
            "A": [TODAY - timedelta(days=1), TODAY + timedelta(days=1)],
            "B": [TODAY],
            "C": [TODAY + timedelta(days=3)],
        },
    )
    code, out, err = run("listar")
    assert code == 0
    assert "Aviso" not in out
    assert "- A | racha: 1 día | hoy: no" in out
    assert "- C | racha: 0 días | hoy: no" in out
    assert err.count("Aviso:") == 2
    assert "«A» (última marca: 2026-10-24)" in err
    assert "«C» (última marca: 2026-10-26)" in err


def test_rf_4_6_cl_26_list_counts_marks_normally_once_date_returns(run: CliRunner, data_path: Path) -> None:
    write_habits(data_path, {"Leer": [TODAY - timedelta(days=2), TODAY - timedelta(days=1), TODAY]})
    assert "racha: 3 días | hoy: sí" in run("listar")[1]


# --- errores de datos y de guardado ------------------------------------------

DAMAGED_FILES = [
    (b"", "el archivo está vacío"),
    (b"{", "no se puede leer"),
    (b'{"version": 2, "habits": []}', "versión de formato desconocida"),
    (b'{"version": 1, "habits": "x"}', "estructura no válida"),
    (
        b'{"version": 1, "habits": [{"name": "Leer", "marks": ["2026-10-23", "2026-10-23"]}]}',
        "contenido incoherente: ",
    ),
]


@pytest.mark.parametrize("argv", [["crear", "Leer"], ["marcar", "Leer"], ["listar"]])
@pytest.mark.parametrize(("content", "reason"), DAMAGED_FILES)
def test_rf_5_3_cl_10_cl_23_damaged_data_exit_1_and_untouched(
    run: CliRunner, data_path: Path, argv: list[str], content: bytes, reason: str
) -> None:
    data_path.write_bytes(content)
    code, out, err = run(*argv)
    assert (code, out) == (1, "")
    assert err.startswith(f"Error: los datos guardados están dañados ({reason}")
    assert err.endswith(
        f"). No se ha modificado nada. Repara o aparta manualmente el archivo «{data_path}» "
        "y vuelve a intentarlo.\n"
    )
    assert data_path.read_bytes() == content


@pytest.mark.parametrize("argv", [["crear", "Leer"], ["marcar", "Leer"]])
def test_rf_5_5_cl_22_save_failure_shows_no_confirmation(
    run: CliRunner, data_path: Path, monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    write_habits(data_path, {"Otro": [], "Leer": []} if argv[0] == "marcar" else {"Otro": []})
    before = data_path.read_bytes()

    def failing_save(path: Path, habits: object) -> None:
        raise StorageError(StorageProblem.SAVE_FAILED, "disco lleno")

    monkeypatch.setattr(storage, "save", failing_save)
    code, out, err = run(*argv)
    assert (code, out) == (1, "")
    assert err == (
        "Error: no se pudo guardar (disco lleno). Tus datos anteriores siguen intactos. "
        f"Revisa el espacio en disco y los permisos de «{data_path}».\n"
    )
    assert data_path.read_bytes() == before


def test_rf_5_3_unknown_user_folder_is_reported_as_unreadable(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_home() -> Path:
        raise StorageError(StorageProblem.UNREADABLE, "sin carpeta")

    monkeypatch.setattr(storage, "default_path", no_home)
    assert main(["listar"], today=TODAY) == 1
    assert "no se puede leer" in capsys.readouterr().err


# --- RNF-7: cada error indica qué hacer ----------------------------------------

HINTS = (
    "Escribe",
    "Escríbelo",
    "Empieza por",
    "Acórtalo",
    "Elige otro nombre",
    "Usa «listar»",
    "Repara o aparta",
    "Revisa",
    "Uso:",
)


@pytest.mark.parametrize(("name", "message"), CREATE_ERRORS)
def test_rnf_7_name_errors_include_a_suggestion(name: str, message: str) -> None:
    assert any(hint in message for hint in HINTS)


@pytest.mark.parametrize("argv", [[], ["borrar"], ["crear"], ["crear", "a", "b"], ["listar", "x"]])
def test_rnf_7_usage_errors_include_the_correct_usage(run: CliRunner, argv: list[str]) -> None:
    assert "Uso: python -m habits" in run(*argv)[2]


ENGLISH_MARKERS = ("usage:", "options:", "positional arguments", "invalid choice", "unrecognized", "required")


def test_rnf_1_user_texts_have_no_english_default_messages(run: CliRunner, data_path: Path) -> None:
    write_habits(data_path, {"Leer": []})
    texts: list[str] = []
    for argv in ([], ["borrar"], ["crear"], ["listar", "x"], ["-h"], ["listar"], ["marcar", "x"]):
        _, out, err = run(*argv)
        texts += [out, err]
    for text in texts:
        assert not any(marker in text.lower() for marker in ENGLISH_MARKERS)


# --- CL-24: «hoy» se lee una sola vez por ejecución ---------------------------


def test_cl_24_today_is_read_once_per_execution(
    capsys: pytest.CaptureFixture[str], data_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[date] = []

    def fake_today() -> date:
        calls.append(TODAY + timedelta(days=len(calls)))
        return calls[-1]

    monkeypatch.setattr(cli, "_read_today", fake_today)
    main(["crear", "Leer"], path=data_path)
    assert len(calls) == 1
    main(["marcar", "Leer"], path=data_path)
    assert len(calls) == 2
    assert storage.load(data_path)[0].marks == {calls[1]}
    main(["listar"], path=data_path)
    assert len(calls) == 3
    capsys.readouterr()


# --- RF-6.5: consola sin soporte de algún carácter ----------------------------


def test_rf_6_5_cl_28_configure_output_replaces_unencodable_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict", newline="")
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stderr", stream)
    with pytest.raises(UnicodeEncodeError):
        stream.write("🚀")
    configure_output()
    stream.write("Estudio 🚀\n")
    stream.flush()
    assert buffer.getvalue() == b"Estudio ?\n"
