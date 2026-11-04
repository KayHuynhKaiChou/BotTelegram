import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.services.api_service import api_service

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /start."""
    user = update.effective_user
    username = user.first_name if user else "bạn"
    status_api = "🟢 Đã kết nối Gemini AI" if api_service.is_configured() else "🟡 Chưa cấu hình API"

    welcome_text = (
        f"👋 Xin chào {username}!\n\n"
        f"🤖 Tôi là **Bot Secretary** (@Kayhuyn_bot), được tích hợp **Google Gemini AI**.\n"
        f"📊 Trạng thái AI: {status_api}\n\n"
        f"💡 **Tôi có thể làm gì?**\n"
        f"• Trò chuyện, giải đáp thắc mắc mọi chủ đề\n"
        f"• Viết lách, dịch thuật, tóm tắt tài liệu\n"
        f"• Lập kế hoạch, viết code & sửa lỗi lập trình\n\n"
        f"📌 **Lệnh điều khiển:**\n"
        f"/reset - Xóa ngữ cảnh cũ, bắt đầu chủ đề mới\n"
        f"/status - Kiểm tra trạng thái hệ thống và API\n"
        f"/help - Hướng dẫn sử dụng chi tiết\n\n"
        f"👉 Hãy nhắn tin bất kỳ câu hỏi nào để bắt đầu!"
    )
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /help."""
    help_text = (
        "📖 **Hướng dẫn sử dụng Bot Secretary:**\n\n"
        "1. **Trò chuyện trực tiếp**: Gửi bất kỳ câu hỏi nào, bot sẽ suy nghĩ và trả lời tự động.\n"
        "2. **Ghi nhớ ngữ cảnh**: Bot tự động nhớ các câu hỏi trước đó trong cuộc trò chuyện.\n"
        "3. **/reset**: Dùng lệnh này khi muốn chuyển sang chủ đề khác để tránh nhầm lẫn ngữ cảnh cũ.\n"
        "4. **/status**: Kiểm tra thông số kết nối và tình trạng bot."
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /status."""
    is_ready = api_service.is_configured()
    status_msg = (
        "⚙️ **Trạng thái hệ thống:**\n\n"
        f"• Telegram Bot: 🟢 Online\n"
        f"• Gemini AI Engine: {'🟢 Sẵn sàng hoạt động' if is_ready else '🔴 Chưa cấu hình'}\n"
        f"• Phiên bản mô hình: `Gemini 3.5 Flash`\n"
        f"• Định dạng trả lời: Markdown hỗ trợ code & list"
    )
    if update.message:
        await update.message.reply_text(status_msg, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /reset xóa lịch sử hội thoại."""
    user_id = update.effective_user.id if update.effective_user else 0
    api_service.reset_conversation(user_id)
    if update.message:
        await update.message.reply_text(
            "🧹 Đã xóa ngữ cảnh cũ! Bạn có thể bắt đầu chủ đề mới ngay bây giờ."
        )
