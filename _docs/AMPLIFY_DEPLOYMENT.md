# AWS Amplify Frontend Deployment Guide

This guide walks you through deploying the DungeonCrawlerBlueprints frontend to AWS Amplify.

## Prerequisites

- Backend deployed via AWS SAM (see main README.md)
- API Gateway URL and API Key from backend deployment
- GitHub repository connected to AWS Amplify

## Step 1: Get Backend Configuration

After deploying the backend with SAM, retrieve your API Gateway URL and API Key:

```bash
# Get API Gateway URL
aws cloudformation describe-stacks \
  --stack-name dungeoncrawler-blueprints \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text

# Get API Key (run the script)
# Windows PowerShell
.\scripts\create-api-key.ps1

# Linux/Mac
bash scripts/create-api-key.sh
```

## Step 2: Connect Repository to Amplify

1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. Click **"New app"** → **"Host web app"**
3. Select **GitHub** as your source
4. Authorize AWS Amplify to access your GitHub account
5. Select your repository: `DungeonCrawlerBlueprints`
6. Select the branch: `main` (or your default branch)

## Step 3: Configure Build Settings

Amplify should automatically detect the `amplify.yml` file. Verify the build settings:

**Build settings** (should be auto-detected):
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

## Step 4: Configure Environment Variables

In the Amplify Console, go to your app → **Environment variables** and add:

| Key | Value | Description |
|-----|-------|-------------|
| `VITE_API_URL` | `https://your-api-id.execute-api.us-east-1.amazonaws.com/dev` | Your API Gateway URL from Step 1 |
| `VITE_API_KEY` | `your-api-key-here` | Your API Key from Step 1 |

**Important:** Replace the placeholder values with your actual API Gateway URL and API Key.

## Step 5: Deploy

1. Click **"Save and deploy"**
2. Amplify will:
   - Install dependencies (`npm ci` in the `frontend` directory)
   - Build the React app (`npm run build`)
   - Deploy to a CloudFront distribution
3. Wait for the deployment to complete (usually 3-5 minutes)

## Step 6: Access Your Application

Once deployment completes, Amplify will provide you with:
- **App URL**: `https://<branch-name>.<app-id>.amplifyapp.com`
- **Custom domain**: (optional, can be configured later)

## Step 7: Test the Application

1. Open your Amplify app URL in a browser
2. Upload a blueprint image (PNG/JPG, max 10MB)
3. Wait for room detection (<30 seconds)
4. Verify bounding boxes are displayed correctly
5. Test export functionality (JSON/SVG)

## Troubleshooting

### Build Failures

**Error: "Cannot find module"**
- Ensure `amplify.yml` correctly changes to `frontend` directory
- Check that `package.json` exists in `frontend/`
- Verify all dependencies are listed in `package.json`

**Error: "Environment variables not found"**
- Double-check environment variable names (must start with `VITE_`)
- Ensure variables are set in Amplify Console → Environment variables
- Rebuild after adding environment variables

### Runtime Errors

**Error: "API request failed"**
- Verify `VITE_API_URL` is correct (no trailing slash)
- Verify `VITE_API_KEY` matches your API Gateway key
- Check API Gateway logs in CloudWatch
- Ensure CORS is configured in API Gateway (should be handled by SAM template)

**Error: "CORS error"**
- Check API Gateway CORS settings
- Verify API Gateway URL is correct
- Check browser console for detailed error messages

### Performance Issues

**Slow page loads:**
- Check CloudFront cache settings
- Verify build artifacts are correctly deployed
- Check browser network tab for slow requests

## Updating the Frontend

After making changes to the frontend:

1. Commit and push to your GitHub repository
2. Amplify will automatically detect the changes
3. A new build will be triggered
4. Once complete, changes will be live on your app URL

## Custom Domain (Optional)

1. In Amplify Console → **Domain management**
2. Click **"Add domain"**
3. Enter your domain name
4. Follow DNS configuration instructions
5. Wait for SSL certificate provisioning (can take up to 1 hour)

## Monitoring

- **Build logs**: Available in Amplify Console → Build history
- **Runtime logs**: Check browser console and CloudWatch (for API calls)
- **Performance**: Use AWS CloudWatch metrics in Amplify Console

## Rollback

If a deployment fails or introduces issues:

1. Go to **Deployments** in Amplify Console
2. Find the previous successful deployment
3. Click **"Redeploy this version"**

## Cost Considerations

- **Amplify Hosting**: Free tier includes 15 GB storage and 5 GB served per month
- **CloudFront**: First 1 TB data transfer free per month
- **Build minutes**: 1000 minutes/month free for 12 months

For production workloads, consider upgrading to Amplify Pro plan for more build minutes and better performance.

