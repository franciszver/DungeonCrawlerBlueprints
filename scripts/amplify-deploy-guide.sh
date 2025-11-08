#!/bin/bash
# Amplify Deployment Helper Script
# This script helps you prepare for AWS Amplify deployment

echo "========================================"
echo "Amplify Deployment Preparation"
echo "========================================"
echo ""

# Check if backend is deployed
echo "Step 1: Verify Backend Deployment"
echo "-----------------------------------"

read -p "Enter your SAM stack name (default: dungeoncrawler-blueprints): " stack_name
stack_name=${stack_name:-dungeoncrawler-blueprints}

echo "Checking CloudFormation stack..."
if ! aws cloudformation describe-stacks --stack-name "$stack_name" > /dev/null 2>&1; then
    echo "ERROR: Stack not found. Please deploy backend first."
    echo "Run: cd infrastructure && sam build && sam deploy --guided"
    exit 1
fi

echo "✓ Stack found: $stack_name"

# Get API URL
echo "Retrieving API Gateway URL..."
api_url=$(aws cloudformation describe-stacks \
    --stack-name "$stack_name" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
    --output text 2>&1)

if [ $? -eq 0 ] && [ -n "$api_url" ]; then
    echo "✓ API URL: $api_url"
else
    echo "WARNING: Could not retrieve API URL"
    read -p "Please enter your API Gateway URL manually: " api_url
fi

echo ""
echo "Step 2: Get API Key"
echo "-----------------------------------"

read -p "Enter your API Key (or press Enter to run create-api-key script): " api_key
if [ -z "$api_key" ]; then
    echo "Running create-api-key script..."
    bash scripts/create-api-key.sh
    read -p "Enter the API Key shown above: " api_key
fi

if [ -z "$api_key" ]; then
    echo "ERROR: API Key is required"
    exit 1
fi

echo "✓ API Key retrieved"

echo ""
echo "Step 3: Verify Frontend Configuration"
echo "-----------------------------------"

# Check if amplify.yml exists
if [ -f "amplify.yml" ]; then
    echo "✓ amplify.yml found"
else
    echo "ERROR: amplify.yml not found"
    exit 1
fi

# Check if frontend/package.json exists
if [ -f "frontend/package.json" ]; then
    echo "✓ frontend/package.json found"
else
    echo "ERROR: frontend/package.json not found"
    exit 1
fi

echo ""
echo "========================================"
echo "Deployment Information"
echo "========================================"
echo ""
echo "Environment Variables for Amplify Console:"
echo "-------------------------------------------"
echo ""
echo "VITE_API_URL = $api_url"
echo "VITE_API_KEY = $api_key"
echo ""
echo "========================================"
echo ""
echo "Next Steps:"
echo "1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify/"
echo "2. Click 'New app' -> 'Host web app'"
echo "3. Connect your GitHub repository"
echo "4. Add the environment variables shown above"
echo "5. Click 'Save and deploy'"
echo ""
echo "For detailed instructions, see: _docs/AMPLIFY_DEPLOYMENT.md"
echo ""

# Save to file for reference
env_file="amplify-env-vars.txt"
cat > "$env_file" << EOF
# Environment Variables for AWS Amplify
# Generated on $(date '+%Y-%m-%d %H:%M:%S')

VITE_API_URL=$api_url
VITE_API_KEY=$api_key

# Instructions:
# 1. Copy these values to AWS Amplify Console -> Environment variables
# 2. Or use AWS CLI to set them (see Amplify CLI documentation)
EOF

echo "✓ Environment variables saved to: $env_file"
echo ""

