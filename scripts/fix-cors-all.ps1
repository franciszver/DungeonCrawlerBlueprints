# Fix CORS for all API Gateway resources
$apiId = "pr6y3dwk98"
$region = "us-east-1"

# Resources to configure
$resources = @(
    @{id="qe9xmy"; path="/upload"},
    @{id="77d099"; path="/detect"},
    @{id="7jywen"; path="/results/{id}"},
    @{id="9dvjnh"; path="/health"},
    @{id="gl821j"; path="/export/{id}"}
)

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

