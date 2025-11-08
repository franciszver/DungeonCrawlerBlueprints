# MockData.md — DungeonCrawlerBlueprints

This document provides mock data examples for testing and development, based on the requirements in `REQUIREMENTS.md`.

## Input Mock Data

### Wall Segment JSON (Vector Input)

For testing with structured wall data, use this simplified format representing key structural lines in normalized coordinates (0–1000):

```json
[
  {
    "type": "line",
    "start": [100, 100],
    "end": [500, 100],
    "is_load_bearing": false
  },
  {
    "type": "line",
    "start": [100, 100],
    "end": [100, 400],
    "is_load_bearing": false
  },
  {
    "type": "line",
    "start": [500, 100],
    "end": [500, 400],
    "is_load_bearing": false
  },
  {
    "type": "line",
    "start": [100, 400],
    "end": [500, 400],
    "is_load_bearing": false
  },
  {
    "type": "line",
    "start": [500, 200],
    "end": [700, 200],
    "is_load_bearing": false
  },
  {
    "type": "line",
    "start": [700, 200],
    "end": [700, 400],
    "is_load_bearing": false
  },
  {
    "type": "line",
    "start": [500, 400],
    "end": [700, 400],
    "is_load_bearing": false
  }
]
```

This represents a simple floor plan with two rooms:
- Room 1: Bounded by (100, 100) to (500, 400)
- Room 2: Bounded by (500, 200) to (700, 400)

## Expected Output Mock Data

### Detected Rooms (JSON Response)

The service returns a JSON array containing identified room boundaries:

```json
[
  {
    "id": "room_001",
    "bounding_box": [50, 50, 200, 300],
    "confidence": 0.92,
    "name_hint": "Entry Hall"
  },
  {
    "id": "room_002",
    "bounding_box": [250, 50, 700, 500],
    "confidence": 0.88,
    "name_hint": "Main Office"
  },
  {
    "id": "room_003",
    "bounding_box": [720, 50, 950, 300],
    "confidence": 0.85,
    "name_hint": "Conference Room"
  }
]
```

### Complete Detection Response

Full response from the `/detect` endpoint:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "blueprint_id": "blueprint-001",
  "status": "completed",
  "rooms": [
    {
      "id": "room_001",
      "bounding_box": [50, 50, 200, 300],
      "confidence": 0.92,
      "name_hint": "Entry Hall"
    },
    {
      "id": "room_002",
      "bounding_box": [250, 50, 700, 500],
      "confidence": 0.88,
      "name_hint": "Main Office"
    }
  ],
  "metadata": {
    "model_used": "openai/gpt-4o",
    "processing_time_ms": 18450,
    "timestamp": "2025-01-08T15:30:00Z"
  }
}
```

## Coordinate System

### Normalization Rules

- All coordinates are normalized to the range **0–1000**
- Origin (0, 0) is at the **top-left** corner
- X increases to the **right**
- Y increases **downward**
- Bounding boxes use format: `[x_min, y_min, x_max, y_max]`

### Example Conversion

If an image is 2000x1500 pixels and a room is detected at pixel coordinates (400, 300) to (1200, 900):

```
Normalized x_min = (400 / 2000) * 1000 = 200
Normalized y_min = (300 / 1500) * 1000 = 200
Normalized x_max = (1200 / 2000) * 1000 = 600
Normalized y_max = (900 / 1500) * 1000 = 600

Result: [200, 200, 600, 600]
```

## Test Blueprint Descriptions

### Simple Two-Room Floor Plan

**Description:** A basic rectangular floor plan with two adjacent rooms separated by a single wall.

**Expected Output:**
- 2 rooms detected
- Non-overlapping bounding boxes
- Confidence scores > 0.8

### Complex Multi-Room Office

**Description:** An office floor plan with multiple rooms, hallways, and shared spaces.

**Expected Output:**
- 5-10 rooms detected
- Hallways identified as separate spaces
- Adjacent rooms properly separated

## Validation Rules

### Bounding Box Validation

1. **Non-overlapping:** Rooms must not have significantly overlapping bounding boxes (small overlaps < 5% are acceptable for adjacent rooms)
2. **Valid coordinates:** All coordinates must be within 0-1000 range
3. **Valid dimensions:** Width and height must be > 0
4. **Closed polygons:** For future polygonal detection, rooms must form closed shapes

### Confidence Score Guidelines

- **0.9 - 1.0:** Very high confidence, clear room boundaries
- **0.7 - 0.9:** High confidence, mostly clear boundaries
- **0.5 - 0.7:** Medium confidence, some ambiguity
- **< 0.5:** Low confidence, may be false positive

## Sample Test Cases

### Test Case 1: Simple Rectangle

**Input:** Single rectangular room in image

**Expected:**
```json
[
  {
    "id": "room_001",
    "bounding_box": [100, 100, 900, 800],
    "confidence": 0.95,
    "name_hint": "Main Room"
  }
]
```

### Test Case 2: L-Shaped Room

**Input:** L-shaped room configuration

**Expected:**
```json
[
  {
    "id": "room_001",
    "bounding_box": [100, 100, 600, 600],
    "confidence": 0.85,
    "name_hint": "L-Shaped Room"
  }
]
```

Note: For MVP, L-shaped rooms will be detected as a single bounding box covering the entire area. Precise polygonal detection is planned for Phase 2.

## Notes

- **Doors and windows:** Not included in MVP detection
- **Load-bearing walls:** Flagged in input but not used in MVP detection logic
- **Multi-floor support:** Single-floor blueprints only for MVP
- **Vector parsing:** If vector parsing fails, system falls back to rasterized image processing

