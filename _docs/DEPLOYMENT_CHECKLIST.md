# Deployment Checklist

Use this checklist to ensure all components are properly deployed and configured.

## Pre-Deployment

- [ ] AWS CLI installed and configured
- [ ] AWS SAM CLI installed (`sam --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] OpenRouter API key obtained from [openrouter.ai](https://openrouter.ai/)
- [ ] GitHub repository created and code pushed

## Backend Deployment

- [ ] OpenRouter API key stored in AWS Secrets Manager
  ```bash
  .\scripts\setup-secret.ps1 YOUR_OPENROUTER_API_KEY
  ```
- [ ] SAM stack built successfully
  ```bash
  cd infrastructure
  sam build
  ```
- [ ] SAM stack deployed successfully
  ```bash
  sam deploy --guided
  ```
- [ ] API Gateway URL retrieved and saved
- [ ] API Key created and saved
  ```bash
  .\scripts\create-api-key.ps1
  ```
- [ ] Health endpoint tested
  ```bash
  curl -H "x-api-key: YOUR_API_KEY" https://YOUR_API_URL/health
  ```

## Frontend Deployment

- [ ] GitHub repository connected to AWS Amplify
- [ ] Environment variables configured in Amplify Console:
  - [ ] `VITE_API_URL` = Your API Gateway URL
  - [ ] `VITE_API_KEY` = Your API Key
- [ ] Build completed successfully in Amplify
- [ ] Frontend URL accessible in browser

## Testing

- [ ] Frontend loads without errors
- [ ] Can upload a blueprint image (PNG/JPG)
- [ ] Upload completes successfully
- [ ] Room detection starts automatically
- [ ] Results appear within 30 seconds
- [ ] Bounding boxes displayed correctly on blueprint
- [ ] JSON export works
- [ ] SVG export works (if implemented)
- [ ] Error handling works (test with invalid file)

## Post-Deployment Verification

- [ ] Check CloudWatch logs for Lambda functions
- [ ] Verify S3 bucket has uploaded blueprints
- [ ] Verify DynamoDB table has job records
- [ ] Check API Gateway logs for errors
- [ ] Monitor OpenRouter API usage/credits
- [ ] Test with multiple blueprint images
- [ ] Verify CORS is working (no browser console errors)

## Documentation

- [ ] README.md updated with deployment instructions
- [ ] API documentation complete (`_docs/api.md`)
- [ ] Architecture documentation complete (`_docs/architecture.md`)
- [ ] Amplify deployment guide complete (`_docs/AMPLIFY_DEPLOYMENT.md`)

## Security Checklist

- [ ] API Key stored securely (not in code)
- [ ] OpenRouter API key in Secrets Manager (not hardcoded)
- [ ] API Gateway requires API key for all endpoints
- [ ] CORS configured correctly (not allowing all origins)
- [ ] S3 bucket has appropriate access policies
- [ ] DynamoDB table has appropriate access policies
- [ ] No sensitive data in frontend code

## Performance

- [ ] Upload completes in <5 seconds
- [ ] Detection completes in <30 seconds
- [ ] Frontend loads in <3 seconds
- [ ] No memory leaks in polling logic
- [ ] API responses are cached appropriately

## Monitoring

- [ ] CloudWatch alarms configured (optional)
- [ ] Error tracking set up (optional)
- [ ] Usage metrics being collected
- [ ] Cost monitoring enabled

## Rollback Plan

- [ ] Know how to rollback frontend deployment in Amplify
- [ ] Know how to rollback backend deployment in SAM
- [ ] Have previous working versions documented
- [ ] Know how to restore from backups (if applicable)

