# Steam Hunter

Bot automatizado que busca códigos gratis, giveaways y juegos temporalmente gratis de Steam en múltiples fuentes (FreeSteamKeys, GamerPower, Givee.Club, Steam Store, CheapShark, Epic Games, etc.) y los canjea automáticamente vía ArchiSteamFarm.

## Stack

- **Backend**: Python + FastAPI + SQLite + APScheduler + **MCP Server (SSE)**
- **Frontend**: React + Vite + TypeScript (React.lazy code splitting)
- **Despliegue**: Docker Compose + CI/CD a GCP
- **ASF**: ArchiSteamFarm v6.3.6.1 (Docker, red aislada steam_hunter_net)

## Seguridad

- **CORS**: Restringido a `localhost:5173`, `localhost:8000`, `127.0.0.1:8000`
- **Rate limiting**: 3000 requests/60s por IP en endpoints `/api/*` (TTLCache, sin memory leak)
- **nginx rate limiting**: 30r/s con burst 50 en frontend
- **SSL/TLS recomendado**: nginx config preparado para certbot/Let's Encrypt
- **Security headers**: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`
- **API Key requerible**: Setear `STEAM_HUNTER_API_KEY` para requerir Bearer token en TODAS las rutas, incluyendo MCP Server, WebSocket, y API
- **WebSocket autenticado**: Token vía query param `?token=` o header `Authorization`
- **MCP Server asegurado**: Ya no está excluido de autenticación — requiere API key
- **XSS prevenido**: Validación de protocolo (`http://`/`https://`) en todos los hrefs del frontend
- **SSRF prevenido**: Validación de URLs en `redeemer.py` contra dominios conocidos de Steam
- **Secretos**: `fgc-data/browser/` excluido de git (contenía cookies de sesión)

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
| **Amazon Prime Gaming** | Juegos mensuales | ✅ Vía Reddit /r/FreeGameFindings |
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

### ¡Importante! ArchiSteamFarm (ASF) es exclusivo para Steam

La integración actual asume que usas ASF para canjear en automático. ASF **no** puede canjear juegos de Epic, GOG o Amazon Prime. `steam-hunter` los rastreará y te notificará en el dashboard, pero no los canjeará.

Para automatizar la reclamación en **Epic Games, GOG y Prime Gaming**, se recomienda usar [FreeGamesClaimer](https://github.com/vogler/free-games-claimer) junto a tu setup. Hemos incluido un archivo de ejemplo `fgc-docker-compose.yml` en la raíz de este proyecto.

Para levantar todo el ecosistema (Steam Hunter + ASF + FGC), simplemente corre el ejecutable incluido:
```bash
./start.sh
```
Ingresa al puerto `:6080` de tu servidor en el navegador para hacer el login inicial (resolver captchas), y FGC se encargará de reclamar todos los juegos diarios y semanales en esas 3 plataformas por ti.

---

## 🏗️ Arquitectura y Flujo de Datos

```
[25+ Sources] ──> [12 Scrapers en paralelo (6 workers)] ──> [Parser + Validator] ──> [SQLite DB]
                                              │                        │
                            ┌─────────────────┘                        └─────────────────┐
                            ▼                                                          ▼
                    [Auto-Redeem via ASF IPC]                                  [WebSocket Broadcast]
                    (sesión DB propia por operación)                                  + Notifications
                                                                                  (Discord / Telegram)
    [MCP Server (SSE)] ──> [7 tools para asistentes AI]
    (requiere API key)
```

## Autenticación API

Requerible via `STEAM_HUNTER_API_KEY`. Protege todas las rutas: API REST, WebSocket, MCP Server, SSE, y docs.

## Integración ASF (ArchiSteamFarm)

En Docker, ASF corre como servicio independiente en la red `steam_hunter_net` (puerto `1242`). Backend se conecta a `http://asf:1242` con healthcheck.

Para configurar bots manualmente, editar los JSONs en `./asf-config/config/`.

### Endpoints ASF

| Ruta | Descripción |
|---|---|
| `GET /api/asf/bots` | Listar bots de ASF |
| `POST /api/asf/redeem` | Canjear key via ASF |
| `POST /api/asf/redeem-all` | Canjear todas las keys pendientes |
| `POST /api/asf/retry-failed` | Reintentar canjes fallidos |

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

### Conexión (requiere API key si configurada)

```
SSE endpoint: /mcp/sse (Authorization: Bearer <API_KEY>)
Messages POST: /mcp/messages/ (Authorization: Bearer <API_KEY>)
```

## Scrapers

Los scrapers se ejecutan **en paralelo** (ThreadPoolExecutor, max 6 workers) cada 15 minutos vía APScheduler. Cada scraper tiene cooldown de 2 horas tras 3 fallos consecutivos (thread-safe con `threading.Lock`).

- **giveaway_apis**: FreeSteamKeys API, GamerPower API, Givee.Club — resuelve URLs de Steam desde páginas de eventos
- **keysites**: GamerPower, GiveAway.su + Reddit fallback
- **moresources**: CheapShark API, Reddit, Epic Games API, Fanatical, Prime Gaming
- **gog**: GOG Catalog — free games en GOG.com
- **xbox_catalog**: Xbox Catalog — free games en Xbox
- **steam_store**: Temp free games (-100%), free weekends, F2P
- **steamgifts**: SteamGifts (requiere cookies)
- **twitter**: Nitter instances, cuentas de giveaways
- **telegram**: Canales públicos de keys
- **reddit**: Reddit API con OAuth leyendo posts y comentarios ninja en 12 subreddits
- **BaseScraper**: Clase abstracta — USER_AGENTS y BASE_HEADERS centralizados en `constants.py`

---

## Deploy

### Docker Compose (recomendado)

Puedes levantar todo usando el script automatizado (incluye FGC):
```bash
./start.sh
```

O si solo quieres levantar Steam Hunter + ASF:
```bash
docker compose up -d --build
```

Esto levanta ASF + Backend + Frontend en una red aislada `steam_hunter_net`:
- **ASF**: `http://asf:1242` con healthcheck
- **Backend**: `http://backend:8000` con healthcheck
- **Frontend**: `http://localhost:80` (vía nginx, con rate limiting 30r/s)

### GCP VM

El repo se auto-despliega a GCP vía GitHub Actions al hacer push a `main`:
1. CI ejecuta `npm ci && npm run build` y `pytest` como test stage
2. SSH deploy via `appleboy/ssh-action` usando secrets: `GCP_VM_HOST`, `GCP_VM_USERNAME`, `GCP_VM_SSH_KEY`

### Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `STEAM_HUNTER_API_KEY` | `""` | API Key para autenticación Bearer (protege API + WS + MCP) |
| `ASF_IPC_URL` | `http://asf:1242` | URL del IPC de ASF |
| `ASF_IPC_PASSWORD` | `""` | Password del IPC |
| `ASF_DEFAULT_BOT` | `principal` | Bot por defecto para canjes |
| `ASF_AUTO_REDEEM` | `true` | Auto-canjear al detectar keys |
| `XBOX_CATALOG_PAGES` | `15` | Páginas a escanear en catálogo Xbox |
| `LOG_LEVEL` | `INFO` | Nivel de logging |

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

### 2026-06-21 — Auditoría Completa de Seguridad, Calidad e Infraestructura

- **Seguridad CRÍTICA**:
  - MCP Server ahora requiere API key para todas las tools (SSE + messages)
  - WebSocket autenticado vía `?token=` query param o header `Authorization`
  - XSS prevenido: validación de protocolos `http://`/`https://` en todos los hrefs
  - SSRF prevenido: validación de URLs en redeemer contra dominios conocidos de Steam
  - `fgc-data/browser/` excluido de git (contenía cookies de sesión de Epic/GOG/Amazon)
- **Race conditions corregidas**:
  - `threading.Lock` en `_scraper_cooldowns` (thread-safe)
  - Sesiones DB separadas para redeem (cada operación usa su propia sesión, sin compartir con el scheduler)
- **ASF configs**:
  - Creados templates: `ASF.json`, `IPC.config`, `principal.json`, `secundaria1.json`
  - ASF ahora corre en red Docker `steam_hunter_net` con healthcheck (ya no `network_mode: host`)
- **Calidad de código**:
  - USER_AGENTS y BASE_HEADERS centralizados en `backend/app/constants.py` (8 scrapers actualizados)
  - Inconsistencia parser/validator corregida: ambos usan exactamente 3 grupos
  - `pyproject.toml` con ruff, pytest, mypy config
  - TS strict mode: `strict: true` en ambos tsconfigs
  - Pre-commit hooks: `.pre-commit-config.yaml` con ruff
- **Frontend**:
  - Code splitting: ConfigModal con `React.lazy` + `Suspense`
  - Skeleton loaders en tabla de códigos
  - API client: timeout 30s, verificación `res.ok`, header `Authorization` automático
  - Toast race condition corregida (IDs incrementales)
  - Filter remount eliminado (CodeTable ya no se desmonta al cambiar filtros)
  - `index.css` simplificado: eliminados estilos conflictivos con `App.css`
- **Infraestructura**:
  - nginx: security headers, rate limiting (30r/s), WebSocket timeout extendido
  - Imágenes Docker con tags fijos (ASF `v6.3.6.1`, no más `latest`)
  - Puertos restringidos a `127.0.0.1` (frontend y VNC)
  - CI/CD: IP/username movidos a secrets, test stage añadido
  - `start.sh`: `set -e`, Docker check, verificación post-deploy
  - Dockerfile: `COPY --chown=app:app . .` single layer

### 2026-06-19 — Rediseño Premium Frontend, Nginx Proxy y Estabilidad

- **Rediseño Premium**: Se reconstruyó completamente la interfaz web (`index.html` y `App.css`) utilizando una estética moderna de "Dark Glassmorphism", tipografía premium (Outfit/Inter) y micro-animaciones interactivas.
- **Nginx Proxy & CORS**: Se configuró Nginx en producción para hacer proxy pasivo de `/api/` y `/ws` hacia el backend. Se refactorizó el cliente React para usar rutas relativas, eliminando por completo los bloqueos CORS (Cross-Origin Resource Sharing).
- **Rate Limit**: Se aumentó el límite de seguridad de FastAPI de 30 a 3,000 requests por minuto, previniendo bloqueos accidentales al refrescar masivamente el frontend.
- **Boot-loop de Docker**: Se eliminó la dependencia bloqueante del `healthcheck` de ASF en `docker-compose.yml`, permitiendo un inicio asíncrono y evitando que el backend reinicie constantemente si ASF demora en conectarse a Steam.
- **Manejo de WebSockets**: Se implementó `run_coroutine_threadsafe` en el backend para poder transmitir notificaciones de WebSocket desde hilos síncronos de manera segura, evitando excepciones asíncronas bloqueantes.

### 2026-06-16 — Prime Gaming, Estabilidad y Fugas de Memoria

- **Amazon Prime Gaming**: Se implementó un scraper en `moresources.py` que lee `r/FreeGameFindings` buscando posts con la etiqueta de "Amazon Prime", solucionando la falta de esta fuente.
- **Concurrencia (SQLite)**: Se optimizó `scheduler.py` para separar los commits de la base de datos de las llamadas HTTP al cliente de ASF. Esto soluciona los errores de `database is locked` cuando el scraper ejecuta en paralelo.
- **Fuga de Memoria**: Se reemplazó el limitador de requests (`_rate_limit_store`) que usaba un diccionario estático en memoria por `cachetools.TTLCache`, previniendo que se acumulen IPs de forma indefinida a lo largo del tiempo.
- **Robustez de Scrapers**: Se añadió un manejo robusto de errores de decodificación JSON (`JSONDecodeError`) en el método base de peticiones y en `giveaway_apis.py` y `moresources.py`, previniendo que respuestas inválidas tiren el hilo del scraper.

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
