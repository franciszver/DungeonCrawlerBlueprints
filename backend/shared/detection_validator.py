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


def should_retry_with_strict_mode(validation_results: Dict[str, Any]) -> bool:
    """
    Determine if detection should be retried with strict mode.
    
    Args:
        validation_results: Results from validate_and_enhance_detection
        
    Returns:
        True if retry is recommended
    """
    return validation_results.get("needs_retry", False)

