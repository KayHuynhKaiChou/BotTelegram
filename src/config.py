import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Tải cấu hình từ file .env
load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    """Cấu hình toàn hệ thống bot."""
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    api_key: str = os.getenv("API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    api_type: str = os.getenv("API_TYPE", "gemini")
    default_subscriber_ids: str = os.getenv("DEFAULT_SUBSCRIBER_IDS", "")

    def validate(self) -> None:
        """Kiểm tra tính hợp lệ của các biến môi trường thiết yếu."""
        if not self.telegram_bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN chưa được thiết lập trong file .env!"
            )


config = AppConfig()
