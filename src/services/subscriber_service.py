import json
import logging
import os
from typing import List, Set

logger = logging.getLogger(__name__)

SUBSCRIBER_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "subscribers.json"
)


class SubscriberService:
    """Quản lý danh sách người dùng nhận tin nhắn từ vựng tự động."""

    def __init__(self):
        self.subscribers: Set[int] = set()
        self.load_subscribers()

    def load_subscribers(self) -> None:
        """Đọc danh sách chat_id từ file JSON."""
        if os.path.exists(SUBSCRIBER_FILE):
            try:
                with open(SUBSCRIBER_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.subscribers = set(data.get("subscribers", []))
                    logger.info("Đã tải %d subscribers từ file", len(self.subscribers))
            except Exception as e:
                logger.error("Lỗi khi đọc file subscribers: %s", e)
                self.subscribers = set()
        else:
            self.subscribers = set()

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

    def get_all(self) -> List[int]:
        """Lấy tất cả subscriber IDs."""
        return list(self.subscribers)


subscriber_service = SubscriberService()
