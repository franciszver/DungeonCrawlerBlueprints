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
| `/extend`                | POST   | Generates room suggestions or procedurally creates new rooms |
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
```

#### Notes
- Images must be ≤10MB, normalized to 0–1000 coordinate space.
- Vector input must follow the wall segment schema:

```json
{
  "type": "line",
  "start": [100, 100],
  "end": [500, 100],
  "is_load_bearing": false
}
```

---

## 3. Request: `/detect`
### Method: `POST`
Triggers the detection pipeline using AWS + OpenRouter routing with multi-model validation.

#### Payload
```json
{
  "blueprint_id": "string",
  "model": "openai/gpt-4o",
  "enable_polygon_detection": true,
  "enable_door_detection": true,
  "enable_multi_model_validation": true
}
```

#### Notes
- Primary model processes the blueprint first
- If confidence is below threshold, secondary models validate results
- Detection is asynchronous; use `/results/:id` to retrieve output
- Supports polygon boundaries for irregular room shapes
- Automatically detects doors and openings

---

## 4. Response: `/results/:id`
### Method: `GET`
Returns detection results for a given blueprint.

#### Response Schema
```json
{
  "job_id": "string",
  "status": "completed" | "processing" | "failed",
  "rooms": [
    {
      "id": "room_001",
      "bounding_box": [50, 50, 200, 300],
      "polygon": [[50, 50], [200, 50], [200, 300], [50, 300]],
      "confidence": 0.92,
      "name_hint": "Main Office",
      "adjacent_to": ["room_002", "room_003"],
      "doors": [
        {
          "id": "door_001",
          "location": [125, 50],
          "connects_to": ["room_001", "room_002"]
        }
      ]
    }
  ],
  "doors": [
    {
      "id": "door_001",
      "location": [125, 50],
      "connects_to": ["room_001", "room_002"]
    }
  ],
  "confidence": 0.89,
  "metadata": {
    "primary_model": "openai/gpt-4o",
    "models_used": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"],
    "retry_count": 1,
    "primary_confidence": 0.65,
    "final_confidence": 0.89,
    "detection_type": "polygon",
    "processing_time_ms": 18450,
    "timestamp": "2025-11-08T15:30:00Z",
    "few_shot_examples_used": 3
  }
}
```
5. Request: /export/:id
Method: GET
Downloads detection results in JSON or SVG format.
Query Parameters
	• format=json (default)
	• format=svg

---

## 6. Request: `/extend`
### Method: `POST`
Generates room suggestions or procedurally creates new rooms for interactive blueprint extension.

#### Payload
```json
{
  "job_id": "string",
  "action": "suggest" | "generate" | "validate",
  "door_id": "string",
  "current_room_type": "string",
  "target_room_type": "string (required for 'generate')",
  "mode": "realistic" | "fantasy",
  "existing_rooms": [
    {
      "id": "string",
      "bounding_box": [x_min, y_min, x_max, y_max],
      "polygon": [[x1, y1], [x2, y2], ...],
      "name_hint": "string",
      "confidence": 0.0-1.0
    }
  ]
}
```

#### Response Schema

**For `action: "suggest"`:**
```json
{
  "suggestions": [
    {
      "room_type": "Bedroom",
      "confidence": 0.85,
      "reasoning": "Typically adjacent to hallways in residential layouts"
    }
  ]
}
```

**For `action: "generate"`:**
```json
{
  "room": {
    "id": "extended_room_001",
    "bounding_box": [500, 200, 700, 400],
    "polygon": [[500, 200], [700, 200], [700, 400], [500, 400]],
    "name_hint": "Bedroom",
    "confidence": 0.80,
    "is_extended": true,
    "doors": [
      {
        "id": "door_001",
        "location": [500, 300],
        "connects_to": ["room_001", "extended_room_001"]
      }
    ]
  },
  "validation": {
    "is_valid": true,
    "warnings": [],
    "overlaps": []
  }
}
```

**For `action: "validate"`:**
```json
{
  "is_valid": true,
  "warnings": ["Room is smaller than typical bedroom dimensions"],
  "overlaps": [],
  "suggestions": ["Consider increasing width by 50 units"]
}
```

#### Notes
- The `extend` endpoint uses adjacency patterns and procedural generation algorithms
- Validation checks for overlaps with existing rooms and ensures reasonable dimensions
- Fantasy mode allows for more creative room shapes and adjacencies
- All generated rooms include `is_extended: true` flag for tracking

---

## 7. Request: /health
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
8. Error Handling
Code	Message	Cause
400	Invalid input format	Missing or malformed payload
404	Blueprint not found	Invalid blueprint ID
500	Detection failed	AI service error or timeout
503	Model unavailable	OpenRouter or AWS outage
9. Notes for Contributors
	• All coordinates must be normalized to 0–1000.
	• Detection must return partial results with error metadata if needed.
	• All outputs must include audit metadata (model, time, version).
