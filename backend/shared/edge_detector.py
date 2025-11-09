"""Edge detection module for refining room boundaries.

Uses PIL-based lightweight edge detection as primary method (works out of box).
OpenCV is optional upgrade for maximum accuracy (requires container image).
"""
from typing import List, Dict, Any, Tuple, Optional, TYPE_CHECKING
import base64
from io import BytesIO
import logging

if TYPE_CHECKING:
    import numpy as np

# Import lightweight PIL-based detector (primary)
try:
    from edge_detector_lightweight import refine_room_boundaries_lightweight
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    refine_room_boundaries_lightweight = None

# Try to import OpenCV - optional upgrade
try:
    import cv2
    import numpy as np
    from PIL import Image
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None
    np = None
    Image = None

logger = logging.getLogger(__name__)


def refine_room_boundaries(
    image_base64: str,
    rooms: List[Dict[str, Any]],
    threshold: int = 50,
    image_format: str = 'png'
) -> Dict[str, Any]:
    """
    Refine room boundaries by snapping polygon vertices to detected edges.
    
    Uses PIL-based lightweight detection as primary (works out of box).
    Falls back to OpenCV if available (optional upgrade for maximum accuracy).
    
    Args:
        image_base64: Base64-encoded blueprint image
        rooms: List of rooms with polygon coordinates
        threshold: Maximum distance (pixels) to snap vertices to edges
        image_format: Image format (png, jpg, etc.)
        
    Returns:
        Dictionary with refined rooms and metadata
    """
    # Try OpenCV first if available (optional upgrade for maximum accuracy)
    if OPENCV_AVAILABLE:
        try:
            logger.info("Using OpenCV edge detection (optional upgrade)")
            result = refine_room_boundaries_opencv(image_base64, rooms, threshold, image_format)
            if result.get('success'):
                result['method'] = 'OpenCV'
                return result
            else:
                logger.warning(f"OpenCV edge detection failed: {result.get('error')}, falling back to PIL")
        except Exception as e:
            logger.warning(f"OpenCV edge detection error: {str(e)}, falling back to PIL")
    
    # Use PIL-based lightweight solution (primary/default)
    if PIL_AVAILABLE and refine_room_boundaries_lightweight:
        logger.info("Using PIL lightweight edge detection (default)")
        return refine_room_boundaries_lightweight(image_base64, rooms, threshold, image_format)
    
    # If neither available, return error
    return {
        "success": False,
        "error": "Edge detection unavailable. Neither PIL nor OpenCV is available. Please ensure Pillow is installed.",
        "refined_rooms": rooms
    }


def refine_room_boundaries_opencv(
    image_base64: str,
    rooms: List[Dict[str, Any]],
    threshold: int = 50,
    image_format: str = 'png'
) -> Dict[str, Any]:
    """
    Refine room boundaries using OpenCV (optional upgrade for maximum accuracy).
    
    Args:
        image_base64: Base64-encoded blueprint image
        rooms: List of rooms with polygon coordinates
        threshold: Maximum distance (pixels) to snap vertices to edges
        image_format: Image format (png, jpg, etc.)
        
    Returns:
        Dictionary with refined rooms and metadata
    """
    if not OPENCV_AVAILABLE:
        return {
            "success": False,
            "error": "OpenCV is not available. Use container image deployment for OpenCV support.",
            "refined_rooms": rooms
        }
    
    try:
        # Decode image
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        image_np = np.array(image)
        
        # Convert to grayscale if needed
        if len(image_np.shape) == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np
        
        # Detect edges using Canny
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=100,
            minLineLength=50,
            maxLineGap=10
        )
        
        if lines is None:
            lines = []
        else:
            lines = lines.reshape(-1, 4)  # Flatten to (N, 4) array
        
        # Refine each room
        refined_rooms = []
        refinement_stats = {
            "total_rooms": len(rooms),
            "refined_rooms": 0,
            "vertices_snapped": 0,
            "average_snap_distance": 0.0
        }
        
        total_snap_distance = 0.0
        
        for room in rooms:
            polygon = room.get('polygon')
            if not polygon or len(polygon) < 3:
                # Keep room as-is if no valid polygon
                refined_rooms.append(room)
                continue
            
            # Snap polygon vertices to edges
            refined_polygon, snap_info = _snap_polygon_to_edges(
                polygon,
                edges,
                lines,
                threshold
            )
            
            # Update room with refined polygon
            refined_room = room.copy()
            refined_room['polygon'] = refined_polygon
            
            # Recalculate bounding box
            refined_room['bounding_box'] = _polygon_to_bbox(refined_polygon)
            
            # Add refinement metadata
            refined_room['refinement_applied'] = snap_info['vertices_snapped'] > 0
            refined_room['vertices_snapped'] = snap_info['vertices_snapped']
            
            refined_rooms.append(refined_room)
            
            # Update stats
            if snap_info['vertices_snapped'] > 0:
                refinement_stats['refined_rooms'] += 1
                refinement_stats['vertices_snapped'] += snap_info['vertices_snapped']
                total_snap_distance += snap_info['total_distance']
        
        # Calculate average snap distance
        if refinement_stats['vertices_snapped'] > 0:
            refinement_stats['average_snap_distance'] = (
                total_snap_distance / refinement_stats['vertices_snapped']
            )
        
        return {
            "success": True,
            "refined_rooms": refined_rooms,
            "stats": refinement_stats,
            "method": "OpenCV"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Edge detection failed: {str(e)}",
            "refined_rooms": rooms  # Return original rooms on error
        }


def _snap_polygon_to_edges(
    polygon: List[List[float]],
    edges: Any,  # np.ndarray when OpenCV available
    lines: Any,  # np.ndarray when OpenCV available
    threshold: int
) -> Tuple[List[List[float]], Dict[str, Any]]:
    """
    Snap polygon vertices to nearby detected edges.
    
    Args:
        polygon: List of [x, y] vertices
        edges: Edge detection result (binary image)
        lines: Detected lines from Hough transform
        threshold: Maximum snap distance
        
    Returns:
        Tuple of (refined_polygon, snap_info)
    """
    refined_polygon = []
    vertices_snapped = 0
    total_distance = 0.0
    
    for vertex in polygon:
        x, y = int(vertex[0]), int(vertex[1])
        
        # Find nearest edge point
        best_point, best_distance = _find_nearest_edge_point(
            x, y, edges, lines, threshold
        )
        
        if best_point is not None and best_distance < threshold:
            # Snap to edge
            refined_polygon.append([float(best_point[0]), float(best_point[1])])
            vertices_snapped += 1
            total_distance += best_distance
        else:
            # Keep original vertex
            refined_polygon.append([float(x), float(y)])
    
    snap_info = {
        "vertices_snapped": vertices_snapped,
        "total_distance": total_distance
    }
    
    return refined_polygon, snap_info


def _find_nearest_edge_point(
    x: int,
    y: int,
    edges: Any,  # np.ndarray when OpenCV available
    lines: Any,  # np.ndarray when OpenCV available
    threshold: int
) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    Find the nearest edge point to a given coordinate.
    
    Args:
        x, y: Coordinate to search from
        edges: Edge detection result
        lines: Detected lines
        threshold: Maximum search distance
        
    Returns:
        Tuple of (nearest_point, distance) or (None, inf)
    """
    height, width = edges.shape
    
    # Ensure coordinates are within bounds
    x = max(0, min(width - 1, x))
    y = max(0, min(height - 1, y))
    
    best_point = None
    best_distance = float('inf')
    
    # First, try snapping to detected lines (more accurate)
    if len(lines) > 0:
        for line in lines:
            x1, y1, x2, y2 = line
            
            # Find closest point on line segment
            point, distance = _point_to_line_segment_distance(
                x, y, x1, y1, x2, y2
            )
            
            if distance < best_distance and distance < threshold:
                best_point = point
                best_distance = distance
    
    # If no line found, search for nearest edge pixel
    if best_point is None:
        search_radius = min(threshold, 100)  # Limit search area
        
        for dy in range(-search_radius, search_radius + 1):
            for dx in range(-search_radius, search_radius + 1):
                nx, ny = x + dx, y + dy
                
                # Check bounds
                if 0 <= nx < width and 0 <= ny < height:
                    # Check if this pixel is an edge
                    if edges[ny, nx] > 0:
                        distance = np.sqrt(dx*dx + dy*dy)
                        if distance < best_distance:
                            best_point = (nx, ny)
                            best_distance = distance
    
    return best_point, best_distance


def _point_to_line_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float
) -> Tuple[Tuple[int, int], float]:
    """
    Calculate distance from point to line segment and return closest point.
    
    Args:
        px, py: Point coordinates
        x1, y1, x2, y2: Line segment endpoints
        
    Returns:
        Tuple of (closest_point, distance)
    """
    # Vector from line start to point
    dx = x2 - x1
    dy = y2 - y1
    
    # Handle degenerate case (line is a point)
    if dx == 0 and dy == 0:
        distance = np.sqrt((px - x1)**2 + (py - y1)**2)
        return (int(x1), int(y1)), distance
    
    # Calculate projection parameter
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    
    # Clamp to line segment
    t = max(0, min(1, t))
    
    # Calculate closest point
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Calculate distance
    distance = np.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    return (int(closest_x), int(closest_y)), distance


def _polygon_to_bbox(polygon: List[List[float]]) -> List[float]:
    """Convert polygon vertices to bounding box."""
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

