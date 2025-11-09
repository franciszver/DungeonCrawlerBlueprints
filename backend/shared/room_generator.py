"""Procedural room generation for interactive floor plan extension."""
import json
import random
from typing import Dict, Any, List, Optional, Tuple
import sys
import os

shared_path = os.path.dirname(__file__)
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from openrouter_client import suggest_room_type
from config import (
    MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT, COORDINATE_MAX,
    ENABLE_SIZE_VARIATION, ENABLE_POLYGON_COLLISION,
    ENABLE_SHAPED_ROOMS, ENABLE_SMART_PLACEMENT
)

# Try to import Shapely for polygon collision detection
try:
    from shapely.geometry import Polygon as ShapelyPolygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


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
        
        # Generate polygon based on door direction (with shape selection)
        polygon = _generate_shaped_room(
            room_type,
            door_location,
            door_direction,
            dimensions["width"],
            dimensions["height"],
            mode
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


def _generate_l_shaped_room(door_location: List[float], door_direction: str,
                            width: float, height: float) -> List[List[float]]:
    """Generate L-shaped room polygon for hallways/corridors."""
    x, y = door_location
    
    # Create L-shape: main section + perpendicular extension
    if door_direction == "N":
        # Main horizontal section, extension going left
        return [
            [x - width/2, y - height],
            [x + width/2, y - height],
            [x + width/2, y - height * 0.6],
            [x - width/2 + width * 0.3, y - height * 0.6],
            [x - width/2 + width * 0.3, y],
            [x - width/2, y]
        ]
    elif door_direction == "S":
        return [
            [x - width/2, y],
            [x - width/2 + width * 0.3, y],
            [x - width/2 + width * 0.3, y + height * 0.6],
            [x + width/2, y + height * 0.6],
            [x + width/2, y + height],
            [x - width/2, y + height]
        ]
    elif door_direction == "E":
        return [
            [x, y - height/2],
            [x + width * 0.6, y - height/2],
            [x + width * 0.6, y + height/2 - height * 0.3],
            [x + width, y + height/2 - height * 0.3],
            [x + width, y + height/2],
            [x, y + height/2]
        ]
    else:  # W
        return [
            [x - width, y - height/2],
            [x, y - height/2],
            [x, y - height/2 + height * 0.3],
            [x - width * 0.6, y - height/2 + height * 0.3],
            [x - width * 0.6, y + height/2],
            [x - width, y + height/2]
        ]


def _generate_room_with_alcove(door_location: List[float], door_direction: str,
                               width: float, height: float) -> List[List[float]]:
    """Generate room with small alcove (for bathrooms, closets)."""
    x, y = door_location
    alcove_size = min(width, height) * 0.3
    
    if door_direction == "N":
        return [
            [x - width/2, y - height],
            [x + width/2, y - height],
            [x + width/2, y - height * 0.7],
            [x + width/2 - alcove_size, y - height * 0.7],
            [x + width/2 - alcove_size, y - height * 0.5],
            [x + width/2, y - height * 0.5],
            [x + width/2, y],
            [x - width/2, y]
        ]
    elif door_direction == "S":
        return [
            [x - width/2, y],
            [x + width/2, y],
            [x + width/2, y + height * 0.5],
            [x + width/2 - alcove_size, y + height * 0.5],
            [x + width/2 - alcove_size, y + height * 0.7],
            [x + width/2, y + height * 0.7],
            [x + width/2, y + height],
            [x - width/2, y + height]
        ]
    elif door_direction == "E":
        return [
            [x, y - height/2],
            [x + width * 0.5, y - height/2],
            [x + width * 0.5, y - height/2 + alcove_size],
            [x + width * 0.7, y - height/2 + alcove_size],
            [x + width * 0.7, y - height/2],
            [x + width, y - height/2],
            [x + width, y + height/2],
            [x, y + height/2]
        ]
    else:  # W
        return [
            [x - width, y - height/2],
            [x, y - height/2],
            [x, y - height/2 + alcove_size],
            [x - width * 0.3, y - height/2 + alcove_size],
            [x - width * 0.3, y - height/2],
            [x - width * 0.5, y - height/2],
            [x - width * 0.5, y + height/2],
            [x - width, y + height/2]
        ]


def _generate_shaped_room(room_type: str, door_location: List[float],
                          door_direction: str, width: float, height: float,
                          mode: str) -> List[List[float]]:
    """Generate room with appropriate shape based on type."""
    if not ENABLE_SHAPED_ROOMS:
        return _generate_polygon_from_door(door_location, door_direction, width, height)
    
    room_type_lower = room_type.lower()
    
    # L-shaped rooms for hallways/corridors
    if "hallway" in room_type_lower or "corridor" in room_type_lower:
        if random.random() < 0.4:  # 40% chance of L-shape
            return _generate_l_shaped_room(door_location, door_direction, width, height)
    
    # Alcove rooms for bathrooms/closets/pantries
    elif any(term in room_type_lower for term in ["bathroom", "closet", "pantry"]):
        if random.random() < 0.3:  # 30% chance of alcove
            return _generate_room_with_alcove(door_location, door_direction, width, height)
    
    # Default: rectangle
    return _generate_polygon_from_door(door_location, door_direction, width, height)


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
    
    base_dims = dimensions_map.get(room_type, {"width": 300, "height": 300})
    
    # Apply size variation if enabled
    if ENABLE_SIZE_VARIATION:
        return _get_dimensions_with_variation(base_dims)
    
    return base_dims


def _get_dimensions_with_variation(base_dims: Dict[str, float]) -> Dict[str, float]:
    """Get dimensions with ±15% random variation for organic layouts."""
    variation = random.uniform(0.85, 1.15)
    return {
        "width": base_dims["width"] * variation,
        "height": base_dims["height"] * variation
    }


def _polygons_overlap(poly1: List[List[float]], poly2: List[List[float]]) -> bool:
    """True polygon intersection check using Shapely if available, otherwise bbox fallback."""
    if ENABLE_POLYGON_COLLISION and SHAPELY_AVAILABLE:
        try:
            shape1 = ShapelyPolygon(poly1)
            shape2 = ShapelyPolygon(poly2)
            return shape1.intersects(shape2)
        except Exception:
            # Fallback to bbox check if polygon is invalid
            bbox1 = _polygon_to_bbox(poly1)
            bbox2 = _polygon_to_bbox(poly2)
            return _bboxes_overlap(bbox1, bbox2)
    else:
        # Fallback to bbox check
        bbox1 = _polygon_to_bbox(poly1)
        bbox2 = _polygon_to_bbox(poly2)
        return _bboxes_overlap(bbox1, bbox2)


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
    new_bbox = _polygon_to_bbox(new_room_polygon)
    
    for room in existing_rooms:
        # Skip extended rooms that are being edited
        if room.get("is_extended") and room.get("is_temp"):
            continue
        
        # Use polygon collision if enabled and polygon is available
        if ENABLE_POLYGON_COLLISION and room.get("polygon"):
            if _polygons_overlap(new_room_polygon, room["polygon"]):
                return {
                    "valid": False,
                    "error": f"Room overlaps with existing room: {room.get('name_hint', room.get('id'))}",
                    "overlapping_room_id": room.get("id")
                }
        else:
            # Fallback to bbox check
            existing_bbox = room.get("bounding_box", [])
            if not existing_bbox or len(existing_bbox) != 4:
                continue
            
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


def _generate_with_offset(door_location: List[float], door_direction: str,
                         width: float, height: float, offset: float) -> List[List[float]]:
    """Generate room polygon with lateral offset from door."""
    x, y = door_location
    
    # Apply offset perpendicular to door direction
    if door_direction in ["N", "S"]:
        offset_location = [x + offset, y]
    else:
        offset_location = [x, y + offset]
    
    return _generate_polygon_from_door(offset_location, door_direction, width, height)


def _is_valid_placement(polygon: List[List[float]],
                       existing_rooms: List[Dict[str, Any]]) -> bool:
    """Check if polygon placement is valid (no overlaps, within bounds)."""
    # Check bounds
    bbox = _polygon_to_bbox(polygon)
    if bbox[0] < 0 or bbox[1] < 0 or bbox[2] > MAX_CANVAS_WIDTH or bbox[3] > MAX_CANVAS_HEIGHT:
        return False
    
    # Check overlaps using validate_room_placement
    validation = validate_room_placement(polygon, existing_rooms)
    return validation.get("valid", False)


def smart_room_placement(door_location: List[float], door_direction: str,
                        dimensions: Dict[str, float], existing_rooms: List[Dict[str, Any]],
                        room_type: str, mode: str) -> Optional[List[List[float]]]:
    """
    Try multiple placement strategies to find valid room placement.
    Returns best valid polygon or None if no valid placement found.
    """
    if not ENABLE_SMART_PLACEMENT:
        # Fallback to standard placement
        polygon = _generate_shaped_room(room_type, door_location, door_direction,
                                       dimensions["width"], dimensions["height"], mode)
        if _is_valid_placement(polygon, existing_rooms):
            return polygon
        return None
    
    candidates = []
    width = dimensions["width"]
    height = dimensions["height"]
    
    # Try standard placement
    standard = _generate_shaped_room(room_type, door_location, door_direction, width, height, mode)
    if _is_valid_placement(standard, existing_rooms):
        candidates.append(("standard", standard, 1.0))
    
    # Try offset placements (left/right of door)
    for offset in [-200, -100, -50, 50, 100, 200]:
        offset_polygon = _generate_with_offset(door_location, door_direction, width, height, offset)
        if _is_valid_placement(offset_polygon, existing_rooms):
            score = 1.0 - abs(offset) / 200  # Prefer less offset
            candidates.append(("offset", offset_polygon, score))
    
    # Try smaller dimensions if no valid placement
    if not candidates:
        smaller_dims = {"width": width * 0.7, "height": height * 0.7}
        smaller_polygon = _generate_shaped_room(room_type, door_location, door_direction,
                                                smaller_dims["width"], smaller_dims["height"], mode)
        if _is_valid_placement(smaller_polygon, existing_rooms):
            candidates.append(("smaller", smaller_polygon, 0.8))
    
    # Try even smaller
    if not candidates:
        tiny_dims = {"width": width * 0.5, "height": height * 0.5}
        tiny_polygon = _generate_shaped_room(room_type, door_location, door_direction,
                                            tiny_dims["width"], tiny_dims["height"], mode)
        if _is_valid_placement(tiny_polygon, existing_rooms):
            candidates.append(("tiny", tiny_polygon, 0.6))
    
    # Return best candidate
    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[0][1]
    
    return None

