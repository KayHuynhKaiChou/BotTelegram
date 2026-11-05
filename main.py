import asyncio
import logging
import os
import sys
from aiohttp import web
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.config import config
from src.handlers.command_handlers import (
    start_command,
    help_command,
    status_command,
    reset_command,
    vocab_command,
    testcron_command,
    subscribe_command,
    unsubscribe_command,
)
from src.handlers.message_handlers import handle_user_text_message
from src.services.scheduler_service import vocab_scheduler

# Đảm bảo console Windows in tiếng Việt UTF-8 không bị lỗi charmap
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Cấu hình logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


async def healthcheck(request: web.Request) -> web.Response:
    """Endpoint HTTP healthcheck cho Render / Cloud."""
    return web.Response(text="Bot is running healthy!", content_type="text/plain")


async def main() -> None:
    """Điểm khởi chạy ứng dụng Telegram Bot kết hợp Web Healthcheck và Scheduler."""
    try:
        config.validate()
    except ValueError as e:
        logger.error("Lỗi cấu hình: %s", e)
        sys.exit(1)

    # 1. Khởi chạy HTTP server ngầm để Render nhận diện service
    port = int(os.getenv("PORT", "10000"))
    app = web.Application()
    app.router.add_get("/", healthcheck)
    app.router.add_get("/health", healthcheck)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    try:
        await site.start()
        logger.info("Healthcheck web server đã chạy tại port %s", port)
    except Exception as e:
        logger.warning("Không thể bind web port %s: %s", port, e)

    # 2. Khởi tạo Telegram Bot Application
    logger.info("Đang khởi động Telegram Bot...")
    application = ApplicationBuilder().token(config.telegram_bot_token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("vocab", vocab_command))
    application.add_handler(CommandHandler("testcron", testcron_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))

    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_text_message)
    )

    # Khởi chạy Polling bất đồng bộ
    await application.initialize()
    await application.start()

    # 3. Kích hoạt Scheduler Cron Job (10:00 & 18:00 mỗi ngày)
    vocab_scheduler.initialize(application.bot)

    await application.updater.start_polling(drop_pending_updates=True)
    logger.info("Bot đã sẵn sàng và đang lắng nghe (polling)...")

    # Giữ tiến trình chạy liên tục
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Đang dừng ứng dụng...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
