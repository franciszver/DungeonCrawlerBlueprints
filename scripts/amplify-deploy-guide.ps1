# Amplify Deployment Helper Script
# This script helps you prepare for AWS Amplify deployment

# Change to repo root directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptPath
Set-Location $repoRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Amplify Deployment Preparation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is deployed
Write-Host "Step 1: Verify Backend Deployment" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

$stackName = Read-Host "Enter your SAM stack name (default: dungeoncrawler-blueprints)"
if ([string]::IsNullOrWhiteSpace($stackName)) {
    $stackName = "dungeoncrawler-blueprints"
}

Write-Host "Checking CloudFormation stack..." -ForegroundColor Gray

# Check if stack exists
$stackCheck = aws cloudformation describe-stacks --stack-name $stackName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Stack not found. Please deploy backend first." -ForegroundColor Red
    Write-Host "Run: cd infrastructure && sam build && sam deploy --guided" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Stack found: $stackName" -ForegroundColor Green

# Get API URL
Write-Host "Retrieving API Gateway URL..." -ForegroundColor Gray
$apiUrl = aws cloudformation describe-stacks `
    --stack-name $stackName `
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" `
    --output text 2>&1

if ($LASTEXITCODE -eq 0 -and $apiUrl -and $apiUrl -notmatch "error") {
    Write-Host "[OK] API URL: $apiUrl" -ForegroundColor Green
} else {
    Write-Host "WARNING: Could not retrieve API URL" -ForegroundColor Yellow
    $apiUrl = Read-Host "Please enter your API Gateway URL manually"
}

Write-Host ""
Write-Host "Step 2: Get API Key" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

$apiKey = Read-Host "Enter your API Key (or press Enter to run create-api-key script)"
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "Running create-api-key script..." -ForegroundColor Gray
    & "$scriptPath\create-api-key.ps1"
    $apiKey = Read-Host "Enter the API Key shown above"
}

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "ERROR: API Key is required" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] API Key retrieved" -ForegroundColor Green

Write-Host ""
Write-Host "Step 3: Verify Frontend Configuration" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

# Check if amplify.yml exists
if (Test-Path "amplify.yml") {
    Write-Host "[OK] amplify.yml found" -ForegroundColor Green
} else {
    Write-Host "ERROR: amplify.yml not found" -ForegroundColor Red
    exit 1
}

# Check if frontend/package.json exists
if (Test-Path "frontend/package.json") {
    Write-Host "[OK] frontend/package.json found" -ForegroundColor Green
} else {
    Write-Host "ERROR: frontend/package.json not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Information" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment Variables for Amplify Console:" -ForegroundColor Yellow
Write-Host "-------------------------------------------" -ForegroundColor Yellow
Write-Host ""
Write-Host "VITE_API_URL = $apiUrl" -ForegroundColor White
Write-Host "VITE_API_KEY = $apiKey" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Go to AWS Amplify Console: https://console.aws.amazon.com/amplify/" -ForegroundColor White
Write-Host "2. Click 'New app' -> 'Host web app'" -ForegroundColor White
Write-Host "3. Connect your GitHub repository" -ForegroundColor White
Write-Host "4. Add the environment variables shown above" -ForegroundColor White
Write-Host "5. Click 'Save and deploy'" -ForegroundColor White
Write-Host ""
Write-Host "For detailed instructions, see: _docs/AMPLIFY_DEPLOYMENT.md" -ForegroundColor Cyan
Write-Host ""

# Save to file for reference
$envFile = "amplify-env-vars.txt"
@"
# Environment Variables for AWS Amplify
# Generated on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

VITE_API_URL=$apiUrl
VITE_API_KEY=$apiKey

# Instructions:
# 1. Copy these values to AWS Amplify Console -> Environment variables
# 2. Or use AWS CLI to set them (see Amplify CLI documentation)
"@ | Out-File -FilePath $envFile -Encoding UTF8

Write-Host "[OK] Environment variables saved to: $envFile" -ForegroundColor Green
Write-Host ""

