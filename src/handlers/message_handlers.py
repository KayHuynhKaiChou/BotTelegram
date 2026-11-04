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

    logger.info("Nhận tin nhắn từ [%s - ID %s]: %s", username, user_id, user_text)

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
