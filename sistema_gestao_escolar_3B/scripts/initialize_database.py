"""Inicializa o schema SQLite sem iniciar o servidor web."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from school_system.web import initialize_database


if __name__ == "__main__":
    initialize_database()
    print("Banco de dados inicializado.")
