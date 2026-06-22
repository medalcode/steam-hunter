#!/bin/bash
set -e

# Este script levanta el ecosistema completo (Steam Hunter + ASF + FreeGamesClaimer)

if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker no está instalado o no está en el PATH"
  exit 1
fi

echo "=== Iniciando Steam Hunter Stack ==="
docker compose up -d --build

echo ""
echo "=== Iniciando FreeGamesClaimer Stack ==="
docker compose -f fgc-docker-compose.yml up -d

echo ""
echo "=== Verificando servicios ==="
docker compose ps
docker compose -f fgc-docker-compose.yml ps

echo ""
echo "¡Todo listo! Los servicios están corriendo en segundo plano."
echo "- Frontend de Steam Hunter: http://localhost/"
echo "- FreeGamesClaimer (VNC para login): http://localhost:6080"
