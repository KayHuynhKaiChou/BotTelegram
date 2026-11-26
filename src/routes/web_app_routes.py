import json
import logging
import os
from aiohttp import web
from src.services.vocab_service import vocab_service
from src.config import config

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


async def handle_api_status(request: web.Request) -> web.Response:
    """API kiểm tra trạng thái và danh sách subscribers thực tế trên server."""
    from src.services.subscriber_service import subscriber_service
    subs = subscriber_service.get_all()
    return web.json_response({
        "status": "online",
        "total_vocab": len(vocab_service.vocabularies),
        "subscribers_count": len(subs),
        "subscribers": subs,
        "has_env_subscribers": bool(config.default_subscriber_ids)
    })


async def handle_cron_trigger(request: web.Request) -> web.Response:
    """Endpoint HTTP Trigger cho cronjob bên ngoài (như cron-job.org).
    Khi gọi vào đây: vừa đánh thức Render dậy vừa gửi ngay từ vựng mà không lo server bị ngủ."""
    from src.services.scheduler_service import vocab_scheduler
    label = request.query.get("label", "10:00 SÁNG")
    count = await vocab_scheduler.broadcast_vocab_to_all(time_label=label)
    return web.json_response({
        "success": True,
        "message": f"Đã gửi từ vựng cho {count} người dùng",
        "subscribers_sent": count
    })


def register_web_routes(app: web.Application) -> None:
    """Đăng ký các route Web và API vào aiohttp application."""
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/app", handle_mini_app)
    app.router.add_get("/api/vocabs", handle_api_vocabs)
    app.router.add_get("/api/status", handle_api_status)
    app.router.add_get("/cron/broadcast-vocab", handle_cron_trigger)
    app.router.add_post("/cron/broadcast-vocab", handle_cron_trigger)
    logger.info("Đã đăng ký routes cho Telegram Mini App, API và Webhook Cron.")
