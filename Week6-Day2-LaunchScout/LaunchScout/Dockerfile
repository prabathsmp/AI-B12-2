FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CREWAI_TELEMETRY_OPT_OUT=true \
    OTEL_SDK_DISABLED=true \
    CREWAI_TRACING_ENABLED=false \
    OUTPUT_DIR=/app/outputs

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN useradd -m scout && mkdir -p /app/outputs && chown -R scout:scout /app
USER scout

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD curl -fs http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
