import asyncio
import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from src.services.api_service import api_service

logger = logging.getLogger(__name__)


async def keep_typing(bot, chat_id: int, stop_event: asyncio.Event) -> None:
    """Liên tục phát tín hiệu typing lên thanh trạng thái Telegram mỗi 4 giây."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            pass


async def handle_user_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý tin nhắn văn bản với phản hồi tức thì 'Đang suy nghĩ...' và cập nhật kết quả."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.strip()
    user = update.effective_user
    user_id = user.id if user else 0
    username = user.first_name if user else "User"
    chat_id = update.message.chat.id

    # Đảm bảo lưu chat_id của user để gửi thông báo định kỳ
    from src.services.subscriber_service import subscriber_service
    subscriber_service.add_subscriber(chat_id)

    logger.info("Nhận tin nhắn từ [%s - ID %s]: %s", username, user_id, user_text)

    # Nếu người dùng hỏi về danh sách lệnh, trả về ngay danh sách slash commands
    lower_text = user_text.lower()
    command_keywords = [
        "danh sách lệnh", "các lệnh", "danh sach lenh", "cac lenh",
        "lệnh nào", "lenh nao", "có lệnh gì", "co lenh gi",
        "lệnh có thể sài", "lệnh có thể dùng", "lệnh có sẵn", "xem lệnh"
    ]
    if any(kw in lower_text for kw in command_keywords):
        commands_reply = (
            "📌 **Danh sách các lệnh hỗ trợ của Bot:**\n\n"
            "• `/vocab` : Bốc ngay 3 từ vựng ngẫu nhiên kèm ví dụ thực tế\n"
            "• `/status` : Xem trạng thái hệ thống, Chat ID và số lượng từ vựng\n"
            "• `/testcron` : Chạy thử nghiệm gửi từ vựng tự động ngay lập tức\n"
            "• `/start` : Khởi động và đăng ký nhận từ vựng lúc 10:00 & 18:00\n"
            "• `/reset` : Xóa ngữ cảnh trò chuyện AI cũ để đổi chủ đề\n"
            "• `/subscribe` : Bật nhận từ vựng mỗi ngày\n"
            "• `/unsubscribe` : Tắt nhận từ vựng định kỳ\n"
            "• `/help` : Hướng dẫn sử dụng chi tiết\n\n"
            "💡 **Mẹo:** Bạn có thể bấm vào nút **[Menu]** ở góc dưới bên trái khung chat hoặc gõ dấu `/` để chọn lệnh nhanh!"
        )
        try:
            await update.message.reply_text(commands_reply, parse_mode="Markdown")
        except BadRequest:
            await update.message.reply_text(commands_reply)
        return

    # 1. Gửi tin nhắn phản hồi tức thì (< 0.2s) để người dùng biết bot đã tiếp nhận
    thinking_msg = None
    try:
        thinking_msg = await update.message.reply_text(
            "⏳ *Đang suy nghĩ và soạn câu trả lời...*",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning("Không thể gửi tin nhắn phản hồi nhanh: %s", e)

    # 2. Bật tín hiệu 'typing...' liên tục trên thanh tiêu đề trong lúc AI tạo nội dung
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(keep_typing(context.bot, chat_id, stop_typing))

    try:
        # 3. Gọi Gemini AI xử lý prompt
        reply_content = await api_service.process_prompt(
            user_text=user_text,
            user_id=user_id
        )

        # 4. Khi có kết quả, cập nhật thẳng vào tin nhắn đang chờ (hoặc gửi mới nếu chưa có)
        if thinking_msg:
            try:
                await thinking_msg.edit_text(reply_content, parse_mode="Markdown")
            except BadRequest as parse_err:
                logger.warning("Lỗi parse Markdown (%s), cập nhật lại dạng plain text.", parse_err)
                await thinking_msg.edit_text(reply_content)
        else:
            try:
                await update.message.reply_text(reply_content, parse_mode="Markdown")
            except BadRequest:
                await update.message.reply_text(reply_content)

    except Exception as e:
        logger.error("Lỗi khi xử lý tin nhắn: %s", e, exc_info=True)
        err_text = "⚠️ Có lỗi xảy ra trong quá trình xử lý tin nhắn của bạn. Vui lòng thử lại sau!"
        if thinking_msg:
            await thinking_msg.edit_text(err_text)
        else:
            await update.message.reply_text(err_text)
    finally:
        # Dừng luồng typing
        stop_typing.set()
        await typing_task
