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
        f"/find <từ> - Tra cứu từ khóa nhanh (không tốn API Key)\n"
        f"/find_high <chủ đề> - Tìm kiếm ngữ nghĩa bằng AI (VD: /find_high chủ đề giao thông)\n"
        f"/vocab - Bốc ngay 3 từ vựng ngẫu nhiên kèm ví dụ\n"
        f"/testcron - Thử ngay chức năng gửi tự động của hệ thống\n"
        f"/status - Kiểm tra trạng thái hệ thống và Chat ID\n"
        f"/unsubscribe - Tạm dừng nhận lịch từ vựng\n"
        f"/subscribe - Bật lại lịch từ vựng\n"
        f"/help - Hướng dẫn sử dụng chi tiết"
    )
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown")


async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tra cứu 1 hoặc nhiều từ vựng trong kho dữ liệu (hoàn toàn không dùng API Key)."""
    if not update.message:
        return

    # Nếu người dùng gõ /find -high ... hoặc /find-high
    if context.args and context.args[0].lower() in ["-high", "high"]:
        context.args = context.args[1:]
        return await find_high_command(update, context)

    query = " ".join(context.args) if context.args else ""
    if not query.strip():
        guide = (
            "🔍 **Hướng dẫn tra cứu từ vựng:**\n\n"
            "• **Tra từ khóa nhanh (0.001s, Free)**: `/find simplify` hoặc `/find branch, loan`\n"
            "• **Tra ngữ nghĩa/chủ đề bằng AI**: `/find_high những từ về chủ đề giao thông`\n\n"
            "💡 *Lệnh /find thông thường hoàn toàn KHÔNG tốn API Key!*"
        )
        await update.message.reply_text(guide, parse_mode="Markdown")
        return

    results = vocab_service.search_vocabs(query, limit=15)
    if not results:
        await update.message.reply_text(
            f"❌ Không tìm thấy từ vựng nào khớp với: *{query}*\n"
            f"💡 Bạn có thể thử tìm theo chủ đề thông minh hơn bằng lệnh: `/find_high {query}`",
            parse_mode="Markdown"
        )
        return

    reply = f"🔍 **Kết quả tìm kiếm cho:** `{query}` ({len(results)} kết quả)\n\n"
    for i, r in enumerate(results, 1):
        reply += f"**{i}. {r['word']}**\n   • Nghĩa: _{r['meaning']}_\n   • Tệp: `{r['source']}`\n\n"

    try:
        await update.message.reply_text(reply, parse_mode="Markdown")
    except BadRequest:
        await update.message.reply_text(reply)


async def find_high_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tra cứu ngữ nghĩa chuyên sâu bằng Gemini AI theo chủ đề/ngữ cảnh (VD: /find_high từ vựng về chủ đề giao thông)."""
    if not update.message:
        return

    query = " ".join(context.args) if context.args else ""
    if not query.strip():
        guide = (
            "🧠 **Hướng dẫn tìm kiếm ngữ nghĩa chuyên sâu bằng AI:**\n\n"
            "AI sẽ đọc hiểu toàn bộ kho 1.445 từ của bạn để tìm từ theo **ý nghĩa, ngữ cảnh hoặc chủ đề** "
            "(kể cả khi trong nghĩa không chứa chính xác từ khóa đó).\n\n"
            "📌 **Ví dụ:**\n"
            "• `/find_high từ vựng liên quan đến chủ đề giao thông, xe cộ`\n"
            "• `/find_high các từ miêu tả cảm xúc vui vẻ, tích cực`\n"
            "• `/find_high từ vựng dùng trong ký kết hợp đồng thương mại`"
        )
        await update.message.reply_text(guide, parse_mode="Markdown")
        return

    user_id = update.effective_user.id if update.effective_user else 0
    wait_msg = await update.message.reply_text(
        "🔍 *Gemini AI đang phân tích toàn bộ 1.445 từ vựng theo chủ đề của bạn...*",
        parse_mode="Markdown"
    )

    try:
        result = await vocab_service.search_high(query=query, user_id=user_id)
        try:
            await wait_msg.edit_text(result, parse_mode="Markdown")
        except BadRequest:
            await wait_msg.edit_text(result)
    except Exception as e:
        logger.error("Lỗi khi chạy find_high: %s", e)
        await wait_msg.edit_text(f"⚠️ Có lỗi xảy ra trong quá trình tìm kiếm: {e}")


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
