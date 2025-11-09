# Configure CORS for API Gateway
# Usage: .\scripts\configure-cors.ps1 -ApiId YOUR_API_ID -ResourceId YOUR_RESOURCE_ID

param(
    [Parameter(Mandatory=$false)]
    [string]$ApiId = "",
    [Parameter(Mandatory=$false)]
    [string]$ResourceId = "",
    [string]$Region = "us-east-1"
)

if ([string]::IsNullOrWhiteSpace($ApiId)) {
    Write-Host "Error: API Gateway ID required" -ForegroundColor Red
    Write-Host "Usage: .\scripts\configure-cors.ps1 -ApiId YOUR_API_ID -ResourceId YOUR_RESOURCE_ID" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To get your API ID and Resource IDs, run:" -ForegroundColor Cyan
    Write-Host "  aws apigateway get-resources --rest-api-id YOUR_API_ID --region us-east-1" -ForegroundColor White
    exit 1
}

if ([string]::IsNullOrWhiteSpace($ResourceId)) {
    Write-Host "Error: Resource ID required" -ForegroundColor Red
    Write-Host "Usage: .\scripts\configure-cors.ps1 -ApiId YOUR_API_ID -ResourceId YOUR_RESOURCE_ID" -ForegroundColor Yellow
    exit 1
}

$apiId = $ApiId
$resourceId = $ResourceId

Write-Host "Configuring CORS for API Gateway..." -ForegroundColor Yellow
Write-Host "API ID: $apiId" -ForegroundColor Gray
Write-Host "Resource ID: $resourceId" -ForegroundColor Gray
Write-Host ""

# Step 1: Configure OPTIONS method response
Write-Host "Step 1: Configuring OPTIONS method response..." -ForegroundColor Cyan
$methodResponseParams = @{
    "method.response.header.Access-Control-Allow-Origin" = $true
    "method.response.header.Access-Control-Allow-Headers" = $true
    "method.response.header.Access-Control-Allow-Methods" = $true
    "method.response.header.Access-Control-Max-Age" = $true
} | ConvertTo-Json -Compress

$methodResponseParams = $methodResponseParams -replace '"', '\"'

aws apigateway put-method-response `
    --rest-api-id $apiId `
    --resource-id $resourceId `
    --http-method OPTIONS `
    --status-code 200 `
    --response-parameters $methodResponseParams `
    --region $region

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Method response configured" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Method response may already be configured" -ForegroundColor Yellow
}

# Step 2: Configure OPTIONS integration (MOCK)
Write-Host ""
Write-Host "Step 2: Configuring OPTIONS integration..." -ForegroundColor Cyan
$requestTemplates = '{"application/json":"{\"statusCode\":200}"}'

aws apigateway put-integration `
    --rest-api-id $apiId `
    --resource-id $resourceId `
    --http-method OPTIONS `
    --type MOCK `
    --request-templates $requestTemplates `
    --region $region

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Integration configured" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Integration may already be configured" -ForegroundColor Yellow
}

# Step 3: Configure OPTIONS integration response
Write-Host ""
Write-Host "Step 3: Configuring OPTIONS integration response..." -ForegroundColor Cyan
$integrationResponseParams = @{
    "method.response.header.Access-Control-Allow-Origin" = "'*'"
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,x-api-key,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Max-Age" = "'600'"
} | ConvertTo-Json -Compress

$integrationResponseParams = $integrationResponseParams -replace '"', '\"'

aws apigateway put-integration-response `
    --rest-api-id $apiId `
    --resource-id $resourceId `
    --http-method OPTIONS `
    --status-code 200 `
    --response-parameters $integrationResponseParams `
    --region $region

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Integration response configured" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Integration response may already be configured" -ForegroundColor Yellow
}

# Step 4: Update POST method responses to include CORS headers
Write-Host ""
Write-Host "Step 4: Updating POST method responses..." -ForegroundColor Cyan

# Get existing POST method response
$postResponse = aws apigateway get-method-response `
    --rest-api-id $apiId `
    --resource-id $resourceId `
    --http-method POST `
    --status-code 200 `
    --region $region `
    --output json | ConvertFrom-Json

if ($postResponse) {
    $postParams = @{}
    if ($postResponse.responseParameters) {
        $postResponse.responseParameters.PSObject.Properties | ForEach-Object {
            $postParams[$_.Name] = $_.Value
        }
    }
    $postParams["method.response.header.Access-Control-Allow-Origin"] = $true
    
    $postParamsJson = $postParams | ConvertTo-Json -Compress
    $postParamsJson = $postParamsJson -replace '"', '\"'
    
    aws apigateway put-method-response `
        --rest-api-id $apiId `
        --resource-id $resourceId `
        --http-method POST `
        --status-code 200 `
        --response-parameters $postParamsJson `
        --region $region
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] POST method response updated" -ForegroundColor Green
    }
}

# Step 5: Deploy API
Write-Host ""
Write-Host "Step 5: Deploying API..." -ForegroundColor Cyan
aws apigateway create-deployment `
    --rest-api-id $apiId `
    --stage-name dev `
    --region $region `
    --description "CORS configuration update" `
    --output json | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] API deployed successfully!" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to deploy API" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CORS Configuration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your API Gateway now has CORS enabled." -ForegroundColor White
Write-Host "Test your frontend again!" -ForegroundColor Yellow
Write-Host ""

