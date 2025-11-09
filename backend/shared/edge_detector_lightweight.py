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
MAX_PROCESSING_SIZE = 3000  # Increased for better accuracy (was 2000)
MIN_PROCESSING_SIZE = 100  # Minimum dimension (don't resize smaller images)


def refine_room_boundaries_lightweight(
    image_base64: str,
    rooms: List[Dict[str, Any]],
    threshold: int = 25,  # Reduced from 50 for more precise snapping
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
        
        # Calculate adaptive blur radius - reduced for thinner, more precise edges
        # Less blur = thinner edges = better alignment
        image_size = max(image.size)
        # Reduced blur: max 1.5 instead of 2.5, and less aggressive scaling
        blur_radius = max(0.5, min(1.5, image_size / 1000))
        
        # Apply minimal Gaussian blur to reduce noise without thickening edges
        blurred = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Detect edges using FIND_EDGES filter (Sobel-like)
        edges = blurred.filter(ImageFilter.FIND_EDGES)
        
        # Calculate adaptive threshold using image statistics
        threshold_value = _calculate_adaptive_threshold(edges)
        
        # Use more aggressive thresholding to get cleaner, thinner edges
        # Increase threshold slightly to reduce noise while keeping edges
        threshold_value = int(threshold_value * 1.2)
        threshold_value = min(threshold_value, 100)  # Cap at 100
        
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
    min_line_length: int = 30  # Reduced from 50 to detect shorter wall segments
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
    
    # If no line found, search for nearest edge pixel with more precise search
    if best_point is None:
        # Use smaller search radius for more precise snapping
        search_radius = min(threshold, 50)  # Reduced from 100
        
        # Search in expanding circles for better precision
        for radius in range(1, search_radius + 1):
            found = False
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    # Only check pixels on the circle perimeter for efficiency
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    
                    nx, ny = x + dx, y + dy
                    
                    # Check bounds
                    if 0 <= nx < width and 0 <= ny < height:
                        # Check if this pixel is an edge
                        if edges_array[nx, ny] != 0:
                            distance = math.sqrt(dx*dx + dy*dy)
                            if distance < best_distance and distance < threshold:
                                best_point = (nx, ny)
                                best_distance = distance
                                found = True
                                break
                if found:
                    break
            if found and best_distance < threshold:
                break
    
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
    
    # Use median + offset as threshold - adjusted for better edge detection
    # Lower multiplier for more sensitive edge detection
    threshold = int(median * 0.3 + 25)
    
    # Clamp to reasonable range - slightly lower for better sensitivity
    threshold = max(15, min(70, threshold))
    
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


def detect_room_from_label_center(
    label_center: List[float],
    image_base64: str,
    existing_rooms: List[Dict[str, Any]],
    canvas_bounds: List[float],
    image_format: str = 'png',
    timeout_seconds: int = 5
) -> Tuple[Optional[List[List[float]]], Optional[str]]:
    """
    Detect room boundaries using flood-fill from label center point.
    
    Expands outward from center until hitting:
    - Detected edges from blueprint
    - Boundaries of surrounding rooms
    - Canvas edge
    
    Args:
        label_center: [x, y] center position of label
        image_base64: Base64-encoded blueprint image
        existing_rooms: List of existing rooms (for boundary constraints)
        canvas_bounds: [x_min, y_min, x_max, y_max] canvas boundaries
        image_format: Image format (png, jpg, etc.)
        timeout_seconds: Maximum time to spend on flood-fill (default 5s)
        
    Returns:
        Tuple of (polygon, error_message). Polygon is None if boundaries cannot be determined.
    """
    import time
    start_time = time.time()
    
    if not PIL_AVAILABLE:
        return (None, "PIL (Pillow) is not available")
    
    # Check if label center is outside canvas bounds
    x, y = label_center
    if len(canvas_bounds) == 4:
        x_min, y_min, x_max, y_max = canvas_bounds
        if x < x_min or x > x_max or y < y_min or y > y_max:
            return (None, f"Label center [{x:.1f}, {y:.1f}] is outside canvas bounds")
    
    try:
        # Decode and prepare image
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        
        # Resize if needed (same logic as refine_room_boundaries_lightweight)
        original_width, original_height = image.size
        scale_factor = 1.0
        
        if max(original_width, original_height) > MAX_PROCESSING_SIZE:
            scale_factor = MAX_PROCESSING_SIZE / max(original_width, original_height)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Scale label center
            x = int(x * scale_factor)
            y = int(y * scale_factor)
        
        width, height = image.size
        
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Detect edges (same process as refine_room_boundaries_lightweight)
        image_size = max(width, height)
        blur_radius = max(0.5, min(1.5, image_size / 1000))
        blurred = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        edges = blurred.filter(ImageFilter.FIND_EDGES)
        threshold_value = _calculate_adaptive_threshold(edges)
        threshold_value = int(threshold_value * 1.2)
        threshold_value = min(threshold_value, 100)
        edges_binary = edges.point(lambda px: 255 if px > threshold_value else 0, mode='1')
        
        # Convert to pixel array for faster access
        edges_array = edges_binary.load()
        
        # Scale canvas bounds if image was resized
        if scale_factor < 1.0:
            canvas_x_min = int(canvas_bounds[0] * scale_factor) if len(canvas_bounds) >= 1 else 0
            canvas_y_min = int(canvas_bounds[1] * scale_factor) if len(canvas_bounds) >= 2 else 0
            canvas_x_max = int(canvas_bounds[2] * scale_factor) if len(canvas_bounds) >= 3 else width
            canvas_y_max = int(canvas_bounds[3] * scale_factor) if len(canvas_bounds) >= 4 else height
        else:
            canvas_x_min = canvas_bounds[0] if len(canvas_bounds) >= 1 else 0
            canvas_y_min = canvas_bounds[1] if len(canvas_bounds) >= 2 else 0
            canvas_x_max = canvas_bounds[2] if len(canvas_bounds) >= 3 else width
            canvas_y_max = canvas_bounds[3] if len(canvas_bounds) >= 4 else height
        
        # Perform flood-fill from center
        polygon, error_msg = _grow_region_from_center(
            x, y,
            edges_array,
            existing_rooms,
            width, height,
            canvas_x_min, canvas_y_min, canvas_x_max, canvas_y_max,
            scale_factor,
            start_time,
            timeout_seconds
        )
        
        if polygon and scale_factor < 1.0:
            # Scale polygon back to original coordinates
            polygon = [[p[0] / scale_factor, p[1] / scale_factor] for p in polygon]
        
        return (polygon, error_msg)
        
    except Exception as e:
        logger.error(f"Error detecting room from label center: {str(e)}", exc_info=True)
        return (None, f"Error during flood-fill: {str(e)}")


def _grow_region_from_center(
    start_x: int,
    start_y: int,
    edges_array: Any,
    existing_rooms: List[Dict[str, Any]],
    width: int,
    height: int,
    canvas_x_min: int,
    canvas_y_min: int,
    canvas_x_max: int,
    canvas_y_max: int,
    scale_factor: float,
    start_time: float,
    timeout_seconds: int
) -> Tuple[Optional[List[List[float]]], Optional[str]]:
    """
    Grow region from center point using flood-fill (5px step size).
    
    Stops when hitting:
    - Edge pixels (from edges_array)
    - Room boundaries (from existing_rooms)
    - Canvas edges
    
    Args:
        start_x, start_y: Starting coordinates
        edges_array: PIL pixel access object (binary edge map)
        existing_rooms: List of existing rooms
        width, height: Image dimensions
        canvas_x_min, canvas_y_min, canvas_x_max, canvas_y_max: Canvas boundaries
        scale_factor: Scale factor if image was resized
        start_time: Start time for timeout checking
        timeout_seconds: Maximum time to spend
        
    Returns:
        Tuple of (polygon, error_message)
    """
    import time
    STEP_SIZE = 5  # 5px step size as specified
    
    # Ensure start point is within bounds
    start_x = max(0, min(width - 1, start_x))
    start_y = max(0, min(height - 1, start_y))
    
    # Check timeout
    if time.time() - start_time > timeout_seconds:
        return (None, f"Flood-fill timeout after {timeout_seconds}s")
    
    # Track visited pixels and region boundary
    visited = set()
    region_pixels = set()
    boundary_pixels = set()
    
    # Queue for flood-fill (BFS)
    queue = [(start_x, start_y)]
    visited.add((start_x, start_y))
    region_pixels.add((start_x, start_y))
    
    # Directions for 8-connected neighbors (but with 5px step)
    directions = [
        (STEP_SIZE, 0), (-STEP_SIZE, 0), (0, STEP_SIZE), (0, -STEP_SIZE),
        (STEP_SIZE, STEP_SIZE), (-STEP_SIZE, -STEP_SIZE),
        (STEP_SIZE, -STEP_SIZE), (-STEP_SIZE, STEP_SIZE)
    ]
    
    while queue:
        # Check timeout periodically
        if time.time() - start_time > timeout_seconds:
            break
        
        current_x, current_y = queue.pop(0)
        
        # Check all directions
        for dx, dy in directions:
            nx, ny = current_x + dx, current_y + dy
            
            # Check bounds
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                # Hit canvas edge - add to boundary
                boundary_pixels.add((current_x, current_y))
                continue
            
            # Check canvas bounds
            if nx < canvas_x_min or nx > canvas_x_max or ny < canvas_y_min or ny > canvas_y_max:
                # Hit canvas boundary - add to boundary
                boundary_pixels.add((current_x, current_y))
                continue
            
            if (nx, ny) in visited:
                continue
            
            # Check if this pixel is an edge
            if edges_array[nx, ny] != 0:
                # Hit edge - add current pixel to boundary
                boundary_pixels.add((current_x, current_y))
                continue
            
            # Check if this pixel is inside an existing room
            pixel_in_room = False
            for room in existing_rooms:
                polygon = room.get('polygon')
                if polygon:
                    # Scale polygon if needed
                    if scale_factor < 1.0:
                        scaled_polygon = [[p[0] * scale_factor, p[1] * scale_factor] for p in polygon]
                    else:
                        scaled_polygon = polygon
                    
                    if _is_point_in_polygon(nx, ny, scaled_polygon):
                        pixel_in_room = True
                        break
                else:
                    # Use bounding box
                    bbox = room.get('bounding_box', [])
                    if len(bbox) == 4:
                        if scale_factor < 1.0:
                            bbox = [b * scale_factor for b in bbox]
                        x_min, y_min, x_max, y_max = bbox
                        if x_min <= nx <= x_max and y_min <= ny <= y_max:
                            pixel_in_room = True
                            break
            
            if pixel_in_room:
                # Hit room boundary - add current pixel to boundary
                boundary_pixels.add((current_x, current_y))
                continue
            
            # This pixel is part of the region
            visited.add((nx, ny))
            region_pixels.add((nx, ny))
            queue.append((nx, ny))
    
    # Convert boundary pixels to polygon
    if not boundary_pixels:
        return (None, "No boundaries detected - cannot determine room shape")
    
    # Create polygon from boundary pixels using convex hull or simple ordering
    polygon = _boundary_pixels_to_polygon(boundary_pixels)
    
    if not polygon or len(polygon) < 3:
        return (None, "Insufficient boundary points to form polygon")
    
    return (polygon, None)


def _is_point_in_polygon(x: float, y: float, polygon: List[List[float]]) -> bool:
    """Check if point is inside polygon using ray casting algorithm."""
    if len(polygon) < 3:
        return False
    
    inside = False
    j = len(polygon) - 1
    
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside


def _boundary_pixels_to_polygon(boundary_pixels: set) -> List[List[float]]:
    """
    Convert boundary pixels to a polygon.
    Uses a simple approach: find the convex hull of boundary pixels.
    """
    if not boundary_pixels or len(boundary_pixels) < 3:
        return []
    
    # Convert to list and find convex hull
    points = list(boundary_pixels)
    
    # Simple convex hull algorithm (Graham scan simplified)
    # Sort points by x, then y
    points.sort(key=lambda p: (p[0], p[1]))
    
    # For simplicity, use a bounding box approach and create a rectangle
    # In a full implementation, you'd use a proper convex hull algorithm
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]
    
    x_min, x_max = min(x_coords), max(x_coords)
    y_min, y_max = min(y_coords), max(y_coords)
    
    # Create a rectangle polygon (can be improved with proper convex hull)
    polygon = [
        [x_min, y_min],
        [x_max, y_min],
        [x_max, y_max],
        [x_min, y_max]
    ]
    
    return polygon


def _validate_room_boundaries(
    polygon: Optional[List[List[float]]],
    existing_rooms: List[Dict[str, Any]],
    edges_detected: bool
) -> Tuple[bool, Optional[str]]:
    """
    Validate that room boundaries are accounted for.
    
    Args:
        polygon: Detected room polygon (None if not detected)
        existing_rooms: List of existing rooms
        edges_detected: Whether edges were detected in the region
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if polygon is None:
        return (False, "Cannot determine room boundaries")
    
    if len(polygon) < 3:
        return (False, "Insufficient boundary points")
    
    # Check if we have edges or surrounding rooms
    if not edges_detected and not existing_rooms:
        return (False, "No edges detected and no surrounding rooms to use as boundaries")
    
    return (True, None)

