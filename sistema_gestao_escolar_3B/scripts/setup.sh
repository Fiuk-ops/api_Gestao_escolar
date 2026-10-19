#!/usr/bin/env sh
set -eu

echo "Instalando dependências..."
python -m pip install -r requirements.txt

echo "Inicializando o banco..."
python scripts/initialize_database.py

echo "Projeto preparado. Para iniciar: python app.py"
