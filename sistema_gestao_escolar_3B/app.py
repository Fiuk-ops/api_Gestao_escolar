"""Ponto de entrada do Sistema de Gestão Escolar.

O código da aplicação fica em ``src/school_system``. Este arquivo mantém uma
forma simples e compatível de iniciar o projeto: ``python app.py``.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from school_system.web import app, run_server  # noqa: E402


if __name__ == "__main__":
    run_server()
