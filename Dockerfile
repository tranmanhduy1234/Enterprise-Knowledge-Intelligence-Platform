FROM python:3.10-slim

WORKDIR /app

# Khắc phục thiếu thư viện hệ thống khi build C++ extensions (ví dụ: cho docling, fastembed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và install trước để tận dụng Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code ứng dụng
COPY app /app/app
COPY pipeline /app/pipeline
COPY run.py .
COPY private.py .

# API listening port
EXPOSE 8000

# Default command
CMD ["python", "run.py"]