# Constitución de habits-cli

1. **Stack mínimo:** solo Python 3.12+ y biblioteca estándar; pytest únicamente para tests. Añadir una dependencia exige enmendar antes esta constitución.
2. **Spec primero:** todo cambio de comportamiento parte de una spec en `specs/`; si código y spec difieren, se corrige primero la spec.
3. **Lógica separada de la interfaz:** `habits/core.py` es puro (sin I/O, sin `print`, la fecha llega como parámetro); `habits/cli.py` solo lee argumentos y muestra resultados.
4. **Tests obligatorios:** toda función pública de `core.py` tiene test, todo bug corregido añade un test de regresión y `pytest -q` pasa antes de cada commit.
5. **Persistencia simple:** un único archivo JSON local, accedido solo desde `habits/storage.py`; cambiar su formato exige actualizar antes la spec.
6. **Idioma:** identificadores en inglés y mensajes al usuario en español.
