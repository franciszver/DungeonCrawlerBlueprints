# 🚀 Amplify Deployment Status

## ✅ Completed Steps

1. ✅ **Code Committed and Pushed**
   - All code has been committed to git
   - Pushed to GitHub: `franciszver/DungeonCrawlerBlueprints`
   - Branch: `main`

2. ✅ **Backend Verified**
   - API Gateway URL: `https://YOUR_API_GATEWAY_URL.execute-api.us-east-1.amazonaws.com/dev`
   - API Key: `YOUR_API_KEY_HERE` (run `.\scripts\create-api-key.ps1` to get it)
   - Stack: `dungeoncrawler-blueprints`

3. ✅ **Frontend Ready**
   - `amplify.yml` configured
   - All React components implemented
   - Environment variables documented

## 📋 Next Steps (Manual - Required)

### Step 1: Create Amplify App in AWS Console

1. **Open AWS Amplify Console**
   - Go to: https://console.aws.amazon.com/amplify/home?region=us-east-1#/create
   - Or navigate: AWS Console → Amplify → New app

2. **Create New App**
   - Click **"New app"** → **"Host web app"**
   - Select **"GitHub"** as your source
   - Authorize AWS Amplify (if first time - this requires GitHub OAuth)
   - Select repository: **franciszver/DungeonCrawlerBlueprints**
   - Select branch: **main**
   - App name: **DungeonCrawlerBlueprints** (or leave default)

3. **Configure Build Settings**
   - Amplify should auto-detect `amplify.yml`
   - Verify the build settings look correct:
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
     ```

4. **Add Environment Variables**
   - In the "Environment variables" section, add:
     - **Key**: `VITE_API_URL`
       **Value**: `https://YOUR_API_GATEWAY_URL.execute-api.us-east-1.amazonaws.com/dev` (get from CloudFormation outputs or run `.\scripts\create-api-key.ps1`)
     - **Key**: `VITE_API_KEY`
       **Value**: `YOUR_API_KEY_HERE` (run `.\scripts\create-api-key.ps1` to get it)

5. **Deploy**
   - Click **"Save and deploy"**
   - Wait for deployment to complete (~3-5 minutes)

### Step 2: After App Creation (Automated)

Once you've created the app in the console, run this script to configure everything:

```powershell
.\scripts\amplify-quick-deploy.ps1
```

Or if you prefer the full automation script:

```powershell
.\scripts\deploy-amplify.ps1
```

## 🔧 Alternative: Fully Automated (If You Have GitHub Token)

If you have a GitHub Personal Access Token, you can fully automate:

1. **Create GitHub Token**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Name: "AWS Amplify Deployment"
   - Scopes: Check `repo` (Full control of private repositories)
   - Generate and copy the token

2. **Run Automated Script**
   ```powershell
   .\scripts\deploy-amplify.ps1 -GitHubToken YOUR_TOKEN_HERE
   ```

This will:
- Create the Amplify app
- Configure environment variables
- Connect the branch
- Trigger deployment

## 📊 Deployment Information

**Backend API:**
- URL: `https://YOUR_API_GATEWAY_URL.execute-api.us-east-1.amazonaws.com/dev` (get from CloudFormation outputs)
- API Key: `YOUR_API_KEY_HERE` (run `.\scripts\create-api-key.ps1` to get it)

**Frontend:**
- Repository: `https://github.com/franciszver/DungeonCrawlerBlueprints.git`
- Branch: `main`
- Build Config: `amplify.yml` (auto-detected)

**Environment Variables Required:**
```
VITE_API_URL=https://YOUR_API_GATEWAY_URL.execute-api.us-east-1.amazonaws.com/dev
VITE_API_KEY=YOUR_API_KEY_HERE
```

**To get these values:**
- Run `.\scripts\create-api-key.ps1` to retrieve your API Gateway URL and API Key
- Or check CloudFormation stack outputs in AWS Console

## 🎯 After Deployment

Once deployment completes:

1. **Get Your App URL**
   - Go to Amplify Console → Your App
   - The URL will be: `https://main.<app-id>.amplifyapp.com`

2. **Test the Application**
   - Open the app URL
   - Upload a blueprint image (PNG/JPG)
   - Verify room detection works
   - Test export functionality

3. **Monitor**
   - View build logs in Amplify Console
   - Check API Gateway logs in CloudWatch
   - Monitor Lambda function execution

## 📚 Documentation

- **Quick Start**: `_docs/QUICK_START.md`
- **Detailed Guide**: `_docs/AMPLIFY_DEPLOYMENT.md`
- **Deployment Checklist**: `_docs/DEPLOYMENT_CHECKLIST.md`
- **API Documentation**: `_docs/api.md`

## 🆘 Troubleshooting

### Build Fails
- Check Amplify build logs
- Verify `amplify.yml` is in repo root
- Ensure `frontend/package.json` exists

### Environment Variables Not Working
- Verify variable names start with `VITE_`
- Rebuild after adding variables
- Check browser console for errors

### API Calls Fail
- Verify API Gateway URL is correct
- Check API Key matches backend
- Review CloudWatch logs for Lambda errors

## ✨ Success!

Once deployed, your DungeonCrawlerBlueprints application will be live and ready to process blueprint images!

---

**Last Updated**: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Status**: Ready for Amplify deployment (manual GitHub OAuth step required)

