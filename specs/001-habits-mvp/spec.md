# Spec 001 — MVP de habits-cli

Estado: aprobada el 2026-10-23 · Fecha: 2026-10-23

Ciclo de vida: *borrador* → *aprobada*. La aprobación la da la persona dueña del proyecto cambiando este campo a «aprobada» con la fecha. Solo una spec aprobada puede guiar el código; cualquier cambio posterior la devuelve a *borrador* hasta que se reapruebe.

## 1. Contexto y objetivo

Quien estudia de forma autónoma suele abandonar sus rutinas porque no ve su propia constancia. Ver cuántos días seguidos lleva cumpliendo un hábito (la **racha**) motiva a no romperla.

**Objetivo del MVP:** que una persona pueda, desde la terminal, (1) dar de alta un hábito de estudio, (2) marcarlo como hecho hoy y (3) consultar todos sus hábitos con la racha actual de cada uno.

**Éxito:** tres personas que nunca han usado la herramienta completan el flujo crear → marcar → ver la racha en menos de un minuto cada una, usando solo la ayuda de la propia herramienta.

### Glosario

- **Hábito:** actividad diaria de estudio con un nombre (por ejemplo, «Leer 20 minutos»).
- **Marca:** registro de que un hábito se cumplió en un día concreto. Un hábito tiene como máximo una marca por día.
- **Día:** día natural según la fecha local del equipo de la persona usuaria. «Hoy» es la fecha local en el momento de ejecutar el comando y se determina una sola vez por ejecución; el MVP no guarda zona horaria.
- **Racha:** número de días consecutivos con marca que terminan hoy o ayer. Si no hay marca ni hoy ni ayer, la racha es 0. Las marcas posteriores a hoy no cuentan.
- **Espacio:** el espacio ordinario, el tabulador y los espacios Unicode (como el espacio de no separación). Los saltos de línea no son espacios.
- **Nombre normalizado:** el nombre sin espacios al inicio ni al final y con cada secuencia de espacios internos reducida a un único espacio ordinario.
- **Nombre válido:** nombre que, una vez normalizado, (a) no está vacío, (b) tiene como máximo 100 caracteres Unicode, (c) no contiene caracteres de control (como los saltos de línea; los caracteres de ancho cero que forman emojis compuestos sí se permiten) y (d) no empieza por «-».
- **Nombre equivalente:** dos nombres son equivalentes si, una vez normalizados, son iguales ignorando mayúsculas/minúsculas (también en letras especiales) y tratando como iguales las formas Unicode que se ven idénticas (por ejemplo, una «é» compuesta y una «e» con acento combinado). Los acentos sí distinguen: «Leer» y «Léer» no son equivalentes.

## 2. Usuarios

- **Estudiante autónomo (principal):** persona que estudia por su cuenta, cómoda con la terminal, que quiere registrar a diario sus hábitos con el mínimo esfuerzo.
- **Desarrollador junior mantenedor (secundario):** persona que mantiene la herramienta; necesita que el comportamiento esté descrito sin ambigüedades.

## 3. Historias de usuario

- **HU-1:** Como estudiante, quiero crear un hábito con un nombre, para empezar a registrar mi constancia.
- **HU-2:** Como estudiante, quiero marcar un hábito como hecho hoy, para dejar constancia de que lo cumplí.
- **HU-3:** Como estudiante, quiero listar mis hábitos con su racha, para saber cuántos días seguidos llevo y si hoy me falta algo.
- **HU-4:** Como estudiante, quiero que los errores me expliquen en español qué pasó y no me corrompan los datos, para poder corregirlos sin miedo.

## 4. Requisitos funcionales

Notación EARS: *«El sistema deberá…»* (ubicuo), *«Cuando…»* (evento), *«Mientras…»* (estado), *«Si… entonces…»* (situación no deseada).

### RF-1 — Crear un hábito (HU-1)

- **RF-1.1** Cuando la persona crea un hábito con un nombre válido, el sistema deberá guardarlo con su nombre normalizado, sin marcas y con racha 0, y deberá confirmar la creación con un mensaje.
- **RF-1.2** Si el nombre, una vez normalizado, está vacío, entonces el sistema deberá rechazar la creación, mostrar un error y no modificar los datos.
- **RF-1.3** Si ya existe un hábito con un nombre equivalente, entonces el sistema deberá rechazar la creación, mostrar un error que cite el hábito existente con su nombre guardado y no modificar los datos.
- **RF-1.4** El sistema deberá conservar en el nombre guardado las mismas letras, mayúsculas, acentos y emojis que escribió la persona; solo se modifican los espacios, según el nombre normalizado.
- **RF-1.5** Si el nombre normalizado supera los 100 caracteres Unicode, entonces el sistema deberá rechazar la creación, mostrar un error que indique el límite y no modificar los datos.
- **RF-1.6** Si el nombre contiene caracteres de control o empieza por «-», entonces el sistema deberá rechazar la creación, mostrar un error que explique la regla incumplida y no modificar los datos.

### RF-2 — Marcar un hábito como hecho hoy (HU-2)

- **RF-2.1** Cuando la persona marca un hábito existente que hoy no tiene marca, el sistema deberá registrar una marca con la fecha de hoy y confirmar la acción mostrando la racha resultante.
- **RF-2.2** El sistema deberá identificar el hábito por su nombre, comparándolo mediante nombre equivalente.
- **RF-2.3** Si el hábito ya tiene marca de hoy, entonces el sistema deberá avisar de que ya estaba marcado hoy, no registrar una segunda marca y terminar sin error.
- **RF-2.4** Si no existe ningún hábito con ese nombre, entonces el sistema deberá mostrar un error que indique que el hábito no existe, no modificar los datos y terminar con error.
- **RF-2.5** El sistema deberá permitir marcar únicamente el día de hoy; no deberá ofrecer forma de marcar días pasados ni futuros.
- **RF-2.6** Si el nombre indicado, una vez normalizado, está vacío, entonces el sistema deberá mostrar un error de nombre vacío (no de hábito inexistente), no modificar los datos y terminar con error.

### RF-3 — Listar hábitos con su racha (HU-3)

- **RF-3.1** Cuando la persona pide el listado y existe al menos un hábito, el sistema deberá mostrar, por cada hábito y en el orden en que se crearon, su nombre, su racha actual (expresada como «día» o «días» según corresponda) y si ya está marcado hoy.
- **RF-3.2** Cuando la persona pide el listado y no existe ningún hábito, el sistema deberá mostrar un mensaje que la invite a crear el primero y terminar sin error.
- **RF-3.3** El listado no deberá modificar los datos.

### RF-4 — Cálculo de la racha (HU-3)

- **RF-4.1** El sistema deberá calcular la racha como el número de días naturales consecutivos con marca que terminan hoy o, si hoy no hay marca, ayer. Los cambios de horario y el 29 de febrero no alteran el recuento: se cuentan días naturales.
- **RF-4.2** Mientras el hábito tenga marca de ayer pero aún no de hoy, el sistema deberá conservar la racha acumulada hasta ayer (no deberá mostrar 0 antes de que termine el día).
- **RF-4.3** Si el hábito no tiene marca ni hoy ni ayer, entonces el sistema deberá mostrar racha 0.
- **RF-4.4** El sistema deberá asignar racha 0 a un hábito sin ninguna marca.
- **RF-4.5** Cuando existe un hueco de al menos un día entre marcas, el sistema deberá contar solo el tramo consecutivo más reciente.
- **RF-4.6** El sistema deberá ignorar, al calcular la racha y al determinar si el hábito está hecho hoy, las marcas con fecha posterior a hoy (por ejemplo, si la fecha del equipo retrocedió), y deberá conservarlas en los datos sin modificarlas.
- **RF-4.7** Cuando al listar o marcar existan marcas con fecha posterior a hoy, el sistema deberá avisar en español de que la fecha del equipo parece anterior a alguna marca, sin modificar los datos.

### RF-5 — Datos y su conservación (HU-1, HU-2, HU-4)

- **RF-5.1** El sistema deberá conservar los hábitos y sus marcas entre ejecuciones, de modo que lo creado o marcado en una ejecución se vea en las siguientes.
- **RF-5.2** Cuando se ejecuta por primera vez y no hay datos previos (ausentes, no vacíos), el sistema deberá comportarse como si no existiera ningún hábito, sin error.
- **RF-5.3** Si los datos guardados están vacíos, no se pueden leer, son de una versión desconocida o son incoherentes (fechas imposibles, varias marcas de un mismo hábito en un mismo día, nombres equivalentes duplicados o nombres no válidos), entonces el sistema deberá mostrar un error en español, indicar que los datos no se han modificado y que deben repararse o apartarse manualmente antes de seguir, terminar con error y no modificar los datos.
- **RF-5.4** El sistema deberá guardar junto con los datos una indicación de la versión de su formato.
- **RF-5.5** Si no se puede guardar el resultado de una operación (disco lleno, falta de permisos, ubicación de datos que no se puede crear o datos de solo lectura), entonces el sistema deberá mostrar un error en español, no mostrar la confirmación de éxito, terminar con error y dejar intactos los datos anteriores.
- **RF-5.6** Los datos pertenecen a la persona usuaria del sistema operativo y deberán ser los mismos sea cual sea la carpeta desde la que se ejecute la herramienta.

### RF-6 — Interfaz, ayuda y uso incorrecto (HU-4)

- **RF-6.1** Si la persona ejecuta la herramienta sin comando, con un comando desconocido, sin un argumento obligatorio o con argumentos sobrantes (por ejemplo, un nombre con espacios escrito sin comillas), entonces el sistema deberá mostrar un mensaje en español con el uso correcto de los comandos y terminar con error.
- **RF-6.2** Cuando la persona pide la ayuda con su opción específica, el sistema deberá mostrar la lista de comandos disponibles con una breve descripción de cada uno y terminar sin error.
- **RF-6.3** El sistema deberá distinguir el éxito del error mediante el código de salida: cero cuando la operación se completó (incluidos el aviso de RF-2.3, el listado vacío de RF-3.2 y la ayuda de RF-6.2) y distinto de cero en cualquier error.
- **RF-6.4** El sistema deberá expresar en español los nombres de sus comandos.
- **RF-6.5** Si la consola no puede mostrar algún carácter del nombre de un hábito, entonces el sistema deberá sustituirlo por un marcador, completar el comando con normalidad, sin errores ni trazas técnicas, y no alterar los datos guardados.
- **RF-6.6** El sistema deberá emitir los errores, los mensajes de uso y el aviso de RF-4.7 por la salida de error, y las confirmaciones, el aviso de RF-2.3 y los listados por la salida estándar.

## 5. Requisitos no funcionales

- **RNF-1 Idioma:** todo texto dirigido a la persona usuaria (confirmaciones, avisos, errores, ayuda y nombres de comandos) deberá estar en español.
- **RNF-2 Rapidez:** cada comando deberá terminar en menos de 1 segundo, medido desde su inicio, en un equipo de uso general con menos de 5 años de antigüedad, con 100 hábitos y 5 años de marcas por hábito como carga de referencia.
- **RNF-3 Uso sin conexión:** la herramienta no deberá requerir conexión a internet ni cuenta de usuario.
- **RNF-4 Datos locales:** la herramienta no deberá realizar conexiones de red ni escribir fuera de la ubicación de sus datos.
- **RNF-5 Integridad:** si una operación se interrumpe (cierre forzado, interrupción con el teclado, corte de energía) o falla al guardar, los hábitos y marcas anteriores deberán permanecer íntegros.
- **RNF-6 Verificabilidad:** los requisitos funcionales y los casos límite deberán ser verificables con pruebas automáticas; los requisitos no funcionales que no puedan automatizarse deberán verificarse mediante una revisión documentada.
- **RNF-7 Claridad:** cada mensaje de error deberá indicar qué falló; los errores de RF-1.2, RF-1.3, RF-1.5, RF-1.6, RF-2.4, RF-2.6, RF-5.3, RF-5.5 y RF-6.1 deberán indicar además qué puede hacer la persona para corregirlos.
- **RNF-8 Limitación declarada:** el uso simultáneo de varias ejecuciones sobre los mismos datos no está garantizado en el MVP.

## 6. Casos límite

| # | Situación | Comportamiento esperado |
|---|-----------|------------------------|
| CL-1 | Crear «Leer» y después «leer» o « LEER » | Se rechaza el segundo (RF-1.3) |
| CL-2 | Crear un hábito con nombre vacío o solo espacios | Se rechaza (RF-1.2) |
| CL-3 | Marcar dos veces el mismo hábito en el mismo día | Aviso, sin segunda marca, sin error (RF-2.3) |
| CL-4 | Marcar un hábito que no existe | Error, sin cambios (RF-2.4) |
| CL-5 | Marcas ayer, anteayer y hace tres días; hoy sin marca | Racha 3 (RF-4.2) |
| CL-6 | Marcas hace tres y dos días; ayer y hoy sin marca | Racha 0 (RF-4.3) |
| CL-7 | Marcas hoy y hace dos días; ayer sin marca | Racha 1 (RF-4.5) |
| CL-8 | Un hábito con marcas el lunes y el martes se consulta el miércoles a las 00:05 | Figura como no hecho hoy y con racha 2 (RF-4.2) |
| CL-9 | Primera ejecución sin datos previos | Listado vacío con invitación a crear (RF-5.2, RF-3.2) |
| CL-10 | Datos guardados dañados | Error, datos intactos (RF-5.3) |
| CL-11 | Racha que cruza el fin de mes o de año | Se cuenta por días naturales consecutivos (RF-4.1) |
| CL-12 | Nombre con acentos, ñ o emojis (incluidos los compuestos) | Se admite y se conservan sus letras, acentos y emojis (RF-1.1, RF-1.4) |
| CL-13 | Nombre normalizado de exactamente 100 caracteres, y otro de 101 | El de 100 se acepta; el de 101 se rechaza. Los espacios sobrantes de los bordes no cuentan (RF-1.5) |
| CL-14 | Crear «Leer» y después «Léer», o «Leer  mucho» (dos espacios) tras «Leer mucho» | «Léer» se acepta como hábito distinto; el segundo «Leer mucho» se rechaza por equivalente (RF-1.3) |
| CL-15 | La fecha del equipo retrocede y existen marcas posteriores a hoy | Esas marcas se ignoran para la racha y para «hecho hoy», se conservan y se avisa (RF-4.6, RF-4.7) |
| CL-16 | La persona cambia de zona horaria y «hoy» retrocede un día | Las marcas del día «futuro» se ignoran y la racha puede bajar o el hábito dejar de figurar como hecho hoy, con aviso (RF-4.6, RF-4.7). Si «hoy» avanza, puede omitirse un día y romperse la racha. Es una limitación aceptada del MVP |
| CL-17 | Marcar con un nombre vacío o de solo espacios | Error de nombre vacío, sin cambios (RF-2.6) |
| CL-18 | Crear un hábito cuyo nombre contiene un salto de línea o empieza por «-» | Se rechaza con un error que explica la regla (RF-1.6) |
| CL-19 | Crear «é» compuesta y después la misma «é» con acento combinado | Se tratan como el mismo nombre; se rechaza el segundo (glosario, RF-1.3) |
| CL-20 | `crear Leer mucho` (sin comillas, con argumentos sobrantes) | Mensaje de uso y error (RF-6.1) |
| CL-21 | Ejecutar la herramienta sin comando, y después pedir la ayuda con su opción | Sin comando: uso y error. Con la opción de ayuda: lista de comandos y éxito (RF-6.1, RF-6.2) |
| CL-22 | No se puede guardar (disco lleno, sin permisos, datos de solo lectura) | Error sin confirmación de éxito, datos anteriores intactos (RF-5.5) |
| CL-23 | Datos vacíos, de versión desconocida, con marcas repetidas el mismo día, con fechas imposibles o con nombres equivalentes duplicados | Error, datos sin modificar (RF-5.3) |
| CL-24 | El día cambia mientras se ejecuta un comando (23:59:59 → 00:00:01) | La marca y el cálculo de la racha usan la misma fecha de «hoy» (glosario) |
| CL-25 | Racha que cruza un cambio de horario de verano o un 29 de febrero | Se cuentan días naturales, sin días perdidos ni duplicados (RF-4.1) |
| CL-26 | La fecha del equipo se corrige después de haber retrocedido | Las marcas hechas durante el retroceso son marcas normales y cuentan cuando vuelve la fecha real (RF-4.6) |
| CL-27 | Existen más de 100 hábitos | Se aceptan; no hay límite (RNF-2 es solo carga de referencia) |
| CL-28 | La consola no puede mostrar un carácter del nombre | Se sustituye por un marcador, el comando se completa y los datos no cambian (RF-6.5) |
| CL-29 | Dos ejecuciones a la vez sobre los mismos datos | No garantizado en el MVP (RNF-8) |
| CL-30 | Ejecutar la herramienta desde dos carpetas distintas | Se ven los mismos hábitos (RF-5.6) |
| CL-31 | Se produce un error o el aviso de RF-4.7 con la salida estándar redirigida a un archivo, y después un listado con la misma redirección | El archivo del listado no contiene mensajes de error ni avisos de RF-4.7; estos aparecen en la salida de error (RF-6.6) |

## 7. Fuera de alcance

- Marcar días pasados o futuros: solo se puede marcar el día de hoy (RF-2.5).
- Borrar y renombrar hábitos: un hábito creado por error permanece (spec posterior).
- Desmarcar: la marca de hoy no se puede deshacer (spec posterior).
- Otras frecuencias, metas semanales y recordatorios: todos los hábitos son diarios.
- Estadísticas: racha máxima histórica, total de días e historial; el listado solo muestra racha actual y si está hecho hoy.
- Guardar la zona horaria: «hoy» siempre es la fecha local del equipo (CL-16).
- Garantizar el uso simultáneo de varias ejecuciones sobre los mismos datos (RNF-8, CL-29).
- Cualquier interfaz que no sea la línea de comandos (gráfica, web, móvil).
- Sincronización entre equipos, cuentas de usuario o uso compartido de datos.

## 8. Criterios de finalización

El MVP se considera terminado cuando:

1. [ ] Cada requisito RF-1 a RF-6 tiene al menos una prueba automática que verifica su criterio de aceptación.
2. [ ] Cada caso límite CL-1 a CL-31 tiene una prueba automática, salvo CL-16, CL-28 y CL-29, que se verifican mediante una revisión documentada.
3. [ ] RNF-1, RNF-3, RNF-5 y RNF-7 tienen prueba automática; RNF-2 tiene una prueba de rendimiento con la carga de referencia; RNF-4 y RNF-8 se verifican mediante una revisión documentada.
4. [ ] Tres personas que nunca han usado la herramienta completan el flujo crear → marcar → listar en menos de un minuto cada una, usando solo la ayuda de la propia herramienta.
5. [ ] Todos los textos que ve la persona usuaria están en español (RNF-1).
6. [ ] Los datos creados en una ejecución están disponibles en la siguiente (RF-5.1).
7. [ ] Todas las dudas marcadas como [NECESITA ACLARACIÓN] están resueltas o movidas de forma explícita a una spec posterior.
8. [ ] La suite de pruebas completa pasa.

## 9. Dudas abiertas

No quedan dudas abiertas.

### Decisiones tomadas el 2026-10-23

- **Caracteres de ancho cero:** se permiten, porque forman emojis compuestos; solo se rechazan los de control (glosario, RF-1.6, CL-12).
- **Canal de salida:** errores, usos y aviso de RF-4.7 por la salida de error; el resto por la estándar (RF-6.6, CL-31).
- **Ciclo de vida de la spec:** borrador → aprobada, con aprobación de la persona dueña del proyecto registrada en el campo Estado (cabecera).

- **Borrar y renombrar, desmarcar, frecuencia y estadísticas:** fuera del MVP (sección 7).
- **Nombre válido:** texto imprimible sin caracteres de control y sin empezar por «-»; los espacios Unicode se normalizan (glosario, RF-1.6).
- **Comparación Unicode:** lo que se ve igual es igual; los acentos distinguen (glosario, CL-19).
- **Longitud:** máximo 100 caracteres Unicode, sin contar símbolos visibles (RF-1.5, CL-13).
- **Nombre guardado:** el normalizado, conservando mayúsculas, acentos y emojis (RF-1.1, RF-1.4).
- **Alcance de los datos:** por usuario del sistema operativo (RF-5.6, CL-30).
- **Argumentos sobrantes:** error de uso; el nombre con espacios va entre comillas (RF-6.1, CL-20).
- **Sin comando y ayuda:** sin comando es error; la ayuda explícita es éxito (RF-6.1, RF-6.2, CL-21).
- **Idioma de los comandos:** en español (RF-6.4).
- **Reloj y zona horaria:** marcas futuras ignoradas, conservadas y con aviso (RF-4.6, RF-4.7, CL-15, CL-16).
- **Formato de datos:** versión de formato en los datos; el formato concreto se define en el plan (RF-5.4).
- **Error de nombre duplicado:** cita el hábito con el nombre guardado (RF-1.3).
- **Datos dañados:** criterio estricto (RF-5.3, CL-23).
- **Concurrencia:** fuera del MVP, documentado (RNF-8, CL-29).
- **Límite de hábitos:** sin límite (CL-27).
- **Consola sin soporte de algún carácter:** se sustituye sin fallar (RF-6.5, CL-28).
- **Medida del éxito:** tres personas nuevas, menos de un minuto cada una, sin ayuda externa (sección 1, criterio 8.4).
