# Simple CORS enablement using AWS CLI
# This uses the AWS API Gateway CORS feature
# Usage: .\scripts\enable-cors-simple.ps1 -ApiId YOUR_API_ID

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiId = "",
    [string]$Region = "us-east-1"
)

if ([string]::IsNullOrWhiteSpace($ApiId)) {
    Write-Host "Error: API Gateway ID required" -ForegroundColor Red
    Write-Host "Usage: .\scripts\enable-cors-simple.ps1 -ApiId YOUR_API_ID" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To get your API ID, run:" -ForegroundColor Cyan
    Write-Host "  aws cloudformation describe-stacks --stack-name dungeoncrawler-blueprints --query 'Stacks[0].Outputs[?OutputKey==\`"ApiId\`"].OutputValue' --output text" -ForegroundColor White
    exit 1
}

$apiId = $ApiId

Write-Host "Enabling CORS on API Gateway..." -ForegroundColor Yellow
Write-Host "API ID: $apiId" -ForegroundColor Gray
Write-Host ""

# Get all resources
Write-Host "Getting API resources..." -ForegroundColor Cyan
$resources = aws apigateway get-resources --rest-api-id $apiId --region $region --output json | ConvertFrom-Json

$resourcesToUpdate = @()
foreach ($resource in $resources.items) {
    if ($resource.path -match "^/(upload|detect|results|export|health)") {
        $resourcesToUpdate += $resource
        Write-Host "Found resource: $($resource.path) (ID: $($resource.id))" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "To enable CORS properly, please use the AWS Console:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Go to: https://console.aws.amazon.com/apigateway/home?region=$region#/apis/$apiId/resources" -ForegroundColor White
Write-Host ""
Write-Host "2. For EACH resource (/upload, /detect, /results, /export, /health):" -ForegroundColor Cyan
Write-Host "   a. Click on the resource" -ForegroundColor Gray
Write-Host "   b. Click 'Actions' -> 'Enable CORS'" -ForegroundColor Gray
Write-Host "   c. Configure:" -ForegroundColor Gray
Write-Host "      - Allow Origin: *" -ForegroundColor White
Write-Host "      - Allow Methods: GET, POST, OPTIONS" -ForegroundColor White
Write-Host "      - Allow Headers: Content-Type, x-api-key, Authorization" -ForegroundColor White
Write-Host "      - Max Age: 600" -ForegroundColor White
Write-Host "   d. Click 'Enable CORS and replace existing CORS headers'" -ForegroundColor Gray
Write-Host ""
Write-Host "3. After configuring all resources:" -ForegroundColor Cyan
Write-Host "   a. Click 'Actions' -> 'Deploy API'" -ForegroundColor Gray
Write-Host "   b. Select stage: dev" -ForegroundColor Gray
Write-Host "   c. Click 'Deploy'" -ForegroundColor Gray
Write-Host ""

Write-Host "OR use this AWS CLI command for each resource:" -ForegroundColor Yellow
Write-Host ""
foreach ($resource in $resourcesToUpdate) {
    Write-Host "# For $($resource.path):" -ForegroundColor Cyan
    Write-Host "aws apigateway put-integration-response --rest-api-id $apiId --resource-id $($resource.id) --http-method OPTIONS --status-code 200 --response-parameters '{\"method.response.header.Access-Control-Allow-Origin\":\"'\''*'\''\",\"method.response.header.Access-Control-Allow-Headers\":\"'\''Content-Type,x-api-key,Authorization'\''\",\"method.response.header.Access-Control-Allow-Methods\":\"'\''GET,POST,OPTIONS'\''\"}' --region $region" -ForegroundColor White
    Write-Host ""
}

Write-Host "After enabling CORS, test your frontend!" -ForegroundColor Green

