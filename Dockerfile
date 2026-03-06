FROM python:3.10-slim

WORKDIR /appplication

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir sse_starlette

COPY app ./app
COPY pipeline ./pipeline
COPY run.py .
COPY private.py .

RUN mkdir data