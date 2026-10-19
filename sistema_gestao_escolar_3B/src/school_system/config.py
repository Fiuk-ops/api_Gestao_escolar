"""Configuração centralizada e caminhos da aplicação."""

from __future__ import annotations

import os
import secrets
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("SCHOOL_DATA_DIR", PROJECT_ROOT / "data"))
DATABASE_FILE = Path(os.environ.get("SCHOOL_DATABASE_PATH", DATA_DIR / "escola.db"))
UPLOADS_DIR = Path(os.environ.get("SCHOOL_UPLOADS_DIR", DATA_DIR / "uploads"))
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"


def database_path() -> str:
    """Retorna o caminho do SQLite, criando o diretório de dados quando preciso."""
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return str(DATABASE_FILE)


def ensure_runtime_directories() -> None:
    """Cria diretórios locais que não devem ser versionados."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    """Valores de execução, todos ajustáveis por variáveis de ambiente."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    UPLOAD_FOLDER = str(UPLOADS_DIR)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))

