import logging
import sys

# Đảm bảo console Windows in tiếng Việt UTF-8 không bị lỗi charmap
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.config import config
from src.handlers.command_handlers import (
    start_command,
    help_command,
    status_command,
    reset_command,
)
from src.handlers.message_handlers import handle_user_text_message

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


def main() -> None:
    """Điểm khởi chạy ứng dụng Telegram Bot."""
    try:
        config.validate()
    except ValueError as e:
        logger.error("Lỗi cấu hình: %s", e)
        sys.exit(1)

    logger.info("Đang khởi động Telegram Bot...")

    application = ApplicationBuilder().token(config.telegram_bot_token).build()

    # Đăng ký các command handler
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("reset", reset_command))

    # Đăng ký handler xử lý tin nhắn thường
    application.add_handler(
        MessageHandler(filters.TEXT & (~filters.COMMAND), handle_user_text_message)
    )

    logger.info("Bot đã sẵn sàng và đang lắng nghe (polling)...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
