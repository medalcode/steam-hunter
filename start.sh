#!/bin/bash

# Este script levanta el ecosistema completo (Steam Hunter + ASF + FreeGamesClaimer)

echo "=== Iniciando Steam Hunter Stack ==="
docker compose up -d --build

echo ""
echo "=== Iniciando FreeGamesClaimer Stack ==="
docker compose -f fgc-docker-compose.yml up -d

echo ""
echo "¡Todo listo! Los servicios están corriendo en segundo plano."
echo "- Frontend de Steam Hunter: http://localhost/"
echo "- FreeGamesClaimer (VNC para login): http://localhost:6080"
