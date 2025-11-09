"""Post-processing validation for room detection results."""
from typing import Dict, Any, List, Tuple, Optional
import sys
import os

# Add shared module to path if not already there
shared_path = os.path.dirname(__file__)
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)


def validate_and_enhance_detection(
    rooms: List[Dict[str, Any]], 
    doors: List[Dict[str, Any]],
    image_base64: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Validate detection results and return validation metadata.
    
    Args:
        rooms: List of detected rooms
        doors: List of detected doors
        image_base64: Optional base64 image for re-detection
        
    Returns:
        Tuple of (rooms, validation_results)
    """
    validation_results = {
        "coverage_score": 0.0,
        "room_count_adequate": False,
        "overlaps_detected": False,
        "validation_passed": False,
        "warnings": [],
        "needs_retry": False
    }
    
    # Validate coverage
    coverage_score = validate_coverage(rooms)
    validation_results["coverage_score"] = coverage_score
    
    if coverage_score < 0.85:
        validation_results["warnings"].append(
            f"Low coverage detected: {coverage_score:.1%}. Some rooms may be missing."
        )
        validation_results["needs_retry"] = True
    
    # Validate room count
    room_count_adequate = validate_room_count(rooms)
    validation_results["room_count_adequate"] = room_count_adequate
    
    if not room_count_adequate:
        validation_results["warnings"].append(
            f"Only {len(rooms)} rooms detected. This seems low for the blueprint size."
        )
        validation_results["needs_retry"] = True
    
    # Validate overlaps
    overlaps = validate_overlaps(rooms)
    validation_results["overlaps_detected"] = len(overlaps) > 0
    
    if overlaps:
        validation_results["warnings"].append(
            f"Detected {len(overlaps)} room overlaps that may indicate errors."
        )
    
    # Validate proportions
    proportion_issues = validate_proportions(rooms)
    if proportion_issues:
        validation_results["warnings"].append(
            f"Detected {len(proportion_issues)} rooms with unusual proportions."
        )
    
    # Overall validation
    validation_results["validation_passed"] = (
        coverage_score >= 0.85 and 
        room_count_adequate and 
        len(overlaps) == 0
    )
    
    # Resolve overlaps by adjusting room shapes (instead of removing)
    if overlaps:
        rooms = resolve_overlaps_by_adjusting_shapes(rooms, overlaps)
        # Re-check overlaps after adjustment
        remaining_overlaps = validate_overlaps(rooms)
        validation_results["overlaps_detected"] = len(remaining_overlaps) > 0
        validation_results["validation_passed"] = (
            validation_results.get("coverage_score", 0) >= 0.85 and 
            validation_results.get("room_count_adequate", False) and 
            len(remaining_overlaps) == 0
        )
        # Update warning
        if len(remaining_overlaps) == 0:
            validation_results["warnings"] = [
                w for w in validation_results.get("warnings", [])
                if "overlap" not in w.lower()
            ]
            validation_results["warnings"].append(
                f"Adjusted {len(overlaps)} overlapping room(s) to fit blueprint boundaries."
            )
    
    return rooms, validation_results


def validate_coverage(rooms: List[Dict[str, Any]]) -> float:
    """
    Calculate what percentage of the blueprint is covered by detected rooms.
    
    Args:
        rooms: List of detected rooms with bounding boxes
        
    Returns:
        Coverage score (0.0-1.0)
    """
    if not rooms:
        return 0.0
    
    # Calculate total area covered by rooms (accounting for overlaps)
    # Using a simplified grid-based approach
    GRID_SIZE = 100
    grid = [[False for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    
    for room in rooms:
        bbox = room.get('bounding_box', [])
        if len(bbox) != 4:
            continue
            
        x_min, y_min, x_max, y_max = bbox
        
        # Normalize to grid coordinates (0-100)
        grid_x_min = int((x_min / 1000) * GRID_SIZE)
        grid_y_min = int((y_min / 1000) * GRID_SIZE)
        grid_x_max = int((x_max / 1000) * GRID_SIZE)
        grid_y_max = int((y_max / 1000) * GRID_SIZE)
        
        # Clamp to grid bounds
        grid_x_min = max(0, min(GRID_SIZE - 1, grid_x_min))
        grid_y_min = max(0, min(GRID_SIZE - 1, grid_y_min))
        grid_x_max = max(0, min(GRID_SIZE - 1, grid_x_max))
        grid_y_max = max(0, min(GRID_SIZE - 1, grid_y_max))
        
        # Mark grid cells as covered
        for y in range(grid_y_min, grid_y_max + 1):
            for x in range(grid_x_min, grid_x_max + 1):
                grid[y][x] = True
    
    # Calculate coverage percentage
    covered_cells = sum(sum(row) for row in grid)
    total_cells = GRID_SIZE * GRID_SIZE
    
    return covered_cells / total_cells


def validate_room_count(rooms: List[Dict[str, Any]]) -> bool:
    """
    Check if the number of detected rooms is reasonable.
    
    Args:
        rooms: List of detected rooms
        
    Returns:
        True if room count seems adequate
    """
    room_count = len(rooms)
    
    # Heuristic: Most residential blueprints have at least 4-5 rooms
    # (living room, kitchen, bedroom, bathroom, etc.)
    if room_count < 3:
        return False
    
    # Calculate average room size
    if room_count > 0:
        total_area = 0
        for room in rooms:
            bbox = room.get('bounding_box', [])
            if len(bbox) == 4:
                x_min, y_min, x_max, y_max = bbox
                area = (x_max - x_min) * (y_max - y_min)
                total_area += area
        
        avg_area = total_area / room_count
        
        # If average room is very large (>40% of blueprint), might be missing rooms
        if avg_area > (1000 * 1000 * 0.4):
            return False
    
    return True


def validate_overlaps(rooms: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    """
    Detect significant overlaps between rooms (which usually indicates errors).
    
    Args:
        rooms: List of detected rooms
        
    Returns:
        List of (room_id1, room_id2) tuples with significant overlaps
    """
    overlaps = []
    
    for i, room1 in enumerate(rooms):
        bbox1 = room1.get('bounding_box', [])
        if len(bbox1) != 4:
            continue
            
        for j, room2 in enumerate(rooms[i + 1:], start=i + 1):
            bbox2 = room2.get('bounding_box', [])
            if len(bbox2) != 4:
                continue
            
            # Calculate overlap
            overlap_area = calculate_overlap_area(bbox1, bbox2)
            
            # Calculate areas
            area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
            area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
            
            # If overlap is > 30% of either room, flag it
            if area1 > 0 and area2 > 0:
                overlap_ratio1 = overlap_area / area1
                overlap_ratio2 = overlap_area / area2
                
                if overlap_ratio1 > 0.3 or overlap_ratio2 > 0.3:
                    overlaps.append((
                        room1.get('id', f'room_{i}'),
                        room2.get('id', f'room_{j}')
                    ))
    
    return overlaps


def calculate_overlap_area(bbox1: List[float], bbox2: List[float]) -> float:
    """Calculate the overlapping area between two bounding boxes."""
    x_min1, y_min1, x_max1, y_max1 = bbox1
    x_min2, y_min2, x_max2, y_max2 = bbox2
    
    # Calculate intersection
    x_overlap = max(0, min(x_max1, x_max2) - max(x_min1, x_min2))
    y_overlap = max(0, min(y_max1, y_max2) - max(y_min1, y_min2))
    
    return x_overlap * y_overlap


def validate_proportions(rooms: List[Dict[str, Any]]) -> List[str]:
    """
    Check for rooms with unusual proportions (very thin, very small, etc.).
    
    Args:
        rooms: List of detected rooms
        
    Returns:
        List of room IDs with proportion issues
    """
    issues = []
    
    for room in rooms:
        bbox = room.get('bounding_box', [])
        if len(bbox) != 4:
            continue
        
        x_min, y_min, x_max, y_max = bbox
        width = x_max - x_min
        height = y_max - y_min
        
        # Check for very thin rooms (aspect ratio > 10:1)
        if width > 0 and height > 0:
            aspect_ratio = max(width / height, height / width)
            if aspect_ratio > 10:
                issues.append(room.get('id', 'unknown'))
                continue
        
        # Check for very small rooms (< 1% of blueprint)
        area = width * height
        if area < (1000 * 1000 * 0.01):
            issues.append(room.get('id', 'unknown'))
    
    return issues


def resolve_overlaps_by_adjusting_shapes(rooms: List[Dict[str, Any]], overlaps: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
    """
    Resolve overlaps by adjusting room shapes to fit appropriately.
    Shrinks or adjusts the overlapping room's boundaries to eliminate overlap.
    
    Args:
        rooms: List of detected rooms
        overlaps: List of (room_id1, room_id2) tuples with significant overlaps
        
    Returns:
        List of rooms with adjusted shapes to eliminate overlaps
    """
    # Create a map of room_id to room for quick lookup
    room_map = {room.get('id'): room for room in rooms}
    
    for room_id1, room_id2 in overlaps:
        room1 = room_map.get(room_id1)
        room2 = room_map.get(room_id2)
        
        if not room1 or not room2:
            continue
        
        bbox1 = room1.get('bounding_box', [])
        bbox2 = room2.get('bounding_box', [])
        
        if len(bbox1) != 4 or len(bbox2) != 4:
            continue
        
        # Calculate overlap area
        overlap_area = calculate_overlap_area(bbox1, bbox2)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        # Determine which room to adjust (prefer adjusting the larger or lower confidence one)
        conf1 = room1.get('confidence', 0.5)
        conf2 = room2.get('confidence', 0.5)
        
        # Adjust the room with lower confidence, or larger room if confidences are equal
        if conf1 < conf2 or (conf1 == conf2 and area1 > area2):
            room_to_adjust = room1
            other_room = room2
            room_id_to_adjust = room_id1
        else:
            room_to_adjust = room2
            other_room = room1
            room_id_to_adjust = room_id2
        
        # Store original bbox before adjustment
        original_bbox = room_to_adjust.get('bounding_box', [])
        
        # Adjust the room's bounding box to eliminate overlap
        adjusted_bbox = _adjust_bbox_to_remove_overlap(
            original_bbox,
            other_room.get('bounding_box', [])
        )
        
        # Update the room's bounding box
        room_to_adjust['bounding_box'] = adjusted_bbox
        
        # If room has a polygon, adjust it proportionally
        if room_to_adjust.get('polygon') and len(original_bbox) == 4:
            polygon = room_to_adjust['polygon']
            # Calculate scale factors
            old_width = original_bbox[2] - original_bbox[0]
            old_height = original_bbox[3] - original_bbox[1]
            new_width = adjusted_bbox[2] - adjusted_bbox[0]
            new_height = adjusted_bbox[3] - adjusted_bbox[1]
            
            if old_width > 0 and old_height > 0:
                scale_x = new_width / old_width
                scale_y = new_height / old_height
                
                # Adjust polygon
                adjusted_polygon = [
                    [
                        (p[0] - original_bbox[0]) * scale_x + adjusted_bbox[0],
                        (p[1] - original_bbox[1]) * scale_y + adjusted_bbox[1]
                    ]
                    for p in polygon
                ]
                room_to_adjust['polygon'] = adjusted_polygon
        
        # Update room map
        room_map[room_id_to_adjust] = room_to_adjust
    
    # Return updated rooms
    return list(room_map.values())


def _adjust_bbox_to_remove_overlap(bbox1: List[float], bbox2: List[float]) -> List[float]:
    """
    Adjust bbox1 to remove overlap with bbox2.
    Shrinks bbox1 on the side(s) where overlap occurs.
    
    Returns:
        Adjusted bounding box [x_min, y_min, x_max, y_max]
    """
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2
    
    # Calculate overlap
    x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
    y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
    
    if x_overlap == 0 and y_overlap == 0:
        return bbox1  # No overlap
    
    # Determine which side to shrink (prefer shrinking the smaller overlap)
    if x_overlap < y_overlap:
        # Shrink horizontally
        # Check which side has less space
        left_space = x2_min - x1_min
        right_space = x1_max - x2_max
        
        if left_space > 0 and right_space > 0:
            # Shrink from the side with less space
            if left_space < right_space:
                x1_min = x2_max  # Move left edge to right
            else:
                x1_max = x2_min  # Move right edge to left
        elif left_space > 0:
            x1_min = x2_max
        elif right_space > 0:
            x1_max = x2_min
        else:
            # Overlap is complete, shrink proportionally
            overlap_ratio = x_overlap / (x1_max - x1_min)
            shrink_amount = (x1_max - x1_min) * overlap_ratio * 0.5
            x1_min += shrink_amount
            x1_max -= shrink_amount
    else:
        # Shrink vertically
        top_space = y2_min - y1_min
        bottom_space = y1_max - y2_max
        
        if top_space > 0 and bottom_space > 0:
            if top_space < bottom_space:
                y1_min = y2_max
            else:
                y1_max = y2_min
        elif top_space > 0:
            y1_min = y2_max
        elif bottom_space > 0:
            y1_max = y2_min
        else:
            # Overlap is complete, shrink proportionally
            overlap_ratio = y_overlap / (y1_max - y1_min)
            shrink_amount = (y1_max - y1_min) * overlap_ratio * 0.5
            y1_min += shrink_amount
            y1_max -= shrink_amount
    
    # Ensure minimum size (at least 50x50)
    if x1_max - x1_min < 50:
        center_x = (x1_min + x1_max) / 2
        x1_min = center_x - 25
        x1_max = center_x + 25
    
    if y1_max - y1_min < 50:
        center_y = (y1_min + y1_max) / 2
        y1_min = center_y - 25
        y1_max = center_y + 25
    
    return [x1_min, y1_min, x1_max, y1_max]


def should_retry_with_strict_mode(validation_results: Dict[str, Any]) -> bool:
    """
    Determine if detection should be retried with strict mode.
    
    Args:
        validation_results: Results from validate_and_enhance_detection
        
    Returns:
        True if retry is recommended
    """
    return validation_results.get("needs_retry", False)

