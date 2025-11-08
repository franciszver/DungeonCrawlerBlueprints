# PowerShell script to set up OpenRouter API key in AWS Secrets Manager
# Usage: .\setup-secret.ps1 YOUR_OPENROUTER_API_KEY

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey
)

$SECRET_NAME = "dungeoncrawler/openrouter-api-key"
$REGION = "us-east-1"

Write-Host "Creating/updating secret in AWS Secrets Manager..."

# Check if secret exists
try {
    aws secretsmanager describe-secret --secret-id $SECRET_NAME --region $REGION 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Secret exists, updating..."
        aws secretsmanager update-secret `
            --secret-id $SECRET_NAME `
            --secret-string "{\"api_key\": \"$ApiKey\"}" `
            --region $REGION
    }
} catch {
    Write-Host "Secret does not exist, creating..."
    aws secretsmanager create-secret `
        --name $SECRET_NAME `
        --description "OpenRouter API key for room detection" `
        --secret-string "{\"api_key\": \"$ApiKey\"}" `
        --region $REGION
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Secret created/updated successfully!" -ForegroundColor Green
Write-Host "Secret Name: $SECRET_NAME" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

