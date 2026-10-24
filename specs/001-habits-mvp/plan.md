# Plan 001 — MVP de habits-cli

Spec de referencia: `specs/001-habits-mvp/spec.md` · Estado del plan: borrador · Fecha: 2026-10-23

> La spec 001 fue **aprobada el 2026-10-23**. Este plan sigue en borrador hasta que se resuelvan los puntos de la sección 9. Si la spec cambia, vuelve a «borrador» y este plan se revisa.

**Cómo leer las marcas de cobertura:** cada sección indica entre corchetes los requisitos que cubre, por ejemplo **[RF-1.1, RF-1.4]**. La sección 8 reúne todo en una matriz RF → diseño → prueba.

## 1. Restricciones de la constitución y cómo se respetan

| Principio | Cómo lo respeta este plan |
|-----------|---------------------------|
| 1. Stack mínimo | Solo Python 3.12+ y biblioteca estándar (`dataclasses`, `datetime`, `enum`, `json`, `os`, `pathlib`, `sys`, `unicodedata`). pytest solo en `tests/`. Sin argparse (decisión D1). Una prueba automática verifica los imports. |
| 2. Spec primero | Este plan solo desarrolla lo que la spec exige; lo que la spec no dice se marca en la sección 9 en vez de decidirse en silencio. |
| 3. Lógica separada | `core.py` no importa `os`, `sys`, `json` ni `pathlib`, no usa `print`, no abre archivos y nunca llama a `date.today()`: recibe `today`. `cli.py` interpreta argumentos, llama a `core` y `storage`, y muestra resultados. |
| 4. Tests obligatorios | Toda función pública de `core.py` tiene test (sección 7.3). Se añaden pruebas de `storage`, `cli` y de la propia constitución. |
| 5. Persistencia simple | Un único archivo JSON, leído y escrito solo desde `storage.py`. El único archivo extra es un temporal que existe solo durante el guardado (sección 9, punto 1). |
| 6. Idioma | Identificadores, módulos, clases y funciones en inglés. Textos de la persona usuaria, ayuda, errores y nombres de comandos (`crear`, `marcar`, `listar`) en español **[RF-6.4]**. |

## 2. Estructura de módulos

```text
habits/
  __init__.py      # vacío (marca el paquete)
  __main__.py      # punto de entrada de `python -m habits`
  core.py          # lógica pura: nombres, hábitos, racha
  storage.py       # lectura y escritura del JSON
  cli.py           # argumentos, textos en español, códigos de salida
tests/
  conftest.py
  test_names.py
  test_streak.py
  test_operations.py
  test_storage.py
  test_cli.py
  test_cli_process.py
  test_constitution.py
```

**Regla de dependencias** (verificada por `test_constitution.py`):

```text
__main__ ──► cli ──► core
              └────► storage ──► core
core ──► (solo biblioteca estándar, sin os/sys/json/pathlib)
```

### 2.1 `habits/core.py` — lógica pura

**Tipos**

| Tipo | Contenido | Cubre |
|------|-----------|-------|
| `Habit` (dataclass inmutable) | `name: str` (nombre normalizado) y `marks: frozenset[date]` | RF-1.1, RF-1.4, RF-2.1 |
| `HabitList` | `tuple[Habit, ...]`; el orden de la tupla es el orden de creación | RF-3.1 |
| `HabitStatus` (dataclass inmutable) | `name`, `streak: int`, `done_today: bool`, `has_future_marks: bool` | RF-3.1, RF-4.7 |
| `MarkResult` (dataclass inmutable) | `habits: HabitList`, `habit_name: str` (nombre guardado), `already_marked: bool`, `streak: int`, `has_future_marks: bool` | RF-2.1, RF-2.3, RF-4.7 |
| `NameProblem` (enum) | `EMPTY`, `CONTROL_CHARS`, `LEADING_DASH`, `TOO_LONG` | RF-1.2, RF-1.5, RF-1.6 |
| `MAX_NAME_LENGTH = 100` | constante | RF-1.5 |

**Excepciones** (llevan datos, no texto: los mensajes en español viven en `cli.py`)

| Excepción | Datos | Cubre |
|-----------|-------|-------|
| `HabitError` | base de todas | — |
| `InvalidNameError` | `problem: NameProblem`, `length: int \| None` (solo con `TOO_LONG`) | RF-1.2, RF-1.5, RF-1.6, RF-2.6 |
| `DuplicateHabitError` | `existing_name: str` | RF-1.3 |
| `HabitNotFoundError` | `name: str` (nombre normalizado que se buscó) | RF-2.4 |
| `IncoherentDataError` | `detail: str` | RF-5.3 |

**Funciones públicas**

| Función | Qué hace | Cubre |
|---------|----------|-------|
| `normalize_name(raw) -> str` | Recorta y compacta espacios (sección 4.1) | RF-1.1, RF-2.2 |
| `validate_name(raw) -> str` | Devuelve el nombre normalizado o lanza `InvalidNameError` | RF-1.2, RF-1.5, RF-1.6 |
| `name_key(name) -> str` | Clave de equivalencia (sección 4.2) | RF-1.3, RF-2.2 |
| `find_habit(habits, raw_name) -> Habit \| None` | Busca por nombre equivalente | RF-2.2 |
| `add_habit(habits, raw_name) -> HabitList` | Valida, comprueba duplicado y añade al final | RF-1.1 a RF-1.6 |
| `mark_done(habits, raw_name, today) -> MarkResult` | Marca el hábito en `today` (sección 4.4) | RF-2.1 a RF-2.6 |
| `compute_streak(marks, today) -> int` | Racha actual (sección 4.3) | RF-4.1 a RF-4.6 |
| `has_future_marks(marks, today) -> bool` | Hay alguna marca posterior a `today` | RF-4.7 |
| `summarize(habits, today) -> tuple[HabitStatus, ...]` | Estado de cada hábito para el listado | RF-3.1, RF-4.7 |
| `check_integrity(habits) -> None` | Lanza `IncoherentDataError` si hay nombres inválidos, no normalizados o equivalentes duplicados | RF-5.3 |

### 2.2 `habits/storage.py` — persistencia

| Elemento | Qué hace | Cubre |
|----------|----------|-------|
| `FORMAT_VERSION = 1` | Versión del formato actual | RF-5.4 |
| `default_path() -> Path` | `Path.home() / ".habits-cli" / "habits.json"` | RF-5.6 |
| `load(path) -> HabitList` | Lee, valida estructura y coherencia; archivo ausente = tupla vacía | RF-5.1, RF-5.2, RF-5.3 |
| `save(path, habits) -> None` | Escritura atómica (sección 3.4) | RF-5.1, RF-5.4, RF-5.5 |
| `StorageError` | `problem: StorageProblem` y `detail: str` | RF-5.3, RF-5.5 |
| `StorageProblem` (enum) | `EMPTY`, `UNREADABLE`, `UNKNOWN_VERSION`, `INVALID_STRUCTURE`, `INCOHERENT`, `SAVE_FAILED` | RF-5.3, RF-5.5 |

### 2.3 `habits/cli.py` — interfaz

| Elemento | Qué hace | Cubre |
|----------|----------|-------|
| `main(argv, *, today=None, path=None) -> int` | Orquesta una ejecución y devuelve el código de salida. `today` y `path` solo se inyectan en tests | RF-6.3, CL-24 |
| `parse_args(argv) -> Command` | Interpreta los argumentos a mano (D1) | RF-6.1, RF-6.2, RF-6.4 |
| `Command` (dataclass inmutable) | `kind` (`"crear"`, `"marcar"`, `"listar"`, `"ayuda"`) y `argument: str \| None` | RF-6.1 |
| `UsageError` | Lleva el motivo en español | RF-6.1 |
| `help_text() -> str` | Texto de la ayuda | RF-6.2 |
| `configure_output() -> None` | Hace que stdout y stderr sustituyan los caracteres no representables | RF-6.5 |

### 2.4 `habits/__main__.py`

Llama a `configure_output()` y después a `sys.exit(main(sys.argv[1:]))`. No contiene más lógica. **[RF-6.3, RF-6.5]**

## 3. Modelo de datos JSON

### 3.1 Ubicación **[RF-5.6]**

`~/.habits-cli/habits.json` (en Windows, `C:\Users\<usuario>\.habits-cli\habits.json`). Es la misma desde cualquier carpeta de trabajo. La carpeta se crea solo al guardar, nunca al leer (así `listar` no escribe nada: RF-3.3, RNF-4).

### 3.2 Esquema **[RF-5.4, RF-1.4, RF-3.1]**

| Campo | Tipo | Regla |
|-------|------|-------|
| `version` | entero | Debe ser exactamente `1` |
| `habits` | lista | Orden de creación; puede estar vacía |
| `habits[].name` | texto | Nombre válido **y ya normalizado** (sección 4.1); se guarda tal como lo escribió la persona, salvo los espacios |
| `habits[].marks` | lista de texto | Fechas `AAAA-MM-DD`, sin repetir. Se escriben en orden ascendente; al leer se acepta cualquier orden |

Codificación UTF-8, sangría de 2 espacios y `ensure_ascii` desactivado, para que los acentos y emojis se lean a simple vista.

### 3.3 Ejemplo

```json
{
  "version": 1,
  "habits": [
    {
      "name": "Leer 20 minutos",
      "marks": ["2026-10-21", "2026-10-22", "2026-10-23"]
    },
    {
      "name": "Repasar álgebra",
      "marks": ["2026-10-19", "2026-10-22"]
    },
    {
      "name": "Escribir diario",
      "marks": []
    }
  ]
}
```

Con `today = 2026-10-23`, este archivo produce el listado de la sección 5.4: racha 3 y hecho hoy; racha 1 (ayer sí, anteayer no) y no hecho hoy; racha 0.

### 3.4 Lectura y validación **[RF-5.2, RF-5.3]**

El archivo es **dañado** (`StorageError`, sin tocar nada) en estos casos:

| Situación | `StorageProblem` |
|-----------|------------------|
| El archivo existe pero tiene 0 bytes | `EMPTY` |
| No se puede abrir o leer (permisos, es una carpeta), no es UTF-8 válido o no es JSON válido | `UNREADABLE` |
| `version` ausente, no es entero o distinto de `1` | `UNKNOWN_VERSION` |
| La raíz no es un objeto con solo `version` y `habits`; un hábito no tiene solo `name` (texto) y `marks` (lista de textos) | `INVALID_STRUCTURE` |
| Una fecha no es exactamente `AAAA-MM-DD` o es imposible (por ejemplo `2026-02-30`) | `INCOHERENT` |
| Un hábito repite una fecha | `INCOHERENT` |
| Un nombre no es válido o no está normalizado | `INCOHERENT` (vía `core.check_integrity`) |
| Dos hábitos tienen nombres equivalentes | `INCOHERENT` (vía `core.check_integrity`) |

**Archivo ausente** (`FileNotFoundError`) **no es un error:** devuelve una tupla vacía **[RF-5.2]**. Las marcas con fecha posterior a hoy son válidas y se conservan **[RF-4.6]**. Se rechazan los campos desconocidos en lugar de ignorarlos, porque al volver a guardar se perderían en silencio (D12).

### 3.5 Escritura atómica **[RF-5.1, RF-5.5, RNF-5]**

```text
save(path, habits):
    intentar:
        crear la carpeta padre de path si no existe
        si path existe y no es escribible (os.access W_OK):   # datos de solo lectura
            fallar
        tmp = path + ".tmp"                                    # misma carpeta (RNF-4)
        escribir en tmp el JSON completo (UTF-8), flush y fsync
        os.replace(tmp, path)                                  # atómico
    finalmente:
        borrar tmp si todavía existe                           # interrupción o fallo
    si ocurre cualquier OSError:
        lanzar StorageError(SAVE_FAILED, detalle del sistema)
```

El archivo definitivo solo cambia en el último paso. Si el proceso muere antes (Ctrl+C, corte de energía, disco lleno), `path` conserva su contenido anterior. Un `.tmp` huérfano nunca se lee: el siguiente guardado lo sobrescribe.

## 4. Algoritmos

### 4.1 Normalización y validación del nombre **[RF-1.1, RF-1.2, RF-1.5, RF-1.6, RF-2.6]**

```text
es_espacio(c):  c es tabulador  O  categoría_unicode(c) == "Zs"
                # incluye el espacio, el de no separación y los espacios Unicode;
                # los saltos de línea NO son espacios (glosario de la spec)

normalize_name(raw):
    palabras = separar raw por los caracteres es_espacio, descartando trozos vacíos
    devolver palabras unidas con un único espacio ordinario

es_salto_o_control(c):  categoría_unicode(c) en {"Cc", "Zl", "Zp"}
                        # los de ancho cero (categoría "Cf") NO se rechazan: forman emojis compuestos

validate_name(raw):
    nombre = normalize_name(raw)
    si nombre == "":                               lanzar InvalidNameError(EMPTY)          # RF-1.2
    si algún carácter de nombre es_salto_o_control: lanzar InvalidNameError(CONTROL_CHARS) # RF-1.6
    si nombre empieza por "-":                     lanzar InvalidNameError(LEADING_DASH)   # RF-1.6
    si longitud(nombre) > 100:                     lanzar InvalidNameError(TOO_LONG, longitud(nombre))  # RF-1.5
    devolver nombre
```

La longitud cuenta caracteres Unicode (`len` de Python), tal como decide la spec. Si un nombre incumple varias reglas, se informa de la primera en el orden anterior. Se considera «salto de línea» también a los separadores de línea y de párrafo Unicode (`Zl`, `Zp`): es una interpretación del glosario que conviene confirmar (sección 9, punto 7).

### 4.2 Equivalencia de nombres **[RF-1.3, RF-2.2]**

```text
name_key(nombre):
    s = NFD(normalize_name(nombre))
    devolver NFD(casefold(s))
```

NFD hace idénticas las formas compuestas y combinadas de una letra acentuada (CL-19). `casefold` iguala mayúsculas y minúsculas, incluidas las letras especiales. NFD **conserva** los acentos como marcas separadas, por lo que «Leer» y «Léer» tienen claves distintas (CL-14). Dos nombres son equivalentes si y solo si sus claves son iguales.

### 4.3 Cálculo de la racha **[RF-4.1 a RF-4.6]**

```text
compute_streak(marks, today):
    dias = { d en marks  tal que  d <= today }         # RF-4.6: las marcas futuras no cuentan
    si today en dias:
        cursor = today
    si no, si (today - 1 día) en dias:
        cursor = today - 1 día                          # RF-4.2: la racha se conserva hasta fin de día
    si no:
        devolver 0                                      # RF-4.3 y RF-4.4 (sin marcas, dias está vacío)
    racha = 0
    mientras cursor en dias:
        racha = racha + 1
        si cursor == fecha mínima representable: salir  # evita desbordar la fecha
        cursor = cursor - 1 día
    devolver racha                                      # RF-4.5: el primer hueco detiene el recuento
```

Usa objetos `date` (días naturales) y resta de `timedelta(days=1)`, nunca horas ni marcas de tiempo; por eso el horario de verano, el 29 de febrero y el cambio de mes o año no afectan al resultado **[RF-4.1, CL-11, CL-25]**. El coste es proporcional a la longitud de la racha, no al historial.

`has_future_marks(marks, today)` devuelve verdadero si alguna marca es mayor que `today` **[RF-4.7]**.

### 4.4 Marcar un hábito **[RF-2.1 a RF-2.6]**

```text
mark_done(habits, raw_name, today):
    nombre = normalize_name(raw_name)
    si nombre == "":  lanzar InvalidNameError(EMPTY)                    # RF-2.6 (no "inexistente")
    habito = find_habit(habits, nombre)                                 # RF-2.2
    si habito es nada: lanzar HabitNotFoundError(nombre)                # RF-2.4
    si today en habito.marks:                                           # RF-2.3
        devolver MarkResult(habits sin cambios, habito.name, already_marked=verdadero,
                            racha de habito, has_future_marks)
    nuevo = habito con marks ∪ {today}                                  # RF-2.1; RF-2.5: solo today
    devolver MarkResult(habits con nuevo en el lugar de habito, habito.name,
                        already_marked=falso, racha de nuevo, has_future_marks)
```

`mark_done` no recibe ninguna fecha elegida por la persona: solo `today`. Por eso la herramienta no ofrece forma de marcar otros días **[RF-2.5]**. Al marcar solo se exige que el nombre no esté vacío; los demás incumplimientos de nombre simplemente no coinciden con ningún hábito y dan «no existe».

### 4.5 Añadir un hábito **[RF-1.1 a RF-1.6]**

```text
add_habit(habits, raw_name):
    nombre = validate_name(raw_name)                    # lanza EMPTY / CONTROL_CHARS / LEADING_DASH / TOO_LONG
    existente = find_habit(habits, nombre)
    si existente: lanzar DuplicateHabitError(existente.name)   # RF-1.3: se cita el nombre guardado
    devolver habits + (Habit(nombre, marks vacío),)             # al final: orden de creación
```

### 4.6 Resumen para el listado **[RF-3.1, RF-4.7]**

```text
summarize(habits, today):
    por cada habito, en orden:
        HabitStatus(habito.name,
                    compute_streak(habito.marks, today),
                    today en habito.marks,                      # las marcas futuras no cuentan (RF-4.6)
                    has_future_marks(habito.marks, today))
```

### 4.7 Flujo de una ejecución **[RF-3.3, RF-5.5, RF-6.3, CL-24]**

```text
main(argv, today, path):
    today = today o fecha local de hoy                          # una sola vez por ejecución (CL-24)
    path  = path o storage.default_path()
    comando = parse_args(argv)                                  # UsageError → mensaje + ayuda a stderr, devolver 2
    si comando es ayuda: escribir ayuda en stdout, devolver 0
    intentar:
        habits = storage.load(path)                             # StorageError → devolver 1 (nada se modifica)
        según comando:
            crear:  nuevos = core.add_habit(habits, arg)
                    storage.save(path, nuevos)                  # si falla, no hay confirmación (RF-5.5)
                    escribir confirmación en stdout
            marcar: resultado = core.mark_done(habits, arg, today)
                    si no resultado.already_marked: storage.save(path, resultado.habits)
                    escribir confirmación o aviso en stdout
                    si resultado.has_future_marks: escribir aviso RF-4.7 en stderr
            listar: estados = core.summarize(habits, today)     # nunca guarda
                    escribir listado en stdout (o el mensaje de lista vacía)
                    por cada estado con has_future_marks: aviso RF-4.7 en stderr
    capturar core.HabitError o StorageError: escribir el error en stderr, devolver 1
    devolver 0
```

La confirmación se escribe **después** de guardar: si `save` falla, la persona nunca ve un «creado» falso **[RF-5.5]**. `listar` y `marcar` sobre un hábito ya marcado no llaman a `save`, por lo que no tocan el disco **[RF-3.3, RF-2.3]**.

## 5. Contrato de la CLI

Invocación: `python -m habits <comando> [argumentos]`.

### 5.1 Comandos **[RF-6.4]**

| Comando | Argumentos | Qué hace | Cubre |
|---------|-----------|----------|-------|
| `crear <nombre>` | Exactamente uno | Crea un hábito | RF-1.1 a RF-1.6 |
| `marcar <nombre>` | Exactamente uno | Marca el hábito como hecho hoy | RF-2.1 a RF-2.6 |
| `listar` | Ninguno | Muestra los hábitos con su racha | RF-3.1 a RF-3.3 |
| `-h`, `--ayuda` | — | Muestra la ayuda | RF-6.2 |

Reglas de interpretación **[RF-6.1, RF-6.2]**:
- Si cualquier argumento es `-h` o `--ayuda`, se muestra la ayuda y se termina con 0, sea cual sea el resto.
- El primer argumento es el comando; el segundo, el nombre. Un nombre con espacios debe ir entre comillas.
- Un argumento vacío (`crear ""`) cuenta como argumento presente: llega a la validación del nombre (RF-1.2 o RF-2.6), no es un error de uso.
- Un nombre que empieza por «-» (`crear -x`) se interpreta como nombre y lo rechaza la validación (RF-1.6). No existe ninguna otra opción.

### 5.2 Códigos de salida **[RF-6.3]**

| Código | Significado | Ejemplos |
|--------|-------------|----------|
| `0` | La operación se completó | Creado, marcado, «ya estaba marcado», listado (también vacío), ayuda |
| `1` | Error de la operación | Nombre inválido o duplicado, hábito inexistente, datos dañados, fallo al guardar |
| `2` | Uso incorrecto | Sin comando, comando desconocido, falta o sobra un argumento |

### 5.3 Salidas por canal **[RF-6.6]**

| Canal | Contenido |
|-------|-----------|
| Salida estándar | Confirmaciones, el aviso «ya estaba marcado» (RF-2.3), el listado, el mensaje de lista vacía y la ayuda pedida con `-h`/`--ayuda` |
| Salida de error | Errores, mensajes de uso incorrecto (con la ayuda) y el aviso de fecha del equipo (RF-4.7) |

### 5.4 Textos exactos

Los textos son parte del contrato: las pruebas los comprueban literalmente (RNF-1). `«…»` rodea el nombre del hábito tal como está guardado.

**Salida estándar, código 0**

| Situación | Texto | RF |
|-----------|-------|----|
| `crear` correcto | `Hábito «Leer 20 minutos» creado.` | RF-1.1 |
| `marcar` correcto | `Hábito «Leer 20 minutos» marcado hoy. Racha: 3 días.` | RF-2.1 |
| `marcar` ya marcado | `El hábito «Leer 20 minutos» ya estaba marcado hoy. Racha: 3 días.` | RF-2.3 |
| `listar` con hábitos | Primera línea `Tus hábitos:` y, por cada hábito en orden de creación, `- {nombre} \| racha: {n} {día\|días} \| hoy: {sí\|no}` | RF-3.1 |
| `listar` sin hábitos | `Aún no tienes hábitos. Crea el primero con: python -m habits crear "Leer 20 minutos"` | RF-3.2 |

«día» se usa si la racha es 1; «días» en cualquier otro caso, incluido 0 (`1 día`, `0 días`, `3 días`).

Ejemplo de `listar` con el archivo de la sección 3.3 y `today = 2026-10-23`:

```text
Tus hábitos:
- Leer 20 minutos | racha: 3 días | hoy: sí
- Repasar álgebra | racha: 1 día | hoy: no
- Escribir diario | racha: 0 días | hoy: no
```

**Salida de error, código 1** (cada uno indica qué falló y qué hacer, RNF-7)

| Situación | Texto | RF |
|-----------|-------|----|
| Nombre vacío (`crear` o `marcar`) | `Error: el nombre del hábito está vacío. Escribe al menos un carácter, por ejemplo: crear "Leer".` | RF-1.2, RF-2.6 |
| Caracteres de control | `Error: el nombre contiene caracteres de control (como saltos de línea). Escríbelo en una sola línea.` | RF-1.6 |
| Empieza por «-» | `Error: el nombre no puede empezar por «-». Empieza por una letra o un número.` | RF-1.6 |
| Más de 100 caracteres | `Error: el nombre tiene {n} caracteres y el máximo es 100. Acórtalo.` | RF-1.5 |
| Duplicado | `Error: ya existe el hábito «{guardado}» (los nombres no distinguen mayúsculas ni espacios de más). Elige otro nombre.` | RF-1.3 |
| Hábito inexistente | `Error: no existe ningún hábito llamado «{nombre}». Usa «listar» para ver tus hábitos.` | RF-2.4 |
| Datos dañados | `Error: los datos guardados están dañados ({motivo}). No se ha modificado nada. Repara o aparta manualmente el archivo «{ruta}» y vuelve a intentarlo.` | RF-5.3 |
| No se pudo guardar | `Error: no se pudo guardar ({detalle del sistema}). Tus datos anteriores siguen intactos. Revisa el espacio en disco y los permisos de «{ruta}».` | RF-5.5 |

`{motivo}` depende de `StorageProblem`: `el archivo está vacío`, `no se puede leer`, `versión de formato desconocida`, `estructura no válida` o `contenido incoherente: {detalle}`.

**Salida de error, código 2** (uso incorrecto; después del error se imprime la ayuda completa, que incluye el uso correcto)

| Situación | Primera línea | RF |
|-----------|---------------|----|
| Sin comando | `Error: falta el comando.` | RF-6.1 |
| Comando desconocido | `Error: comando desconocido «{comando}».` | RF-6.1 |
| Falta el nombre | `Error: el comando «{comando}» necesita un nombre.` | RF-6.1 |
| Sobran argumentos en `crear` o `marcar` | `Error: el comando «{comando}» recibió argumentos de más: {lista}. Si el nombre tiene espacios, escríbelo entre comillas.` | RF-6.1 |
| Sobran argumentos en `listar` | `Error: el comando «listar» no admite argumentos.` | RF-6.1 |

**Aviso de fecha (salida de error, no cambia el código de salida)** **[RF-4.7]**

`Aviso: la fecha del equipo parece anterior a alguna marca de «{nombre}» (última marca: {AAAA-MM-DD}). Esas marcas se ignoran hasta que la fecha del equipo las alcance.`

**Ayuda** (con `-h`/`--ayuda` sale por la salida estándar y termina con 0; tras un error de uso, la misma ayuda sale por la salida de error) **[RF-6.2]**

```text
Uso: python -m habits <comando> [argumentos]

Comandos:
  crear <nombre>    Crea un hábito nuevo.
  marcar <nombre>   Marca un hábito como hecho hoy.
  listar            Muestra tus hábitos con su racha.

Opciones:
  -h, --ayuda       Muestra esta ayuda.

Si el nombre tiene espacios, escríbelo entre comillas.
```

### 5.5 Caracteres que la consola no puede mostrar **[RF-6.5]**

`configure_output()` reconfigura stdout y stderr para que los caracteres no representables se escriban como marcador (`?`) en lugar de lanzar un error. Solo afecta a lo que se muestra: los datos guardados no cambian. Se aplica en `__main__.py`, no dentro de `main`, para no alterar los flujos de las pruebas.

## 6. Decisiones técnicas

| # | Decisión | Justificación | Alternativa descartada | Cubre |
|---|----------|---------------|------------------------|-------|
| D1 | Interpretar los argumentos a mano en `parse_args` | La ayuda y los errores salen 100 % en español sin personalizar nada; no hay abreviaturas de opciones; un nombre que empieza por «-» llega a la validación en vez de ser tratado como opción. Son unas decenas de líneas fáciles de leer | `argparse`: sus textos de ayuda y error son en inglés por defecto, habría que sobrescribir cada uno y se arriesga RNF-1; además interpreta «-x» como opción | RF-6.1, RF-6.2, RF-1.6, RNF-1 |
| D2 | `core` con dataclasses inmutables y funciones que devuelven datos nuevos | Cada función se prueba con entradas y salidas, sin estado oculto; coincide con el principio 3 | Clases con métodos que mutan su estado: más cortas, pero cada prueba exige preparar y comparar estado | RF-1 a RF-4 |
| D3 | Fechas como `datetime.date` (días naturales), no como instantes | El horario de verano y los 29 de febrero desaparecen del problema | Guardar y comparar `datetime` o marcas de tiempo: obliga a convertir a día local en cada cálculo | RF-4.1, CL-25 |
| D4 | Derivar la racha de las marcas cada vez; no guardarla | Un dato derivado guardado puede quedar desfasado (nuevo día, reloj atrasado); así `hoy` siempre se aplica al momento de ejecutar | Guardar `streak` y `last_mark` en el JSON: lectura más rápida, pero contradice RF-4.2 y RF-4.6 sin lógica extra | RF-4.1 a RF-4.6 |
| D5 | Un solo archivo en `~/.habits-cli/habits.json`, bajo la carpeta del usuario | Cumple RF-5.6 con una línea; es multiplataforma | Carpetas del sistema (`%APPDATA%`, `XDG_*`): más «correcto», pero exige código por plataforma. Carpeta de trabajo: incumple RF-5.6 | RF-5.6 |
| D6 | Guardar escribiendo un temporal y haciendo `os.replace` | El reemplazo es atómico en Windows y Linux; una interrupción deja intacto el archivo anterior | Escribir directamente sobre el archivo: una interrupción lo deja truncado | RF-5.5, RNF-5 |
| D7 | Clave de equivalencia = NFD + `casefold` + NFD | Cubre las formas compuestas y combinadas, las letras especiales y deja que los acentos distingan | `lower()`: falla con letras especiales y formas combinadas. Quitar los acentos: contradice la spec | RF-1.3, RF-2.2 |
| D8 | Los errores del `core` son excepciones con datos; los textos están en `cli.py` | El `core` queda sin idioma ni presentación (principios 3 y 6); un cambio de redacción no toca la lógica | Excepciones con el mensaje en español dentro de `core`: mezcla lógica y presentación. Valores de retorno de error: se ignoran con facilidad | RF-1.x, RF-2.x |
| D9 | Códigos de salida 0 / 1 / 2 | Separar «uso incorrecto» (2) de «la operación falló» (1) es la convención habitual en terminal y permite que otros programas distingan | Un único código distinto de cero: cumple la spec pero da menos información | RF-6.3 |
| D10 | Sustituir los caracteres no representables (`errors="replace"`) | La consola de Windows suele tener una codificación limitada; la spec pide no fallar | Forzar UTF-8 en la consola: se ven caracteres corruptos. No hacer nada: trazas técnicas | RF-6.5 |
| D11 | Reescribir el archivo completo en cada operación que cambia datos | Con 100 hábitos y 5 años de marcas son unos cientos de KB; es lo más simple y se combina con D6 | Añadir líneas a un registro: más rápido, pero exige compactar y complica la validación | RF-5.1, RNF-2 |
| D12 | Validación estricta de la lectura: se rechazan campos desconocidos, fechas no canónicas, marcas repetidas y archivos vacíos | Reescribir un archivo con campos desconocidos los perdería sin aviso; la spec pide tratar lo incoherente como dañado | Ignorar lo desconocido o reparar solo: oculta problemas y puede perder datos | RF-5.3 |
| D13 | `version` entera con valor 1; una versión mayor es un error | Es lo mínimo que exige RF-5.4 y deja abierta una futura migración | Sin versión: contradice RF-5.4 | RF-5.4 |
| D14 | Sin bloqueo de archivo | Fuera del MVP por la spec | Archivo de bloqueo o `msvcrt`/`fcntl`: dependiente de plataforma | RNF-8 |
| D15 | «Hoy» se lee una sola vez en `main` y se pasa a `core` | Evita que una ejecución use dos fechas si cruza la medianoche; coincide con el principio 3 | Leer la fecha dentro de cada función: rompe la pureza de `core` y CL-24 | CL-24 |
| D16 | `main` recibe `today` y `path` opcionales | Permite probar sin tocar el reloj ni el disco real, sin variables de entorno ocultas | Variable de entorno para la ruta: comportamiento extra no pedido por la spec | RNF-6 |

## 7. Estrategia de tests

Todo se ejecuta con `pytest -q`. Ninguna prueba toca el `~/.habits-cli` real: usan `tmp_path`.

### 7.1 Niveles

| Nivel | Archivo | Qué comprueba | Cómo |
|-------|---------|---------------|------|
| Unitario puro | `test_names.py`, `test_streak.py`, `test_operations.py` | `core` completo, sin disco ni reloj | Funciones con `today` fijo (`2026-10-23`) y tablas `@pytest.mark.parametrize` |
| Persistencia | `test_storage.py` | Lectura, validación y guardado atómico | `tmp_path`; fallos simulados con `monkeypatch` (`os.replace`, `os.fsync`, `os.access`) |
| CLI en proceso | `test_cli.py` | Textos, canales y códigos de salida | `main([...], today=…, path=…)` con `capsys`; se comparan los textos literales de la sección 5.4 |
| CLI en proceso hijo | `test_cli_process.py` | Punto de entrada real, persistencia entre ejecuciones, redirección de canales, carpetas distintas, codificación, tiempo | `subprocess.run([sys.executable, "-m", "habits", ...])` con `PYTHONPATH` al proyecto y carpeta de usuario falsa en `tmp_path` |
| Constitución | `test_constitution.py` | Principios 1, 3 y 5 de forma automática | Análisis del código fuente con `ast` y `sys.stdlib_module_names`, sin ejecutar nada |

`conftest.py` ofrece: `TODAY = date(2026, 10, 23)`, un fixture `data_path` (`tmp_path / "habits.json"`) y una función auxiliar que escribe un JSON de datos de prueba.

### 7.2 Pruebas de la constitución (`test_constitution.py`)

| Principio | Comprobación |
|-----------|--------------|
| 1 | Todo `import` de `habits/` está en `sys.stdlib_module_names` o es del propio paquete; los tests solo añaden `pytest` |
| 3 | `core.py` no importa `os`, `sys`, `json`, `pathlib` ni `io`; no llama a `print`, `open` ni `input`; no usa `date.today` ni `datetime.now` |
| 3 | `cli.py` no importa `json` |
| 5 | `json` solo se importa en `storage.py` |

### 7.3 Funciones públicas de `core.py` y su test (principio 4)

| Función | Archivo y casos mínimos |
|---------|------------------------|
| `normalize_name` | `test_names.py`: bordes, espacios internos repetidos, tabuladores, espacio de no separación, solo espacios |
| `validate_name` | `test_names.py`: vacío, salto de línea, `\x00`, separador de línea Unicode, «-x», 100 válido, 101 inválido, 100 con espacios de borde, emoji compuesto (ancho cero) válido |
| `name_key` | `test_names.py`: mayúsculas, «é» compuesta frente a combinada (CL-19), «Léer» ≠ «Leer», letras especiales |
| `find_habit` | `test_operations.py`: coincide por equivalencia, no coincide, lista vacía |
| `add_habit` | `test_operations.py`: orden de creación, duplicado equivalente (CL-1, CL-14), nombre guardado conserva mayúsculas y emojis (RF-1.4), más de 100 hábitos (CL-27) |
| `mark_done` | `test_operations.py`: marca nueva, ya marcada sin cambiar nada, inexistente, nombre vacío, marca solo `today` |
| `compute_streak` | `test_streak.py`: tabla de la sección 7.4 |
| `has_future_marks` | `test_streak.py`: con y sin marcas futuras |
| `summarize` | `test_operations.py`: orden, `done_today`, racha, marcas futuras no cuentan |
| `check_integrity` | `test_operations.py`: nombre sin normalizar, nombre inválido, equivalentes duplicados, lista válida |

### 7.4 Tabla de la racha (`test_streak.py`) **[RF-4.1 a RF-4.6]**

Con `today = 2026-10-23`:

| Marcas | Racha | Caso |
|--------|-------|------|
| ninguna | 0 | RF-4.4 |
| 23 | 1 | hoy |
| 22 | 1 | RF-4.2 |
| 22, 21, 20 | 3 | CL-5 |
| 20, 21 | 0 | CL-6 |
| 23, 21 | 1 | CL-7, RF-4.5 |
| 23, 22, 20 | 2 | hueco |
| 22, 23, 24, 25 | 2 | RF-4.6, CL-15 |
| 24, 25 | 0 | solo futuras |
| 2026-02-27, 2026-02-28, 2026-03-01 con `today = 2026-03-01` | 3 | cambio de mes |
| 2024-02-28, 2024-02-29, 2024-03-01 con `today = 2024-03-01` | 3 | 29 de febrero, CL-25 |
| 2025-12-30, 2025-12-31, 2026-01-01 con `today = 2026-01-01` | 3 | cambio de año, CL-11 |
| marcas que alcanzan `date.min` | sin error | desbordamiento |
| 2026-10-21 y 2026-10-22 con `today = 2026-10-24` | 0 | RF-4.3: ayer sin marca |
| lunes y martes con `today` = miércoles | 2 | CL-8 |

### 7.5 Trazabilidad de casos límite y no funcionales

| CL | Dónde se prueba |
|----|-----------------|
| CL-1, CL-14, CL-19 | `test_operations.py` (`add_habit`) y `test_cli.py` |
| CL-2, CL-17, CL-18, CL-13, CL-12 | `test_names.py` y `test_cli.py` |
| CL-3, CL-4 | `test_operations.py` y `test_cli.py` |
| CL-5, CL-6, CL-7, CL-8, CL-11, CL-25 | `test_streak.py` |
| CL-9 | `test_storage.py` (archivo ausente) y `test_cli.py` |
| CL-10, CL-23 | `test_storage.py` (una prueba por motivo de la sección 3.4) y `test_cli.py` (texto y código 1, archivo sin cambios) |
| CL-15, CL-26 | `test_streak.py`, `test_cli.py` (aviso en stderr) |
| CL-16 | Revisión documentada (según el criterio 8.2 de la spec); la cubre en parte la prueba de CL-15 |
| CL-20, CL-21 | `test_cli.py` |
| CL-22 | `test_storage.py` (`os.replace` y `os.access` simulados) y `test_cli.py` |
| CL-24 | `test_cli.py`: se inyecta `today`; una prueba comprueba que `main` lo lee una sola vez |
| CL-27 | `test_operations.py` (101 hábitos) |
| CL-28 | Revisión documentada según la spec; además se automatiza en `test_cli_process.py` con `PYTHONIOENCODING=cp1252` y un nombre con emoji |
| CL-29 | Revisión documentada (limitación declarada, RNF-8) |
| CL-30 | `test_cli_process.py`: dos carpetas de trabajo distintas, misma carpeta de usuario |
| CL-31 | `test_cli_process.py`: redirección de stdout; el archivo no contiene errores ni avisos |

| RNF | Verificación |
|-----|--------------|
| RNF-1 | Comparación literal de todos los textos de la sección 5.4 en `test_cli.py` |
| RNF-2 | `test_cli_process.py`: 100 hábitos × 1 826 marcas; `listar`, `marcar` y `crear` terminan en menos de 1 s (mejor de 3 intentos con datos nuevos, para descartar el ruido puntual del equipo) |
| RNF-3 | `test_constitution.py`: ningún módulo de red importado (`socket`, `urllib`, `http`, `ssl`) |
| RNF-4 | Revisión documentada (spec) más la comprobación anterior; la escritura se limita a la carpeta de datos (sección 3.5) |
| RNF-5 | `test_storage.py`: `os.replace` y `os.fsync` fallan o se interrumpen (`KeyboardInterrupt`); el archivo anterior queda intacto y el temporal se borra |
| RNF-6 | Esta estrategia |
| RNF-7 | `test_cli.py`: cada error de la lista de RNF-7 contiene su sugerencia (textos de la sección 5.4) |
| RNF-8 | Revisión documentada (spec) |

### 7.6 Regresiones

Todo bug corregido añade un test con el nombre `test_regression_<descripción>` en el archivo del módulo afectado (principio 4).

## 8. Matriz de cobertura de RF

| RF | Diseño (sección y módulo) | Prueba principal |
|----|---------------------------|------------------|
| RF-1.1 | 4.5 `add_habit`, 3.2 `habits[].name`; 5.4 `Hábito «…» creado.` | `test_operations`, `test_cli` |
| RF-1.2 | 4.1 `validate_name` (`EMPTY`); 5.4 error 1 | `test_names`, `test_cli` |
| RF-1.3 | 4.2 `name_key`, 4.5; 5.4 duplicado | `test_operations`, `test_cli` |
| RF-1.4 | 4.1 (solo cambian los espacios); 3.2 | `test_names`, `test_operations` |
| RF-1.5 | 4.1 `TOO_LONG`; 5.4 | `test_names`, `test_cli` |
| RF-1.6 | 4.1 `CONTROL_CHARS`, `LEADING_DASH`; 5.1 | `test_names`, `test_cli` |
| RF-2.1 | 4.4 `mark_done`; 5.4 | `test_operations`, `test_cli` |
| RF-2.2 | 4.2 `name_key`, `find_habit` | `test_operations` |
| RF-2.3 | 4.4, 4.7 (no se llama a `save`); 5.4 | `test_operations`, `test_cli` |
| RF-2.4 | 4.4 `HabitNotFoundError`; 5.4 | `test_operations`, `test_cli` |
| RF-2.5 | 4.4 (`mark_done` solo recibe `today`); 5.1 (sin opción de fecha) | `test_operations`, `test_cli` |
| RF-2.6 | 4.4 (nombre vacío antes de buscar); 5.4 | `test_operations`, `test_cli` |
| RF-3.1 | 4.6 `summarize`; 5.4 listado | `test_operations`, `test_cli` |
| RF-3.2 | 4.7; 5.4 lista vacía | `test_cli` |
| RF-3.3 | 4.7 (`listar` nunca guarda); 3.1 | `test_cli` (archivo y carpeta intactos) |
| RF-4.1 | 4.3 (`date`, días naturales) | `test_streak` |
| RF-4.2 | 4.3 (rama de `ayer`) | `test_streak` |
| RF-4.3 | 4.3 (rama `devolver 0`) | `test_streak` |
| RF-4.4 | 4.3 | `test_streak` |
| RF-4.5 | 4.3 (el primer hueco detiene el bucle) | `test_streak` |
| RF-4.6 | 4.3 (`d <= today`); 3.4 (se conservan) | `test_streak`, `test_storage` |
| RF-4.7 | 4.3 `has_future_marks`, 4.7; 5.4 aviso | `test_cli`, `test_cli_process` |
| RF-5.1 | 3.5, 4.7 (`save` tras cada cambio) | `test_storage`, `test_cli_process` |
| RF-5.2 | 3.4 (archivo ausente) | `test_storage`, `test_cli` |
| RF-5.3 | 3.4 (tabla de motivos); `core.check_integrity`; 5.4 | `test_storage`, `test_cli` |
| RF-5.4 | 3.2 `version`; D13 | `test_storage` |
| RF-5.5 | 3.5, 4.7 (confirmación después de guardar) | `test_storage`, `test_cli` |
| RF-5.6 | 3.1 `default_path`; D5 | `test_cli_process` |
| RF-6.1 | 2.3 `parse_args`; 5.1; 5.4 (código 2) | `test_cli` |
| RF-6.2 | 2.3 `help_text`; 5.4 ayuda | `test_cli` |
| RF-6.3 | 5.2 | `test_cli`, `test_cli_process` |
| RF-6.4 | 5.1 | `test_cli` |
| RF-6.5 | 5.5 `configure_output`; D10 | `test_cli_process` |
| RF-6.6 | 5.3 | `test_cli_process` |

## 9. Puntos a confirmar

Aquí queda lo que el plan no puede resolver sin una decisión de la persona dueña del proyecto o sin cambiar un documento que este plan no modifica.

1. **Principio 5 y el archivo temporal.** La constitución pide «un único archivo JSON». El guardado atómico (D6) crea `habits.json.tmp` solo durante la escritura. El archivo de datos sigue siendo uno solo, pero conviene aclararlo en el principio.
2. **Principio 5 y dónde se define el formato.** La constitución y `AGENTS.md` dicen «actualizar la spec» al cambiar el formato. La spec (RF-5.4) delega el formato en el plan, por lo que esta frase debería decir «spec o plan».
3. **Principio 6 y los nombres de los comandos.** Este plan los trata como texto de la interfaz, en español (RF-6.4), y los identificadores del código en inglés. La constitución no lo dice expresamente.
4. **Principio 3 y la orquestación.** `cli.py` también llama a `storage` y decide los códigos de salida (sección 4.7). Se entiende que forma parte de «leer argumentos y mostrar resultados»; la alternativa de un módulo intermedio se descartó para no añadir un cuarto módulo.
5. **Principio 4 y el alcance de los tests.** La constitución exige tests para `core.py`; la spec exige además pruebas de persistencia, CLI y códigos de salida. Este plan las incluye; la constitución no las menciona.
6. **Estado de la spec.** Aprobada el 2026-10-23. Resuelto.
7. **Interpretación del glosario.** Se tratan como saltos de línea, además de los caracteres de control, los separadores de línea y de párrafo Unicode (`Zl`, `Zp`). La spec solo dice «caracteres de control (como saltos de línea)»; si se quiere otra regla, la spec debe precisarlo.
8. **Carpeta personal indeterminable.** Si el sistema no puede determinar la carpeta del usuario, `default_path()` falla. Se propone tratarlo como un error de datos (`UNREADABLE`) con el mismo mensaje de la sección 5.4; la spec no lo contempla.
9. **Interrupción con el teclado.** La spec exige integridad (RNF-5), no un mensaje. Una interrupción mostrará la traza normal de Python; el plan no define un mensaje en español para ese caso.
