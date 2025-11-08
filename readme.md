# DungeonCrawlerBlueprints

## Overview
DungeonCrawlerBlueprints is an AI-powered service that detects rooms, hallways, and enclosed spaces from architectural blueprints using OpenRouter's GPT-4 Vision model. Inspired by procedural map generation in video games, it transforms static blueprints into dynamic, auditable room graphs in seconds.

### Why OpenRouter?

We chose **OpenRouter** as our primary AI service over AWS-native options (Rekognition, Textract) for several key reasons:

1. **Superior Vision Capabilities**: GPT-4 Vision provides state-of-the-art image understanding, specifically trained for complex visual analysis tasks like architectural blueprint interpretation.

2. **Flexibility & Model Selection**: OpenRouter allows easy switching between models (GPT-4, Claude, Gemini) without code changes, enabling cost optimization and performance tuning.

3. **Rapid Development**: OpenRouter's unified API eliminates the need for multiple AWS service integrations, reducing complexity and development time.

4. **Cost Efficiency**: Pay-per-use pricing with transparent costs, often more economical than AWS AI services for variable workloads.

5. **Future-Proof**: Easy integration of new models as they become available, keeping the system at the cutting edge of AI capabilities.

While AWS AI services are excellent for general-purpose tasks, OpenRouter's specialized vision models provide the accuracy and flexibility needed for precise architectural blueprint analysis.

---

## 1. Core Demo Goals
These features are prioritized for a 20-minute demo and meet the original spec:
- **Upload Blueprint** (PNG/JPG) via React front-end.
- **Automatic Room Detection**: Bounding boxes drawn on the blueprint.
- **JSON Output**: Returned coordinates visible in a panel or console.
- **Confidence Scores**: Each detected room includes a confidence metric.
- **Processing Speed**: Results returned in <30 seconds.

---

## 2. High-Impact Enhancements (Demo Polish)
These lightweight features make the product feel complete:
- **Adjacency Graphs**: Show simple connectivity between rooms/hallways.
- **Semantic Label Hints**: Display suggested names (mocked or heuristic).
- **Export Options**: JSON and SVG overlay download.
- **Audit Metadata**: Show model version + processing time in output.

---

## 3. Architecture (AWS + OpenRouter)
DungeonCrawlerBlueprints uses a serverless architecture:
- **AWS Services**:  
  - Lambda for serverless compute
  - API Gateway for REST API with API key authentication
  - S3 for blueprint storage
  - DynamoDB for job tracking
  - Secrets Manager for secure API key storage
  - CloudWatch for logging and monitoring
- **OpenRouter Integration**:  
  - GPT-4 Vision (openai/gpt-4o) for room detection
  - Configurable via environment variables
  - Error handling with structured responses
  - Audit logging of model usage

---

## 4. Mock Data Strategy
- **Input**: Simplified JSON wall segments (normalized 0–1000).
- **Output**: Bounding boxes + confidence scores + optional adjacency.
- **Validation**: Rooms must be closed polygons; bounding boxes non-overlapping.
- **Note**: Doors/windows and load-bearing flags are out of scope for MVP.

---

## 5. Deliverables
- **Repo**: Includes README.md, API.md, MockData.md, Architecture.md.
- **Demo**: End-to-end flow (upload → detect → render → export).
- **Docs**: Technical writeup + AI service configs.
- **Tests**: Basic unit tests for detection logic; integration demo required.

---

## 6. Roadmap
- **Phase 2**: Polygonal detection, richer adjacency graphs, semantic labeling.  
- **Phase 3**: Vector/PDF parsing, CAD export (DXF/SVG/IFC), multi-floor support.  
  - *Note*: Current version supports single-floor blueprints only. Multi-floor support is explicitly planned for future enterprise deployments.

---

## 7. Best Practices
- **Coordinate System**: Normalize to 0–1000, origin top-left.  
- **Vector Inputs**: Parse wall geometry layers only; snap endpoints; rasterize fallback.  
- **Outputs**: Include confidence scores, adjacency graphs, semantic hints, and audit metadata.  
- **Compliance**: All outputs must be auditable and reproducible.

---

## 8. Differentiator
DungeonCrawlerBlueprints draws on **game-inspired procedural room generation** to dynamically segment and connect spaces. This approach makes the system more adaptable to arbitrary blueprint styles and positions the product as both technically rigorous and creatively differentiated.

---

## Quick Start

For a fast deployment, see the [Quick Start Guide](_docs/QUICK_START.md).

**TL;DR:**
1. Deploy backend: `cd infrastructure && sam build && sam deploy --guided`
2. Get credentials: `.\scripts\create-api-key.ps1`
3. Deploy frontend: Use helper script `.\scripts\amplify-deploy-guide.ps1` or follow [Amplify guide](_docs/AMPLIFY_DEPLOYMENT.md)

## Setup & Deployment

### Prerequisites

- AWS CLI configured with appropriate credentials
- AWS SAM CLI installed (`pip install aws-sam-cli`)
- Node.js 18+ and npm
- OpenRouter API key ([get one here](https://openrouter.ai/))

### 1. Backend Deployment (AWS SAM)

1. **Store OpenRouter API Key in Secrets Manager:**
   ```bash
   # Linux/Mac
   bash scripts/setup-secret.sh YOUR_OPENROUTER_API_KEY
   
   # Windows PowerShell
   .\scripts\setup-secret.ps1 YOUR_OPENROUTER_API_KEY
   
   # Or manually:
   aws secretsmanager create-secret \
     --name dungeoncrawler/openrouter-api-key \
     --secret-string '{"api_key": "YOUR_OPENROUTER_API_KEY"}'
   ```

2. **Deploy Infrastructure:**
   ```bash
   cd infrastructure
   sam build
   sam deploy --guided
   ```

3. **Get API Gateway URL:**
   ```bash
   aws cloudformation describe-stacks \
     --stack-name dungeoncrawler-blueprints \
     --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
     --output text
   ```

4. **Create API Key:**
   ```bash
   # Linux/Mac
   bash scripts/create-api-key.sh
   
   # Windows PowerShell
   .\scripts\create-api-key.ps1
   ```

### 2. Frontend Deployment (AWS Amplify)

See the detailed [Amplify Deployment Guide](_docs/AMPLIFY_DEPLOYMENT.md) for step-by-step instructions.

**Quick Steps:**
1. Get your API Gateway URL and API Key from backend deployment
2. Connect your GitHub repository to AWS Amplify
3. Configure environment variables (`VITE_API_URL` and `VITE_API_KEY`)
4. Deploy - Amplify will automatically detect `amplify.yml` and build/deploy

### 3. Local Development

**Backend:**
```bash
cd backend
pip install -r requirements.txt

# Test Lambda functions locally with SAM
cd ../infrastructure
sam local start-api
```

**Frontend:**
```bash
cd frontend
cp .env.example .env
# Edit .env with your API URL and key
npm install
npm run dev
```

### 4. API Key Configuration

The API uses API Gateway API keys for authentication. To get your API key:

1. After deploying the SAM stack, run the script:
   ```bash
   bash scripts/create-api-key.sh
   ```

2. Add the API key to your frontend environment variables in Amplify

3. For local development, add to `frontend/.env`:
   ```
   VITE_API_KEY=your-api-key-here
   VITE_API_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/dev
   ```

### Project Structure

```
/
├── frontend/              # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── services/     # API client
│   │   └── types/        # TypeScript types
│   └── package.json
├── backend/              # Python Lambda functions
│   ├── functions/        # Lambda handlers
│   │   ├── upload/
│   │   ├── detect/
│   │   ├── results/
│   │   └── export/
│   └── shared/           # Shared utilities
├── infrastructure/       # AWS SAM templates
│   ├── template.yaml
│   └── samconfig.toml
├── scripts/              # Deployment scripts
└── _docs/                # Documentation
```

### Testing

1. **Upload a blueprint image** (PNG/JPG, max 10MB)
2. **Wait for detection** (<30 seconds)
3. **View results** with bounding boxes overlaid
4. **Export** as JSON or SVG

### Troubleshooting

**OpenRouter API Errors:**
- Verify API key is correctly stored in Secrets Manager
- Check Lambda function logs in CloudWatch
- Ensure API key has sufficient credits

**API Gateway Errors:**
- Verify API key is included in requests (`x-api-key` header)
- Check usage plan limits
- Review API Gateway logs

**Frontend Issues:**
- Verify environment variables are set in Amplify
- Check browser console for API errors
- Ensure CORS is properly configured

### Documentation

- [Quick Start Guide](_docs/QUICK_START.md) - Get started in 5 minutes
- [API Documentation](_docs/api.md) - API endpoints and usage
- [Architecture](_docs/architecture.md) - System architecture overview
- [Mock Data Examples](_docs/MockData.md) - Sample data structures
- [Requirements](_docs/REQUIREMENTS.md) - Project requirements and specs
- [Amplify Deployment Guide](_docs/AMPLIFY_DEPLOYMENT.md) - Detailed frontend deployment
- [Deployment Checklist](_docs/DEPLOYMENT_CHECKLIST.md) - Complete deployment checklist

### License

This project is part of the DungeonCrawlerBlueprints MVP implementation.
