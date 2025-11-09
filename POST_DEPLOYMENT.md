# 🎉 Post-Deployment Guide

Your DungeonCrawlerBlueprints application is now deployed! Here's what to do next.

## ✅ Verify Deployment

### 1. Get Your App URL

Your app should be live at:
```
https://main.<app-id>.amplifyapp.com
```

To find your app URL:
1. Go to [AWS Amplify Console](https://console.aws.amazon.com/amplify/home?region=us-east-1)
2. Click on your app (DungeonCrawlerBlueprints)
3. Copy the URL from the app overview page

Or run this command:
```powershell
aws amplify list-apps --region us-east-1 --query "apps[?contains(repository, 'DungeonCrawlerBlueprints')].{Name:name, AppId:appId, Domain:defaultDomain}" --output table
```

### 2. Test the Application

1. **Open the App URL** in your browser
2. **Upload a Blueprint Image**
   - Click "Upload Blueprint"
   - Select a PNG or JPG image of an architectural blueprint
   - Maximum file size: 10MB
3. **Watch the Magic Happen!**
   - The image will be uploaded to S3
   - AI will analyze the blueprint using GPT-4 Vision
   - Room boundaries will be detected automatically
   - Results will display with bounding boxes

### 3. Test Export Functionality

Once detection completes:
- Click "Export" button
- Choose format: JSON or SVG
- Download the results

## 🔍 Verify Everything Works

### Backend Health Check

Test the backend API directly:

```powershell
# Get your API Gateway URL (run: .\scripts\create-api-key.ps1)
$apiUrl = "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev"
$apiKey = "YOUR_API_KEY_HERE"

# Test health endpoint
Invoke-RestMethod -Uri "$apiUrl/health" -Method Get -Headers @{"x-api-key"=$apiKey}
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-08T..."
}
```

### Frontend Console Check

1. Open your app URL in browser
2. Open Developer Tools (F12)
3. Check Console tab for any errors
4. Check Network tab to verify API calls are working

## 📊 Monitor Your Application

### AWS Amplify Console
- **Build History**: View all deployments
- **Build Logs**: Debug build issues
- **Environment Variables**: Update config
- **Custom Domain**: Add your own domain (optional)

### AWS CloudWatch
- **Lambda Logs**: Check function execution
- **API Gateway Logs**: Monitor API requests
- **Error Tracking**: Find and fix issues

### S3 Bucket
- **Blueprint Storage**: View uploaded images
- **Access Logs**: Monitor file access

## 🎯 Next Steps

### 1. Test with Real Blueprints

Try uploading different types of blueprints:
- Simple floor plans
- Complex multi-room layouts
- Different image formats (PNG, JPG)

### 2. Review Results

Check the accuracy of room detection:
- Are rooms correctly identified?
- Are bounding boxes accurate?
- Are room names/numbers detected?

### 3. Customize (Optional)

- **Update UI**: Modify React components in `frontend/src/components/`
- **Adjust Detection**: Tune AI prompts in `backend/shared/room_detector.py`
- **Add Features**: Extend functionality as needed

### 4. Share Your App

- Share the Amplify URL with others
- Set up a custom domain (optional)
- Monitor usage and performance

## 🐛 Troubleshooting

### App Won't Load

1. **Check Amplify Console** → Build status
2. **Verify Environment Variables** are set correctly
3. **Check Browser Console** for errors
4. **Verify API Gateway** is accessible

### Room Detection Not Working

1. **Check CloudWatch Logs** for Lambda errors
2. **Verify OpenRouter API Key** is set in Secrets Manager
3. **Check API Gateway** logs for request errors
4. **Verify Image Format** (PNG/JPG, max 10MB)

### API Errors

1. **Check API Key** is correct in Amplify env vars
2. **Verify API Gateway URL** has no trailing slash
3. **Check CORS** settings in API Gateway
4. **Review CloudWatch** logs for detailed errors

## 📚 Documentation

- **API Reference**: `_docs/api.md`
- **Architecture**: `_docs/architecture.md`
- **Requirements**: `_docs/REQUIREMENTS.md`
- **Deployment Guide**: `_docs/AMPLIFY_DEPLOYMENT.md`

## 🎊 Success!

Your DungeonCrawlerBlueprints application is live and ready to detect rooms from architectural blueprints!

**Key URLs:**
- **Frontend**: Your Amplify app URL
- **Backend API**: `https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev` (get from CloudFormation outputs or run `.\scripts\create-api-key.ps1`)
- **Amplify Console**: https://console.aws.amazon.com/amplify/home?region=us-east-1
- **CloudWatch**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1

---

**Need help?** Check the troubleshooting section above or review the CloudWatch logs for detailed error messages.

