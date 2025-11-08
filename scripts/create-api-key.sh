#!/bin/bash
# Script to create API Gateway API key and retrieve the key value
# Requires AWS CLI to be configured

STACK_NAME="dungeoncrawler-blueprints"
REGION="us-east-1"

echo "Retrieving API Key ID from CloudFormation stack..."
API_KEY_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" \
  --output text)

if [ -z "$API_KEY_ID" ]; then
  echo "Error: Could not find API Key ID in stack outputs"
  exit 1
fi

echo "Retrieving API Key value..."
API_KEY_VALUE=$(aws apigateway get-api-key \
  --api-key $API_KEY_ID \
  --include-value \
  --region $REGION \
  --query "value" \
  --output text)

if [ -z "$API_KEY_VALUE" ]; then
  echo "Error: Could not retrieve API Key value"
  exit 1
fi

echo ""
echo "=========================================="
echo "API Key created successfully!"
echo "=========================================="
echo "API Key ID: $API_KEY_ID"
echo "API Key Value: $API_KEY_VALUE"
echo ""
echo "Add this to your Amplify environment variables:"
echo "VITE_API_KEY=$API_KEY_VALUE"
echo ""
echo "And set VITE_API_URL to your API Gateway URL"
echo "=========================================="

