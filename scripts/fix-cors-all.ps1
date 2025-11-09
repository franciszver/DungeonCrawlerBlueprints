# Fix CORS for all API Gateway resources
# Usage: .\scripts\fix-cors-all.ps1 -ApiId YOUR_API_ID
param(
    [Parameter(Mandatory=$false)]
    [string]$ApiId = "",
    [string]$Region = "us-east-1"
)

if ([string]::IsNullOrWhiteSpace($ApiId)) {
    Write-Host "Error: API Gateway ID required" -ForegroundColor Red
    Write-Host "Usage: .\scripts\fix-cors-all.ps1 -ApiId YOUR_API_ID" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To get your API ID, run:" -ForegroundColor Cyan
    Write-Host "  aws cloudformation describe-stacks --stack-name dungeoncrawler-blueprints --query 'Stacks[0].Outputs[?OutputKey==\`"ApiId\`"].OutputValue' --output text" -ForegroundColor White
    exit 1
}

$apiId = $ApiId

Write-Host "Fetching API Gateway resources..." -ForegroundColor Cyan
$allResources = aws apigateway get-resources --rest-api-id $apiId --region $region --output json | ConvertFrom-Json

# Filter resources to configure (only endpoints we care about)
$endpointsToConfigure = @("/upload", "/detect", "/results", "/health", "/export")
$resources = @()

foreach ($resource in $allResources.items) {
    $path = $resource.path
    # Match exact paths or paths with parameters (e.g., /results/{id})
    foreach ($endpoint in $endpointsToConfigure) {
        if ($path -eq $endpoint -or $path -match "^$endpoint/") {
            $resources += @{id=$resource.id; path=$path}
            break
        }
    }
}

if ($resources.Count -eq 0) {
    Write-Host "Warning: No matching resources found. Available resources:" -ForegroundColor Yellow
    foreach ($resource in $allResources.items) {
        Write-Host "  - $($resource.path) (ID: $($resource.id))" -ForegroundColor Gray
    }
    exit 1
}

Write-Host "Found $($resources.Count) resources to configure" -ForegroundColor Green
Write-Host ""
Write-Host "Configuring CORS for all API Gateway resources..." -ForegroundColor Yellow
Write-Host ""

foreach ($resource in $resources) {
    Write-Host "Configuring $($resource.path) (ID: $($resource.id))..." -ForegroundColor Cyan
    
    # Configure OPTIONS method response
    aws apigateway put-method-response `
        --rest-api-id $apiId `
        --resource-id $resource.id `
        --http-method OPTIONS `
        --status-code 200 `
        --response-parameters file://scripts/cors-method-response.json `
        --region $region 2>&1 | Out-Null
    
    # Configure OPTIONS integration
    aws apigateway put-integration `
        --rest-api-id $apiId `
        --resource-id $resource.id `
        --http-method OPTIONS `
        --type MOCK `
        --request-templates file://scripts/cors-request-templates.json `
        --region $region 2>&1 | Out-Null
    
    # Configure OPTIONS integration response
    aws apigateway put-integration-response `
        --rest-api-id $apiId `
        --resource-id $resource.id `
        --http-method OPTIONS `
        --status-code 200 `
        --response-parameters file://scripts/cors-integration-response.json `
        --region $region 2>&1 | Out-Null
    
    Write-Host "  [OK] $($resource.path)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Deploying API..." -ForegroundColor Cyan
aws apigateway create-deployment `
    --rest-api-id $apiId `
    --stage-name dev `
    --region $region `
    --description "CORS configuration update" `
    --output json | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "CORS Configuration Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "All resources have been configured with CORS." -ForegroundColor White
    Write-Host "Test your frontend now!" -ForegroundColor Yellow
} else {
    Write-Host "[ERROR] Failed to deploy API" -ForegroundColor Red
}

