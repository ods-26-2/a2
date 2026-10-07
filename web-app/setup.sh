#!/usr/bin/env bash
set -e

# instala dependências e prepara o banco (idempotente: pode rodar quantas vezes quiser)
pip install -r requirements.txt
python backend/db/init_db.py