"""Procedural room generation for interactive floor plan extension."""
import json
from typing import Dict, Any, List, Optional, Tuple
import sys
import os

shared_path = os.path.dirname(__file__)
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from openrouter_client import suggest_room_type
from config import MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT, COORDINATE_MAX


def generate_room(door_location: List[float], door_direction: str,
                 current_room_type: str, mode: str = "realistic",
                 room_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a new room connected to an existing door.
    
    Args:
        door_location: [x, y] coordinates of the door
        door_direction: Direction the door faces (N/S/E/W)
        current_room_type: Type of the room the door is in
        mode: "realistic" or "fantasy"
        room_type: Optional specific room type (if None, AI suggests)
        
    Returns:
        Dictionary with generated room data
    """
    try:
        # Get room type suggestions if not specified
        if room_type is None:
            suggestions_result = suggest_room_type(current_room_type, door_direction, mode)
            if suggestions_result.get("success") and suggestions_result.get("suggestions"):
                # Use the highest probability suggestion
                suggestions = suggestions_result["suggestions"]
                suggestions.sort(key=lambda x: x.get("probability", 0), reverse=True)
                room_type = suggestions[0]["room_type"]
                dimensions = suggestions[0].get("typical_dimensions", {"width": 300, "height": 300})
            else:
                # Fallback
                room_type = "Room"
                dimensions = {"width": 300, "height": 300}
        else:
            # Use default dimensions for specified room type
            dimensions = _get_default_dimensions(room_type, mode)
        
        # Generate polygon based on door direction
        polygon = _generate_polygon_from_door(
            door_location,
            door_direction,
            dimensions["width"],
            dimensions["height"]
        )
        
        # Validate polygon is within canvas bounds
        polygon = _clamp_polygon_to_canvas(polygon)
        
        # Calculate bounding box
        bounding_box = _polygon_to_bbox(polygon)
        
        # Generate room ID
        import uuid
        room_id = f"extended_{uuid.uuid4().hex[:8]}"
        
        return {
            "success": True,
            "room": {
                "id": room_id,
                "polygon": polygon,
                "bounding_box": bounding_box,
                "name_hint": room_type,
                "confidence": 0.95,  # High confidence for user-generated rooms
                "is_extended": True,
                "connected_door": {
                    "location": door_location,
                    "direction": door_direction
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate room: {str(e)}",
            "error_code": "GENERATION_ERROR"
        }


def _generate_polygon_from_door(door_location: List[float], door_direction: str,
                                width: float, height: float) -> List[List[float]]:
    """
    Generate a rectangular polygon extending from a door.
    
    Args:
        door_location: [x, y] coordinates of the door
        door_direction: Direction the door faces (N/S/E/W)
        width: Room width
        height: Room height
        
    Returns:
        List of polygon vertices [[x1,y1], [x2,y2], ...]
    """
    x, y = door_location
    
    # Generate rectangle based on door direction
    if door_direction == "N":  # Door faces north, room extends upward
        return [
            [x - width/2, y - height],
            [x + width/2, y - height],
            [x + width/2, y],
            [x - width/2, y]
        ]
    elif door_direction == "S":  # Door faces south, room extends downward
        return [
            [x - width/2, y],
            [x + width/2, y],
            [x + width/2, y + height],
            [x - width/2, y + height]
        ]
    elif door_direction == "E":  # Door faces east, room extends right
        return [
            [x, y - height/2],
            [x + width, y - height/2],
            [x + width, y + height/2],
            [x, y + height/2]
        ]
    elif door_direction == "W":  # Door faces west, room extends left
        return [
            [x - width, y - height/2],
            [x, y - height/2],
            [x, y + height/2],
            [x - width, y + height/2]
        ]
    else:
        # Default: extend to the right
        return [
            [x, y - height/2],
            [x + width, y - height/2],
            [x + width, y + height/2],
            [x, y + height/2]
        ]


def _clamp_polygon_to_canvas(polygon: List[List[float]]) -> List[List[float]]:
    """Clamp polygon vertices to canvas bounds."""
    clamped = []
    for point in polygon:
        x = max(0, min(MAX_CANVAS_WIDTH, point[0]))
        y = max(0, min(MAX_CANVAS_HEIGHT, point[1]))
        clamped.append([x, y])
    return clamped


def _polygon_to_bbox(polygon: List[List[float]]) -> List[float]:
    """Convert polygon to bounding box."""
    if not polygon:
        return [0, 0, 0, 0]
    
    x_coords = [p[0] for p in polygon]
    y_coords = [p[1] for p in polygon]
    
    return [
        min(x_coords),
        min(y_coords),
        max(x_coords),
        max(y_coords)
    ]


def _get_default_dimensions(room_type: str, mode: str) -> Dict[str, float]:
    """Get default dimensions for a room type."""
    
    if mode == "fantasy":
        # Fantasy/dungeon dimensions
        dimensions_map = {
            "Treasure Room": {"width": 250, "height": 250},
            "Boss Chamber": {"width": 400, "height": 400},
            "Corridor": {"width": 150, "height": 400},
            "Secret Room": {"width": 200, "height": 200},
            "Trap Room": {"width": 300, "height": 300},
            "Storage": {"width": 200, "height": 250},
            "Guard Post": {"width": 250, "height": 250},
        }
    else:
        # Realistic architectural dimensions
        dimensions_map = {
            "Bedroom": {"width": 350, "height": 400},
            "Bathroom": {"width": 250, "height": 300},
            "Kitchen": {"width": 400, "height": 350},
            "Living Room": {"width": 500, "height": 450},
            "Dining Room": {"width": 400, "height": 400},
            "Hallway": {"width": 150, "height": 400},
            "Closet": {"width": 200, "height": 150},
            "Office": {"width": 350, "height": 350},
            "Garage": {"width": 600, "height": 600},
            "Pantry": {"width": 200, "height": 250},
        }
    
    return dimensions_map.get(room_type, {"width": 300, "height": 300})


def validate_room_placement(new_room_polygon: List[List[float]],
                           existing_rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that a new room doesn't overlap with existing rooms.
    
    Args:
        new_room_polygon: Polygon of the new room
        existing_rooms: List of existing rooms with polygons or bounding boxes
        
    Returns:
        Dictionary with validation result
    """
    # Simple bounding box overlap check
    new_bbox = _polygon_to_bbox(new_room_polygon)
    
    for room in existing_rooms:
        # Skip extended rooms that are being edited
        if room.get("is_extended") and room.get("is_temp"):
            continue
        
        existing_bbox = room.get("bounding_box", [])
        if not existing_bbox or len(existing_bbox) != 4:
            continue
        
        # Check for overlap
        if _bboxes_overlap(new_bbox, existing_bbox):
            return {
                "valid": False,
                "error": f"Room overlaps with existing room: {room.get('name_hint', room.get('id'))}",
                "overlapping_room_id": room.get("id")
            }
    
    return {"valid": True}


def _bboxes_overlap(bbox1: List[float], bbox2: List[float]) -> bool:
    """Check if two bounding boxes overlap."""
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2
    
    # No overlap if one is to the left of the other
    if x1_max <= x2_min or x2_max <= x1_min:
        return False
    
    # No overlap if one is above the other
    if y1_max <= y2_min or y2_max <= y1_min:
        return False
    
    return True

