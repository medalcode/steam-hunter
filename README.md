# Steam Hunter

Bot automatizado que busca códigos gratis, giveaways y juegos temporalmente gratis de Steam en múltiples fuentes (Reddit, GamerPower, Steam Store, CheapShark, Epic Games, etc.) y los canjea automáticamente.

## Stack

- **Backend**: Python + FastAPI + SQLite + APScheduler
- **Frontend**: React + Vite + TypeScript
- **Despliegue**: Docker Compose

## Fuentes (20+)

| Fuente | Tipo | Estado |
|---|---|---|
| GamerPower | Keys/ Giveaways curados | ✅ |
| Steam Store (temp free) | Juegos en -100% temporal | ✅ |
| Steam Store (free weekend) | Fines de semana gratis | ✅ |
| CheapShark API | Deals en $0 o cerca | ✅ |
| Epic Games Store | Juegos gratis semanales | ✅ |
| Reddit (r/FreeGameFindings) | Giveaways comunitarios | ✅ |
| Reddit (r/GameDealsFree) | Deals gratis | ✅ |
| Reddit (r/FreeSteamGames) | Keys comunitarias | ✅ |
| Reddit (r/FreeGamesOnSteam) | Giveaways | ✅ |
| Reddit (r/GameDeals) | Ofertas | ✅ |
| GiveAway.su | Keys directas | ✅ |
| Reddit (r/Gamebundles) | Bundles/giveaways | ⏳ |
| SteamDB | Free promotions | 🔒 Cloudflare |
| SteamGifts | Giveaways | 🔒 Requiere login |
| GG.deals | Giveaways | 🔒 Cloudflare |
| FreeSteamKeys | Giveaways comunitarios | ⏳ |
| IndieGameBundles | Free games | ⏳ |
| IndieGala Freebies | Freebies | ⏳ |
| Fanatical | Juegos gratis | ⏳ |
| Twitter/X | Giveaways | ⏳ |
| Telegram | Canales de keys | ⏳ |

✅ = Funcionando  |  🔒 = Bloqueado (requiere cookies)  |  ⏳ = Ocasional

## Cómo correrlo

### Local (Linux)

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000

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
7. (Opcional) **Config > ASF** — conectar ArchiSteamFarm para auto-canjear keys

## Integración ASF (ArchiSteamFarm)

Steam Hunter se conecta al IPC de ArchiSteamFarm para canjear keys automáticamente:

1. ASF debe estar corriendo con IPC habilitado (puerto `1242` o `1243`)
2. En la web app ir a **Config > ASF**
3. Ingresar URL del IPC (`http://localhost:1243`) y password si aplica
4. Seleccionar bot por defecto (`principal`, `secundaria1`, etc.)
5. Activar **Auto-redeem** para canjear automáticamente al detectar keys nuevas

### Endpoints ASF

| Ruta | Descripción |
|---|---|
| `GET /api/asf/bots` | Listar bots de ASF |
| `POST /api/asf/redeem` | Canjear key via ASF |
| `POST /api/asf/redeem-all` | Canjear todas las keys pendientes |

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

## MCP Server (Model Context Protocol)

Steam Hunter incluye un servidor MCP que expone su funcionalidad como herramientas para asistentes de IA (compatible con opencode, Claude, etc.).

### Herramientas MCP

| Tool | Descripción |
|------|-------------|
| `search_free_games` | Ejecuta todos los scrapers y guarda resultados |
| `list_found_codes` | Lista códigos encontrados con filtros |
| `redeem_with_asf` | Envía una key al IPC de ASF para canjear |
| `get_asf_status` | Estado de bots de ArchiSteamFarm |
| `get_stats` | Estadísticas del sistema |
| `validate_key` | Valida formato de key Steam |
| `configure_asf` | Configura conexión con ASF |

### Usar con opencode

Agrega a tu `opencode.json`:

```json
{
  "mcpServers": {
    "steam-hunter": {
      "command": "python",
      "args": ["-m", "app.mcp_server"],
      "cwd": "/ruta/a/steam-hunter/backend"
    }
  }
}
```

Ejemplo de uso:

```
opencode> busca juegos gratis en steam y canjea las keys con ASF
```

### Ejecutar standalone

```bash
cd backend
source venv/bin/activate
python -m app.mcp_server
```

## Scrapers

Cada scraper corre cada 15 minutos vía APScheduler:

- **keysites**: GamerPower, GiveAway.su + Reddit fallback via JSON API
- **moresources**: CheapShark API, 4 subreddits adicionales, Epic Games API, Fanatical
- **steamdb**: SteamDB (bloqueado, fallback a Steam Store specials)
- **steam_store**: Temp free games (-100%), free weekends, F2P
- **steamgifts**: SteamGifts (requiere cookies)
- **twitter**: Nitter instances, cuentas de giveaways
- **telegram**: Canales públicos de keys
- **reddit**: Reddit API con OAuth

---

## Deploy

This repo auto-deploys to GCP (`136.109.212.18`) via GitHub Actions on push to `main`.

