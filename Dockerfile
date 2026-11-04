FROM python:3.12-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Ngăn Python tạo bytecode .pyc và bật unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn dự án
COPY . .

# Lệnh khởi chạy Bot
CMD ["python", "main.py"]
