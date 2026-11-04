import logging
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from src.services.subscriber_service import subscriber_service
from src.services.vocab_service import vocab_service

logger = logging.getLogger(__name__)

# Múi giờ Việt Nam
VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


class VocabSchedulerService:
    """Quản lý các cron job định kỳ gửi từ vựng vào 10:00 và 18:00 hàng ngày."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=VN_TZ)
        self.bot: Bot = None

    def initialize(self, bot: Bot) -> None:
        """Khởi tạo scheduler với bot instance."""
        self.bot = bot

        # 1. Job 10:00 Sáng mỗi ngày
        self.scheduler.add_job(
            self.broadcast_vocab_to_all,
            trigger="cron",
            hour=10,
            minute=0,
            args=["10:00 SÁNG"],
            id="vocab_morning_10am",
            replace_existing=True
        )

        # 2. Job 18:00 Chiều mỗi ngày
        self.scheduler.add_job(
            self.broadcast_vocab_to_all,
            trigger="cron",
            hour=18,
            minute=0,
            args=["18:00 CHIỀU"],
            id="vocab_evening_6pm",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Scheduler đã kích hoạt: Lên lịch gửi từ vựng vào 10:00 và 18:00 (giờ VN).")

    async def broadcast_vocab_to_all(self, time_label: str = "ĐỊNH KỲ") -> None:
        """Gửi 3 từ vựng ngẫu nhiên tới tất cả người dùng đã đăng ký."""
        if not self.bot:
            logger.error("Bot instance chưa được khởi tạo trong Scheduler!")
            return

        subscribers = subscriber_service.get_all()
        if not subscribers:
            logger.info("Chưa có subscriber nào đăng ký nhận từ vựng.")
            return

        logger.info("Bắt đầu gửi từ vựng cho %d người dùng (Khung giờ: %s)...", len(subscribers), time_label)

        # Lấy nội dung từ vựng kèm ví dụ thông minh
        message_text = await vocab_service.generate_vocab_message(count=3, time_label=time_label)

        for chat_id in subscribers:
            try:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="Markdown"
                )
                logger.info("Đã gửi từ vựng thành công cho chat_id %s", chat_id)
            except Exception as e:
                logger.warning("Không thể gửi tin nhắn cho chat_id %s: %s", chat_id, e)


vocab_scheduler = VocabSchedulerService()
