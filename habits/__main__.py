"""Punto de entrada de `python -m habits`."""

import sys

from habits.cli import configure_output, main

if __name__ == "__main__":
    configure_output()
    sys.exit(main(sys.argv[1:]))
