# Quick Start Guide

Get your DungeonCrawlerBlueprints application up and running in minutes!

## Prerequisites Checklist

- [ ] AWS Account with appropriate permissions
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] AWS SAM CLI installed (`sam --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] OpenRouter API key ([get one here](https://openrouter.ai/))
- [ ] GitHub repository (code pushed)

## 5-Minute Deployment

### Step 1: Backend (3 minutes)

```bash
# 1. Store OpenRouter API key
.\scripts\setup-secret.ps1 YOUR_OPENROUTER_API_KEY
# or: bash scripts/setup-secret.sh YOUR_OPENROUTER_API_KEY

# 2. Deploy backend
cd infrastructure
sam build
sam deploy --guided
# Accept defaults, or customize as needed

# 3. Get API credentials
cd ..
.\scripts\create-api-key.ps1
# or: bash scripts/create-api-key.sh
```

**Save these values:**
- API Gateway URL (from deployment output)
- API Key (from create-api-key script)

### Step 2: Frontend (2 minutes)

**Option A: Using Helper Script (Recommended)**

```bash
# Windows PowerShell
.\scripts\amplify-deploy-guide.ps1

# Linux/Mac
bash scripts/amplify-deploy-guide.sh
```

**Option B: Manual Steps**

1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. Click **"New app"** → **"Host web app"**
3. Connect GitHub repository
4. Add environment variables:
   - `VITE_API_URL` = Your API Gateway URL
   - `VITE_API_KEY` = Your API Key
5. Click **"Save and deploy"**

### Step 3: Test (30 seconds)

1. Open your Amplify app URL
2. Upload a blueprint image (PNG/JPG)
3. Watch rooms get detected automatically!

## Troubleshooting

**Backend deployment fails:**
- Check AWS credentials: `aws configure list`
- Verify SAM CLI: `sam --version`
- Check CloudFormation console for errors

**Frontend build fails:**
- Verify environment variables are set in Amplify
- Check build logs in Amplify Console
- Ensure `amplify.yml` exists in repo root

**API calls fail:**
- Verify API Gateway URL is correct (no trailing slash)
- Check API Key matches backend
- Review CloudWatch logs for Lambda errors

## Next Steps

- Read [Full Deployment Guide](AMPLIFY_DEPLOYMENT.md)
- Check [Deployment Checklist](DEPLOYMENT_CHECKLIST.md)
- Review [API Documentation](api.md)

## Need Help?

- Check CloudWatch logs for backend errors
- Check Amplify build logs for frontend errors
- Review browser console for API errors
- See [Troubleshooting section](AMPLIFY_DEPLOYMENT.md#troubleshooting) in deployment guide

