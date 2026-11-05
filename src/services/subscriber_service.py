import json
import logging
import os
from typing import List, Set
from src.config import config

logger = logging.getLogger(__name__)

SUBSCRIBER_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "subscribers.json"
)


class SubscriberService:
    """Quản lý danh sách người dùng nhận tin nhắn từ vựng tự động."""

    def __init__(self):
        self.subscribers: Set[int] = set()
        self.load_subscribers()

    def _get_env_subscribers(self) -> Set[int]:
        """Lấy các ID được cấu hình qua biến môi trường DEFAULT_SUBSCRIBER_IDS."""
        env_ids = set()
        if config.default_subscriber_ids:
            for item in config.default_subscriber_ids.split(","):
                item = item.strip()
                if item.isdigit() or (item.startswith("-") and item[1:].isdigit()):
                    env_ids.add(int(item))
        return env_ids

    def load_subscribers(self) -> None:
        """Đọc danh sách chat_id từ file JSON kết hợp với biến môi trường."""
        file_ids = set()
        if os.path.exists(SUBSCRIBER_FILE):
            try:
                with open(SUBSCRIBER_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    file_ids = set(data.get("subscribers", []))
            except Exception as e:
                logger.error("Lỗi khi đọc file subscribers: %s", e)

        # Gộp cả ID từ file và ID từ biến môi trường (không sợ mất khi container restart)
        self.subscribers = file_ids.union(self._get_env_subscribers())
        logger.info("Đã tải tổng cộng %d subscribers (từ file + env)", len(self.subscribers))

    def save_subscribers(self) -> None:
        """Ghi danh sách chat_id vào file JSON."""
        os.makedirs(os.path.dirname(SUBSCRIBER_FILE), exist_ok=True)
        try:
            with open(SUBSCRIBER_FILE, "w", encoding="utf-8") as f:
                json.dump({"subscribers": list(self.subscribers)}, f, indent=2)
        except Exception as e:
            logger.error("Lỗi khi lưu subscribers: %s", e)

    def add_subscriber(self, chat_id: int) -> bool:
        """Thêm chat_id vào danh sách nhận lịch nhắc."""
        if chat_id not in self.subscribers:
            self.subscribers.add(chat_id)
            self.save_subscribers()
            logger.info("Đã thêm subscriber mới: %s", chat_id)
            return True
        return False

    def remove_subscriber(self, chat_id: int) -> bool:
        """Xóa chat_id khỏi danh sách."""
        if chat_id in self.subscribers:
            self.subscribers.remove(chat_id)
            self.save_subscribers()
            logger.info("Đã xóa subscriber: %s", chat_id)
            return True
        return False

    def is_subscribed(self, chat_id: int) -> bool:
        """Kiểm tra xem user đã đăng ký chưa."""
        return chat_id in self.subscribers

    def get_all(self) -> List[int]:
        """Lấy tất cả subscriber IDs."""
        # Luôn đảm bảo nạp đủ các ID từ biến môi trường
        return list(self.subscribers.union(self._get_env_subscribers()))


subscriber_service = SubscriberService()
