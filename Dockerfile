FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY cli_python/ /app/cli_python/

RUN pip install --no-cache-dir \
    opendataloader-pdf \
    fastapi \
    uvicorn \
    streamlit \
    plotly \
    requests \
    beautifulsoup4 \
    duckduckgo-search \
    python-dotenv \
    pydantic

ENV PYTHONPATH=/app/cli_python
ENV PYTHONIOENCODING=utf-8

EXPOSE 8000 8501
