FROM python:3.10

WORKDIR /app

# 🔥 системные зависимости для opencv / onnx / insightface
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 🔥 pip upgrade
RUN pip install --upgrade pip setuptools wheel

# 🔥 копируем зависимости
COPY requirements.txt .

# 🔥 ставим зависимости (важно — no cache)
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 копируем проект
COPY . .

# 🔥 защита от OOM (важно для Railway)
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

# 🔥 запуск gunicorn (СТАБИЛЬНЫЙ)
CMD ["gunicorn", "app:app", "--workers", "1", "--threads", "1", "--timeout", "120", "--preload"]