# Steam Hunter

Bot automatizado que busca códigos gratis, giveaways y juegos temporalmente gratis de Steam en múltiples fuentes (FreeSteamKeys, GamerPower, Givee.Club, Steam Store, CheapShark, Epic Games, etc.) y los canjea automáticamente vía ArchiSteamFarm.

## Stack

- **Backend**: Python + FastAPI + SQLite + APScheduler + **MCP Server (SSE)**
- **Frontend**: React + Vite + TypeScript
- **Despliegue**: Docker Compose + CI/CD a GCP
- **ASF**: ArchiSteamFarm v6.3.6.1 (Docker, network=host)

## Seguridad

- **CORS**: Restringido a `localhost:5173`, `localhost:8000`, `127.0.0.1:8000`
- **Rate limiting**: 30 requests/60s por IP en endpoints `/api/*`
- **ASF IPC**: Usa header `X-API-Key` para autenticación (puerto 1242)
- **API Key opcional**: Setear `STEAM_HUNTER_API_KEY` para requerir Bearer token
- **.dockerignore**: Excluye `venv/`, `__pycache__/`, `*.db`, `xbox_cookies.json`

## Fuentes (25+)

| Fuente | Tipo | Estado |
|---|---|---|
| **FreeSteamKeys API** | Giveaways curados + free-to-keep | ✅ ~29 |
| **GamerPower API** | Giveaways oficiales | ✅ ~2 |
| **Givee.Club** | Sorteos + free-to-keep (Steam/Epic/GOG) | ✅ ~44 |
| Steam Store (temp free) | Juegos en -100% temporal | ✅ |
| Steam Store (free weekend) | Fines de semana gratis | ✅ |
| CheapShark API | Deals en $0 o cerca | ✅ |
| **GOG Catalog** | Juegos gratis en GOG | ✅ 140 items (mods/DLCs/prologues — requieren base game) |
| **Xbox Catalog** | Juegos gratis en Xbox | ✅ 90 items (F2P permanente, no promocional) |
| Epic Games Store | Juegos gratis semanales | ✅ Actuales reclamados. Próximos Jun 11 |
| **Amazon Prime Gaming** | Juegos mensuales | ❌ No implementado |
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

## Autenticación API

Opcional. Setear `STEAM_HUNTER_API_KEY` en el entorno para requerir Bearer token en todas las rutas excepto `/api/health`, `/mcp/*`, `/docs`, `/openapi.json`, `/ws`.

## Integración ASF (ArchiSteamFarm)

En Docker, ASF corre como servicio adjunto (`network_mode: host`, puerto `1242`). Backend se conecta a `http://127.0.0.1:1242` sin password.

Para configurar bots manualmente, editar los JSONs en `./asf-config/`.

### Endpoints ASF

| Ruta | Descripción |
|---|---|
| `GET /api/asf/bots` | Listar bots de ASF |
| `POST /api/asf/redeem` | Canjear key via ASF |
| `POST /api/asf/redeem-all` | Canjear todas las keys pendientes |

## API

| Ruta | Descripción |
|---|---|
| `GET /api/health` | Health check + bots online + stats |
| `GET /api/codes` | Listar códigos (filtros: status, code_type, source) |
| `GET /api/stats` | Estadísticas |
| `POST /api/redeem` | Canjear código |
| `POST /api/validate/{id}` | Validar formato de key |
| `POST /api/auto-enter` | Auto-participar en giveaway |
| `POST /api/cleanup` | Limpiar entradas antiguas |
| `GET /api/export/json` | Exportar a JSON |
| `GET /api/export/csv` | Exportar a CSV |
| `POST /api/config/reddit` | Configurar Reddit |
| `POST /api/config/steam-session` | Configurar cuenta Steam |
| `GET/POST /api/config/notifications` | Configurar notificaciones |
| `WS /ws` | WebSocket para tiempo real |
| `GET /api/scrape` | Forzar ejecución de scrapers |

## MCP Server (Model Context Protocol)

El backend expone un **servidor MCP via SSE** montado en `/mcp`. Compatible con asistentes IA que soporten el protocolo MCP.

### Tools disponibles (7)

| Tool | Descripción |
|---|---|
| `search_free_games` | Ejecuta todos los scrapers |
| `list_found_codes` | Consulta códigos con filtros (estado, tipo, fuente) |
| `redeem_with_asf` | Envía key a ASF para canje |
| `get_asf_status` | Estado de los bots de ASF |
| `get_stats` | Estadísticas del sistema |
| `validate_key` | Valida formato de key Steam |
| `configure_asf` | Actualiza configuración de conexión ASF |

### Conexión

```
SSE endpoint: /mcp/sse
Messages POST: /mcp/messages/
```

## Scrapers

Los scrapers se ejecutan **en paralelo** (ThreadPoolExecutor, max 6 workers) cada 15 minutos vía APScheduler. Cada scraper tiene cooldown de 2 horas tras 3 fallos consecutivos.

- **giveaway_apis**: FreeSteamKeys API, GamerPower API, Givee.Club — resuelve URLs de Steam desde páginas de eventos
- **keysites**: GamerPower, GiveAway.su + Reddit fallback
- **moresources**: CheapShark API, Reddit, Epic Games API, Fanatical
- **gog**: GOG Catalog — free games en GOG.com
- **xbox_catalog**: Xbox Catalog — free games en Xbox
- **steam_store**: Temp free games (-100%), free weekends, F2P
- **steamgifts**: SteamGifts (requiere cookies)
- **twitter**: Nitter instances, cuentas de giveaways
- **telegram**: Canales públicos de keys
- **reddit**: Reddit API con OAuth (bloqueado desde GCP)
- **BaseScraper**: Clase abstracta compartida con `_fetch()`, `_headers()`, y `make_result()`

---

## Deploy

### Docker Compose (recomendado)

```bash
docker compose up -d --build
```

Esto levanta ASF + Backend + Frontend. ASF usa `network_mode: host`.

### GCP VM

El repo se auto-despliega a GCP vía GitHub Actions al hacer push a `main` (IP configurada como `GCP_VM_HOST` en secrets del repo):

1. SSH a la VM como `medalcode`
2. `git pull origin main`
3. `pip install -r requirements.txt` y restart del servicio
4. `npm install && npm run build` en frontend

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `STEAM_HUNTER_API_KEY` | `""` | API Key para autenticación Bearer |
| `ASF_IPC_URL` | `http://127.0.0.1:1242` | URL del IPC de ASF |
| `ASF_IPC_PASSWORD` | `""` | Password del IPC (vacío = sin auth) |
| `ASF_DEFAULT_BOT` | `principal` | Bot por defecto para canjes |
| `ASF_AUTO_REDEEM` | `true` | Auto-canjear al detectar keys |
| `XBOX_CATALOG_PAGES` | `15` | Páginas a escanear en catálogo Xbox |

## Migraciones (Alembic)

```bash
cd backend
alembic upgrade head    # Aplicar migraciones
alembic revision --autogenerate -m "desc"   # Crear nueva migración
```

## Tests

```bash
cd backend
pytest -v
```

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
|---|---|---|---|---|
| `principal` | forgerb | 76561198051997214 | ✅ Farming, Wallet 94¢ |
| `secundaria1` | forgerb2 | 76561199125215505 | ✅ Limitada (no farmea) |
| `secundaria2` | — | — | ❌ Deshabilitado en config |
| `tryh4rd` | tryh4rdgame | 76561198691635889 | ❌ Template en repo, no existe en Docker |

## Historial de cambios recientes

### 2026-06-08 — Sesión completa: revisión de todas las tiendas + cuentas

- **Epic LISA**: Se descubrió que LISA: The Definitive Edition **no era un juego gratis** sino que estaba en oferta (-45%). El `addToCart` funcionaba porque agrega cualquier oferta al carrito (incluso pagas). Falsa alarma.
- **quickPurchase API descubierta**: Endpoint `orderprocessor-public-service-ecomprod01.ol.epicgames.com/orderprocessor/api/shared/accounts/{id}/orders/quickPurchase` para free claims. Retorna `CHECKOUT` pero no se completó el reclamo para LISA (consistente con que no era gratis).
- **Browser non-headless**: Chromium con `--remote-debugging-port=43465` + `--disable-blink-features=AutomationControlled` funciona a través de Cloudflare en display `:0`. Firefox no disponible (Playwright no soporta Ubuntu 26.04).
- **DB review**: 466 entradas en DB, solo ~8 redeemeadas (1.7%). 140 GOG, 90 Xbox sin reclamar.
- **GOG**: 140 items gratis pero son mods/DLCs/prologues que requieren base game. Ninguno redeemado.
- **Xbox**: 90 items F2P permanente (Apex, Destiny 2, CoD Warzone, etc.). No promocional.
- **Amazon Prime Gaming**: **No hay scraper** — gap importante.
- **ASF**: Docker con 2 bots activos (principal/secundaria1), secundaria2 deshabilitado, tryh4rd no existe en Docker.
- **Epic actuales**: Rogue Waters + Songs of Conquest ya "In Library". Próximos Jun 11: The Ouroboros King, Warhammer 40K Speed Freeks.

### Anteriores

- **2026-06-07 — Epic Extras claiming**: 10/16 Epic Extras items reclamados vía GraphQL + browser (Fall Guys, Infinity Nikki, WW, NW, STO, Asphalt, WW, WoW, Idle Champions, Firestone). Discord Nitro/Duet Night/RAVEN2 no reclamables (requieren base game).
- **2026-06-07 — GCP Budgets**: Configurados budgets de $1, $10, $100, $1000 CLP con alertas al 50%, 90%, 100%.
- **2026-06-07 — ASF 3 cuentas**: Configuradas y operativas (principal/secundaria1/tryh4rd). Farming completado.
- **GiveawayAPIScraper**: Nuevo scraper con 3 fuentes (FreeSteamKeys API + GamerPower API + Givee.Club HTML) que resuelve URLs de Steam desde páginas de eventos
- **Steam URL resolution**: Scraper fetchea páginas de giveaways para extraer `store.steampowered.com/app/<ID>` y permitir auto-redeem
- **ASF IPC fix**: Se eliminó `IPCPassword` de ASF (bug en v6.3.6.1 causa 401 en todas las requests); IPC funciona sin auth en localhost
- **Skip non-free**: Eliminado fallback `app/<ID>` — juegos que no son free-to-keep se marcan como `skipped`
- **Retry existing**: El auto-redeem ahora reprocesa entradas existentes en estado `new` que no se pudieron canjear antes
- **ASF Client fix**: `get_bots()` ahora parsea correctamente la respuesta de ASF IPC (formato dict-keyed por bot)
- **Multi-bot redeem**: Auto-redeem prueba los 3 bots en secuencia, no solo el default
- **Free game detection**: Helper `_get_free_sub()` que obtiene el sub ID promocional desde la API de Steam
- **Scheduler fix**: Se agregó `scheduler.start()` que faltaba; scrapers ahora corren cada 15 min
