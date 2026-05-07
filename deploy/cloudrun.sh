#!/usr/bin/env bash
# One-shot deploy to Google Cloud Run.
# Currently deployed at: https://er-triage-v2-tjb2srbb2q-uw.a.run.app (us-west1)
#
# Prereqs:
#   - gcloud auth login + gcloud config set project $GCP_PROJECT
#   - APIs enabled: run.googleapis.com, cloudbuild.googleapis.com, artifactregistry.googleapis.com
#   - Secret in Secret Manager: anthropic-api-key
#   - Embeddings (Vertex AI gemini-embedding-001) auth via Cloud Run service account — no API key needed
#
# Cost: ~$0/month idle (scales to zero), ~$0.40 per 1k requests at this size.

set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT env var}"
REGION="${GCP_REGION:-us-west1}"
SERVICE="er-triage-v2"
REPO="cloud-run-source-deploy"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${SERVICE}:latest"

echo "[1/3] Building image to Artifact Registry..."
gcloud builds submit --tag "$IMAGE" --project "$PROJECT" .

echo "[2/3] Deploying to Cloud Run..."
gcloud run deploy "$SERVICE" \
    --image "$IMAGE" \
    --region "$REGION" \
    --project "$PROJECT" \
    --platform managed \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 3 \
    --set-secrets "ANTHROPIC_API_KEY=anthropic-api-key:latest"

echo "[3/3] Service URL:"
gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'
