#!/bin/bash
# Script to set up OpenRouter API key in AWS Secrets Manager
# Usage: ./setup-secret.sh YOUR_OPENROUTER_API_KEY

if [ -z "$1" ]; then
  echo "Error: OpenRouter API key required"
  echo "Usage: ./setup-secret.sh YOUR_OPENROUTER_API_KEY"
  exit 1
fi

API_KEY=$1
SECRET_NAME="dungeoncrawler/openrouter-api-key"
REGION="us-east-1"

echo "Creating/updating secret in AWS Secrets Manager..."

# Check if secret exists
if aws secretsmanager describe-secret --secret-id $SECRET_NAME --region $REGION > /dev/null 2>&1; then
  echo "Secret exists, updating..."
  aws secretsmanager update-secret \
    --secret-id $SECRET_NAME \
    --secret-string "{\"api_key\": \"$API_KEY\"}" \
    --region $REGION
else
  echo "Secret does not exist, creating..."
  aws secretsmanager create-secret \
    --name $SECRET_NAME \
    --description "OpenRouter API key for room detection" \
    --secret-string "{\"api_key\": \"$API_KEY\"}" \
    --region $REGION
fi

echo ""
echo "=========================================="
echo "Secret created/updated successfully!"
echo "Secret Name: $SECRET_NAME"
echo "=========================================="

