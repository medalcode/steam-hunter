import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

from .database import init_db, SessionLocal, FoundCode, ASFConfig
from .asf_client import ASFClient
from .validator import validate_key_format

logger = logging.getLogger(__name__)

server = Server("steam-hunter")


def _get_asf_client(db=None):
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    try:
        config = db.query(ASFConfig).first()
        if config and config.ipc_url:
            return ASFClient(config.ipc_url, config.ipc_password)
        return ASFClient()
    finally:
        if close_db:
            db.close()


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_free_games",
            description="Ejecuta todos los scrapers configurados (Reddit, SteamDB, GamerPower, Epic Games, etc.) buscando juegos gratis, giveaways y keys. Los resultados se guardan en la base de datos.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="list_found_codes",
            description="Lista los códigos/giveaways encontrados con filtros opcionales por estado, tipo o fuente.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filtrar por estado: new, redeemed, failed, expired",
                        "enum": ["new", "redeemed", "failed", "expired"],
                    },
                    "code_type": {
                        "type": "string",
                        "description": "Filtrar por tipo: key, gift_link, giveaway",
                        "enum": ["key", "gift_link", "giveaway"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Máximo de resultados (max 100)",
                        "default": 20,
                    },
                },
            },
        ),
        Tool(
            name="redeem_with_asf",
            description="Envía una key encontrada a ArchiSteamFarm vía IPC para canjearla en Steam.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code_id": {
                        "type": "integer",
                        "description": "ID del código a canjear (obténlo de list_found_codes)",
                    },
                    "bot": {
                        "type": "string",
                        "description": "Nombre del bot de ASF a usar (opcional, usa el default configurado)",
                    },
                },
                "required": ["code_id"],
            },
        ),
        Tool(
            name="get_asf_status",
            description="Verifica el estado de ArchiSteamFarm: bots conectados, estado de farming, si está online.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_stats",
            description="Estadísticas de códigos encontrados y canjeados: totales por estado y tipo.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="validate_key",
            description="Valida el formato de una key de Steam (XXXXX-XXXXX-XXXXX).",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "La key de Steam a validar",
                    },
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="configure_asf",
            description="Configura la conexión con ArchiSteamFarm (URL IPC, password, bot por defecto).",
            inputSchema={
                "type": "object",
                "properties": {
                    "ipc_url": {
                        "type": "string",
                        "description": "URL del IPC de ASF (ej: http://localhost:1243)",
                    },
                    "ipc_password": {
                        "type": "string",
                        "description": "Password del IPC de ASF",
                    },
                    "default_bot": {
                        "type": "string",
                        "description": "Nombre del bot por defecto para canjes",
                    },
                    "auto_redeem": {
                        "type": "boolean",
                        "description": "Activar canje automático al encontrar keys",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    db = SessionLocal()
    try:
        if name == "search_free_games":
            return await _handle_search_free_games()
        elif name == "list_found_codes":
            return await _handle_list_found_codes(db, arguments)
        elif name == "redeem_with_asf":
            return await _handle_redeem_with_asf(db, arguments)
        elif name == "get_asf_status":
            return await _handle_get_asf_status(db)
        elif name == "get_stats":
            return await _handle_get_stats(db)
        elif name == "validate_key":
            return await _handle_validate_key(arguments)
        elif name == "configure_asf":
            return await _handle_configure_asf(db, arguments)
        else:
            return [TextContent(type="text", text=f"Tool not found: {name}")]
    finally:
        db.close()


async def _handle_search_free_games() -> list[TextContent]:
    from .scheduler import run_scrapers_once
    from .database import SessionLocal as DbSession, SearchSource

    db_cfg = DbSession()
    try:
        source = db_cfg.query(SearchSource).filter(SearchSource.name == "reddit").first()
        reddit_scraper = None
        if source and source.config:
            from .scrapers.reddit import RedditScraper
            cfg = source.config
            reddit_scraper = RedditScraper(
                cfg.get("client_id", ""),
                cfg.get("client_secret", ""),
                cfg.get("user_agent", "steam-hunter/1.0"),
            )
    finally:
        db_cfg.close()

    loop = asyncio.get_event_loop()
    new_entries = await loop.run_in_executor(
        None, lambda: run_scrapers_once(reddit_scraper=reddit_scraper)
    )

    if not new_entries:
        return [TextContent(type="text", text="Búsqueda completada. No se encontraron códigos nuevos.")]

    summary = {}
    for e in new_entries:
        summary[e.code_type] = summary.get(e.code_type, 0) + 1

    lines = [f"Búsqueda completada. {len(new_entries)} códigos nuevos encontrados:"]
    for t, c in summary.items():
        lines.append(f"  - {t}: {c}")
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_list_found_codes(db: SessionLocal, arguments: dict) -> list[TextContent]:
    from sqlalchemy import desc

    status = arguments.get("status")
    code_type = arguments.get("code_type")
    limit = min(arguments.get("limit", 20), 100)

    query = db.query(FoundCode).order_by(desc(FoundCode.found_at))
    if status:
        query = query.filter(FoundCode.status == status)
    if code_type:
        query = query.filter(FoundCode.code_type == code_type)

    codes = query.limit(limit).all()
    if not codes:
        return [TextContent(type="text", text="No se encontraron códigos.")]

    lines = [f"{'ID':<4} {'Tipo':<10} {'Estado':<10} {'Fuente':<20} {'Código/URL':<40} {'Fecha':<20}",
             "-" * 104]
    for c in codes:
        ts = c.found_at.strftime("%Y-%m-%d %H:%M") if c.found_at else ""
        code_display = (c.code[:37] + "...") if c.code and len(c.code) > 40 else (c.code or "")
        source_display = (c.source[:17] + "...") if len(c.source) > 20 else c.source
        lines.append(f"{c.id:<4} {c.code_type:<10} {c.status:<10} {source_display:<20} {code_display:<40} {ts:<20}")

    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_redeem_with_asf(db: SessionLocal, arguments: dict) -> list[TextContent]:
    code_id = arguments["code_id"]
    bot = arguments.get("bot")

    code_entry = db.query(FoundCode).filter(FoundCode.id == code_id).first()
    if not code_entry:
        return [TextContent(type="text", text=f"Código ID {code_id} no encontrado.")]
    if code_entry.status == "redeemed":
        return [TextContent(type="text", text="Este código ya fue canjeado.")]
    if code_entry.code_type != "key":
        return [TextContent(type="text", text="Solo keys pueden canjearse vía ASF.")]

    asf_config = db.query(ASFConfig).first()
    client = _get_asf_client(db)
    bot_name = bot or (asf_config.default_bot if asf_config else "principal")

    keys = [k.strip() for k in code_entry.code.replace(",", " ").split()]
    results = []
    for key in keys:
        result = client.redeem_key(bot_name, key)
        status_icon = "✅" if result["success"] else "❌"
        results.append(f"  {status_icon} {key}: {result.get('message', 'sin respuesta')}")

    any_success = any(r.get("success") for r in results)
    if any_success:
        code_entry.status = "redeemed"
        code_entry.redeemed_at = datetime.now(timezone.utc)
    else:
        code_entry.status = "failed"
        code_entry.error_message = results[0] if results else "Error desconocido"
    db.commit()

    lines = [f"Resultado del canje para código #{code_id} en bot '{bot_name}':"] + results
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_get_asf_status(db: SessionLocal) -> list[TextContent]:
    client = _get_asf_client(db)
    bots = client.get_bots()
    if not bots:
        return [TextContent(type="text", text="ASF no está accesible o no hay bots configurados.")]

    lines = [f"{'Bot':<20} {'Estado':<15} {'Juegos farmeando':<10}", "-" * 45]
    for b in bots:
        lines.append(f"{b['name']:<20} {b.get('status', '?'):<15} {b.get('games', 0):<10}")
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_get_stats(db: SessionLocal) -> list[TextContent]:
    total = db.query(FoundCode).count()
    new_count = db.query(FoundCode).filter(FoundCode.status == "new").count()
    redeemed = db.query(FoundCode).filter(FoundCode.status == "redeemed").count()
    failed = db.query(FoundCode).filter(FoundCode.status == "failed").count()
    expired = db.query(FoundCode).filter(FoundCode.status == "expired").count()

    lines = [
        "📊 Estadísticas de Steam Hunter:",
        f"  Total:     {total}",
        f"  Nuevos:    {new_count}",
        f"  Canjeados: {redeemed}",
        f"  Fallidos:  {failed}",
        f"  Expirados: {expired}",
    ]
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_validate_key(arguments: dict) -> list[TextContent]:
    key = arguments["key"]
    result = validate_key_format(key)
    if result["valid"]:
        return [TextContent(type="text", text=f"✅ La key '{key}' tiene formato válido.")]
    return [TextContent(type="text", text=f"❌ La key '{key}' es inválida: {result['reason']}")]


async def _handle_configure_asf(db: SessionLocal, arguments: dict) -> list[TextContent]:
    asf_config = db.query(ASFConfig).first()
    if not asf_config:
        asf_config = ASFConfig()
        db.add(asf_config)

    changed = []
    if "ipc_url" in arguments:
        asf_config.ipc_url = arguments["ipc_url"]
        changed.append(f"IPC URL → {arguments['ipc_url']}")
    if "ipc_password" in arguments:
        asf_config.ipc_password = arguments["ipc_password"]
        changed.append("IPC Password → actualizado")
    if "default_bot" in arguments:
        asf_config.default_bot = arguments["default_bot"]
        changed.append(f"Bot default → {arguments['default_bot']}")
    if "auto_redeem" in arguments:
        asf_config.auto_redeem = arguments["auto_redeem"]
        changed.append(f"Auto-redeem → {arguments['auto_redeem']}")

    db.commit()

    if not changed:
        current = {
            "ipc_url": asf_config.ipc_url,
            "has_password": bool(asf_config.ipc_password),
            "default_bot": asf_config.default_bot,
            "auto_redeem": asf_config.auto_redeem,
        }
        lines = ["Configuración actual de ASF:"] + [f"  {k}: {v}" for k, v in current.items()]
        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text="Configuración ASF actualizada:\n" + "\n".join(changed))]


async def main():
    from mcp.server.stdio import stdio_server

    init_db()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="steam-hunter",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
