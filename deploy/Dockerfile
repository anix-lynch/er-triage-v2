# Cloud Run target — Streamlit on :8080 (Cloud Run's expected port).
# Build:  gcloud builds submit --tag gcr.io/$PROJECT/er-triage-v2
# Deploy: see deploy/cloudrun.sh

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8080/_stcore/health || exit 1

CMD streamlit run app/streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
