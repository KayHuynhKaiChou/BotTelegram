# Kayhuyn Telegram Bot

Dự án Telegram Bot được xây dựng bằng Python (sử dụng thư viện `python-telegram-bot` v22+ Async/Await), kiến trúc module hoá sẵn sàng tích hợp với các API bên ngoài (OpenAI, Gemini, Claude, hoặc Custom API).

## 1. Cấu trúc thư mục

```
BotTelegram/
├── .venv/                      # Môi trường ảo Python
├── src/
│   ├── __init__.py
│   ├── config.py               # Quản lý cấu hình & biến môi trường (.env)
│   ├── handlers/
│   │   ├── command_handlers.py # Xử lý các lệnh (/start, /help, /status)
│   │   └── message_handlers.py # Xử lý tin nhắn văn bản từ người dùng
│   └── services/
│       └── api_service.py      # Module xử lý tích hợp API bên thứ ba
├── .env                        # File biến môi trường (chứa Bot Token & API Key)
├── .env.example                # File mẫu cấu hình
├── .gitignore
├── requirements.txt
├── main.py                     # Entry point khởi chạy Bot
└── README.md
```

## 2. Hướng dẫn cài đặt & Khởi chạy

### Bước 1: Kích hoạt môi trường ảo
```powershell
.\.venv\Scripts\Activate.ps1
```

### Bước 2: Cài đặt thư viện (nếu chưa có)
```powershell
pip install -r requirements.txt
```

### Bước 3: Cấu hình API Key
Mở file `.env` và cập nhật thông tin:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
API_KEY=your_api_key_here
API_TYPE=gemini # hoặc openai, custom,...
```

### Bước 4: Chạy Bot
```powershell
python main.py
```

## 3. Các lệnh có sẵn trên Telegram
- `/start`: Bắt đầu và xem lời chào cùng trạng thái kết nối API.
- `/status`: Kiểm tra trạng thái hoạt động của Bot và API Key.
- `/help`: Xem hướng dẫn sử dụng.
