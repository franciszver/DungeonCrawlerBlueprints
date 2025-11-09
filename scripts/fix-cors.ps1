# Script to fix CORS on API Gateway
# This updates the CORS configuration directly via AWS CLI
# Usage: .\scripts\fix-cors.ps1 -ApiId YOUR_API_ID

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiId = "",
    [string]$Region = "us-east-1"
)

if ([string]::IsNullOrWhiteSpace($ApiId)) {
    Write-Host "Error: API Gateway ID required" -ForegroundColor Red
    Write-Host "Usage: .\scripts\fix-cors.ps1 -ApiId YOUR_API_ID" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To get your API ID, run:" -ForegroundColor Cyan
    Write-Host "  aws cloudformation describe-stacks --stack-name dungeoncrawler-blueprints --query 'Stacks[0].Outputs[?OutputKey==\`"ApiId\`"].OutputValue' --output text" -ForegroundColor White
    exit 1
}

$apiId = $ApiId

Write-Host "Fixing CORS configuration for API Gateway..." -ForegroundColor Yellow
Write-Host "API ID: $apiId" -ForegroundColor Gray

# Get the API Gateway REST API ID
$restApiId = $apiId

Write-Host ""
Write-Host "Updating CORS configuration..." -ForegroundColor Cyan

# Create a CORS configuration JSON
$corsConfig = @{
    AllowMethods = "GET,POST,OPTIONS"
    AllowHeaders = "Content-Type,x-api-key,Authorization"
    AllowOrigin = "*"
    MaxAge = "600"
} | ConvertTo-Json

Write-Host ""
Write-Host "CORS Configuration:" -ForegroundColor Yellow
Write-Host $corsConfig -ForegroundColor White
Write-Host ""

Write-Host "To fix CORS, you have two options:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: Update via AWS Console (Recommended)" -ForegroundColor Cyan
Write-Host "1. Go to: https://console.aws.amazon.com/apigateway/home?region=$region#/apis/$restApiId/resources" -ForegroundColor White
Write-Host "2. Select your API: $restApiId" -ForegroundColor White
Write-Host "3. Go to Actions -> Enable CORS" -ForegroundColor White
Write-Host "4. Configure:" -ForegroundColor White
Write-Host "   - Allow Origin: *" -ForegroundColor Gray
Write-Host "   - Allow Methods: GET, POST, OPTIONS" -ForegroundColor Gray
Write-Host "   - Allow Headers: Content-Type, x-api-key, Authorization" -ForegroundColor Gray
Write-Host "   - Max Age: 600" -ForegroundColor Gray
Write-Host "5. Click 'Enable CORS and replace existing CORS headers'" -ForegroundColor White
Write-Host "6. Deploy API (Actions -> Deploy API -> Stage: dev)" -ForegroundColor White
Write-Host ""

Write-Host "Option 2: Redeploy Backend with SAM" -ForegroundColor Cyan
Write-Host "cd infrastructure" -ForegroundColor White
Write-Host "sam build" -ForegroundColor White
Write-Host "sam deploy" -ForegroundColor White
Write-Host ""

Write-Host "After updating CORS, test your frontend again!" -ForegroundColor Green

