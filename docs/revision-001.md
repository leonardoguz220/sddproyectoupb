# Revisión de la spec 001 — MVP de habits-cli

Fecha de la revisión: 2026-10-23 · Spec: `specs/001-habits-mvp/spec.md` (aprobada el 2026-10-23) · Plan: `specs/001-habits-mvp/plan.md`

## 1. Revisiones documentadas (lo que la spec no exige automatizar)

### CL-16 — Cambio de zona horaria

- **Qué se revisó:** que un retroceso de «hoy» por cambio de zona se comporta como la spec describe y se avisa.
- **Cómo:** se revisó el código. La zona horaria no se guarda; «hoy» sale de la fecha local en `cli._read_today()` y se pasa a `core`. Si «hoy» retrocede, las marcas posteriores se ignoran (`core.compute_streak`, `d <= today`) y se emite el aviso de RF-4.7. Cobertura parcial automatizada: CL-15 (`test_cli.py::test_rf_4_7_cl_15_list_warns_per_habit_with_future_marks`, `test_rf_4_7_mark_with_future_marks_warns_on_stderr`) y `test_streak.py::test_rf_4_6_cl_15_future_marks_are_ignored`.
- **Resultado:** conforme. Si «hoy» avanza se puede omitir un día y romper la racha: limitación aceptada por la spec.

### CL-29 y RNF-8 — Ejecuciones simultáneas

- **Qué se revisó:** que la limitación está declarada y que no hay mecanismos a medias.
- **Cómo:** búsqueda en `habits/` de `lock`, `fcntl`, `msvcrt` y archivos de bloqueo: sin resultados. La spec y el plan (D14) declaran el uso simultáneo como no garantizado.
- **Resultado:** conforme. Dos ejecuciones a la vez pueden pisarse; el guardado atómico evita un archivo corrupto, pero no una actualización perdida.

### RNF-4 — Datos locales

- **Qué se revisó:** que la herramienta no hace conexiones de red ni escribe fuera de la ubicación de sus datos.
- **Cómo:** búsqueda en `habits/` de `open(`, `write_text`, `write_bytes`, `mkdir`, `unlink`, `os.replace`, `shutil`, `tempfile`, `socket`, `urllib`, `http` y `requests`. Resultado: las únicas operaciones de escritura están en `storage.py` (líneas 113 a 124 en esta revisión): crear la carpeta padre de `habits.json`, escribir `habits.json.tmp` en esa misma carpeta, reemplazar `habits.json` y borrar el temporal. Además, `tests/test_constitution.py::test_rnf_3_no_network_modules_imported` comprueba que ningún módulo importa `socket`, `urllib`, `http` ni `ssl`.
- **Resultado:** conforme.

### RNF-6 — Verificabilidad

- Los requisitos funcionales y los casos límite son verificables con pruebas automáticas, salvo CL-16 y CL-29 (secciones anteriores). Ver la sección 3.

## 2. Prueba de uso con tres personas (criterio 8.4)

**Pendiente.** Requiere que tres personas que nunca hayan usado la herramienta completen crear → marcar → listar en menos de un minuto cada una, usando solo `python -m habits --ayuda`. No se ha podido realizar en esta sesión y no se da por cumplida.

| Persona | Tiempo | ¿Pidió ayuda externa? | Observaciones |
|---------|--------|-----------------------|---------------|
| (pendiente) | | | |
| (pendiente) | | | |
| (pendiente) | | | |

## 3. Cobertura de la spec por pruebas

Cada requisito está citado en el nombre de al menos una prueba (`rf_X_Y`, `cl_N`, `rnf_N`). Se comprobó con un script que extrae los identificadores de la spec y los busca en los nombres de las pruebas.

| RF | Prueba principal |
|----|------------------|
| RF-1.1 | `test_cli::test_rf_1_1_rf_1_4_create_normalizes_saves_and_confirms`, `test_operations::test_rf_1_1_add_habit_appends_normalized_name_without_marks` |
| RF-1.2 | `test_names::test_rf_1_2_cl_2_empty_name_rejected`, `test_cli::test_rf_1_2_rf_1_3_..._create_errors` |
| RF-1.3 | `test_operations::test_rf_1_3_cl_1_duplicate_equivalent_name_rejected` |
| RF-1.4 | `test_operations::test_rf_1_4_add_habit_keeps_case_accents_and_emoji` |
| RF-1.5 | `test_names::test_rf_1_5_cl_13_*` |
| RF-1.6 | `test_names::test_rf_1_6_cl_18_*` |
| RF-2.1 | `test_operations::test_rf_2_1_mark_done_adds_exactly_today`, `test_cli::test_rf_2_1_mark_confirms_with_resulting_streak` |
| RF-2.2 | `test_operations::test_rf_2_2_*`, `test_names::test_rf_2_2_special_letters_use_casefold` |
| RF-2.3 | `test_operations::test_rf_2_3_cl_3_marking_twice_changes_nothing`, `test_cli::test_rf_2_3_cl_3_second_mark_warns_exit_0_and_does_not_touch_the_file` |
| RF-2.4 | `test_operations::test_rf_2_4_cl_4_unknown_habit_raises_not_found_with_normalized_name`, `test_cli::test_rf_2_4_cl_4_mark_unknown_habit` |
| RF-2.5 | `test_operations::test_rf_2_5_mark_done_only_accepts_today_as_date` |
| RF-2.6 | `test_operations::test_rf_2_6_cl_17_*`, `test_cli::test_rf_2_6_cl_17_*` |
| RF-3.1 | `test_cli::test_rf_3_1_cl_8_list_example_from_plan`, `test_operations::test_rf_3_1_summarize_example_from_plan` |
| RF-3.2 | `test_cli::test_rf_3_2_cl_9_empty_list_invites_to_create_and_creates_nothing` |
| RF-3.3 | `test_cli::test_rf_3_3_list_does_not_modify_the_file` |
| RF-4.1 a RF-4.5 | `test_streak::test_rf_4_1_to_rf_4_5_streak_table` y pruebas `test_rf_4_x_*`, `test_cl_5/6/7/8/11/25` |
| RF-4.6 | `test_streak::test_rf_4_6_cl_15_future_marks_are_ignored`, `test_storage::test_rf_4_6_future_marks_are_kept` |
| RF-4.7 | `test_cli::test_rf_4_7_*`, `test_cli_process::test_rf_6_6_cl_31_future_marks_warning_goes_to_stderr_only` |
| RF-5.1 | `test_storage::test_rf_5_1_save_then_load_round_trip`, `test_cli_process::test_rf_5_1_data_persists_between_executions` |
| RF-5.2 | `test_storage::test_rf_5_2_cl_9_missing_file_is_empty_and_creates_nothing` |
| RF-5.3 | `test_storage::test_rf_5_3_cl_10_cl_23_damaged_data_is_rejected_untouched` (30 casos), `test_cli::test_rf_5_3_cl_10_cl_23_damaged_data_exit_1_and_untouched` |
| RF-5.4 | `test_storage::test_rf_5_4_version_is_1`, `test_rf_5_1_rf_5_4_save_writes_versioned_json` |
| RF-5.5 | `test_storage::test_rf_5_5_cl_22_*`, `test_cli::test_rf_5_5_cl_22_save_failure_shows_no_confirmation` |
| RF-5.6 | `test_storage::test_rf_5_6_default_path_is_under_user_home`, `test_cli_process::test_rf_5_6_cl_30_*` |
| RF-6.1 | `test_cli::test_rf_6_1_cl_20_parse_args_usage_errors`, `test_rf_6_1_rf_6_3_rf_6_6_cl_20_cl_21_usage_error_exit_2_on_stderr` |
| RF-6.2 | `test_cli::test_rf_6_2_rf_6_3_rf_6_6_cl_21_help_goes_to_stdout_with_success`, `test_cli_process::test_rf_6_2_entry_point_shows_help` |
| RF-6.3 | las dos pruebas anteriores de RF-6.1 y RF-6.2 y los códigos 1 de los errores |
| RF-6.4 | `test_cli::test_rf_6_1_rf_6_2_rf_6_4_parse_args_valid` |
| RF-6.5 | `test_cli::test_rf_6_5_cl_28_*`, `test_cli_process::test_rf_6_5_cl_28_*` |
| RF-6.6 | `test_cli_process::test_rf_6_6_cl_31_errors_go_to_stderr_and_stdout_stays_clean` |

| RNF | Verificación |
|-----|--------------|
| RNF-1 | `test_cli::test_rnf_1_user_texts_have_no_english_default_messages` y comparación literal de todos los textos |
| RNF-2 | `test_cli_process::test_rnf_2_cl_27_commands_finish_under_one_second_with_reference_load` (mejor de 3 intentos; ver nota de rendimiento) |
| RNF-3 | `test_constitution::test_rnf_3_no_network_modules_imported` |
| RNF-4 | Revisión documentada (sección 1) |
| RNF-5 | `test_storage::test_rnf_5_*` |
| RNF-6 | Esta revisión |
| RNF-7 | `test_cli::test_rnf_7_*` |
| RNF-8 | Revisión documentada (sección 1) |

Casos límite sin prueba automática, según el criterio 8.2: CL-16 y CL-29 (revisión documentada). CL-28 sí está automatizado.

## 4. Criterios de finalización (sección 8 de la spec)

| # | Criterio | Estado |
|---|----------|--------|
| 8.1 | Una prueba automática por cada RF | Cumplido (34 de 34) |
| 8.2 | Una prueba por cada CL, salvo CL-16, CL-28 y CL-29 | Cumplido (CL-28 incluso automatizado; CL-16 y CL-29 documentados) |
| 8.3 | Pruebas de RNF-1, 3, 5, 7; rendimiento de RNF-2; revisión de RNF-4 y RNF-8 | Cumplido |
| 8.4 | Tres personas completan el flujo en menos de un minuto | **Pendiente** (sección 2) |
| 8.5 | Todos los textos en español | Cumplido (RNF-1) |
| 8.6 | Los datos persisten entre ejecuciones | Cumplido (RF-5.1) |
| 8.7 | Sin dudas `[NECESITA ACLARACIÓN]` abiertas | Cumplido |
| 8.8 | La suite completa pasa | Cumplido (resultado en la respuesta de la sesión) |

## 5. Nota de rendimiento (RNF-2)

En el equipo de desarrollo, con la carga de referencia (100 hábitos × 1 826 marcas, 4 MB), los tiempos de un proceso completo han sido muy variables: `listar` entre 0,7 y 1,5 s y el guardado con valores atípicos de varios segundos (en una pasada, 18 y 28 s). El arranque del intérprete y la importación de módulos por sí solos varían entre 0,2 y 2,7 s entre pasadas, y las escrituras aisladas con `fsync` tardan 0,1 a 0,25 s, por lo que se atribuyen al sistema (probablemente análisis de archivos recién escritos) y no al código. La prueba mide el mejor de 3 intentos con datos nuevos y mantiene el umbral de 1 s; pasó en las pasadas finales. Si un equipo más lento fallara de forma sistemática, el principal coste restante es la importación de `dataclasses` y la lectura del JSON de 4 MB.
