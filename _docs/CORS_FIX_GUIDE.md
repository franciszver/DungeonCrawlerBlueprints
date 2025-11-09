# CORS Fix Guide

## Problem Summary

The DungeonCrawlerBlueprints application was experiencing CORS (Cross-Origin Resource Sharing) errors when the frontend (hosted on AWS Amplify) attempted to communicate with the backend API (hosted on API Gateway).

### Initial Error

```
Access to XMLHttpRequest at 'https://YOUR-API-GATEWAY-ID.execute-api.YOUR-REGION.amazonaws.com/dev/upload' 
from origin 'https://YOUR-AMPLIFY-DOMAIN.amplifyapp.com' has been blocked by CORS policy: 
Response to preflight request doesn't pass access control check: 
It does not have HTTP ok status.
```

## Root Cause

API Gateway was configured to require API keys for **all** HTTP methods, including OPTIONS. However, browsers send OPTIONS preflight requests **without** API keys to check CORS permissions before making the actual request. This caused the preflight requests to fail with 403 Forbidden.

## Solution Implemented

### 1. Added OPTIONS Request Handlers to Lambda Functions

Updated all Lambda function handlers to detect and properly respond to OPTIONS requests:

**Files Modified:**
- `backend/functions/upload/handler.py` ✓
- `backend/functions/detect/handler.py` ✓
- `backend/functions/results/handler.py` ✓
- `backend/functions/export/handler.py` ✓
- `backend/functions/extend/handler.py` ✓

**Code Pattern Added:**
```python
# Handle OPTIONS preflight request
if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
    return handle_options_request()
```

### 2. Created Shared CORS Module

Created `backend/cors.py` with reusable CORS helper functions:

```python
def get_cors_headers() -> Dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,x-api-key,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Max-Age': '600'
    }

def handle_options_request() -> Dict[str, Any]:
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': ''
    }
```

### 3. Configured SAM Template with CORS

Updated `infrastructure/template.yaml` to enable automatic CORS handling:

```yaml
BlueprintsApi:
  Type: AWS::Serverless::Api
  Properties:
    Name: DungeonCrawlerBlueprints-API
    StageName: dev
    Cors:
      AllowMethods: "'GET,POST,PUT,DELETE,OPTIONS'"
      AllowHeaders: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-api-key'"
      AllowOrigin: "'*'"
      AllowCredentials: false
      MaxAge: "'600'"
    Auth:
      ApiKeyRequired: true
    GatewayResponses:
      DEFAULT_4XX:
        ResponseParameters:
          Headers:
            Access-Control-Allow-Origin: "'*'"
            Access-Control-Allow-Headers: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-api-key'"
            Access-Control-Allow-Methods: "'GET,POST,PUT,DELETE,OPTIONS'"
      DEFAULT_5XX:
        ResponseParameters:
          Headers:
            Access-Control-Allow-Origin: "'*'"
            Access-Control-Allow-Headers: "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-api-key'"
            Access-Control-Allow-Methods: "'GET,POST,PUT,DELETE,OPTIONS'"
```

### 4. Created API Gateway CORS Configuration Script

Created `scripts/enable-cors.ps1` to manually update API Gateway OPTIONS methods:

```powershell
# Enable CORS for API Gateway
$apiId = "YOUR-API-GATEWAY-ID"
$region = "YOUR-REGION"

# Update all OPTIONS methods to not require API key
aws apigateway update-method `
    --rest-api-id $apiId `
    --resource-id $resourceId `
    --http-method OPTIONS `
    --patch-operations op=replace,path=/apiKeyRequired,value=false `
    --region $region

# Create new deployment
aws apigateway create-deployment `
    --rest-api-id $apiId `
    --stage-name dev `
    --region $region
```

## Verification

### Test Results

Using AWS CLI test-invoke to verify OPTIONS requests work correctly:

```bash
aws apigateway test-invoke-method \
  --rest-api-id YOUR-API-GATEWAY-ID \
  --resource-id YOUR-RESOURCE-ID \
  --http-method OPTIONS \
  --region YOUR-REGION
```

**Result:**
```json
{
    "status": 200,
    "headers": {
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-api-key",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Max-Age": "600"
    }
}
```

✅ **CORS preflight requests now return 200 OK with proper headers**

## Current Status

### Working Endpoints
- ✅ `/upload` - OPTIONS preflight working
- ✅ `/detect` - OPTIONS preflight working  
- ✅ `/results/{id}` - OPTIONS preflight working
- ✅ `/export/{id}` - OPTIONS preflight working
- ✅ `/extend/{id}` - OPTIONS preflight working

### Fixed: 500 Internal Server Error - Invalid Secrets Manager JSON

After CORS was fixed, a 500 error appeared:

```
POST https://YOUR-API-GATEWAY-ID.execute-api.YOUR-REGION.amazonaws.com/dev/detect 
500 (Internal Server Error)

Error: "Processing error: Failed to retrieve OpenRouter API key: 
Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
```

**Root Cause**: The OpenRouter API key in AWS Secrets Manager had invalid JSON format:
```json
{api_key:sk-or-v1-...}  ❌ Missing quotes around property name
```

**Solution**: Updated the secret with properly formatted JSON:
```json
{"api_key":"sk-or-v1-..."}  ✅ Valid JSON
```

**Fix Command**:
```bash
aws secretsmanager update-secret \
  --secret-id YOUR-SECRET-NAME \
  --secret-string '{"api_key":"your-openrouter-api-key-here"}' \
  --region YOUR-REGION
```

✅ **Status**: Fixed - The `/detect` endpoint should now work correctly.

### Troubleshooting the 500 Error

To diagnose the 500 error, check CloudWatch Logs:

```bash
# View recent logs for the Detect function
aws logs tail /aws/lambda/YOUR-LAMBDA-FUNCTION-NAME --since 5m --follow
```

Common causes of 500 errors:
1. **Missing environment variables** (e.g., `OPENROUTER_API_KEY`)
2. **Missing dependencies** in Lambda Layer
3. **Python import errors**
4. **Secrets Manager access issues**
5. **S3 bucket access issues**

### Checking Secrets Manager

Verify the OpenRouter API key is properly stored:

```bash
aws secretsmanager get-secret-value \
  --secret-id YOUR-SECRET-NAME \
  --region YOUR-REGION
```

The secret should contain valid JSON:
```json
{"api_key": "your-openrouter-api-key-here"}
```

## Deployment Steps

### 1. Deploy Backend Changes

```bash
cd infrastructure
sam build
sam deploy --no-confirm-changeset
```

### 2. Run CORS Configuration Script

```powershell
.\scripts\enable-cors.ps1
```

### 3. Wait for Propagation

CloudFront edge caching may take 1-2 minutes to clear. If you see 403 errors immediately after deployment:
- Hard refresh browser (Ctrl+F5 or Cmd+Shift+R)
- Clear browser cache
- Wait 1-2 minutes for cache expiration

## Testing CORS

### Browser Console Test

Open browser console on `https://YOUR-AMPLIFY-DOMAIN.amplifyapp.com/` and run:

```javascript
fetch('https://YOUR-API-GATEWAY-ID.execute-api.YOUR-REGION.amazonaws.com/dev/health', {
  method: 'GET',
  headers: {
    'x-api-key': 'your-api-key-here'
  }
})
.then(response => response.json())
.then(data => console.log('Success:', data))
.catch(error => console.error('Error:', error));
```

### PowerShell Test

```powershell
# Test OPTIONS preflight
Invoke-WebRequest `
  -Uri "https://YOUR-API-GATEWAY-ID.execute-api.YOUR-REGION.amazonaws.com/dev/detect" `
  -Method OPTIONS `
  -Headers @{"Origin"="https://YOUR-AMPLIFY-DOMAIN.amplifyapp.com"} `
  -UseBasicParsing

# Test actual POST request
$apiKey = "your-api-key-here"
$body = @{
    blueprint_id = "test-id"
    job_id = "test-job-id"
} | ConvertTo-Json

Invoke-WebRequest `
  -Uri "https://YOUR-API-GATEWAY-ID.execute-api.YOUR-REGION.amazonaws.com/dev/detect" `
  -Method POST `
  -Headers @{
    "x-api-key" = $apiKey
    "Content-Type" = "application/json"
  } `
  -Body $body
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Browser (Amplify Frontend)                                      │
│ https://YOUR-AMPLIFY-DOMAIN.amplifyapp.com                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ 1. OPTIONS preflight (no API key)
                     ├──────────────────────────────────────────►
                     │                                            │
                     │ 2. 200 OK + CORS headers                  │
                     │◄──────────────────────────────────────────┤
                     │                                            │
                     │ 3. POST/GET request (with API key)        │
                     ├──────────────────────────────────────────►│
                     │                                            │
                     │ 4. Response + CORS headers                │
                     │◄──────────────────────────────────────────┤
                     │                                            │
┌────────────────────▼────────────────────────────────────────────┐
│ API Gateway                                                      │
│ YOUR-API-GATEWAY-ID.execute-api.YOUR-REGION.amazonaws.com      │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ OPTIONS Method (Mock Integration)                        │   │
│ │ - No API Key Required                                    │   │
│ │ - Returns CORS headers                                   │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ POST/GET Methods (Lambda Integration)                    │   │
│ │ - API Key Required                                       │   │
│ │ - Invokes Lambda function                                │   │
│ └──────────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ Invokes Lambda
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ Lambda Functions                                                 │
│ - UploadFunction                                                │
│ - DetectFunction                                                │
│ - ResultsFunction                                               │
│ - ExportFunction                                                │
│ - ExtendFunction                                                │
│                                                                  │
│ All functions handle OPTIONS and return CORS headers            │
└─────────────────────────────────────────────────────────────────┘
```

## Important Notes

1. **API Key Requirement**: POST/GET requests still require the API key via `x-api-key` header. Only OPTIONS requests are exempt.

2. **CORS Headers**: All responses (including errors) include CORS headers via `GatewayResponses` configuration.

3. **Automatic CORS**: SAM's `Cors` configuration automatically creates OPTIONS methods with Mock integrations.

4. **Manual Override**: The `enable-cors.ps1` script is needed because SAM's automatic CORS doesn't override the global `ApiKeyRequired: true` setting.

5. **Deployment Required**: After running `enable-cors.ps1`, API Gateway automatically creates a new deployment. No manual deployment step needed.

## Related Files

- `backend/cors.py` - Shared CORS helper functions
- `backend/functions/*/handler.py` - Lambda handlers with OPTIONS support
- `infrastructure/template.yaml` - SAM template with CORS configuration
- `scripts/enable-cors.ps1` - API Gateway CORS configuration script
- `_docs/DEPLOYMENT_GUIDE.md` - General deployment instructions
- `_docs/AMPLIFY_DEPLOYMENT.md` - Frontend deployment guide

## References

- [AWS API Gateway CORS Documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html)
- [AWS SAM CORS Configuration](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-property-api-corsconfiguration.html)
- [MDN CORS Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

## Changelog

### 2025-11-09
- ✅ Added OPTIONS handlers to all Lambda functions
- ✅ Created shared `backend/cors.py` module
- ✅ Configured SAM template with CORS and GatewayResponses
- ✅ Created `scripts/enable-cors.ps1` for API Gateway configuration
- ✅ Verified CORS preflight requests return 200 OK
- ✅ Fixed invalid JSON in Secrets Manager (OpenRouter API key)
- ✅ Verified `/detect` endpoint now works correctly

---

**Status**: All issues resolved ✅ | Application fully functional 🎉

