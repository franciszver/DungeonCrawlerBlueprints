# Interactive Room Extension

## Overview

The Interactive Room Extension feature allows users to **procedurally generate and add new rooms** to existing floor plans. Simply click on a door, select a room type, and the AI generates an appropriately-sized room that connects seamlessly.

## Key Features

- 🎯 **AI-Powered Suggestions**: Get room type recommendations based on architectural patterns
- 🎨 **Dual Modes**: Realistic (architectural) and Fantasy (game design) generation
- ✨ **Procedural Generation**: Rooms sized and positioned automatically
- 🔄 **Full Undo/Redo**: Complete history management
- ✅ **Overlap Validation**: Prevents invalid placements
- 📐 **Adjustable**: Drag corners to resize generated rooms
- 💾 **Persistent**: Extended plans saved to database

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│            Interactive Extension Flow                        │
└─────────────────────────────────────────────────────────────┘

1. User clicks door with ➕ icon
   │
2. System analyzes context:
   ├──> Current room type
   ├──> Door direction (N/S/E/W)
   └──> Mode (realistic/fantasy)
   │
3. AI suggests room types:
   ├──> "Bathroom" (65% probability)
   ├──> "Closet" (25%)
   └──> "Hallway" (10%)
   │
4. User selects room type (or types custom)
   │
5. System generates room:
   ├──> Queries AI for typical dimensions
   ├──> Creates polygon extending from door
   ├──> Validates no overlaps
   └──> Adds to floor plan
   │
6. User can:
   ├──> Accept as-is
   ├──> Drag corners to adjust
   ├──> Undo and regenerate
   └──> Export extended plan
```

## User Interface

### Interactive Mode Toggle

Located in the Results Viewer:

```
[View Results] [Interactive Mode: OFF/ON] [Export]
```

When enabled:
- Doors show ➕ icons on hover
- Click to open room generation panel
- Existing rooms become semi-transparent
- Extended rooms highlighted in green

### Room Generation Panel

Appears when clicking a door:

```
┌────────────────────────────────────┐
│  Add Room                          │
├────────────────────────────────────┤
│  Current: Kitchen                  │
│  Door facing: East                 │
│                                    │
│  Mode: [Realistic] [Fantasy]       │
│                                    │
│  Suggested Rooms:                  │
│  ○ Dining Room (65%)              │
│  ○ Pantry (25%)                   │
│  ○ Hallway (10%)                  │
│                                    │
│  Or enter custom: [_________]     │
│                                    │
│  [Cancel] [Generate Room]         │
└────────────────────────────────────┘
```

### Controls

- **Drag corners**: Resize room after generation
- **Undo** (Ctrl+Z): Revert last action
- **Redo** (Ctrl+Y): Reapply undone action
- **Delete**: Remove extended room
- **Regenerate**: Generate different room at same door

## API Endpoints

### Generate Room

```http
POST /extend/{job_id}
Content-Type: application/json

{
  "action": "generate",
  "door_location": [300, 250],
  "door_direction": "E",
  "current_room_type": "Kitchen",
  "room_type": "Dining Room",  // optional
  "mode": "realistic"           // or "fantasy"
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "room": {
    "id": "extended_a1b2c3d4",
    "polygon": [[300,200], [600,200], [600,300], [300,300]],
    "bounding_box": [300, 200, 600, 300],
    "name_hint": "Dining Room",
    "confidence": 0.95,
    "is_extended": true,
    "connected_door": {
      "location": [300, 250],
      "direction": "E"
    }
  },
  "message": "Room generated successfully"
}
```

### Get Room Suggestions

```http
POST /extend/{job_id}
Content-Type: application/json

{
  "action": "suggest",
  "door_direction": "E",
  "current_room_type": "Kitchen",
  "mode": "realistic"
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "suggestions": [
    {
      "room_type": "Dining Room",
      "probability": 0.65,
      "typical_dimensions": {"width": 400, "height": 400}
    },
    {
      "room_type": "Pantry",
      "probability": 0.25,
      "typical_dimensions": {"width": 200, "height": 250}
    },
    {
      "room_type": "Hallway",
      "probability": 0.10,
      "typical_dimensions": {"width": 150, "height": 400}
    }
  ]
}
```

### Validate Placement

```http
POST /extend/{job_id}
Content-Type: application/json

{
  "action": "validate",
  "room_polygon": [[300,200], [600,200], [600,300], [300,300]]
}
```

**Response:**
```json
{
  "job_id": "abc123",
  "valid": true
}
```

Or if invalid:
```json
{
  "job_id": "abc123",
  "valid": false,
  "error": "Room overlaps with existing room: Living Room",
  "overlapping_room_id": "room_002"
}
```

## Generation Modes

### Realistic Mode

Based on architectural best practices and building codes:

**Kitchen connections:**
- Dining Room (40%)
- Pantry (30%)
- Hallway (30%)

**Bedroom connections:**
- Bathroom (40%)
- Closet (30%)
- Hallway (30%)

**Dimensions:**
- Bedroom: 350×400
- Bathroom: 250×300
- Kitchen: 400×350
- Living Room: 500×450

### Fantasy Mode

Based on game design patterns and dungeon conventions:

**Boss Chamber connections:**
- Treasure Room (50%)
- Secret Room (30%)
- Exit (20%)

**Corridor connections:**
- Chamber (30%)
- Trap Room (25%)
- Secret Room (20%)
- Storage (25%)

**Dimensions:**
- Boss Chamber: 400×400
- Treasure Room: 250×250
- Corridor: 150×400
- Trap Room: 300×300

## Room Generation Algorithm

### 1. Analyze Context

```python
current_room = "Kitchen"
door_direction = "E"  # East
mode = "realistic"
```

### 2. Get Suggestions

Query AI or use adjacency patterns:

```python
suggestions = get_adjacency_suggestions(
    room_type="Kitchen",
    direction="E",
    mode="realistic"
)
# Returns: [("Dining Room", 0.65), ("Pantry", 0.25), ...]
```

### 3. Generate Polygon

Based on door direction, create rectangle:

```python
if direction == "E":  # Door faces East, room extends right
    polygon = [
        [x, y - height/2],
        [x + width, y - height/2],
        [x + width, y + height/2],
        [x, y + height/2]
    ]
```

### 4. Validate Placement

Check for overlaps with existing rooms:

```python
for existing_room in all_rooms:
    if bboxes_overlap(new_bbox, existing_room.bbox):
        return {"valid": False, "error": "Overlap detected"}
```

### 5. Clamp to Canvas

Ensure room stays within bounds:

```python
for point in polygon:
    point[0] = max(0, min(MAX_WIDTH, point[0]))
    point[1] = max(0, min(MAX_HEIGHT, point[1]))
```

## Undo/Redo System

### History Stack

```typescript
interface HistoryAction {
  type: 'add' | 'modify' | 'delete';
  room: Room;
  previousState?: Room;
  timestamp: number;
}

const history: HistoryAction[] = [];
let historyIndex = 0;
```

### Undo

```typescript
function undo() {
  if (historyIndex > 0) {
    historyIndex--;
    const action = history[historyIndex];
    
    if (action.type === 'add') {
      removeRoom(action.room.id);
    } else if (action.type === 'modify') {
      restoreRoom(action.previousState);
    } else if (action.type === 'delete') {
      addRoom(action.room);
    }
  }
}
```

### Redo

```typescript
function redo() {
  if (historyIndex < history.length) {
    const action = history[historyIndex];
    historyIndex++;
    
    if (action.type === 'add') {
      addRoom(action.room);
    } else if (action.type === 'modify') {
      updateRoom(action.room);
    } else if (action.type === 'delete') {
      removeRoom(action.room.id);
    }
  }
}
```

## Persistence

Extended rooms are saved to DynamoDB:

```json
{
  "job_id": "abc123",
  "results": [...],  // Original detected rooms
  "extended_rooms": [  // User-generated rooms
    {
      "id": "extended_a1b2c3d4",
      "polygon": [[300,200], [600,200], [600,300], [300,300]],
      "name_hint": "Dining Room",
      "is_extended": true
    }
  ]
}
```

## Export

Extended floor plans include both original and extended rooms:

**JSON Export:**
```json
{
  "job_id": "abc123",
  "rooms": [...],  // Original rooms
  "extended_rooms": [...],  // User-generated rooms
  "doors": [...]
}
```

**SVG Export:**
- Original rooms: Blue outline
- Extended rooms: Green outline
- Doors: Red dots

## Best Practices

### For Users

1. **Start with high-confidence detections**: Extend from well-detected rooms
2. **Use realistic mode for architecture**: More accurate dimensions
3. **Use fantasy mode for games**: Creative, game-appropriate suggestions
4. **Validate before exporting**: Check for overlaps and sizing
5. **Save frequently**: Extended plans persist but undo history doesn't

### For Developers

1. **Validate all inputs**: Check door locations, directions, room types
2. **Handle edge cases**: Doors near canvas edges, very small/large rooms
3. **Optimize API calls**: Cache suggestions for common patterns
4. **Provide feedback**: Show loading states, validation errors
5. **Test modes separately**: Realistic and fantasy have different patterns

## Troubleshooting

### Room overlaps existing space

**Symptom:** "Room overlaps with existing room" error

**Solutions:**
- Try different door
- Manually adjust room size after generation
- Check if door is too close to walls

### Suggestions don't make sense

**Symptom:** Unrealistic room suggestions

**Solutions:**
- Verify correct mode (realistic vs fantasy)
- Check current room type is correct
- Try custom room type input

### Generated room too small/large

**Symptom:** Room dimensions inappropriate

**Solutions:**
- Drag corners to resize
- Regenerate with different room type
- Use custom dimensions in API call

### Undo not working

**Symptom:** Can't undo last action

**Solutions:**
- Check history stack isn't empty
- Verify historyIndex is correct
- Refresh page if state corrupted

## Future Enhancements

- [ ] Multi-room generation (add multiple rooms at once)
- [ ] Room templates (save and reuse custom room shapes)
- [ ] Automatic door placement on extended rooms
- [ ] Furniture generation inside rooms
- [ ] 3D preview of extended floor plan
- [ ] Collaborative editing (multiple users)
- [ ] Room style transfer (match existing architectural style)
- [ ] Constraint-based generation (min/max sizes, specific shapes)

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Get suggestions | <1s | Cached for common patterns |
| Generate room | 2-3s | AI query for dimensions |
| Validate placement | <100ms | Local computation |
| Save to database | <500ms | DynamoDB write |
| Export extended plan | <2s | Includes rendering |

## Cost

| Operation | Cost | Notes |
|-----------|------|-------|
| Get suggestions | $0.005 | AI query |
| Generate room | $0.005 | AI query |
| Validate | $0 | Local |
| Save | $0.0001 | DynamoDB |
| **Average per extension** | **$0.01** | Very affordable |

## Examples

### Example 1: Extend Office Floor Plan

```
1. Detected: 5 offices, 1 conference room, 1 hallway
2. Click door on hallway facing North
3. Suggestions: "Office (45%)", "Bathroom (30%)", "Storage (25%)"
4. Select "Bathroom"
5. Generated: 250×300 bathroom extending north
6. Adjust: Drag to 280×320 to fit space better
7. Export: Include in final floor plan
```

### Example 2: Dungeon Extension (Fantasy Mode)

```
1. Detected: Entrance Hall, 2 Corridors, Boss Chamber
2. Switch to Fantasy Mode
3. Click door on Boss Chamber facing East
4. Suggestions: "Treasure Room (50%)", "Secret Room (30%)", "Exit (20%)"
5. Select "Treasure Room"
6. Generated: 250×250 treasure room
7. Add another door to treasure room
8. Generate "Secret Room" behind treasure room
9. Export: Complete dungeon layout
```

---

For more information, see:
- [API Documentation](api.md)
- [Multi-Model Detection](MULTI_MODEL_DETECTION.md)
- [Demo Script](DEMO.md)

