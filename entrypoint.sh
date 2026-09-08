#!/bin/sh
set -e

echo "[Docker] Running Database Migrations..."
python manage.py migrate --noinput

echo "[Docker] Seeding Database..."
python seed.py

echo "[Docker] Starting ConstructSync Django Application on port 5000..."
exec python app.py
