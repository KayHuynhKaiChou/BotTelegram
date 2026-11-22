import json
import logging
import os
from aiohttp import web
from src.services.vocab_service import vocab_service

logger = logging.getLogger(__name__)

STATIC_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "index.html"
)


async def handle_health(request: web.Request) -> web.Response:
    """Endpoint Healthcheck cho Render/Cloud."""
    return web.Response(text="Bot is running healthy!", content_type="text/plain")


async def handle_mini_app(request: web.Request) -> web.Response:
    """Phục vụ trang giao diện Telegram Mini App (Flashcard UI)."""
    if os.path.exists(STATIC_INDEX_PATH):
        with open(STATIC_INDEX_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        return web.Response(text=content, content_type="text/html")
    return web.Response(text="Mini App HTML not found", status=404)


async def handle_api_vocabs(request: web.Request) -> web.Response:
    """API trả về danh sách 1.445 từ vựng cho Mini App."""
    category = request.query.get("category", "all")
    vocabs = vocab_service.vocabularies

    if category != "all":
        vocabs = [v for v in vocabs if category.lower() in v["source"].lower()]

    data = {
        "total": len(vocabs),
        "category": category,
        "vocabularies": vocabs
    }
    return web.json_response(data)


def register_web_routes(app: web.Application) -> None:
    """Đăng ký các route Web và API vào aiohttp application."""
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/app", handle_mini_app)
    app.router.add_get("/api/vocabs", handle_api_vocabs)
    logger.info("Đã đăng ký routes cho Telegram Mini App và API từ vựng.")
