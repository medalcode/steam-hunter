# Steam Hunter

Bot automatizado que busca códigos gratis, giveaways y juegos temporalmente gratis de Steam en múltiples fuentes (FreeSteamKeys, GamerPower, Givee.Club, Steam Store, CheapShark, Epic Games, etc.) y los canjea automáticamente vía ArchiSteamFarm.

## Stack

- **Backend**: Python + FastAPI + SQLite + APScheduler
- **Frontend**: React + Vite + TypeScript
- **Despliegue**: Docker Compose + CI/CD a GCP

## Fuentes (25+)

| Fuente | Tipo | Estado |
|---|---|---|
| **FreeSteamKeys API** | Giveaways curados + free-to-keep | ✅ ~29 |
| **GamerPower API** | Giveaways oficiales | ✅ ~2 |
| **Givee.Club** | Sorteos + free-to-keep (Steam/Epic/GOG) | ✅ ~44 |
| Steam Store (temp free) | Juegos en -100% temporal | ✅ |
| Steam Store (free weekend) | Fines de semana gratis | ✅ |
| CheapShark API | Deals en $0 o cerca | ✅ |
| Epic Games Store | Juegos gratis semanales | ✅ |
| GiveAway.su | Keys directas | ✅ |
| Telegram | Canales de keys | ✅ |
| Fanatical | Juegos gratis | ✅ |
| Reddit (5 subreddits) | Giveaways comunitarios | 🔒 403 |
| SteamDB | Free promotions | 🔒 Cloudflare |
| SteamGifts | Giveaways | 🔒 Requiere login |
| GG.deals | Giveaways | 🔒 Cloudflare |
| Twitter/X | Giveaways | ⏳ Ocasional |
| IndieGameBundles | Free games | ⏳ Ocasional |
| IndieGala Freebies | Freebies | ⏳ Ocasional |

✅ = Funcionando  |  🔒 = Bloqueado (403/Cloudflare)  |  ⏳ = Ocasional

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

Steam Hunter se conecta al IPC de ArchiSteamFarm para canjear keys y agregar free-to-keep automáticamente:

1. ASF debe estar corriendo con IPC habilitado (puerto `1243`)
2. En la web app ir a **Config > ASF**
3. Ingresar URL del IPC (`http://localhost:1243`)
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
| `GET /api/scrape` | Forzar ejecución de scrapers |

## Scrapers

Cada scraper corre cada 15 minutos vía APScheduler:

- **giveaway_apis**: FreeSteamKeys API, GamerPower API, Givee.Club — resuelve URLs de Steam desde páginas de eventos
- **keysites**: GamerPower, GiveAway.su + Reddit fallback
- **moresources**: CheapShark API, Reddit, Epic Games API, Fanatical
- **steamdb**: SteamDB (bloqueado, fallback a Steam Store specials)
- **steam_store**: Temp free games (-100%), free weekends, F2P
- **steamgifts**: SteamGifts (requiere cookies)
- **twitter**: Nitter instances, cuentas de giveaways
- **telegram**: Canales públicos de keys
- **reddit**: Reddit API con OAuth (bloqueado desde GCP)

---

## Deploy

Este repo se auto-despliega a GCP (`136.109.212.18`) vía GitHub Actions al hacer push a `main`.

## Auto-redeem y Free Games

El sistema procesa automáticamente dos tipos de contenido:

### Keys de Steam
Cuando se encuentra una key (formato `XXXXX-XXXXX-XXXXX`), se intenta canjear en **los 3 bots**:
`principal` → `secundaria1` → `tryh4rd`. Si un bot ya posee el juego, se saltea y se prueba el siguiente.

### Juegos Free-to-Keep de Steam
Cuando se detecta un enlace a `store.steampowered.com/app/<ID>`, el sistema:

1. Consulta la API de Steam para obtener el **sub ID promocional gratuito** (`_get_free_sub`)
2. Si existe un sub con precio $0, ejecuta `addlicense sub/<ID>` en **los 3 bots**
3. Si **no** hay sub gratuito, el juego se omite (no es free-to-keep)

Esto permite agregar juegos como Tell Me Why, Gravity Circuit, Capcom Arcade Stadium automáticamente, evitando falsos positivos con `app/<ID>`.

### Bots disponibles

| Bot | Steam Account | Steam ID | Estado |
|---|---|---|---|
| `principal` | forgerb | 76561198051997214 | ✅ Farming |
| `secundaria1` | forgerb2 | 76561199125215505 | ✅ Limitada |
| `tryh4rd` | tryh4rdgame | 76561198691635889 | ✅ Limitada |

## Historial de cambios recientes

- **GiveawayAPIScraper**: Nuevo scraper con 3 fuentes (FreeSteamKeys API + GamerPower API + Givee.Club HTML) que resuelve URLs de Steam desde páginas de eventos
- **Steam URL resolution**: Scraper fetchea páginas de giveaways para extraer `store.steampowered.com/app/<ID>` y permitir auto-redeem
- **ASF IPC fix**: Se eliminó `IPCPassword` de ASF (bug en v6.3.6.1 causa 401 en todas las requests); IPC funciona sin auth en localhost
- **Skip non-free**: Eliminado fallback `app/<ID>` — juegos que no son free-to-keep se marcan como `skipped`
- **Retry existing**: El auto-redeem ahora reprocesa entradas existentes en estado `new` que no se pudieron canjear antes
- **ASF Client fix**: `get_bots()` ahora parsea correctamente la respuesta de ASF IPC (formato dict-keyed por bot)
- **Multi-bot redeem**: Auto-redeem prueba los 3 bots en secuencia, no solo el default
- **Free game detection**: Helper `_get_free_sub()` que obtiene el sub ID promocional desde la API de Steam
- **Scheduler fix**: Se agregó `scheduler.start()` que faltaba; scrapers ahora corren cada 15 min
