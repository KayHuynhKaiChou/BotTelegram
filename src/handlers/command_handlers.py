import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.services.api_service import api_service
from src.services.subscriber_service import subscriber_service
from src.services.vocab_service import vocab_service

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /start và tự động đăng ký nhận từ vựng định kỳ."""
    user = update.effective_user
    username = user.first_name if user else "bạn"
    chat_id = update.effective_chat.id if update.effective_chat else 0

    # Tự động đăng ký nhận tin nhắn định kỳ
    if chat_id:
        subscriber_service.add_subscriber(chat_id)

    status_api = "🟢 Đã kết nối Gemini AI" if api_service.is_configured() else "🟡 Chưa cấu hình API"

    welcome_text = (
        f"👋 Xin chào {username}!\n\n"
        f"🤖 Tôi là **Bot Secretary** (@Kayhuyn_bot), được tích hợp **Gemini AI**.\n"
        f"📊 Trạng thái AI: {status_api}\n\n"
        f"⏰ **Lịch học từ vựng tự động:**\n"
        f"• Đã bật thông báo nhận ngẫu nhiên 3 từ vựng mỗi ngày vào lúc **10:00** và **18:00**.\n\n"
        f"📌 **Các lệnh hữu ích:**\n"
        f"/vocab - Lấy ngay 3 từ vựng ngẫu nhiên để học liền\n"
        f"/status - Kiểm tra trạng thái hệ thống và số lượng từ vựng\n"
        f"/reset - Xóa ngữ cảnh trò chuyện AI cũ\n"
        f"/unsubscribe - Tạm dừng nhận lịch từ vựng mỗi ngày\n"
        f"/subscribe - Bật lại lịch nhận từ vựng\n"
        f"/help - Xem hướng dẫn chi tiết\n\n"
        f"👉 Nhắn tin bất kỳ để trò chuyện hoặc hỏi đáp cùng AI!"
    )
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def vocab_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lấy ngay 3 từ vựng ngẫu nhiên qua lệnh /vocab."""
    if not update.message:
        return

    # Thông báo đang lấy dữ liệu
    wait_msg = await update.message.reply_text("⏳ *Đang chọn lọc 3 từ vựng và tạo ví dụ thông minh...*", parse_mode="Markdown")

    try:
        content = await vocab_service.generate_vocab_message(count=3, time_label="LUYỆN TẬP NGAY")
        await wait_msg.edit_text(content, parse_mode="Markdown")
    except Exception as e:
        logger.error("Lỗi khi xử lý lệnh /vocab: %s", e)
        # Fallback không có markdown nếu parse lỗi
        try:
            vocabs = vocab_service.get_random_vocabs(3)
            fallback_text = "📖 Danh sách từ vựng hôm nay:\n" + "\n".join([f"- {v['word']}: {v['meaning']}" for v in vocabs])
            await wait_msg.edit_text(fallback_text)
        except Exception:
            await wait_msg.edit_text("⚠️ Đã xảy ra lỗi khi tạo danh sách từ vựng.")


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Đăng ký nhận từ vựng."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id:
        subscriber_service.add_subscriber(chat_id)
        if update.message:
            await update.message.reply_text("🔔 Đã đăng ký nhận 3 từ vựng vào **10:00** và **18:00** mỗi ngày!", parse_mode="Markdown")


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hủy đăng ký nhận từ vựng."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id:
        subscriber_service.remove_subscriber(chat_id)
        if update.message:
            await update.message.reply_text("🔕 Đã tạm dừng lịch nhận từ vựng hàng ngày. Bạn có thể dùng /subscribe để bật lại bất cứ lúc nào.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /help."""
    help_text = (
        "📖 **Hướng dẫn sử dụng Bot:**\n\n"
        "1. **Học từ vựng định kỳ**: Bot tự động gửi 3 từ vựng vào 10:00 và 18:00 mỗi ngày.\n"
        "2. **Học tức thì**: Gõ `/vocab` để lấy ngay 3 từ vựng kèm ví dụ.\n"
        "3. **Trò chuyện cùng AI**: Nhắn tin tự nhiên như bình thường, AI sẽ trả lời bạn.\n"
        "4. **/status**: Xem trạng thái bot và kho dữ liệu từ vựng."
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /status."""
    is_ready = api_service.is_configured()
    total_vocab = len(vocab_service.vocabularies)
    total_subscribers = len(subscriber_service.get_all())

    status_msg = (
        "⚙️ **Trạng thái hệ thống:**\n\n"
        f"• Telegram Bot: 🟢 Online\n"
        f"• Gemini AI Engine: {'🟢 Sẵn sàng' if is_ready else '🔴 Chưa cấu hình'}\n"
        f"• Kho từ vựng: 📚 **{total_vocab:,} từ vựng** (đã chuẩn hóa)\n"
        f"• Lịch Cron: ⏰ **10:00 & 18:00 (GMT+7)**\n"
        f"• Số người đăng ký nhận tin: 👥 **{total_subscribers}**\n"
    )
    if update.message:
        await update.message.reply_text(status_msg, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /reset xóa lịch sử hội thoại."""
    user_id = update.effective_user.id if update.effective_user else 0
    api_service.reset_conversation(user_id)
    if update.message:
        await update.message.reply_text("🧹 Đã xóa ngữ cảnh trò chuyện cũ! Bắt đầu chủ đề mới ngay.")
