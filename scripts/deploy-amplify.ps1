# Comprehensive Amplify Deployment Script
# This script automates as much as possible and guides through manual steps

param(
    [string]$GitHubToken = "",
    [string]$AppName = "DungeonCrawlerBlueprints"
)

$ErrorActionPreference = "Stop"

# Change to repo root directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptPath
Set-Location $repoRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "AWS Amplify Deployment Automation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify backend deployment
Write-Host "Step 1: Verifying Backend Deployment" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

$stackName = "dungeoncrawler-blueprints"
$apiUrl = ""
$apiKey = ""

try {
    $stackCheck = aws cloudformation describe-stacks --stack-name $stackName --region us-east-1 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Backend stack not found. Please deploy backend first." -ForegroundColor Red
        Write-Host "Run: cd infrastructure && sam build && sam deploy --guided" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "[OK] Backend stack found" -ForegroundColor Green
    
    # Get API URL
    $apiUrl = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --region us-east-1 `
        --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" `
        --output text 2>&1
    
    if ($LASTEXITCODE -eq 0 -and $apiUrl -and $apiUrl -notmatch "error") {
        Write-Host "[OK] API URL: $apiUrl" -ForegroundColor Green
    } else {
        Write-Host "WARNING: Could not retrieve API URL automatically" -ForegroundColor Yellow
        $apiUrl = Read-Host "Please enter your API Gateway URL"
    }
    
    # Get API Key
    Write-Host "Retrieving API Key..." -ForegroundColor Gray
    $apiKeyId = aws cloudformation describe-stacks `
        --stack-name $stackName `
        --region us-east-1 `
        --query "Stacks[0].Outputs[?OutputKey=='ApiKeyId'].OutputValue" `
        --output text 2>&1
    
    if ($LASTEXITCODE -eq 0 -and $apiKeyId) {
        $apiKey = aws apigateway get-api-key `
            --api-key $apiKeyId `
            --include-value `
            --region us-east-1 `
            --query "value" `
            --output text 2>&1
        
        if ($LASTEXITCODE -eq 0 -and $apiKey) {
            Write-Host "[OK] API Key retrieved" -ForegroundColor Green
        } else {
            Write-Host "WARNING: Could not retrieve API Key automatically" -ForegroundColor Yellow
            $apiKey = Read-Host "Please enter your API Key"
        }
    } else {
        $apiKey = Read-Host "Please enter your API Key"
    }
} catch {
    Write-Host "ERROR: Failed to verify backend deployment" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Check if Amplify app already exists
Write-Host "Step 2: Checking for Existing Amplify App" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

$existingApps = aws amplify list-apps --region us-east-1 --output json | ConvertFrom-Json
$appId = $null
$appName = $null

foreach ($app in $existingApps.apps) {
    if ($app.repository -eq "https://github.com/franciszver/DungeonCrawlerBlueprints.git" -or 
        $app.name -eq $AppName) {
        $appId = $app.appId
        $appName = $app.name
        Write-Host "[OK] Found existing app: $appName (ID: $appId)" -ForegroundColor Green
        break
    }
}

Write-Host ""

# Step 3: Create Amplify app if it doesn't exist
if (-not $appId) {
    Write-Host "Step 3: Creating Amplify App" -ForegroundColor Yellow
    Write-Host "-----------------------------------" -ForegroundColor Yellow
    
    if ([string]::IsNullOrWhiteSpace($GitHubToken)) {
        Write-Host ""
        Write-Host "To create the Amplify app automatically, you need a GitHub Personal Access Token." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Option 1: Create via AWS Console (Recommended for first-time setup)" -ForegroundColor Cyan
        Write-Host "  1. Go to: https://console.aws.amazon.com/amplify/" -ForegroundColor White
        Write-Host "  2. Click 'New app' -> 'Host web app'" -ForegroundColor White
        Write-Host "  3. Select GitHub and authorize" -ForegroundColor White
        Write-Host "  4. Select repository: franciszver/DungeonCrawlerBlueprints" -ForegroundColor White
        Write-Host "  5. Select branch: main" -ForegroundColor White
        Write-Host "  6. App name: $AppName" -ForegroundColor White
        Write-Host "  7. After creation, come back and run this script with -GitHubToken parameter" -ForegroundColor White
        Write-Host ""
        Write-Host "Option 2: Use GitHub Personal Access Token" -ForegroundColor Cyan
        Write-Host "  1. Create token at: https://github.com/settings/tokens" -ForegroundColor White
        Write-Host "  2. Required scopes: repo (Full control of private repositories)" -ForegroundColor White
        Write-Host "  3. Run: .\scripts\deploy-amplify.ps1 -GitHubToken YOUR_TOKEN" -ForegroundColor White
        Write-Host ""
        
        $choice = Read-Host "Have you created the app in the console? (y/n)"
        if ($choice -eq "y" -or $choice -eq "Y") {
            Write-Host "Checking for the newly created app..." -ForegroundColor Gray
            Start-Sleep -Seconds 3
            $existingApps = aws amplify list-apps --region us-east-1 --output json | ConvertFrom-Json
            foreach ($app in $existingApps.apps) {
                if ($app.repository -eq "https://github.com/franciszver/DungeonCrawlerBlueprints.git" -or 
                    $app.name -eq $AppName) {
                    $appId = $app.appId
                    $appName = $app.name
                    Write-Host "[OK] Found app: $appName (ID: $appId)" -ForegroundColor Green
                    break
                }
            }
            
            if (-not $appId) {
                Write-Host "App not found. Please create it in the console first." -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "Please create the app in the console or provide a GitHub token." -ForegroundColor Yellow
            exit 0
        }
    } else {
        Write-Host "Creating Amplify app with GitHub token..." -ForegroundColor Gray
        
        $createAppJson = @{
            name = $AppName
            repository = "https://github.com/franciszver/DungeonCrawlerBlueprints.git"
            platform = "WEB"
            accessToken = $GitHubToken
            environmentVariables = @{
                VITE_API_URL = $apiUrl
                VITE_API_KEY = $apiKey
            }
        } | ConvertTo-Json -Depth 10
        
        try {
            $createResult = aws amplify create-app `
                --name $AppName `
                --repository "https://github.com/franciszver/DungeonCrawlerBlueprints.git" `
                --platform WEB `
                --access-token $GitHubToken `
                --environment-variables "VITE_API_URL=$apiUrl,VITE_API_KEY=$apiKey" `
                --region us-east-1 `
                --output json | ConvertFrom-Json
            
            $appId = $createResult.app.appId
            $appName = $createResult.app.name
            Write-Host "[OK] App created: $appName (ID: $appId)" -ForegroundColor Green
        } catch {
            Write-Host "ERROR: Failed to create app via CLI" -ForegroundColor Red
            Write-Host $_.Exception.Message -ForegroundColor Red
            Write-Host ""
            Write-Host "Please create the app manually in the console:" -ForegroundColor Yellow
            Write-Host "https://console.aws.amazon.com/amplify/" -ForegroundColor White
            exit 1
        }
    }
} else {
    Write-Host "Step 3: Using Existing Amplify App" -ForegroundColor Yellow
    Write-Host "-----------------------------------" -ForegroundColor Yellow
    Write-Host "[OK] Using app: $appName (ID: $appId)" -ForegroundColor Green
}

Write-Host ""

# Step 4: Configure environment variables
Write-Host "Step 4: Configuring Environment Variables" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

try {
    # Get current environment variables
    $currentEnvVars = aws amplify get-app `
        --app-id $appId `
        --region us-east-1 `
        --output json | ConvertFrom-Json
    
    $envVars = @{}
    if ($currentEnvVars.app.environmentVariables) {
        $currentEnvVars.app.environmentVariables.PSObject.Properties | ForEach-Object {
            $envVars[$_.Name] = $_.Value
        }
    }
    
    # Update with our values
    $envVars["VITE_API_URL"] = $apiUrl
    $envVars["VITE_API_KEY"] = $apiKey
    
    # Convert to AWS CLI format
    $envVarString = ($envVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ","
    
    Write-Host "Updating environment variables..." -ForegroundColor Gray
    aws amplify update-app `
        --app-id $appId `
        --environment-variables $envVarString `
        --region us-east-1 `
        --output json | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Environment variables configured" -ForegroundColor Green
        Write-Host "  VITE_API_URL = $apiUrl" -ForegroundColor Gray
        Write-Host "  VITE_API_KEY = $apiKey" -ForegroundColor Gray
    } else {
        Write-Host "WARNING: Could not update environment variables via CLI" -ForegroundColor Yellow
        Write-Host "Please set them manually in the Amplify Console:" -ForegroundColor Yellow
        Write-Host "  VITE_API_URL = $apiUrl" -ForegroundColor White
        Write-Host "  VITE_API_KEY = $apiKey" -ForegroundColor White
    }
} catch {
    Write-Host "WARNING: Could not configure environment variables automatically" -ForegroundColor Yellow
    Write-Host "Please set them manually in the Amplify Console:" -ForegroundColor Yellow
    Write-Host "  VITE_API_URL = $apiUrl" -ForegroundColor White
    Write-Host "  VITE_API_KEY = $apiKey" -ForegroundColor White
}

Write-Host ""

# Step 5: Connect branch and trigger deployment
Write-Host "Step 5: Connecting Branch and Deploying" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

try {
    # Check if branch already exists
    $branches = aws amplify list-branches `
        --app-id $appId `
        --region us-east-1 `
        --output json | ConvertFrom-Json
    
    $branchExists = $false
    foreach ($branch in $branches.branches) {
        if ($branch.branchName -eq "main") {
            $branchExists = $true
            Write-Host "[OK] Branch 'main' already connected" -ForegroundColor Green
            break
        }
    }
    
    if (-not $branchExists) {
        Write-Host "Creating branch connection..." -ForegroundColor Gray
        
        # Create branch
        aws amplify create-branch `
            --app-id $appId `
            --branch-name main `
            --region us-east-1 `
            --output json | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Branch 'main' created and connected" -ForegroundColor Green
        } else {
            Write-Host "WARNING: Could not create branch via CLI" -ForegroundColor Yellow
            Write-Host "Please connect the branch manually in the Amplify Console" -ForegroundColor Yellow
        }
    }
    
    # Trigger deployment
    Write-Host "Triggering deployment..." -ForegroundColor Gray
    $jobResult = aws amplify start-job `
        --app-id $appId `
        --branch-name main `
        --job-type RELEASE `
        --region us-east-1 `
        --output json | ConvertFrom-Json
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Deployment job started" -ForegroundColor Green
        Write-Host "Job ID: $($jobResult.jobSummary.jobId)" -ForegroundColor Gray
    } else {
        Write-Host "INFO: Deployment will start automatically when branch is connected" -ForegroundColor Cyan
    }
} catch {
    Write-Host "INFO: Deployment will start automatically" -ForegroundColor Cyan
}

Write-Host ""

# Step 6: Get app URL
Write-Host "Step 6: Getting App Information" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow

try {
    $appInfo = aws amplify get-app `
        --app-id $appId `
        --region us-east-1 `
        --output json | ConvertFrom-Json
    
    $appUrl = "https://main.$($appInfo.app.defaultDomain)"
    
    Write-Host "[OK] App URL: $appUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Deployment Summary" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "App Name: $appName" -ForegroundColor White
    Write-Host "App ID: $appId" -ForegroundColor White
    Write-Host "App URL: $appUrl" -ForegroundColor White
    Write-Host ""
    Write-Host "Monitor deployment:" -ForegroundColor Yellow
    Write-Host "https://console.aws.amazon.com/amplify/home?region=us-east-1#/$appId" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "The deployment will take 3-5 minutes to complete." -ForegroundColor Cyan
    Write-Host "Once complete, your app will be live at the URL above." -ForegroundColor Cyan
    Write-Host ""
} catch {
    Write-Host "App URL: https://console.aws.amazon.com/amplify/home?region=us-east-1#/$appId" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Deployment process initiated!" -ForegroundColor Green
Write-Host ""

