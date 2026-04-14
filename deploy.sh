#!/bin/bash
# Deploy Hackathon Oracle API to Google Cloud Run

set -e

PROJECT_ID="predictionpro-io"
SERVICE_NAME="hackathon-oracle-api"
REGION="europe-west1"
IMAGE="europe-west1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}"

echo "Building Docker image..."
docker build --platform linux/amd64 -t ${IMAGE}:latest .

echo "Pushing to Container Registry..."
docker push ${IMAGE}:latest

echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE}:latest \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --quiet

echo "Done! Service URL:"
gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format="value(status.url)"