# Quick Amplify Deployment Helper
# This script guides you through the deployment process

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptPath
Set-Location $repoRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AWS Amplify Quick Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get backend info
Write-Host "Retrieving backend configuration..." -ForegroundColor Gray
$stackName = "dungeoncrawler-blueprints"

try {
    $apiUrl = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --region us-east-1 `
        --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" `
        --output text 2>&1
    
    $apiKeyId = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --region us-east-1 `
        --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" `
        --output text 2>&1
    
    $apiKey = aws apigateway get-api-key `
        --api-key $apiKeyId `
        --include-value `
        --region us-east-1 `
        --query "value" `
        --output text 2>&1
    
    Write-Host "[OK] Backend configuration retrieved" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Could not retrieve backend configuration" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Backend Configuration:" -ForegroundColor Yellow
Write-Host "  API URL: $apiUrl" -ForegroundColor White
Write-Host "  API Key: $apiKey" -ForegroundColor White
Write-Host ""

# Check if app exists
Write-Host "Checking for existing Amplify app..." -ForegroundColor Gray
$apps = aws amplify list-apps --region us-east-1 --output json | ConvertFrom-Json
$appId = $null

foreach ($app in $apps.apps) {
    if ($app.repository -eq "https://github.com/franciszver/DungeonCrawlerBlueprints.git") {
        $appId = $app.appId
        Write-Host "[OK] Found existing app: $($app.name) (ID: $appId)" -ForegroundColor Green
        break
    }
}

if (-not $appId) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "Step 1: Create Amplify App in Console" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Opening AWS Amplify Console..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Follow these steps:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Click 'New app' -> 'Host web app'" -ForegroundColor White
    Write-Host "2. Select 'GitHub' as your source" -ForegroundColor White
    Write-Host "3. Authorize AWS Amplify (if first time)" -ForegroundColor White
    Write-Host "4. Select repository: franciszver/DungeonCrawlerBlueprints" -ForegroundColor White
    Write-Host "5. Select branch: main" -ForegroundColor White
    Write-Host "6. App name: DungeonCrawlerBlueprints" -ForegroundColor White
    Write-Host "7. Click 'Next' -> 'Save and deploy'" -ForegroundColor White
    Write-Host ""
    Write-Host "After creating the app, come back here and press Enter to continue..." -ForegroundColor Cyan
    Write-Host ""
    
    # Open browser
    Start-Process "https://console.aws.amazon.com/amplify/home?region=us-east-1#/create"
    
    Read-Host "Press Enter after creating the app"
    
    # Check again
    Write-Host ""
    Write-Host "Checking for newly created app..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
    $apps = aws amplify list-apps --region us-east-1 --output json | ConvertFrom-Json
    
    foreach ($app in $apps.apps) {
        if ($app.repository -eq "https://github.com/franciszver/DungeonCrawlerBlueprints.git" -or 
            $app.name -eq "DungeonCrawlerBlueprints") {
            $appId = $app.appId
            Write-Host "[OK] Found app: $($app.name) (ID: $appId)" -ForegroundColor Green
            break
        }
    }
    
    if (-not $appId) {
        Write-Host "ERROR: App not found. Please ensure it was created successfully." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Step 2: Configure Environment Variables" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Update environment variables
try {
    $envVarString = "VITE_API_URL=$apiUrl,VITE_API_KEY=$apiKey"
    
    Write-Host "Updating environment variables..." -ForegroundColor Gray
    aws amplify update-app `
        --app-id $appId `
        --environment-variables $envVarString `
        --region us-east-1 `
        --output json | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Environment variables configured" -ForegroundColor Green
    } else {
        Write-Host "WARNING: Could not update via CLI. Please set manually:" -ForegroundColor Yellow
        Write-Host "  VITE_API_URL = $apiUrl" -ForegroundColor White
        Write-Host "  VITE_API_KEY = $apiKey" -ForegroundColor White
    }
} catch {
    Write-Host "WARNING: Please set environment variables manually in console:" -ForegroundColor Yellow
    Write-Host "  VITE_API_URL = $apiUrl" -ForegroundColor White
    Write-Host "  VITE_API_KEY = $apiKey" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "Step 3: Trigger Deployment" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Check if branch exists
$branches = aws amplify list-branches --app-id $appId --region us-east-1 --output json | ConvertFrom-Json
$mainBranchExists = $false

foreach ($branch in $branches.branches) {
    if ($branch.branchName -eq "main") {
        $mainBranchExists = $true
        break
    }
}

if (-not $mainBranchExists) {
    Write-Host "Creating 'main' branch..." -ForegroundColor Gray
    aws amplify create-branch `
        --app-id $appId `
        --branch-name main `
        --region us-east-1 `
        --output json | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Branch 'main' created" -ForegroundColor Green
    }
}

# Trigger deployment
Write-Host "Starting deployment..." -ForegroundColor Gray
try {
    $job = aws amplify start-job `
        --app-id $appId `
        --branch-name main `
        --job-type RELEASE `
        --region us-east-1 `
        --output json | ConvertFrom-Json
    
    Write-Host "[OK] Deployment started!" -ForegroundColor Green
    Write-Host "Job ID: $($job.jobSummary.jobId)" -ForegroundColor Gray
} catch {
    Write-Host "INFO: Deployment will start automatically" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get app info
$appInfo = aws amplify get-app --app-id $appId --region us-east-1 --output json | ConvertFrom-Json
$appUrl = "https://main.$($appInfo.app.defaultDomain)"

Write-Host "App URL: $appUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Monitor deployment:" -ForegroundColor Yellow
Write-Host "https://console.aws.amazon.com/amplify/home?region=us-east-1#/$appId" -ForegroundColor Cyan
Write-Host ""
Write-Host "Deployment typically takes 3-5 minutes." -ForegroundColor Cyan
Write-Host "Once complete, your app will be live!" -ForegroundColor Cyan
Write-Host ""

