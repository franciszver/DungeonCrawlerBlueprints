"""Label-based room generation from blueprint text labels."""
from typing import List, Dict, Any, Tuple, Optional
import logging
import sys
import os

# Add shared module to path
shared_path = os.path.dirname(__file__)
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from edge_detector_lightweight import detect_room_from_label_center, _validate_room_boundaries
from rectangular_room_generator import generate_rectangular_room_from_label
from config import MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT

logger = logging.getLogger(__name__)


def generate_rooms_from_selected_labels(
    image_base64: str,
    selected_label_indices: List[int],
    all_text_labels: List[Dict[str, Any]],
    existing_rooms: List[Dict[str, Any]],
    canvas_bounds: Optional[List[float]] = None,
    label_position_adjustments: Optional[Dict[str, Dict[str, float]]] = None
) -> Dict[str, Any]:
    """
    Generate rooms from selected text labels using rectangular expansion.
    
    Args:
        image_base64: Base64-encoded blueprint image
        selected_label_indices: List of indices into all_text_labels for selected labels
        all_text_labels: All extracted text labels from blueprint
        existing_rooms: List of existing rooms (for boundary constraints)
        canvas_bounds: [x_min, y_min, x_max, y_max] canvas boundaries (defaults to MAX_CANVAS_WIDTH/HEIGHT)
        label_position_adjustments: Dict mapping label index (as string) to {x, y} offset adjustments
        
    Returns:
        Dictionary with:
        - rooms: List of generated room objects
        - warnings: List of warning messages for skipped rooms
    """
    if canvas_bounds is None:
        canvas_bounds = [0, 0, MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT]
    
    if label_position_adjustments is None:
        label_position_adjustments = {}
    
    generated_rooms = []
    warnings = []
    
    # Process each selected label
    for label_idx in selected_label_indices:
        if label_idx >= len(all_text_labels):
            warnings.append(f"Invalid label index: {label_idx}")
            continue
        
        label = all_text_labels[label_idx]
        label_text = label.get('text', 'Unknown Room')
        bbox = label.get('bbox', [])
        
        if len(bbox) != 4:
            warnings.append(f"Label '{label_text}' has invalid bounding box")
            continue
        
        # Get center position from label bbox (convert from Decimal to float for DynamoDB compatibility)
        center_x = float((bbox[0] + bbox[2]) / 2)
        center_y = float((bbox[1] + bbox[3]) / 2)
        
        # Apply user adjustments if present
        adjustment_key = str(label_idx)
        if adjustment_key in label_position_adjustments:
            adjustment = label_position_adjustments[adjustment_key]
            center_x += float(adjustment.get('x', 0))
            center_y += float(adjustment.get('y', 0))
            logger.info(f"Applied position adjustment to label '{label_text}': offset=({adjustment.get('x', 0):.1f}, {adjustment.get('y', 0):.1f})")
        
        label_center = [center_x, center_y]
        
        # Check if label center is outside canvas bounds
        x_min, y_min, x_max, y_max = canvas_bounds
        if center_x < x_min or center_x > x_max or center_y < y_min or center_y > y_max:
            warnings.append(f"Label '{label_text}' center is outside canvas bounds - skipping")
            continue
        
        # Generate rectangular room by expanding from label center
        logger.info(f"Generating rectangular room for label '{label_text}' at [{center_x:.1f}, {center_y:.1f}]")
        polygon, error_msg = generate_rectangular_room_from_label(
            label_center,
            image_base64,
            existing_rooms,
            canvas_bounds,
            image_format='png',
            step_size=5
        )
        
        # Validate boundaries (for rectangular rooms, we're more lenient)
        if polygon is None:
            warning_msg = error_msg or "Cannot determine room boundaries"
            warnings.append(f"Label '{label_text}': {warning_msg}")
            continue
        
        # Basic validation - check if rectangle is reasonable size
        # If too small, create a minimum viable room (100x100) centered on label
        bbox = _polygon_to_bbox(polygon)
        if len(bbox) == 4:
            x_min, y_min, x_max, y_max = bbox
            width = x_max - x_min
            height = y_max - y_min
            MIN_ROOM_SIZE = 100  # Minimum room size in pixels
            
            if width < MIN_ROOM_SIZE or height < MIN_ROOM_SIZE:
                # Create minimum viable square room centered on label
                logger.info(f"Room too small ({width:.0f}x{height:.0f}), creating minimum viable room ({MIN_ROOM_SIZE}x{MIN_ROOM_SIZE})")
                half_size = MIN_ROOM_SIZE / 2
                polygon = [
                    [center_x - half_size, center_y - half_size],
                    [center_x + half_size, center_y - half_size],
                    [center_x + half_size, center_y + half_size],
                    [center_x - half_size, center_y + half_size]
                ]
                warnings.append(f"Label '{label_text}': Created minimum room size ({MIN_ROOM_SIZE}x{MIN_ROOM_SIZE}) - adjust as needed")
        
        # Create room object
        room = {
            'id': f"generated_{label_idx}_{label_text.replace(' ', '_').lower()}",
            'name_hint': label_text,
            'name_source': 'blueprint_text',
            'polygon': polygon,
            'bounding_box': _polygon_to_bbox(polygon),
            'confidence': label.get('confidence', 0.9),
            'is_extended': True,  # Mark as generated/extended room
            'label_position': label_center,  # Store original label position for overlay
            'label_index': label_idx
        }
        
        generated_rooms.append(room)
        logger.info(f"Successfully generated room '{label_text}' with {len(polygon)} vertices")
    
    return {
        'rooms': generated_rooms,
        'warnings': warnings
    }


def generate_room_from_door(
    door_location: List[float],
    door_direction: str,
    room_type: str,
    image_base64: str,
    existing_rooms: List[Dict[str, Any]],
    canvas_bounds: Optional[List[float]] = None,
    mode: str = 'realistic'
) -> Dict[str, Any]:
    """
    Generate room from manually placed door.
    Checks surrounding room boundaries first; if none, uses generic placement.
    
    Args:
        door_location: [x, y] door position
        door_direction: Direction door faces (N, S, E, W)
        room_type: Type of room to generate
        image_base64: Base64-encoded blueprint image
        existing_rooms: List of existing rooms (for boundary checking)
        canvas_bounds: Canvas boundaries (defaults to MAX_CANVAS_WIDTH/HEIGHT)
        mode: Generation mode ('realistic' or 'fantasy')
        
    Returns:
        Dictionary with room object or error message
    """
    if canvas_bounds is None:
        canvas_bounds = [0, 0, MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT]
    
    # Check surrounding room boundaries first
    # Find nearby rooms that could serve as boundaries
    nearby_rooms = []
    door_x, door_y = door_location
    
    for room in existing_rooms:
        polygon = room.get('polygon')
        bbox = room.get('bounding_box', [])
        
        if polygon:
            # Check if door is near this room's polygon
            min_dist = _min_distance_to_polygon(door_location, polygon)
            if min_dist < 200:  # Within 200px
                nearby_rooms.append(room)
        elif len(bbox) == 4:
            # Check if door is near this room's bbox
            x_min, y_min, x_max, y_max = bbox
            room_center_x = (x_min + x_max) / 2
            room_center_y = (y_min + y_max) / 2
            dist = ((door_x - room_center_x) ** 2 + (door_y - room_center_y) ** 2) ** 0.5
            if dist < 200:
                nearby_rooms.append(room)
    
    # If we have nearby rooms, try to use them as boundaries
    if nearby_rooms:
        # Use door location as center and detect room boundaries
        polygon, error_msg = detect_room_from_label_center(
            door_location,
            image_base64,
            existing_rooms,
            canvas_bounds,
            timeout_seconds=5
        )
        
        if polygon:
            room = {
                'id': f"generated_door_{room_type.replace(' ', '_').lower()}",
                'name_hint': room_type,
                'name_source': 'user_generated',
                'polygon': polygon,
                'bounding_box': _polygon_to_bbox(polygon),
                'confidence': 0.8,
                'is_extended': True,
                'door_location': door_location,
                'door_direction': door_direction
            }
            return {'success': True, 'room': room}
    
    # No nearby rooms - use generic placement (allows beyond canvas)
    # Import room_generator for generic placement
    from room_generator import generate_room
    
    generation_result = generate_room(
        door_location,
        door_direction,
        'Room',  # current_room_type
        mode,
        room_type,
        scale_factor=1.0  # No scaling for door-based generation
    )
    
    if generation_result.get('success'):
        room = generation_result['room']
        # Check if room extends beyond canvas - resize canvas if needed
        bbox = room.get('bounding_box', [])
        if len(bbox) == 4:
            x_min, y_min, x_max, y_max = bbox
            canvas_x_min, canvas_y_min, canvas_x_max, canvas_y_max = canvas_bounds
            
            # Check if room extends beyond canvas
            if x_max > canvas_x_max or y_max > canvas_y_max or x_min < canvas_x_min or y_min < canvas_y_min:
                # Room extends beyond canvas - this is allowed for door-based generation
                # Canvas will be resized by frontend
                logger.info(f"Room extends beyond canvas - canvas resize will be handled by frontend")
        
        return {'success': True, 'room': room, 'needs_canvas_resize': True}
    
    return {'success': False, 'error': generation_result.get('error', 'Generation failed')}


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


def _min_distance_to_polygon(point: List[float], polygon: List[List[float]]) -> float:
    """Calculate minimum distance from point to polygon edges."""
    if len(polygon) < 2:
        return float('inf')
    
    px, py = point
    min_dist = float('inf')
    
    # Check distance to each edge
    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]
        
        # Distance from point to line segment
        dist = _point_to_line_segment_distance(px, py, p1[0], p1[1], p2[0], p2[1])
        min_dist = min(min_dist, dist)
    
    return min_dist


def _point_to_line_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate distance from point to line segment."""
    import math
    
    # Vector from line start to end
    dx = x2 - x1
    dy = y2 - y1
    
    # Vector from line start to point
    px_dx = px - x1
    py_dy = py - y1
    
    # Project point onto line
    t = max(0, min(1, (px_dx * dx + py_dy * dy) / (dx * dx + dy * dy) if (dx * dx + dy * dy) > 0 else 0))
    
    # Closest point on line segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Distance from point to closest point
    return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)

