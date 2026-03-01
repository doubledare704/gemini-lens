#!/bin/bash
set -e

# Configuration
PROJECT_ID="gemini-lens-hackathon"
REGION="us-central1"
APP_NAME="gemini-lens"
IMAGE_NAME="gcr.io/$PROJECT_ID/$APP_NAME"

echo "Deploying GeminiLens Interactive Educational Explainer..."

# Ensure gcloud is initialized
if ! command -v gcloud &> /dev/null
then
    echo "Error: gcloud could not be found. Please install the Google Cloud CLI."
    exit 1
fi

echo "Setting working project..."
gcloud config set project "$PROJECT_ID"

echo "Enabling necessary APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com

echo "Building and submitting Docker image via Cloud Build..."
gcloud builds submit --tag "$IMAGE_NAME"

echo "Deploying to Cloud Run..."
# It is assumed GOOGLE_API_KEY is available as a Secret Manager secret
# Or provide it directly via env (not recommended for prod, but okay for hackathon quick start)
# For the hackathon context, we'll prompt the user if they want to pass it as an env var.

read -p "Enter your GOOGLE_API_KEY to inject into the deployment: " API_KEY

gcloud run deploy "$APP_NAME" \
  --image "$IMAGE_NAME" \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_API_KEY=$API_KEY"

echo "Deployment complete! Visit the URL provided by Cloud Run above."
