"""Procedural room generation for interactive floor plan extension."""
import json
import random
import logging
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

logger = logging.getLogger(__name__)

# Try to import Shapely for polygon collision detection
try:
    from shapely.geometry import Polygon as ShapelyPolygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


def generate_room(door_location: List[float], door_direction: str,
                 current_room_type: str, mode: str = "realistic",
                 room_type: Optional[str] = None, scale_factor: float = 1.0) -> Dict[str, Any]:
    """
    Generate a new room connected to an existing door.
    
    Args:
        door_location: [x, y] coordinates of the door
        door_direction: Direction the door faces (N/S/E/W)
        current_room_type: Type of the room the door is in
        mode: "realistic" or "fantasy"
        room_type: Optional specific room type (if None, AI suggests)
        scale_factor: Multiplier to scale dimensions to match blueprint (default: 1.0)
        
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
                # Scale AI-suggested dimensions to match blueprint
                suggested_dims = suggestions[0].get("typical_dimensions", {"width": 300, "height": 300})
                dimensions = {
                    "width": suggested_dims["width"] * scale_factor,
                    "height": suggested_dims["height"] * scale_factor
                }
            else:
                # Fallback
                room_type = "Room"
                dimensions = {"width": 300 * scale_factor, "height": 300 * scale_factor}
        else:
            # Use default dimensions for specified room type, scaled to match blueprint
            dimensions = _get_default_dimensions(room_type, mode, scale_factor)
        
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


def _get_default_dimensions(room_type: str, mode: str, scale_factor: float = 1.0) -> Dict[str, float]:
    """
    Get default dimensions for a room type, scaled to match blueprint.
    
    Args:
        room_type: Type of room (e.g., "Bedroom", "Kitchen")
        mode: "realistic" or "fantasy"
        scale_factor: Multiplier to scale dimensions to match blueprint (default: 1.0)
        
    Returns:
        Dictionary with scaled width and height
    """
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
    
    # Apply scale factor to match blueprint scale (before variation)
    scaled_dims = {
        "width": base_dims["width"] * scale_factor,
        "height": base_dims["height"] * scale_factor
    }
    
    # Apply size variation if enabled (after scaling)
    if ENABLE_SIZE_VARIATION:
        return _get_dimensions_with_variation(scaled_dims)
    
    return scaled_dims


def _get_dimensions_with_variation(base_dims: Dict[str, float]) -> Dict[str, float]:
    """Get dimensions with ±15% random variation for organic layouts."""
    variation = random.uniform(0.85, 1.15)
    return {
        "width": base_dims["width"] * variation,
        "height": base_dims["height"] * variation
    }


def _calculate_scale_factor_from_existing_rooms(existing_rooms: List[Dict[str, Any]]) -> float:
    """
    Calculate scale factor by comparing default room sizes to actual room sizes.
    Returns a multiplier to scale generated rooms to match blueprint scale.
    
    Uses median area (robust to outliers) and filters extreme outliers.
    Only analyzes original detected rooms to match the blueprint's true scale.
    
    Args:
        existing_rooms: List of original detected rooms (from job.results)
        
    Returns:
        Scale factor (0.3 to 2.0) to apply to default dimensions
    """
    if not existing_rooms or len(existing_rooms) < 2:
        return 1.0  # No scaling if not enough data
    
    # Calculate areas of existing rooms
    areas = []
    for room in existing_rooms:
        bbox = room.get('bounding_box', [])
        if len(bbox) == 4:
            x_min, y_min, x_max, y_max = bbox
            width = x_max - x_min
            height = y_max - y_min
            area = width * height
            if area > 0:  # Skip invalid rooms
                areas.append(area)
    
    if len(areas) < 2:
        return 1.0
    
    # Calculate median area (more robust than mean)
    sorted_areas = sorted(areas)
    median_area = sorted_areas[len(sorted_areas) // 2]
    
    # Filter outliers: exclude rooms >3x or <0.3x the median
    filtered_areas = [
        area for area in areas
        if 0.3 * median_area <= area <= 3.0 * median_area
    ]
    
    if len(filtered_areas) < 2:
        # If filtering removed too many, use original areas
        filtered_areas = areas
    
    # Calculate average area of filtered rooms
    avg_existing_area = sum(filtered_areas) / len(filtered_areas)
    
    # Calculate average of all default room sizes as reference
    # This gives us a balanced reference point
    default_dimensions = [
        {"width": 350, "height": 400},  # Bedroom
        {"width": 250, "height": 300},   # Bathroom
        {"width": 400, "height": 350},   # Kitchen
        {"width": 500, "height": 450},   # Living Room
        {"width": 400, "height": 400},   # Dining Room
        {"width": 150, "height": 400},   # Hallway
        {"width": 200, "height": 150},   # Closet
        {"width": 350, "height": 350},   # Office
        {"width": 600, "height": 600},   # Garage
        {"width": 200, "height": 250},   # Pantry
    ]
    default_areas = [d["width"] * d["height"] for d in default_dimensions]
    avg_default_area = sum(default_areas) / len(default_areas)
    
    # Calculate scale factor (square root for linear scaling)
    # If existing rooms are smaller, scale factor < 1.0
    # If existing rooms are larger, scale factor > 1.0
    scale_factor = (avg_existing_area / avg_default_area) ** 0.5
    
    # Clamp scale factor to reasonable range (0.3 to 2.0)
    scale_factor = max(0.3, min(2.0, scale_factor))
    
    return scale_factor


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
                       existing_rooms: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Check if polygon placement is valid (no overlaps, within bounds).
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check bounds
    bbox = _polygon_to_bbox(polygon)
    if bbox[0] < 0:
        return (False, f"Room would extend beyond left edge (x={bbox[0]:.1f} < 0)")
    if bbox[1] < 0:
        return (False, f"Room would extend beyond top edge (y={bbox[1]:.1f} < 0)")
    if bbox[2] > MAX_CANVAS_WIDTH:
        return (False, f"Room would extend beyond right edge (x={bbox[2]:.1f} > {MAX_CANVAS_WIDTH})")
    if bbox[3] > MAX_CANVAS_HEIGHT:
        return (False, f"Room would extend beyond bottom edge (y={bbox[3]:.1f} > {MAX_CANVAS_HEIGHT})")
    
    # Check overlaps using validate_room_placement
    validation = validate_room_placement(polygon, existing_rooms)
    if not validation.get("valid", False):
        error_msg = validation.get("error", "Room overlaps with existing room")
        return (False, error_msg)
    
    return (True, None)


def smart_room_placement(door_location: List[float], door_direction: str,
                        dimensions: Dict[str, float], existing_rooms: List[Dict[str, Any]],
                        room_type: str, mode: str, preferred_position: Optional[List[float]] = None,
                        target_room_size: Optional[Dict[str, float]] = None) -> Tuple[Optional[List[List[float]]], Optional[str]]:
    """
    Try multiple placement strategies to find valid room placement.
    Returns tuple of (best_valid_polygon, error_message).
    If placement found, error_message is None.
    If no placement found, returns (None, detailed_error_message).
    """
    if not ENABLE_SMART_PLACEMENT:
        # Fallback to standard placement
        polygon = _generate_shaped_room(room_type, door_location, door_direction,
                                       dimensions["width"], dimensions["height"], mode)
        is_valid, error_msg = _is_valid_placement(polygon, existing_rooms)
        if is_valid:
            return (polygon, None)
        return (None, error_msg or "Standard placement failed")
    
    candidates = []
    
    # Use target room size from detected room if available (more accurate than default dimensions)
    if target_room_size:
        width = target_room_size.get("width", dimensions["width"])
        height = target_room_size.get("height", dimensions["height"])
        logger.info(f"Using target room size from blueprint: {width:.1f}x{height:.1f} (was {dimensions['width']:.1f}x{dimensions['height']:.1f})")
    else:
        width = dimensions["width"]
        height = dimensions["height"]
    
    all_errors = []
    
    # Try placement at preferred position (from blueprint label) if available
    if preferred_position:
        try:
            # Calculate offset from door to preferred position
            pref_x, pref_y = preferred_position
            door_x, door_y = door_location
            
            # Generate room centered at preferred position, but connected to door
            # Adjust door location to align room center with preferred position
            if door_direction == "N":
                adjusted_door_x = pref_x
                adjusted_door_y = pref_y + height / 2
            elif door_direction == "S":
                adjusted_door_x = pref_x
                adjusted_door_y = pref_y - height / 2
            elif door_direction == "E":
                adjusted_door_x = pref_x - width / 2
                adjusted_door_y = pref_y
            else:  # W
                adjusted_door_x = pref_x + width / 2
                adjusted_door_y = pref_y
            
            preferred_polygon = _generate_shaped_room(
                room_type, [adjusted_door_x, adjusted_door_y], door_direction, width, height, mode
            )
            is_valid, error_msg = _is_valid_placement(preferred_polygon, existing_rooms)
            if is_valid:
                candidates.append(("blueprint_label", preferred_polygon, 1.5))  # Higher score for blueprint alignment
            elif error_msg:
                all_errors.append(f"Blueprint label placement: {error_msg}")
        except Exception as e:
            logger.warning(f"Preferred position placement failed: {str(e)}")
    
    # Try standard placement
    standard = _generate_shaped_room(room_type, door_location, door_direction, width, height, mode)
    is_valid, error_msg = _is_valid_placement(standard, existing_rooms)
    if is_valid:
        candidates.append(("standard", standard, 1.0))
    elif error_msg:
        all_errors.append(f"Standard placement: {error_msg}")
    
    # Try offset placements (left/right of door)
    for offset in [-200, -100, -50, 50, 100, 200]:
        offset_polygon = _generate_with_offset(door_location, door_direction, width, height, offset)
        is_valid, error_msg = _is_valid_placement(offset_polygon, existing_rooms)
        if is_valid:
            score = 1.0 - abs(offset) / 200  # Prefer less offset
            candidates.append(("offset", offset_polygon, score))
        elif error_msg and len(all_errors) < 3:  # Limit error messages
            all_errors.append(f"Offset {offset}px: {error_msg}")
    
    # Try smaller dimensions if no valid placement
    if not candidates:
        smaller_dims = {"width": width * 0.7, "height": height * 0.7}
        smaller_polygon = _generate_shaped_room(room_type, door_location, door_direction,
                                                smaller_dims["width"], smaller_dims["height"], mode)
        is_valid, error_msg = _is_valid_placement(smaller_polygon, existing_rooms)
        if is_valid:
            candidates.append(("smaller", smaller_polygon, 0.8))
        elif error_msg:
            all_errors.append(f"70% size: {error_msg}")
    
    # Try even smaller sizes (more aggressive)
    size_reductions = [0.5, 0.4, 0.3, 0.25, 0.2]
    for reduction in size_reductions:
        if candidates:  # If we found something, stop trying smaller
            break
        reduced_dims = {"width": width * reduction, "height": height * reduction}
        # Ensure minimum viable size
        if reduced_dims["width"] < 100 or reduced_dims["height"] < 100:
            break
        reduced_polygon = _generate_shaped_room(room_type, door_location, door_direction,
                                                reduced_dims["width"], reduced_dims["height"], mode)
        is_valid, error_msg = _is_valid_placement(reduced_polygon, existing_rooms)
        if is_valid:
            score = 0.6 - (1.0 - reduction) * 0.2  # Lower score for smaller rooms
            candidates.append((f"{int(reduction*100)}%", reduced_polygon, score))
        elif error_msg and len(all_errors) < 5:
            all_errors.append(f"{int(reduction*100)}% size: {error_msg}")
    
    # Try placing behind the door (opposite direction) if no candidates yet
    if not candidates:
        opposite_directions = {"N": "S", "S": "N", "E": "W", "W": "E"}
        opposite_dir = opposite_directions.get(door_direction, door_direction)
        for size_mult in [0.7, 0.5, 0.3]:
            behind_dims = {"width": width * size_mult, "height": height * size_mult}
            if behind_dims["width"] < 100 or behind_dims["height"] < 100:
                break
            behind_polygon = _generate_shaped_room(room_type, door_location, opposite_dir,
                                                   behind_dims["width"], behind_dims["height"], mode)
            is_valid, error_msg = _is_valid_placement(behind_polygon, existing_rooms)
            if is_valid:
                candidates.append((f"behind_{int(size_mult*100)}%", behind_polygon, 0.4))
                break
    
    # Try more offset variations with smaller sizes
    if not candidates:
        for size_mult in [0.5, 0.4, 0.3]:
            if candidates:
                break
            reduced_width = width * size_mult
            reduced_height = height * size_mult
            if reduced_width < 100 or reduced_height < 100:
                break
            # Try more offset positions
            for offset in [-300, -250, -150, 150, 250, 300, -400, 400]:
                offset_polygon = _generate_with_offset(door_location, door_direction, 
                                                      reduced_width, reduced_height, offset)
                is_valid, error_msg = _is_valid_placement(offset_polygon, existing_rooms)
                if is_valid:
                    score = 0.5 - abs(offset) / 1000  # Lower score for larger offsets
                    candidates.append((f"offset_{offset}_{int(size_mult*100)}%", offset_polygon, score))
                    break  # Found one, try next size
                if len(candidates) > 0:
                    break
    
    # Try clamping to canvas if it's just a bounds issue (last resort)
    if not candidates:
        # Try a small room and clamp it to canvas bounds
        min_size = {"width": max(150, width * 0.2), "height": max(150, height * 0.2)}
        clamped_polygon = _generate_shaped_room(room_type, door_location, door_direction,
                                                min_size["width"], min_size["height"], mode)
        clamped_polygon = _clamp_polygon_to_canvas(clamped_polygon)
        # Check if clamped version is valid (only check overlaps, not bounds)
        validation = validate_room_placement(clamped_polygon, existing_rooms)
        if validation.get("valid", False):
            candidates.append(("clamped", clamped_polygon, 0.3))
    
    # Return best candidate
    if candidates:
        candidates.sort(key=lambda x: x[2], reverse=True)
        return (candidates[0][1], None)
    
    # Build detailed error message
    if all_errors:
        # Group errors by type
        bounds_errors = [e for e in all_errors if "edge" in e.lower() or "extend" in e.lower()]
        overlap_errors = [e for e in all_errors if "overlap" in e.lower()]
        
        if bounds_errors:
            return (None, f"Room would go out of bounds. {bounds_errors[0]} Tried multiple sizes and positions but couldn't fit within canvas limits.")
        elif overlap_errors:
            return (None, f"{overlap_errors[0]} Tried multiple sizes, offsets, and positions but all overlapped with existing rooms. Try moving or resizing nearby rooms to create space.")
        else:
            return (None, f"Placement failed after trying multiple strategies: {all_errors[0]}")
    
    return (None, "No valid placement found after trying multiple sizes, positions, and directions. The door may be in a very tight space. Try a different door or adjust existing rooms.")

