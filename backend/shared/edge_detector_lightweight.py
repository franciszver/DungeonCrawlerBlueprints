"""Lightweight edge detection module using PIL only (no OpenCV required)."""
from typing import List, Dict, Any, Tuple, Optional
import base64
from io import BytesIO
import math
import logging

try:
    from PIL import Image, ImageFilter, UnidentifiedImageError
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageFilter = None
    UnidentifiedImageError = Exception

logger = logging.getLogger(__name__)

# Performance constants
MAX_PROCESSING_SIZE = 2000  # Maximum dimension for processing (pixels)
MIN_PROCESSING_SIZE = 100  # Minimum dimension (don't resize smaller images)


def refine_room_boundaries_lightweight(
    image_base64: str,
    rooms: List[Dict[str, Any]],
    threshold: int = 50,
    image_format: str = 'png'
) -> Dict[str, Any]:
    """
    Refine room boundaries using PIL-only edge detection (no OpenCV required).
    
    Uses enhanced PIL algorithm:
    1. Gaussian blur to reduce noise
    2. Edge detection using FIND_EDGES filter
    3. Threshold to create binary edge map
    4. Line detection using simple edge following
    
    Args:
        image_base64: Base64-encoded blueprint image
        rooms: List of rooms with polygon coordinates
        threshold: Maximum distance (pixels) to snap vertices to edges
        image_format: Image format (png, jpg, etc.)
        
    Returns:
        Dictionary with refined rooms and metadata
    """
    if not PIL_AVAILABLE:
        return {
            "success": False,
            "error": "PIL (Pillow) is not available. Edge detection requires Pillow to be installed.",
            "refined_rooms": rooms
        }
    
    try:
        # Decode image with better error handling
        try:
            image_data = base64.b64decode(image_base64)
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid base64 image data: {str(e)}. Please ensure the image is properly encoded.",
                "error_code": "INVALID_BASE64",
                "refined_rooms": rooms
            }
        
        # Open image with better error handling
        try:
            image = Image.open(BytesIO(image_data))
        except UnidentifiedImageError as e:
            return {
                "success": False,
                "error": f"Unsupported image format: {str(e)}. Supported formats: PNG, JPG, JPEG, GIF, BMP.",
                "error_code": "UNSUPPORTED_FORMAT",
                "refined_rooms": rooms
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to open image: {str(e)}. Please check the image file is not corrupted.",
                "error_code": "IMAGE_OPEN_ERROR",
                "refined_rooms": rooms
            }
        
        # Performance optimization: Resize large images
        original_width, original_height = image.size
        scale_factor = 1.0
        
        if max(original_width, original_height) > MAX_PROCESSING_SIZE:
            # Calculate scale to fit within MAX_PROCESSING_SIZE
            scale_factor = MAX_PROCESSING_SIZE / max(original_width, original_height)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            
            logger.info(f"Resizing image from {original_width}x{original_height} to {new_width}x{new_height} for performance")
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to grayscale if needed
        if image.mode != 'L':
            image = image.convert('L')
        
        # Calculate adaptive blur radius based on image size
        # Larger images need more blur, but not too much
        image_size = max(image.size)
        blur_radius = max(1.0, min(2.5, image_size / 500))
        
        # Apply Gaussian blur to reduce noise
        blurred = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Detect edges using FIND_EDGES filter (Sobel-like)
        edges = blurred.filter(ImageFilter.FIND_EDGES)
        
        # Calculate adaptive threshold using image statistics
        threshold_value = _calculate_adaptive_threshold(edges)
        
        # Convert to binary edge map
        edges_binary = edges.point(lambda x: 255 if x > threshold_value else 0, mode='1')
        
        # Convert PIL image to list of edge pixels for easier access
        edges_array = edges_binary.load()
        width, height = edges_binary.size
        
        # Scale threshold if image was resized
        scaled_threshold = threshold * scale_factor if scale_factor < 1.0 else threshold
        
        # Detect lines using simple edge following
        lines = _detect_lines_pil(edges_array, width, height)
        
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
            try:
                polygon = room.get('polygon')
                if not polygon or len(polygon) < 3:
                    # Keep room as-is if no valid polygon
                    refined_rooms.append(room)
                    continue
                
                # Scale polygon coordinates if image was resized
                if scale_factor < 1.0:
                    scaled_polygon = [[p[0] * scale_factor, p[1] * scale_factor] for p in polygon]
                else:
                    scaled_polygon = polygon
                
                # Snap polygon vertices to edges
                refined_polygon, snap_info = _snap_polygon_to_edges_pil(
                    scaled_polygon,
                    edges_array,
                    lines,
                    width,
                    height,
                    scaled_threshold
                )
                
                # Scale coordinates back if image was resized
                if scale_factor < 1.0:
                    refined_polygon = [[p[0] / scale_factor, p[1] / scale_factor] for p in refined_polygon]
                
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
            except Exception as e:
                # If refinement fails for a room, keep original
                logger.warning(f"Failed to refine room {room.get('id', 'unknown')}: {str(e)}")
                refined_rooms.append(room)
        
        # Calculate average snap distance
        if refinement_stats['vertices_snapped'] > 0:
            refinement_stats['average_snap_distance'] = (
                total_snap_distance / refinement_stats['vertices_snapped']
            )
        
        return {
            "success": True,
            "refined_rooms": refined_rooms,
            "stats": refinement_stats,
            "method": "PIL",
            "processing_info": {
                "original_size": [original_width, original_height],
                "processed_size": [width, height],
                "scale_factor": scale_factor
            }
        }
        
    except Exception as e:
        logger.error(f"PIL edge detection failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"PIL edge detection failed: {str(e)}. Please check the image format and try again.",
            "error_code": "PROCESSING_ERROR",
            "refined_rooms": rooms
        }


def _detect_lines_pil(
    edges_array: Any,
    width: int,
    height: int,
    min_line_length: int = 50
) -> List[Tuple[int, int, int, int]]:
    """
    Detect lines from edge pixels using simple edge following.
    
    Args:
        edges_array: PIL pixel access object (binary edge map)
        width: Image width
        height: Image height
        min_line_length: Minimum line length to detect
        
    Returns:
        List of line segments as (x1, y1, x2, y2) tuples
    """
    lines = []
    visited = set()
    
    # Scan for edge pixels and follow edges to form lines
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            
            # Check if this is an edge pixel
            if edges_array[x, y] != 0:
                # Try to follow edge to form a line
                line = _follow_edge(edges_array, x, y, width, height, visited, min_line_length)
                if line and len(line) >= 2:
                    # Convert line points to line segments
                    for i in range(len(line) - 1):
                        x1, y1 = line[i]
                        x2, y2 = line[i + 1]
                        lines.append((x1, y1, x2, y2))
    
    return lines


def _follow_edge(
    edges_array: Any,
    start_x: int,
    start_y: int,
    width: int,
    height: int,
    visited: set,
    min_length: int
) -> Optional[List[Tuple[int, int]]]:
    """
    Follow an edge starting from a pixel to form a line.
    
    Args:
        edges_array: PIL pixel access object
        start_x, start_y: Starting pixel coordinates
        width, height: Image dimensions
        visited: Set of visited pixels
        min_length: Minimum line length
        
    Returns:
        List of (x, y) points forming the line, or None if too short
    """
    line_points = [(start_x, start_y)]
    visited.add((start_x, start_y))
    
    current_x, current_y = start_x, start_y
    max_iterations = min_length * 2  # Prevent infinite loops
    
    for _ in range(max_iterations):
        # Check 8-connected neighbors
        found_next = False
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                
                nx, ny = current_x + dx, current_y + dy
                
                # Check bounds
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in visited and edges_array[nx, ny] != 0:
                        line_points.append((nx, ny))
                        visited.add((nx, ny))
                        current_x, current_y = nx, ny
                        found_next = True
                        break
            
            if found_next:
                break
        
        if not found_next:
            break
    
    # Return line if it's long enough
    if len(line_points) >= min_length:
        return line_points
    
    return None


def _snap_polygon_to_edges_pil(
    polygon: List[List[float]],
    edges_array: Any,
    lines: List[Tuple[int, int, int, int]],
    width: int,
    height: int,
    threshold: int
) -> Tuple[List[List[float]], Dict[str, Any]]:
    """
    Snap polygon vertices to nearby detected edges (PIL version).
    
    Args:
        polygon: List of [x, y] vertices
        edges_array: PIL pixel access object (binary edge map)
        lines: Detected lines from edge following
        width, height: Image dimensions
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
        best_point, best_distance = _find_nearest_edge_point_pil(
            x, y, edges_array, lines, width, height, threshold
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


def _find_nearest_edge_point_pil(
    x: int,
    y: int,
    edges_array: Any,
    lines: List[Tuple[int, int, int, int]],
    width: int,
    height: int,
    threshold: int
) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    Find the nearest edge point to a given coordinate (PIL version).
    
    Args:
        x, y: Coordinate to search from
        edges_array: PIL pixel access object
        lines: Detected lines
        width, height: Image dimensions
        threshold: Maximum search distance
        
    Returns:
        Tuple of (nearest_point, distance) or (None, inf)
    """
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
            point, distance = _point_to_line_segment_distance_pil(
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
                    if edges_array[nx, ny] != 0:
                        distance = math.sqrt(dx*dx + dy*dy)
                        if distance < best_distance:
                            best_point = (nx, ny)
                            best_distance = distance
    
    return best_point, best_distance


def _point_to_line_segment_distance_pil(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float
) -> Tuple[Tuple[int, int], float]:
    """
    Calculate distance from point to line segment and return closest point (PIL version).
    
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
        distance = math.sqrt((px - x1)**2 + (py - y1)**2)
        return (int(x1), int(y1)), distance
    
    # Calculate projection parameter
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    
    # Clamp to line segment
    t = max(0, min(1, t))
    
    # Calculate closest point
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Calculate distance
    distance = math.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    return (int(closest_x), int(closest_y)), distance


def _calculate_adaptive_threshold(edges_image: Image.Image) -> int:
    """
    Calculate adaptive threshold for edge binarization using image statistics.
    
    Uses a percentile-based approach to find optimal threshold that works
    across different image brightness levels.
    
    Args:
        edges_image: PIL Image with detected edges
        
    Returns:
        Optimal threshold value (0-255)
    """
    # Get pixel values
    pixels = list(edges_image.getdata())
    
    if not pixels:
        return 30  # Default fallback
    
    # Calculate statistics
    sorted_pixels = sorted(pixels)
    median = sorted_pixels[len(sorted_pixels) // 2]
    
    # Use median + offset as threshold
    # This adapts to the image's edge strength distribution
    threshold = int(median * 0.4 + 30)
    
    # Clamp to reasonable range
    threshold = max(20, min(80, threshold))
    
    return threshold


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

