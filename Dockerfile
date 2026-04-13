FROM python:3.10-slim

WORKDIR /app

# =========================
# СИСТЕМНЫЕ ЗАВИСИМОСТИ
# =========================
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    gcc \
    cmake \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# =========================
# PYTHON ЗАВИСИМОСТИ
# =========================
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =========================
# КОД
# =========================
COPY . .

# =========================
# GUNICORN (ВАЖНО)
# =========================
CMD ["gunicorn", "app:app", "--workers", "1", "--threads", "1", "--timeout", "120", "--preload"]