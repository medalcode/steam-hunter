# Steam Hunter

Bot automatizado que busca códigos gratis de Steam en múltiples fuentes (Reddit, SteamDB, GamerPower, Telegram, Twitter, etc.) y los canjea automáticamente.

## Stack

- **Backend**: Python + FastAPI + SQLite + APScheduler
- **Frontend**: React + Vite + TypeScript
- **Despliegue**: Docker Compose

## Fuentes

| Fuente | Tipo |
|---|---|
| Reddit (r/FreeGameFindings, r/GameDeals, etc.) | Keys, giveaways |
| GamerPower | Giveaways curados |
| SteamDB | Free promotions |
| Steam Store | Free weekends |
| SteamGifts | Giveaways |
| GiveAway.su | Keys directas |
| FreeSteamKeys | Giveaways comunitarios |
| GG.deals | Giveaways |
| IndieGameBundles | Free games |
| IndieGala Freebies | Freebies |
| Twitter/X | Giveaways |
| Telegram | Canales de keys |

## Cómo correrlo

### Local

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (otra terminal)
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173`.

### Docker

```bash
docker compose up -d --build
```

## Configuración

1. Abrir la web app
2. Ir a **Config > Reddit**
3. Crear app en https://www.reddit.com/prefs/apps (tipo "script")
4. Ingresar Client ID y Client Secret
5. (Opcional) **Config > Steam Accts** — pegar cookies de store.steampowered.com
6. (Opcional) **Config > Notifications** — Discord webhook o Telegram

## API

| Ruta | Descripción |
|---|---|
| `GET /api/codes` | Listar códigos (filtros: status, code_type, source) |
| `GET /api/stats` | Estadísticas |
| `POST /api/redeem` | Canjear código |
| `POST /api/validate/{id}` | Validar formato de key |
| `POST /api/auto-enter` | Auto-participar en giveaway |
| `GET /api/export/json` | Exportar a JSON |
| `GET /api/export/csv` | Exportar a CSV |
| `POST /api/config/reddit` | Configurar Reddit |
| `POST /api/config/steam-session` | Configurar cuenta Steam |
| `GET/POST /api/config/notifications` | Configurar notificaciones |
| `WS /ws` | WebSocket para tiempo real |
