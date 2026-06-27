FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
COPY cli_python/ /app/cli_python/

RUN pip install --no-cache-dir -r /app/requirements.txt

ENV PYTHONPATH=/app/cli_python
ENV PYTHONIOENCODING=utf-8
ENV OMP_NUM_THREADS=2

EXPOSE 8000 8501
