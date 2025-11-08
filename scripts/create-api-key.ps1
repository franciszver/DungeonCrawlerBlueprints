# PowerShell script to create API Gateway API key and retrieve the key value
# Requires AWS CLI to be configured

$STACK_NAME = "dungeoncrawler-blueprints"
$REGION = "us-east-1"

Write-Host "Retrieving API Key ID from CloudFormation stack..."
$API_KEY_ID = aws cloudformation describe-stacks `
  --stack-name $STACK_NAME `
  --region $REGION `
  --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" `
  --output text

if ([string]::IsNullOrEmpty($API_KEY_ID)) {
  Write-Host "Error: Could not find API Key ID in stack outputs" -ForegroundColor Red
  exit 1
}

Write-Host "Retrieving API Key value..."
$API_KEY_VALUE = aws apigateway get-api-key `
  --api-key $API_KEY_ID `
  --include-value `
  --region $REGION `
  --query "value" `
  --output text

if ([string]::IsNullOrEmpty($API_KEY_VALUE)) {
  Write-Host "Error: Could not retrieve API Key value" -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "API Key created successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "API Key ID: $API_KEY_ID"
Write-Host "API Key Value: $API_KEY_VALUE"
Write-Host ""
Write-Host "Add this to your Amplify environment variables:" -ForegroundColor Yellow
Write-Host "VITE_API_KEY=$API_KEY_VALUE"
Write-Host ""
Write-Host "And set VITE_API_URL to your API Gateway URL" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Green

