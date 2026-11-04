import logging
from collections import defaultdict
from typing import Dict, List, Any
import aiohttp
from src.config import config

logger = logging.getLogger(__name__)

MODELS_PRIORITY = [
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

SYSTEM_INSTRUCTION = (
    "Bạn là 'Bot Secretary' (@Kayhuyn_bot), một trợ lý ảo thông minh, nhiệt tình và thân thiện. "
    "Bạn hỗ trợ người dùng giải đáp câu hỏi, dịch thuật, lập trình, tóm tắt và xử lý thông tin. "
    "Hãy luôn trả lời bằng tiếng Việt (hoặc theo ngôn ngữ người dùng nhắn), định dạng Markdown rõ ràng, dễ đọc."
)


class GeminiApiService:
    """Service tích hợp Google Gemini API qua async HTTP client (aiohttp)."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or config.api_key or config.gemini_api_key
        self.api_type = "gemini"
        # Lưu lịch sử chat {user_id: [{"role": "user"|"model", "parts": [{"text": "..."}]}]}
        self.conversations: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.max_history_turns = 10

    def is_configured(self) -> bool:
        """Kiểm tra xem API Key đã sẵn sàng chưa."""
        return bool(self.api_key and self.api_key.strip())

    def reset_conversation(self, user_id: int) -> None:
        """Xóa lịch sử hội thoại của user."""
        if user_id in self.conversations:
            self.conversations[user_id].clear()
            logger.info("Đã xóa lịch sử của user %s", user_id)

    async def process_prompt(self, user_text: str, user_id: int) -> str:
        """Gửi prompt tới Gemini và trả về câu trả lời dạng async."""
        if not self.is_configured():
            return (
                "⚠️ Bot hiện chưa được cấu hình API Key.\n"
                "Vui lòng kiểm tra lại file `.env`."
            )

        history = self.conversations[user_id]
        new_user_message = {
            "role": "user",
            "parts": [{"text": user_text}]
        }
        contents = list(history) + [new_user_message]

        payload = {
            "contents": contents,
            "system_instruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
        }

        timeout = aiohttp.ClientTimeout(total=25)
        last_error = None

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for model_name in MODELS_PRIORITY:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                try:
                    logger.info("Đang gọi Gemini model '%s' cho user %s...", model_name, user_id)
                    async with session.post(url, json=payload) as resp:
                        data = await resp.json()

                        if resp.status == 200:
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                reply_text = "".join(p.get("text", "") for p in parts if "text" in p)
                                if reply_text:
                                    # Lưu vào lịch sử
                                    history.append(new_user_message)
                                    history.append({
                                        "role": "model",
                                        "parts": [{"text": reply_text}]
                                    })
                                    if len(history) > self.max_history_turns * 2:
                                        self.conversations[user_id] = history[-self.max_history_turns * 2:]
                                    return reply_text

                        # Nếu lỗi 503 / 429 quá tải, thử model tiếp theo
                        error_msg = data.get("error", {}).get("message", f"HTTP {resp.status}")
                        logger.warning("Model %s trả về lỗi: %s. Thử model tiếp...", model_name, error_msg)
                        last_error = error_msg

                except Exception as e:
                    logger.warning("Gọi model %s gặp lỗi kết nối: %s", model_name, e)
                    last_error = str(e)
                    continue

        return (
            "⚠️ Hệ thống AI hiện đang bận hoặc quá tải tạm thời.\n"
            f"Chi tiết: {last_error}\n"
            "Vui lòng thử lại sau giây lát!"
        )


api_service = GeminiApiService()
