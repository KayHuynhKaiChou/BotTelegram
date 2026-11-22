import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from src.services.vocab_service import vocab_service

logger = logging.getLogger(__name__)

# URL chính thức của Mini App trên Render
MINI_APP_URL = "https://bottelegram-ol9e.onrender.com/app"


def get_vocab_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím nút bấm tương tác cho tin nhắn từ vựng."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Bốc 3 từ khác", callback_data="vocab_refresh"),
            InlineKeyboardButton("💡 Thêm ví dụ AI", callback_data="vocab_ai_example")
        ],
        [
            InlineKeyboardButton("🚀 Mở Flashcard Mini App", web_app=WebAppInfo(url=MINI_APP_URL))
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Tạo bàn phím nút bấm chào mừng cho lệnh /start."""
    keyboard = [
        [
            InlineKeyboardButton("📖 Học 3 từ vựng (/vocab)", callback_data="vocab_refresh"),
            InlineKeyboardButton("🔍 Hướng dẫn tra cứu", callback_data="guide_find")
        ],
        [
            InlineKeyboardButton("🚀 Mở Flashcard Mini App (Lật thẻ 3D)", web_app=WebAppInfo(url=MINI_APP_URL))
        ],
        [
            InlineKeyboardButton("⚙️ Trạng thái (/status)", callback_data="action_status")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xử lý tất cả các tương tác click nút bấm (Inline Keyboard)."""
    query = update.callback_query
    if not query:
        return

    data = query.data
    logger.info("Nhận callback query: %s từ user %s", data, query.from_user.id)

    # 1. Bấm nút: Đổi 3 từ khác
    if data == "vocab_refresh":
        await query.answer("⏳ Đang bốc 3 từ mới...")
        try:
            new_content = await vocab_service.generate_vocab_message(count=3, time_label="LUYỆN TẬP")
            try:
                await query.edit_message_text(
                    text=new_content,
                    parse_mode="Markdown",
                    reply_markup=get_vocab_keyboard()
                )
            except BadRequest:
                await query.edit_message_text(
                    text=new_content,
                    reply_markup=get_vocab_keyboard()
                )
        except Exception as e:
            logger.error("Lỗi khi refresh vocab qua nút bấm: %s", e)
            await query.answer("⚠️ Lỗi khi bốc từ vựng, thử lại sau!")

    # 2. Bấm nút: Thêm ví dụ AI
    elif data == "vocab_ai_example":
        await query.answer("🧠 Gemini AI đang tạo ví dụ...")
        current_text = query.message.text if query.message else ""
        if "💡" in current_text:
            await query.answer("Tin nhắn này đã có câu ví dụ rồi bạn nhé!", show_alert=False)
            return

        try:
            # Bốc 3 từ và tạo ví dụ
            new_content = await vocab_service.generate_vocab_message(count=3, time_label="VÍ DỤ MỚI")
            try:
                await query.edit_message_text(
                    text=new_content,
                    parse_mode="Markdown",
                    reply_markup=get_vocab_keyboard()
                )
            except BadRequest:
                await query.edit_message_text(
                    text=new_content,
                    reply_markup=get_vocab_keyboard()
                )
        except Exception as e:
            logger.error("Lỗi khi thêm ví dụ AI: %s", e)

    # 3. Bấm nút: Hướng dẫn tra cứu
    elif data == "guide_find":
        await query.answer()
        guide_text = (
            "🔍 **Hướng dẫn tra cứu từ vựng:**\n\n"
            "• **Tra nhanh (0.001s, Free)**:\n"
            "  `/find simplify` hoặc `/find branch, loan`\n"
            "  *(Tự động khớp từ chen giữa, chống gõ sai, đảo từ)*\n\n"
            "• **Tra ngữ nghĩa bằng AI**:\n"
            "  `/find_high những từ vựng về chủ đề giao thông`\n"
            "  *(Gemini AI tự động gom từ theo chủ đề)*"
        )
        await query.message.reply_text(guide_text, parse_mode="Markdown")

    # 4. Bấm nút: Xem trạng thái
    elif data == "action_status":
        await query.answer()
        from src.handlers.command_handlers import status_command
        await status_command(update, context)

    else:
        await query.answer()
