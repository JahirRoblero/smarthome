#!/usr/bin/env bash
# Desde la raíz: bash deploy/actualizar-vps.sh
# Requisitos: Docker Compose, rsync, sudo; HTTPS configurado previamente.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== SmartHome: construir imágenes y levantar servicios =="
docker compose up -d --build

echo "== Compilar React para producción =="
docker compose exec -T frontend npm run build

echo "== Publicar build estático, sin borrar PostgreSQL =="
sudo install -d -m 0755 /var/www/smarthome
sudo rsync -a --delete frontend/dist/ /var/www/smarthome/

echo "== Detener Vite: nginx/apache servirá React en 80/443 =="
docker compose stop frontend

echo "== Estado =="
docker compose ps
echo
echo "Sitio configurado para https://smarthome.votaya.com.mx/"
echo "Si aún no funciona HTTPS, sigue docs/DESPLIEGUE_HTTPS_VPS.md"
