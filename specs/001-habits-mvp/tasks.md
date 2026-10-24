# Tareas 001 — MVP de habits-cli

Derivadas de `specs/001-habits-mvp/spec.md` (aprobada el 2026-10-23) y `specs/001-habits-mvp/plan.md` (borrador; sus puntos pendientes están en la sección 9 del plan). Fecha: 2026-10-23.

## Reglas para todas las tareas

- Cada tarea cabe en 20-30 minutos. Si una se alarga, se divide antes de seguir.
- Orden de dependencia: no empieces una tarea sin tener hechas las de su línea «Depende de».
- Dentro de cada tarea, escribe primero las pruebas y luego lo mínimo para que pasen. Las pruebas citan en su nombre el RF o CL que verifican.
- Al terminar cada tarea, `pytest -q` pasa completo (no solo el archivo de la tarea). Si `pytest` no está en el PATH, usa `python -m pytest -q`.
- «Sección X» se refiere a `plan.md`. Los textos exactos de mensajes salen de la sección 5.4 del plan.
- No se modifica nada dentro de `specs/` ni de `docs/constitution.md` desde estas tareas. No se añaden dependencias salvo pytest.
- No se hace commit a menos que la persona dueña del proyecto lo pida.

## Fase 0 — Preparación

- [x] **T01 · Entorno y esqueleto** (≈20 min)
  - Cubre: — (infraestructura de todos los RF)
  - Depende de: —
  - Archivos: `habits/__init__.py`, `habits/__main__.py`, `habits/core.py`, `habits/storage.py`, `habits/cli.py`, `tests/conftest.py`
  - Qué: instalar pytest; crear los cuatro módulos y `__init__.py` vacíos (solo una línea de docstring en español); crear `conftest.py` con la constante `TODAY = date(2026, 10, 23)`, el fixture `data_path` (`tmp_path / "habits.json"`) y una función auxiliar que escribe un texto como archivo de datos.
  - Hecho cuando: `python --version` muestra 3.12 o superior; `python -c "import habits.core, habits.storage, habits.cli"` no da error; `pytest -q` se ejecuta sin errores de importación (termina con «no tests ran»).

- [x] **T02 · Pruebas de la constitución** (≈25 min)
  - Cubre: RNF-3 (principios 1, 3 y 5)
  - Depende de: T01
  - Archivos: `tests/test_constitution.py`
  - Qué: cinco pruebas con `ast` y `sys.stdlib_module_names` (sección 7.2): (1) todo `import` de `habits/` es de la biblioteca estándar o del propio paquete; (2) `core.py` no importa `os`, `sys`, `json`, `pathlib` ni `io`, no llama a `print`, `open` ni `input` y no usa `date.today` ni `datetime.now`; (3) `cli.py` no importa `json`; (4) `json` solo se importa en `storage.py`; (5) ningún módulo importa `socket`, `urllib`, `http` ni `ssl`.
  - Hecho cuando: `pytest -q tests/test_constitution.py` pasa con 5 pruebas; si añades temporalmente `import os` a `core.py`, falla la prueba (2), y al quitarlo vuelve a pasar.

## Fase 1 — `core.py`: tipos y nombres

- [x] **T03 · Tipos y excepciones del núcleo** (≈25 min)
  - Cubre: base de RF-1 a RF-4 (sección 2.1)
  - Depende de: T01
  - Archivos: `habits/core.py`, `tests/test_operations.py`
  - Qué: `MAX_NAME_LENGTH = 100`; `NameProblem`; dataclasses inmutables `Habit`, `HabitStatus`, `MarkResult`; `HabitList`; excepciones `HabitError`, `InvalidNameError` (con `problem` y `length`), `DuplicateHabitError` (con `existing_name`), `HabitNotFoundError` (con `name`), `IncoherentDataError` (con `detail`). Con type hints.
  - Hecho cuando: `pytest -q tests/test_operations.py` pasa con pruebas que comprueban que asignar un campo de `Habit` lanza `FrozenInstanceError` y que cada excepción conserva sus datos y es subclase de `HabitError`.

- [x] **T04 · `normalize_name`** (≈20 min)
  - Cubre: RF-1.1, RF-2.2
  - Depende de: T03
  - Archivos: `habits/core.py`, `tests/test_names.py`
  - Qué: algoritmo de la sección 4.1.
  - Hecho cuando: `pytest -q tests/test_names.py` pasa con casos para: espacios de borde, secuencias internas de espacios, tabulador, espacio de no separación (` `), solo espacios (resultado `""`), un salto de línea que se mantiene (no es espacio) y mayúsculas, acentos y emojis que se conservan.

- [x] **T05 · `validate_name`** (≈25 min)
  - Cubre: RF-1.2, RF-1.5, RF-1.6, RF-2.6 (parte pura); CL-2, CL-12, CL-13, CL-18
  - Depende de: T04
  - Archivos: `habits/core.py`, `tests/test_names.py`
  - Qué: validaciones y orden de la sección 4.1 (vacío, control, guion inicial, longitud).
  - Hecho cuando: `pytest -q tests/test_names.py` pasa con casos: vacío y solo espacios → `EMPTY`; `"a\nb"`, `"\x00"` y `" "` → `CONTROL_CHARS`; `"-x"` → `LEADING_DASH`; 100 caracteres válido y 101 → `TOO_LONG` con `length=101`; 100 caracteres con espacios en los bordes válido; emoji compuesto con carácter de ancho cero válido; un nombre que incumple dos reglas devuelve la primera del orden.

- [x] **T06 · `name_key` y `find_habit`** (≈25 min)
  - Cubre: RF-1.3, RF-2.2; CL-1, CL-14, CL-19
  - Depende de: T05
  - Archivos: `habits/core.py`, `tests/test_names.py`, `tests/test_operations.py`
  - Qué: clave NFD + `casefold` + NFD (sección 4.2); búsqueda por clave en una tupla de hábitos.
  - Hecho cuando: `pytest -q` pasa con casos: «Leer» = «leer» = « LEER » = «Leer  » (misma clave); «Leer» ≠ «Léer»; «é» compuesta = «é» con acento combinado; letra especial (por ejemplo «ß»/«SS» o la i con punto) iguala según `casefold`; `find_habit` devuelve el hábito, `None` si no existe y `None` con la lista vacía.

## Fase 2 — `core.py`: racha

- [x] **T07 · `compute_streak`: casos base** (≈25 min)
  - Cubre: RF-4.1, RF-4.2, RF-4.3, RF-4.4, RF-4.5; CL-5, CL-6, CL-7, CL-8, CL-11, CL-25
  - Depende de: T03
  - Archivos: `habits/core.py`, `tests/test_streak.py`
  - Qué: algoritmo de la sección 4.3 con las marcas ya filtradas por `d <= today`.
  - Hecho cuando: `pytest -q tests/test_streak.py` pasa con las filas de la tabla 7.4 que no usan marcas futuras: ninguna → 0; hoy → 1; ayer → 1; ayer, anteayer y hace tres días → 3; hace tres y dos días → 0; hoy y hace dos días → 1; hoy, ayer y hace tres días → 2; cambio de mes, 29 de febrero de 2024 y cambio de año → 3; lunes y martes consultados el miércoles → 2; ayer y anteayer sin hoy con `today` dos días después → 0.

- [x] **T08 · Marcas futuras y límite de fechas** (≈20 min)
  - Cubre: RF-4.6, RF-4.7 (parte pura); CL-15, CL-26
  - Depende de: T07
  - Archivos: `habits/core.py`, `tests/test_streak.py`
  - Qué: confirmar que las marcas posteriores a `today` se ignoran en `compute_streak`; añadir `has_future_marks`; proteger el bucle de `date.min`.
  - Hecho cuando: `pytest -q tests/test_streak.py` pasa con: marcas 22, 23, 24 y 25 → 2; solo 24 y 25 → 0; `has_future_marks` verdadero con una marca posterior y falso con marcas de hoy o pasadas; una racha que llega a `date.min` termina sin `OverflowError`.

## Fase 3 — `core.py`: operaciones

- [x] **T09 · `add_habit`** (≈25 min)
  - Cubre: RF-1.1, RF-1.2, RF-1.3, RF-1.4, RF-1.5, RF-1.6; CL-1, CL-14, CL-27
  - Depende de: T06
  - Archivos: `habits/core.py`, `tests/test_operations.py`
  - Qué: sección 4.5.
  - Hecho cuando: `pytest -q tests/test_operations.py` pasa con casos: el hábito se añade al final con el nombre normalizado y sin marcas; la tupla original no cambia; «Leer» tras «leer» lanza `DuplicateHabitError` con el nombre guardado; «Léer» tras «Leer» se acepta; el nombre guardado conserva mayúsculas, acentos y emojis; los cuatro `NameProblem` se propagan; se pueden añadir 101 hábitos.

- [x] **T10 · `mark_done`** (≈30 min)
  - Cubre: RF-2.1, RF-2.2, RF-2.3, RF-2.4, RF-2.5, RF-2.6; CL-3, CL-4, CL-17
  - Depende de: T06, T08
  - Archivos: `habits/core.py`, `tests/test_operations.py`
  - Qué: sección 4.4; `MarkResult` con `already_marked`, `streak` y `has_future_marks`.
  - Hecho cuando: `pytest -q tests/test_operations.py` pasa con casos: marcar añade exactamente `today` a las marcas; la racha del resultado incluye hoy; marcar de nuevo da `already_marked=True` y devuelve las mismas marcas; nombre equivalente («LEER ») encuentra el hábito; inexistente lanza `HabitNotFoundError` con el nombre normalizado; nombre vacío o de solo espacios lanza `InvalidNameError(EMPTY)` y no `HabitNotFoundError`; con una marca futura, `has_future_marks` es verdadero; la firma no admite ninguna fecha que no sea `today`.

- [x] **T11 · `summarize`** (≈20 min)
  - Cubre: RF-3.1, RF-4.7 (parte pura)
  - Depende de: T08
  - Archivos: `habits/core.py`, `tests/test_operations.py`
  - Qué: sección 4.6.
  - Hecho cuando: `pytest -q tests/test_operations.py` pasa con el ejemplo del plan (sección 3.3 con `today = 2026-10-23`): resultados `("Leer 20 minutos", 3, True, False)`, `("Repasar álgebra", 1, False, False)`, `("Escribir diario", 0, False, False)` en ese orden; una marca futura da `has_future_marks=True` y no cuenta como «hecho hoy»; lista vacía → tupla vacía.

- [x] **T12 · `check_integrity`** (≈20 min)
  - Cubre: RF-5.3 (parte pura); CL-23
  - Depende de: T06
  - Archivos: `habits/core.py`, `tests/test_operations.py`
  - Qué: lanza `IncoherentDataError` si algún nombre no es válido, no está ya normalizado, o dos hábitos tienen claves equivalentes.
  - Hecho cuando: `pytest -q tests/test_operations.py` pasa con casos: lista válida no lanza; nombre con espacios dobles lanza; nombre vacío lanza; nombre de 101 caracteres lanza; «Leer» y «leer » lanzan; «Leer» y «Léer» no lanzan.

## Fase 4 — `storage.py`

- [x] **T13 · Errores de almacenamiento y `default_path`** (≈20 min)
  - Cubre: RF-5.6
  - Depende de: T01
  - Archivos: `habits/storage.py`, `tests/test_storage.py`
  - Qué: `StorageProblem`, `StorageError(problem, detail)`, `FORMAT_VERSION = 1` y `default_path()` (sección 2.2). Si el sistema no puede determinar la carpeta del usuario (`RuntimeError`), lanza `StorageError(UNREADABLE)` (punto 8 del plan).
  - Hecho cuando: `pytest -q tests/test_storage.py` pasa con: con la carpeta de usuario falsa (variables `HOME` y `USERPROFILE` apuntando a `tmp_path`), `default_path()` es `tmp_path/.habits-cli/habits.json`; si `Path.home` simulada lanza `RuntimeError`, `default_path()` lanza `StorageError` con `UNREADABLE`.

- [x] **T14 · `save`: camino feliz y formato** (≈25 min)
  - Cubre: RF-5.1, RF-5.4
  - Depende de: T13, T03
  - Archivos: `habits/storage.py`, `tests/test_storage.py`
  - Qué: serializar según la sección 3.2 (versión 1, marcas ordenadas, UTF-8, sangría de 2, `ensure_ascii` desactivado); crear la carpeta padre si no existe; escritura vía temporal y `os.replace` (sección 3.5), aún sin los casos de fallo.
  - Hecho cuando: `pytest -q tests/test_storage.py` pasa con: guardar los tres hábitos del ejemplo (sección 3.3) produce un archivo cuyo JSON es igual al del ejemplo; las marcas se escriben ordenadas aunque lleguen desordenadas; un nombre con acento y emoji aparece sin escapar en el archivo; se crea la carpeta si no existía; tras guardar no queda ningún archivo `.tmp`.

- [x] **T15 · `load`: camino feliz** (≈20 min)
  - Cubre: RF-5.1, RF-5.2, RF-4.6; CL-9
  - Depende de: T14, T12
  - Archivos: `habits/storage.py`, `tests/test_storage.py`
  - Qué: leer, convertir a `HabitList` y llamar a `core.check_integrity`; archivo ausente → tupla vacía; `load` no crea archivos ni carpetas.
  - Hecho cuando: `pytest -q tests/test_storage.py` pasa con: archivo ausente → `()` y la carpeta no se crea; `save` seguido de `load` devuelve lo mismo (ida y vuelta); marcas desordenadas en el archivo se aceptan; las marcas futuras se conservan; el ejemplo de la sección 3.3 se lee con 3 hábitos en su orden.

- [x] **T16 · `load`: estructura, versión y codificación** (≈25 min)
  - Cubre: RF-5.3, RF-5.4; CL-10, CL-23
  - Depende de: T15
  - Archivos: `habits/storage.py`, `tests/test_storage.py`
  - Qué: rechazos de la tabla de la sección 3.4 relativos a archivo, versión y estructura, con su `StorageProblem`.
  - Hecho cuando: `pytest -q tests/test_storage.py` pasa con una prueba parametrizada que comprueba el `StorageProblem` de cada caso y que el archivo queda byte a byte igual: 0 bytes → `EMPTY`; bytes no UTF-8, JSON inválido y una carpeta en lugar de archivo → `UNREADABLE`; `version` ausente, `2`, `"1"` y `true` → `UNKNOWN_VERSION`; raíz que no es objeto, clave desconocida en la raíz o en un hábito, `habits` que no es lista, `name` que no es texto, `marks` que no es lista de textos → `INVALID_STRUCTURE`.

- [x] **T17 · `load`: fechas y coherencia** (≈25 min)
  - Cubre: RF-5.3; CL-23
  - Depende de: T16
  - Archivos: `habits/storage.py`, `tests/test_storage.py`
  - Qué: parseo estricto de fechas (solo `AAAA-MM-DD` canónico), detección de marcas repetidas y traducción de `IncoherentDataError` del núcleo.
  - Hecho cuando: `pytest -q tests/test_storage.py` pasa con una prueba parametrizada (todas dan `INCOHERENT` y el archivo no cambia): `"2026-02-30"`, `"20261023"`, `"2026-W43-5"`, `"2026-10-3"`, `""`; la misma fecha dos veces en un hábito; nombre no válido; nombre sin normalizar; dos nombres equivalentes.

- [x] **T18 · `save`: fallos del sistema** (≈25 min)
  - Cubre: RF-5.5; CL-22
  - Depende de: T14
  - Archivos: `habits/storage.py`, `tests/test_storage.py`
  - Qué: convertir `OSError` en `StorageError(SAVE_FAILED)`; rechazar si el archivo existe y `os.access(path, os.W_OK)` es falso.
  - Hecho cuando: `pytest -q tests/test_storage.py` pasa con casos simulados con `monkeypatch`: `os.replace` falla, `os.fsync` falla, `Path.mkdir` falla y `os.access` devuelve falso → en todos `StorageError` con `SAVE_FAILED`, el contenido previo del archivo queda idéntico y no queda `.tmp`.

- [x] **T19 · `save`: interrupciones y temporal huérfano** (≈20 min)
  - Cubre: RNF-5; RF-5.5
  - Depende de: T18
  - Archivos: `habits/storage.py`, `tests/test_storage.py`
  - Qué: garantizar la limpieza del temporal con `finally` ante cualquier excepción, incluida `KeyboardInterrupt`.
  - Hecho cuando: `pytest -q tests/test_storage.py` pasa con: una `KeyboardInterrupt` simulada durante `os.fsync` se propaga, deja el archivo original intacto y borra el `.tmp`; un `.tmp` huérfano previo con basura se sobrescribe en el siguiente guardado y `load` nunca lo lee.

## Fase 5 — `cli.py`

- [x] **T20 · `parse_args`** (≈30 min)
  - Cubre: RF-6.1, RF-6.2, RF-6.4; CL-20, CL-21
  - Depende de: T01
  - Archivos: `habits/cli.py`, `tests/test_cli.py`
  - Qué: `Command`, `UsageError` y las reglas de la sección 5.1; los motivos de error son los de la tabla de códigos 2 (sección 5.4).
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con: `["crear", "Leer"]`, `["marcar", "Leer"]` y `["listar"]` producen el `Command` correcto; `-h` o `--ayuda` en cualquier posición producen `ayuda`; `["crear", ""]` es un `Command` válido con argumento vacío; `["crear", "-x"]` es un `Command` válido (la validación del nombre es del núcleo); `[]`, `["borrar"]`, `["crear"]`, `["crear", "Leer", "mucho"]` y `["listar", "x"]` lanzan `UsageError` con el motivo exacto del plan.

- [x] **T21 · `help_text` y salida de `main` para ayuda y uso incorrecto** (≈25 min)
  - Cubre: RF-6.1, RF-6.2, RF-6.3, RF-6.6; CL-20, CL-21
  - Depende de: T20
  - Archivos: `habits/cli.py`, `tests/test_cli.py`
  - Qué: texto de la ayuda de la sección 5.4; `main(argv, *, today=None, path=None) -> int` solo con las ramas de ayuda y uso incorrecto.
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con: `main(["--ayuda"])` devuelve 0 y la ayuda sale por stdout con la lista de tres comandos; `main([])` devuelve 2, stdout vacío, y stderr con `Error: falta el comando.` seguido de la ayuda; ídem para comando desconocido, falta de nombre, argumentos de más (con la frase sobre comillas) y `listar x`.

- [x] **T22 · `main`: `crear`** (≈30 min)
  - Cubre: RF-1.1, RF-1.2, RF-1.3, RF-1.5, RF-1.6, RF-6.3, RF-6.6; CL-1, CL-2, CL-13, CL-18
  - Depende de: T09, T15, T18, T21
  - Archivos: `habits/cli.py`, `tests/test_cli.py`
  - Qué: flujo de la sección 4.7 para `crear`; textos exactos de la sección 5.4; la confirmación se escribe después de guardar.
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con: `crear "  Leer   20 minutos "` guarda «Leer 20 minutos», imprime `Hábito «Leer 20 minutos» creado.` por stdout y devuelve 0; el archivo contiene el hábito; cada error (vacío, control, guion inicial, 101 caracteres, duplicado) devuelve 1, imprime su texto exacto por stderr, deja stdout vacío y deja el archivo sin cambios.

- [x] **T23 · `main`: `marcar`** (≈30 min)
  - Cubre: RF-2.1, RF-2.2, RF-2.3, RF-2.4, RF-2.6, RF-4.7, RF-6.3, RF-6.6; CL-3, CL-4, CL-17
  - Depende de: T10, T22
  - Archivos: `habits/cli.py`, `tests/test_cli.py`
  - Qué: flujo `marcar` de la sección 4.7; aviso RF-4.7 por stderr; no se llama a `save` si ya estaba marcado.
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con: marcar un hábito imprime `Hábito «Leer» marcado hoy. Racha: 1 día.` y devuelve 0; marcar otra vez imprime `El hábito «Leer» ya estaba marcado hoy. Racha: 1 día.` por stdout, devuelve 0 y no modifica el archivo (misma fecha de modificación y contenido); hábito inexistente → error del plan, código 1; nombre vacío → error de nombre vacío (no el de inexistente), código 1; con una marca futura se imprime por stderr el aviso de fecha del plan y el código sigue siendo 0.

- [x] **T24 · `main`: `listar`** (≈25 min)
  - Cubre: RF-3.1, RF-3.2, RF-3.3, RF-4.7, RF-6.6; CL-8, CL-9
  - Depende de: T11, T22
  - Archivos: `habits/cli.py`, `tests/test_cli.py`
  - Qué: flujo `listar` de la sección 4.7; «día» o «días» según corresponda; no guarda.
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con: el archivo de la sección 3.3 y `today=2026-10-23` produce exactamente las cuatro líneas del ejemplo del plan; con archivo ausente sale el mensaje de lista vacía por stdout, código 0, y no se crea el archivo ni la carpeta; con una marca futura sale el aviso por stderr por cada hábito afectado y el listado queda limpio en stdout; el archivo no cambia tras listar.

- [x] **T25 · `main`: errores de datos y de guardado** (≈30 min)
  - Cubre: RF-5.3, RF-5.5, RF-6.3; CL-10, CL-22, CL-23; RNF-7
  - Depende de: T17, T19, T23, T24
  - Archivos: `habits/cli.py`, `tests/test_cli.py`
  - Qué: traducir `StorageError` a los textos de la sección 5.4, con el motivo y la ruta; la confirmación nunca se imprime si `save` falla.
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con: para cada comando y un archivo dañado (vacío, versión desconocida, incoherente) el resultado es código 1, stderr con `Error: los datos guardados están dañados (…)` y la ruta, y el archivo intacto; con `save` simulado para que falle, `crear` y `marcar` devuelven 1, no imprimen la confirmación y no cambian el archivo; una prueba parametrizada comprueba que cada error de la lista de RNF-7 contiene su sugerencia («Escribe», «Acórtalo», «Elige otro nombre», «Usa «listar»», «Repara o aparta», «Revisa», etc.).

- [x] **T26 · «Hoy» se lee una sola vez** (≈20 min)
  - Cubre: CL-24
  - Depende de: T25
  - Archivos: `habits/cli.py`, `tests/test_cli.py`
  - Qué: cuando `today` no se inyecta, `main` obtiene la fecha una sola vez y la pasa a `core`.
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con una prueba que sustituye la función que lee la fecha por una que cuenta las llamadas y devuelve fechas distintas en cada llamada: tras un `marcar` y tras un `listar`, el contador vale 1 y la marca guardada y la racha usan la misma fecha.

- [x] **T27 · `configure_output` y punto de entrada** (≈25 min)
  - Cubre: RF-6.5, RF-6.3; CL-28
  - Depende de: T25
  - Archivos: `habits/cli.py`, `habits/__main__.py`, `tests/test_cli.py`
  - Qué: `configure_output()` según la sección 5.5; `__main__.py` llama a `configure_output()` y a `sys.exit(main(sys.argv[1:]))`.
  - Hecho cuando: `pytest -q tests/test_cli.py` pasa con una prueba que envuelve un `BytesIO` en un `TextIOWrapper` con codificación `cp1252`, llama a `configure_output()` sobre él y escribe un emoji sin excepción, quedando un `?` en el flujo; y `python -m habits --ayuda` desde la raíz del proyecto imprime la ayuda y termina con código 0.

## Fase 6 — Pruebas de proceso y rendimiento

- [x] **T28 · Persistencia entre ejecuciones y carpetas distintas** (≈25 min)
  - Cubre: RF-5.1, RF-5.6; CL-30
  - Depende de: T27
  - Archivos: `tests/test_cli_process.py`
  - Qué: ayudante que ejecuta `python -m habits …` con `subprocess.run`, `PYTHONPATH` apuntando al proyecto y `HOME`/`USERPROFILE` en una carpeta falsa de `tmp_path`.
  - Hecho cuando: `pytest -q tests/test_cli_process.py` pasa con: `crear`, `marcar` y `listar` en tres procesos distintos muestran el hábito con racha 1 y hecho hoy; ejecutar `listar` desde otra carpeta de trabajo muestra los mismos hábitos; el archivo está en la carpeta falsa y no en el `~` real.

- [x] **T29 · Canales y codificación en proceso real** (≈25 min)
  - Cubre: RF-6.6, RF-6.5; CL-31, CL-28
  - Depende de: T28
  - Archivos: `tests/test_cli_process.py`
  - Qué: pruebas con salidas capturadas por separado.
  - Hecho cuando: `pytest -q tests/test_cli_process.py` pasa con: un error (`marcar` de un hábito inexistente) deja stdout vacío y el mensaje en stderr; el aviso de marcas futuras aparece en stderr y no en stdout; con `PYTHONIOENCODING=cp1252`, `crear "Estudio 🚀"` y `listar` terminan con código 0, sin traza y con un `?` en el lugar del emoji, y el archivo de datos conserva el emoji.

- [x] **T30 · Rendimiento con la carga de referencia** (≈20 min)
  - Cubre: RNF-2; CL-27
  - Depende de: T28
  - Archivos: `tests/test_cli_process.py`
  - Qué: generar un archivo de datos con 100 hábitos y 1 826 marcas cada uno (5 años) directamente con `json`; medir `listar` y `marcar`.
  - Hecho cuando: `pytest -q tests/test_cli_process.py` pasa con: `listar` y `marcar` sobre ese archivo terminan cada uno en menos de 1 segundo, medido desde que se lanza el proceso; `crear` del hábito número 101 funciona (CL-27).

## Fase 7 — Cierre

- [x] **T31 · Revisión documentada de lo no automatizable** (≈25 min)
  - Cubre: RNF-4, RNF-8; CL-16, CL-29
  - Depende de: T30
  - Archivos: `docs/revision-001.md`
  - Qué: documento breve en español con una sección por elemento: CL-16, CL-29, RNF-4 y RNF-8. Para cada uno: qué se revisó, cómo (por ejemplo, para RNF-4, revisión de que el único `open`/escritura está en `storage.py` y dentro de la carpeta de datos) y el resultado.
  - Hecho cuando: el archivo existe con las cuatro secciones y cada una indica fecha, método y resultado; la sección de CL-16 enlaza a la prueba de CL-15 como cobertura parcial.

- [ ] **T32 · Prueba de uso con tres personas** (≈30 min)
  - Cubre: criterio de finalización 8.4 de la spec (éxito de la sección 1)
  - Depende de: T31
  - Archivos: `docs/revision-001.md`
  - Qué: tres personas que nunca han usado la herramienta completan crear → marcar → listar usando solo `python -m habits --ayuda`. Se cronometra a cada una y se anotan las dudas.
  - Hecho cuando: `docs/revision-001.md` tiene una tabla con las tres personas (nombre o inicial, tiempo, si pidió ayuda externa) y las tres terminan en menos de 1 minuto sin ayuda externa; si alguna no lo logra, se anotan los cambios de texto propuestos y la tarea queda sin marcar.

- [ ] **T33 · Verificación final** (≈25 min)
  - Cubre: todos los RF; criterios de finalización 8.1 a 8.8
  - Depende de: T32
  - Archivos: `docs/revision-001.md`
  - Qué: recorrer la matriz de la sección 8 del plan y anotar, para cada RF, el nombre de al menos una prueba que lo cubre; recorrer CL-1 a CL-31 y RNF-1 a RNF-8 con el mismo criterio; ejecutar la suite completa.
  - Hecho cuando: `pytest -q` pasa con todas las pruebas y se confirma en la respuesta final con la salida; `docs/revision-001.md` incluye la tabla RF → prueba con los 34 RF cubiertos y la lista de CL y RNF sin prueba automática (solo CL-16, CL-29, RNF-4 y RNF-8, según el criterio 8.2 y 8.3 de la spec).

## Cobertura de requisitos funcionales

| RF | Tareas |
|----|--------|
| RF-1.1 | T04, T09, T22 |
| RF-1.2 | T05, T09, T22 |
| RF-1.3 | T06, T09, T22 |
| RF-1.4 | T04, T09 |
| RF-1.5 | T05, T09, T22 |
| RF-1.6 | T05, T09, T22 |
| RF-2.1 | T10, T23 |
| RF-2.2 | T04, T06, T10, T23 |
| RF-2.3 | T10, T23 |
| RF-2.4 | T10, T23 |
| RF-2.5 | T10 |
| RF-2.6 | T05, T10, T23 |
| RF-3.1 | T11, T24 |
| RF-3.2 | T24 |
| RF-3.3 | T24 |
| RF-4.1 a RF-4.5 | T07 |
| RF-4.6 | T08, T15 |
| RF-4.7 | T08, T11, T23, T24, T29 |
| RF-5.1 | T14, T15, T28 |
| RF-5.2 | T15 |
| RF-5.3 | T12, T16, T17, T25 |
| RF-5.4 | T14, T16 |
| RF-5.5 | T18, T19, T25 |
| RF-5.6 | T13, T28 |
| RF-6.1 | T20, T21 |
| RF-6.2 | T20, T21 |
| RF-6.3 | T21, T22, T23, T25, T27 |
| RF-6.4 | T20 |
| RF-6.5 | T27, T29 |
| RF-6.6 | T21, T22, T23, T24, T29 |

## Orden de dependencia

Cada tarea indica su dependencia directa en su línea «Depende de». Las cadenas principales son:

| Cadena | Tareas |
|--------|--------|
| Nombres | T01 → T03 → T04 → T05 → T06 |
| Racha | T03 → T07 → T08 → T11 |
| Operaciones del núcleo | T06 → T09; T06 + T08 → T10; T06 → T12 |
| Almacenamiento | T01 → T13 → T14 → T15 → T16 → T17; T14 → T18 → T19 |
| Interfaz | T01 → T20 → T21 → T22 → T23 → T24 → T25 → T26 y T27 |
| Procesos y cierre | T27 → T28 → T29 y T30 → T31 → T32 → T33 |

Las cadenas de nombres, racha, almacenamiento y la parte inicial de la interfaz (T20 y T21) son independientes entre sí. Las operaciones del núcleo necesitan nombres y racha. La interfaz desde T22 necesita además las operaciones del núcleo y el almacenamiento.
