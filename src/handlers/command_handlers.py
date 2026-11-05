import logging
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from src.services.api_service import api_service
from src.services.subscriber_service import subscriber_service
from src.services.vocab_service import vocab_service
from src.services.scheduler_service import vocab_scheduler

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /start và tự động đăng ký nhận từ vựng định kỳ."""
    user = update.effective_user
    username = user.first_name if user else "bạn"
    chat_id = update.effective_chat.id if update.effective_chat else 0

    if chat_id:
        subscriber_service.add_subscriber(chat_id)

    status_api = "🟢 Đã kết nối Gemini AI" if api_service.is_configured() else "🟡 Chưa cấu hình API"

    welcome_text = (
        f"👋 Xin chào {username}!\n\n"
        f"🤖 Tôi là **Bot Secretary** (@Kayhuyn_bot), tích hợp **Gemini AI**.\n"
        f"📊 Trạng thái AI: {status_api}\n"
        f"🆔 **Telegram Chat ID của bạn**: `{chat_id}`\n\n"
        f"🔔 **Lịch học từ vựng (10:00 & 18:00):**\n"
        f"• Đã tự động kích hoạt cho tài khoản này! (Múi giờ GMT+7)\n\n"
        f"📌 **Các lệnh hữu ích:**\n"
        f"/vocab - Bốc ngay 3 từ vựng ngẫu nhiên kèm ví dụ\n"
        f"/testcron - Thử ngay chức năng gửi tự động của hệ thống\n"
        f"/status - Kiểm tra trạng thái hệ thống và Chat ID\n"
        f"/unsubscribe - Tạm dừng nhận lịch từ vựng\n"
        f"/subscribe - Bật lại lịch từ vựng\n"
        f"/help - Hướng dẫn sử dụng chi tiết"
    )
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def vocab_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lấy ngay 3 từ vựng ngẫu nhiên qua lệnh /vocab."""
    if not update.message:
        return

    wait_msg = await update.message.reply_text("⏳ *Đang chọn lọc 3 từ vựng và tạo ví dụ thông minh...*", parse_mode="Markdown")

    try:
        content = await vocab_service.generate_vocab_message(count=3, time_label="LUYỆN TẬP NGAY")
        try:
            await wait_msg.edit_text(content, parse_mode="Markdown")
        except BadRequest:
            await wait_msg.edit_text(content)
    except Exception as e:
        logger.error("Lỗi khi xử lý lệnh /vocab: %s", e)
        try:
            vocabs = vocab_service.get_random_vocabs(3)
            fallback_text = "📖 Danh sách từ vựng hôm nay:\n" + "\n".join([f"- {v['word']}: {v['meaning']}" for v in vocabs])
            await wait_msg.edit_text(fallback_text)
        except Exception:
            await wait_msg.edit_text("⚠️ Đã xảy ra lỗi khi tạo danh sách từ vựng.")


async def testcron_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh test chạy ngay tiến trình gửi tự động của Cronjob."""
    if not update.message:
        return

    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id:
        subscriber_service.add_subscriber(chat_id)

    status_msg = await update.message.reply_text("⏳ Đang chuẩn bị 3 từ vựng và gọi AI tạo câu ví dụ...")

    try:
        # 1. Tạo tin nhắn từ vựng
        message_text = await vocab_service.generate_vocab_message(count=3, time_label="TEST TỰ ĐỘNG")

        # 2. Gửi thẳng vào chat của người test
        try:
            await update.message.reply_text(message_text, parse_mode="Markdown")
        except BadRequest as be:
            logger.warning("Markdown parse error (%s), gửi lại dạng plain text", be)
            await update.message.reply_text(message_text)

        # 3. Cập nhật thông báo trạng thái
        total_subs = len(subscriber_service.get_all())
        await status_msg.edit_text(
            f"✅ **Đã gửi thành công!**\n"
            f"🆔 Chat ID của bạn: `{chat_id}`\n"
            f"👥 Danh sách nhận tin: `{total_subs}` tài khoản\n"
            f"⏰ Lịch hẹn hàng ngày: **10:00** và **18:00** (GMT+7)",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error("Lỗi khi chạy testcron: %s", e)
        await status_msg.edit_text(f"⚠️ Lỗi khi tạo từ vựng: {e}")


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Đăng ký nhận từ vựng."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id:
        subscriber_service.add_subscriber(chat_id)
        if update.message:
            await update.message.reply_text(
                f"🔔 Đã đăng ký nhận từ vựng cho Chat ID `{chat_id}` vào **10:00** và **18:00** mỗi ngày!",
                parse_mode="Markdown"
            )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hủy đăng ký nhận từ vựng."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id:
        subscriber_service.remove_subscriber(chat_id)
        if update.message:
            await update.message.reply_text("🔕 Đã tạm dừng nhận thông báo từ vựng. Dùng /subscribe để bật lại.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /help."""
    help_text = (
        "📖 **Hướng dẫn sử dụng Bot Secretary:**\n\n"
        "1. **/start**: Đăng ký nhận từ vựng tự động (10:00 & 18:00).\n"
        "2. **/vocab**: Bốc ngẫu nhiên 3 từ vựng học ngay lập tức.\n"
        "3. **/testcron**: Kiểm tra chức năng gửi tin nhắn định kỳ.\n"
        "4. **/status**: Xem chi tiết thông số hệ thống và danh sách đăng ký.\n"
        "5. **Chat AI**: Nhắn bất kỳ câu hỏi nào để trò chuyện với Gemini."
    )
    if update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /status."""
    chat_id = update.effective_chat.id if update.effective_chat else 0
    is_ready = api_service.is_configured()
    total_vocab = len(vocab_service.vocabularies)
    subscribers = subscriber_service.get_all()
    is_sub = subscriber_service.is_subscribed(chat_id)

    status_msg = (
        "⚙️ **Trạng thái hệ thống:**\n\n"
        f"• Telegram Bot: 🟢 Online\n"
        f"• Gemini AI: {'🟢 Sẵn sàng' if is_ready else '🔴 Chưa cấu hình'}\n"
        f"• Kho từ vựng: 📚 **{total_vocab:,} từ**\n"
        f"• Khung giờ hẹn: ⏰ **10:00 & 18:00 (GMT+7)**\n"
        f"• Số subscriber: 👥 **{len(subscribers)}**\n\n"
        f"👤 **Tài khoản của bạn:**\n"
        f"• Chat ID: `{chat_id}`\n"
        f"• Trạng thái nhận lịch: {'🟢 ĐÃ ĐĂNG KÝ' if is_sub else '🔴 CHƯA ĐĂNG KÝ (Gõ /subscribe để bật)'}"
    )
    if update.message:
        await update.message.reply_text(status_msg, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý lệnh /reset xóa lịch sử hội thoại."""
    user_id = update.effective_user.id if update.effective_user else 0
    api_service.reset_conversation(user_id)
    if update.message:
        await update.message.reply_text("🧹 Đã xóa ngữ cảnh trò chuyện cũ! Bắt đầu chủ đề mới ngay.")
