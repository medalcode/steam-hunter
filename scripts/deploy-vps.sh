#!/bin/bash
# ============================================================
# Deploy steam-hunter + ASF en VPS (Ubuntu 24.04+)
# ============================================================
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ASF_DIR="$HOME/asf-native"

echo "=== Steam Hunter + ASF Deploy ==="
echo ""

# ─── 1. Instalar Docker si no existe ────────────────────────
if ! command -v docker &>/dev/null; then
  echo "[1/5] Instalando Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "  OK: Docker instalado (re-login para usar sin sudo)"
else
  echo "[1/5] Docker ya instalado"
fi

# ─── 2. Instalar ASF nativo ─────────────────────────────────
echo "[2/5] Configurando ASF nativo..."
if [ ! -f "$ASF_DIR/ArchiSteamFarm" ]; then
  ASF_VERSION="6.3.5.1"
  ARCH="linux-x64"
  [ "$(uname -m)" = "aarch64" ] && ARCH="linux-arm64"
  ASF_URL="https://github.com/JustArchiNET/ArchiSteamFarm/releases/download/${ASF_VERSION}/ArchiSteamFarm-${ASF_VERSION}-${ARCH}.zip"

  mkdir -p "$ASF_DIR"
  TMP_ZIP=$(mktemp)
  curl -sL "$ASF_URL" -o "$TMP_ZIP"
  unzip -qo "$TMP_ZIP" -d "$ASF_DIR"
  chmod +x "$ASF_DIR/ArchiSteamFarm"
  rm "$TMP_ZIP"
  echo "  ASF descargado en $ASF_DIR"
else
  echo "  ASF ya existe en $ASF_DIR"
fi

# Configs de ASF desde medalcode-asf-setup
ASF_SETUP_REPO="${REPO_DIR}/../medalcode-asf-setup"
if [ -d "$ASF_SETUP_REPO" ]; then
  echo "  Usando configs desde $ASF_SETUP_REPO"
  cp -v "$ASF_SETUP_REPO/config/ASF.json" "$ASF_DIR/config/"

  IPC_TOKEN_FILE="$ASF_DIR/config/.ipc_token"
  if [ ! -f "$IPC_TOKEN_FILE" ]; then
    IPC_TOKEN=$(openssl rand -hex 16)
    echo "$IPC_TOKEN" > "$IPC_TOKEN_FILE"
    chmod 600 "$IPC_TOKEN_FILE"
  else
    IPC_TOKEN=$(cat "$IPC_TOKEN_FILE")
  fi

  sed "s/IPC_AUTH_TOKEN/$IPC_TOKEN/g" "$ASF_SETUP_REPO/config/IPC.config" > "$ASF_DIR/config/IPC.config"
  chmod 600 "$ASF_DIR/config/IPC.config"
  echo "  IPC.config con token de autenticacion"

  for template in "$ASF_SETUP_REPO/config/"*.json.template; do
    base=$(basename "$template" .template)
    if [ ! -f "$ASF_DIR/config/$base" ]; then
      cp -v "$template" "$ASF_DIR/config/$base"
      echo "  ATENCION: Edita $ASF_DIR/config/$base con tus credenciales"
    fi
  done
else
  echo "  ATENCION: No se encuentra medalcode-asf-setup"
  echo "  Debes copiar manualmente ASF.json, IPC.config y los bot configs a $ASF_DIR/config/"
fi

# ─── 3. Configurar systemd para ASF ─────────────────────────
echo "[3/5] Instalando servicio systemd para ASF..."
mkdir -p "$HOME/.config/systemd/user"

cat > "$HOME/.config/systemd/user/asf.service" << 'SERVICE'
[Unit]
Description=ArchiSteamFarm - Steam card farming
After=network-online.target

[Service]
Type=simple
ExecStart=%h/asf-native/ArchiSteamFarm
WorkingDirectory=%h/asf-native
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
SERVICE

systemctl --user daemon-reload
systemctl --user enable asf.service
echo "  Servicio ASF instalado"

# ─── 4. Configurar steam-hunter ─────────────────────────────
echo "[4/5] Construyendo steam-hunter con Docker..."
if [ -f "$IPC_TOKEN_FILE" ]; then
  export ASF_IPC_PASSWORD=$(cat "$IPC_TOKEN_FILE")
fi
export ASF_AUTO_REDEEM=true

cd "$REPO_DIR"
docker compose -f docker-compose.full.yml build
echo "  Imagenes construidas"

# ─── 5. Iniciar servicios ──────────────────────────────────
echo "[5/5] Iniciando servicios..."
systemctl --user start asf.service
echo "  ASF iniciado (systemd --user)"

docker compose -f docker-compose.full.yml up -d
echo "  steam-hunter iniciado (Docker)"

echo ""
echo "=== Deploy completado ==="
echo "  ASF:     http://localhost:1242"
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:80"
echo ""
echo "Comandos utiles:"
echo "  systemctl --user status asf.service"
echo "  docker compose -f docker-compose.full.yml logs -f backend"
echo "  docker compose -f docker-compose.full.yml logs -f frontend"
echo ""
echo "NO OLVIDES editar los archivos .json de bots en $ASF_DIR/config/"
