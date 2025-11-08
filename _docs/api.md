# API.md — DungeonCrawlerBlueprints

## Overview
This document defines the API contract for DungeonCrawlerBlueprints, an AI-powered blueprint processing service built on AWS and OpenRouter. The service accepts blueprint images or structured wall data and returns detected room boundaries, confidence scores, adjacency graphs, semantic hints, and audit metadata.
---
## 1. Endpoint Summary
| Endpoint                  | Method | Description                                      |
|--------------------------|--------|--------------------------------------------------|
| `/upload`                | POST   | Uploads blueprint image or JSON wall data       |
| `/detect`                | POST   | Triggers room detection pipeline                |
| `/results/:id`           | GET    | Retrieves detection results by job ID           |
| `/export/:id`            | GET    | Downloads JSON or SVG output                    |
| `/health`                | GET    | Returns service health and model metadata       |
---
## 2. Request: `/upload`
### Method: `POST`
Uploads a blueprint image or structured wall data.
#### Payload (multipart/form-data or JSON)
```json
{
  "file": "<PNG/JPG image OR JSON wall data>",
  "source_type": "image" | "vector",
  "blueprint_id": "optional string"
}
Notes
	• Images must be ≤10MB, normalized to 0–1000 coordinate space.
	• Vector input must follow the wall segment schema:
json
{
  "type": "line",
  "start": [100, 100],
  "end": [500, 100],
  "is_load_bearing": false
}
3. Request: /detect
Method: POST
Triggers the detection pipeline using AWS + OpenRouter routing.
Payload
json
{
  "blueprint_id": "string",
  "model": "gpt-4-vision",
  "fallback": "mistral",
  "tasks": ["room_detection", "semantic_labeling", "adjacency_graph"]
}
Notes
	• Routing is configurable per task.
	• Detection is asynchronous; use /results/:id to retrieve output.
4. Response: /results/:id
Method: GET
Returns detection results for a given blueprint.
Response Schema
json
{
  "id": "room_001",
  "bounding_box": [50, 50, 200, 300],
  "confidence": 0.92,
  "name_hint": "Main Office",
  "adjacent_to": ["room_002", "room_003"],
  "metadata": {
    "model_used": "gpt-4-vision",
    "processing_time_ms": 18450,
    "timestamp": "2025-11-08T15:30:00Z"
  }
}
5. Request: /export/:id
Method: GET
Downloads detection results in JSON or SVG format.
Query Parameters
	• format=json (default)
	• format=svg
6. Request: /health
Method: GET
Returns service status and model metadata.
Response
json
{
  "status": "healthy",
  "models": {
    "room_detection": "gpt-4-vision",
    "semantic_labeling": "claude-2",
    "adjacency_graph": "mixtral"
  },
  "uptime": "99.98%",
  "last_deploy": "2025-11-07T22:00:00Z"
}
7. Error Handling
Code	Message	Cause
400	Invalid input format	Missing or malformed payload
404	Blueprint not found	Invalid blueprint ID
500	Detection failed	AI service error or timeout
503	Model unavailable	OpenRouter or AWS outage
8. Notes for Contributors
	• All coordinates must be normalized to 0–1000.
	• Detection must return partial results with error metadata if needed.
	• All outputs must include audit metadata (model, time, version).
