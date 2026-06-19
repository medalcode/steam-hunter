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
- **moresources**: CheapShark API, Reddit, Epic Games API, Fanatical, Prime Gaming
- **gog**: GOG Catalog — free games en GOG.com
- **xbox_catalog**: Xbox Catalog — free games en Xbox
- **steam_store**: Temp free games (-100%), free weekends, F2P
- **steamgifts**: SteamGifts (requiere cookies)
- **twitter**: Nitter instances, cuentas de giveaways
- **telegram**: Canales públicos de keys
- **reddit**: Reddit API con OAuth leyendo posts y comentarios ninja en 12 subreddits (pcmasterrace, gaming, FreeGameFindings, FREE, etc.)
- **BaseScraper**: Clase abstracta compartida con `_fetch()`, `_headers()`, y `make_result()`

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
