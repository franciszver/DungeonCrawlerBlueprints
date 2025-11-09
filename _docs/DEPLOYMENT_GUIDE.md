# Deployment Guide

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- SAM CLI installed
- Node.js 18+ and npm
- Python 3.11+
- OpenRouter API key

## Backend Deployment

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt -t .
```

### 2. Configure Secrets

Create the OpenRouter API key secret in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name dungeoncrawler/openrouter-api-key \
  --secret-string '{"api_key":"your-openrouter-api-key-here"}'
```

### 3. Deploy with SAM

```bash
cd infrastructure
sam build
sam deploy --guided
```

Follow the prompts:
- Stack Name: `DungeonCrawlerBlueprints`
- AWS Region: Your preferred region
- Confirm changes before deploy: Y
- Allow SAM CLI IAM role creation: Y
- Save arguments to configuration file: Y

### 4. Note API Endpoints

After deployment, SAM will output the API Gateway URL. Save this for frontend configuration.

### 5. Configure CORS (if needed)

If you encounter CORS issues, run:

```bash
cd scripts
./enable-cors-simple.ps1
```

## Frontend Deployment

### Option 1: AWS Amplify (Recommended)

1. **Connect Repository:**
   - Go to AWS Amplify Console
   - Click "New app" > "Host web app"
   - Connect your GitHub repository
   - Select the `main` branch

2. **Configure Build Settings:**
   
   Use the provided `amplify.yml`:
   ```yaml
   version: 1
   frontend:
     phases:
       preBuild:
         commands:
           - cd frontend
           - npm ci
       build:
         commands:
           - npm run build
     artifacts:
       baseDirectory: frontend/dist
       files:
         - '**/*'
     cache:
       paths:
         - frontend/node_modules/**/*
   ```

3. **Set Environment Variables:**
   
   In Amplify Console > App settings > Environment variables:
   ```
   VITE_API_BASE_URL=https://your-api-gateway-url.execute-api.region.amazonaws.com/Prod
   ```

4. **Deploy:**
   
   Amplify will automatically deploy on push to main branch.

### Option 2: Manual S3 + CloudFront

1. **Build Frontend:**
   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. **Create S3 Bucket:**
   ```bash
   aws s3 mb s3://dungeoncrawler-blueprints-frontend
   aws s3 website s3://dungeoncrawler-blueprints-frontend --index-document index.html
   ```

3. **Upload Build:**
   ```bash
   aws s3 sync dist/ s3://dungeoncrawler-blueprints-frontend
   ```

4. **Configure CloudFront (Optional):**
   - Create CloudFront distribution pointing to S3 bucket
   - Configure custom domain if desired

## Training Data Preparation

### 1. Set Environment Variables

```bash
export OPENROUTER_API_KEY=your-key-here
export AWS_REGION=us-east-1
export TRAINING_DATA_BUCKET=your-s3-bucket-name
```

### 2. Run Training Data Script

```bash
cd scripts
python prepare-training-data.py --count 10 --output-bucket $TRAINING_DATA_BUCKET
```

This will:
- Download 10 examples from Hugging Face dataset
- Auto-annotate them using GPT-4 Vision
- Upload to S3 for few-shot learning

### 3. Verify Upload

```bash
aws s3 ls s3://$TRAINING_DATA_BUCKET/training-data/
```

## Post-Deployment Testing

### 1. Health Check

```bash
curl https://your-api-url/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-09T..."
}
```

### 2. Upload Test

```bash
curl -X POST https://your-api-url/upload \
  -F "file=@test-blueprint.png"
```

### 3. Frontend Test

1. Navigate to your Amplify URL
2. Upload a test blueprint
3. Verify detection results appear
4. Test interactive mode (if doors detected)

## Environment Variables Reference

### Backend (SAM template.yaml)

```yaml
Environment:
  Variables:
    DYNAMODB_TABLE_NAME: !Ref JobsTable
    S3_BUCKET_NAME: !Ref BlueprintsBucket
    SECRETS_MANAGER_SECRET_NAME: dungeoncrawler/openrouter-api-key
    OPENROUTER_MODEL: openai/gpt-4o
    CONFIDENCE_THRESHOLD: "0.7"
    MAX_RETRY_ATTEMPTS: "2"
    ENABLE_POLYGON_DETECTION: "true"
    ENABLE_DOOR_DETECTION: "true"
    FEW_SHOT_EXAMPLE_COUNT: "3"
    MAX_CANVAS_WIDTH: "2000"
    MAX_CANVAS_HEIGHT: "2000"
```

### Frontend (Amplify or .env)

```
VITE_API_BASE_URL=https://your-api-gateway-url
```

## Monitoring and Logs

### CloudWatch Logs

View Lambda logs:
```bash
aws logs tail /aws/lambda/DungeonCrawlerBlueprints-DetectFunction --follow
```

### DynamoDB

Check job status:
```bash
aws dynamodb scan --table-name DungeonCrawlerBlueprints-Jobs
```

### S3

List uploaded blueprints:
```bash
aws s3 ls s3://your-blueprints-bucket/
```

## Troubleshooting

### Issue: CORS Errors

**Solution:** Run CORS configuration script:
```bash
cd scripts
./enable-cors-simple.ps1
```

### Issue: Lambda Timeout

**Solution:** Increase timeout in `template.yaml`:
```yaml
Timeout: 60  # Increase from 30
```

### Issue: Out of Memory

**Solution:** Increase memory in `template.yaml`:
```yaml
MemorySize: 2048  # Increase from 1024
```

### Issue: Training Data Not Loading

**Solution:** 
1. Check S3 bucket permissions
2. Verify Lambda has S3 read access
3. Check CloudWatch logs for errors

### Issue: Low Detection Accuracy

**Solution:**
1. Add more training examples
2. Adjust confidence threshold
3. Enable multi-model validation

## Updating Deployment

### Backend Updates

```bash
cd infrastructure
sam build
sam deploy
```

### Frontend Updates

With Amplify:
- Push to main branch (auto-deploys)

Manual:
```bash
cd frontend
npm run build
aws s3 sync dist/ s3://your-bucket --delete
```

## Cost Optimization

### Lambda
- Use reserved concurrency for predictable workloads
- Monitor CloudWatch metrics for cold starts

### S3
- Enable lifecycle policies to archive old blueprints
- Use Intelligent-Tiering for cost savings

### DynamoDB
- Use on-demand pricing for variable workloads
- Enable TTL for temporary job records

### OpenRouter
- Monitor API usage in OpenRouter dashboard
- Adjust retry logic to minimize unnecessary calls
- Use caching for repeated requests

## Security Best Practices

1. **API Gateway:**
   - Enable API key requirement
   - Set up usage plans and throttling
   - Use WAF for DDoS protection

2. **S3:**
   - Enable bucket encryption
   - Block public access
   - Use signed URLs for temporary access

3. **Secrets:**
   - Rotate API keys regularly
   - Use least-privilege IAM roles
   - Enable CloudTrail for audit logs

4. **Frontend:**
   - Enable HTTPS only
   - Set up CSP headers
   - Use environment variables for config

## Rollback Procedure

If deployment fails:

```bash
cd infrastructure
sam deploy --stack-name DungeonCrawlerBlueprints --rollback
```

Or manually in AWS Console:
1. Go to CloudFormation
2. Select stack
3. Click "Stack actions" > "Roll back"

## Support

For issues:
1. Check CloudWatch Logs
2. Review `_docs/` folder for detailed documentation
3. Check `NEXT_STEPS.md` for known issues
4. Review GitHub issues (if applicable)

