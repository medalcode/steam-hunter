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
