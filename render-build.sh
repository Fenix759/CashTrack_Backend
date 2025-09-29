#!/usr/bin/env bash
# 🚀 Render build script para CashTrack

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Migraciones
python manage.py migrate --noinput

# Archivos estáticos
python manage.py collectstatic --noinput
