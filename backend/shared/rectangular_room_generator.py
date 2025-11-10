"""Rectangular room generation by expanding from label center until hitting walls."""
from typing import List, Dict, Any, Tuple, Optional
import base64
from io import BytesIO
import logging

try:
    from PIL import Image, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageFilter = None

logger = logging.getLogger(__name__)

MAX_PROCESSING_SIZE = 3000


def generate_rectangular_room_from_label(
    label_center: List[float],
    image_base64: str,
    existing_rooms: List[Dict[str, Any]],
    canvas_bounds: List[float],
    image_format: str = 'png',
    step_size: int = 5
) -> Tuple[Optional[List[List[float]]], Optional[str]]:
    """
    Generate a rectangular room by expanding from label center until hitting walls.
    
    The rectangle grows outward in all 4 directions (N, S, E, W) from the center
    until it hits:
    - Detected edges (walls) from the blueprint
    - Boundaries of existing rooms
    - Canvas edges
    
    Args:
        label_center: [x, y] center position of label
        image_base64: Base64-encoded blueprint image
        existing_rooms: List of existing rooms (for boundary constraints)
        canvas_bounds: [x_min, y_min, x_max, y_max] canvas boundaries
        image_format: Image format (png, jpg, etc.)
        step_size: Pixel step size for expansion (default 5)
        
    Returns:
        Tuple of (rectangular_polygon, error_message)
    """
    if not PIL_AVAILABLE:
        return (None, "PIL (Pillow) is not available")
    
    # Convert to float in case we receive Decimal from DynamoDB
    x, y = float(label_center[0]), float(label_center[1])
    
    # Check if label center is outside canvas bounds
    if len(canvas_bounds) == 4:
        # Convert canvas_bounds to float in case of Decimal from DynamoDB
        x_min, y_min, x_max, y_max = [float(b) for b in canvas_bounds]
        if x < x_min or x > x_max or y < y_min or y > y_max:
            return (None, f"Label center [{x:.1f}, {y:.1f}] is outside canvas bounds")
    
    try:
        # Decode and prepare image
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        
        # Resize if needed
        original_width, original_height = image.size
        scale_factor = 1.0
        
        if max(original_width, original_height) > MAX_PROCESSING_SIZE:
            scale_factor = MAX_PROCESSING_SIZE / max(original_width, original_height)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Scale label center and canvas bounds
            x = int(x * scale_factor)
            y = int(y * scale_factor)
            if len(canvas_bounds) == 4:
                canvas_bounds = [
                    int(float(canvas_bounds[0]) * scale_factor),
                    int(float(canvas_bounds[1]) * scale_factor),
                    int(float(canvas_bounds[2]) * scale_factor),
                    int(float(canvas_bounds[3]) * scale_factor)
                ]
        
        width, height = image.size
        
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Detect edges
        image_size = max(width, height)
        blur_radius = max(0.5, min(1.5, image_size / 1000))
        blurred = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        edges = blurred.filter(ImageFilter.FIND_EDGES)
        
        # Calculate adaptive threshold
        threshold_value = _calculate_adaptive_threshold(edges)
        threshold_value = int(threshold_value * 1.2)
        threshold_value = min(threshold_value, 100)
        edges_binary = edges.point(lambda px: 255 if px > threshold_value else 0, mode='1')
        edges_array = edges_binary.load()
        
        # Scale canvas bounds if image was resized (already done above, but ensure they're set)
        if len(canvas_bounds) == 4:
            canvas_x_min = int(float(canvas_bounds[0]))
            canvas_y_min = int(float(canvas_bounds[1]))
            canvas_x_max = int(float(canvas_bounds[2]))
            canvas_y_max = int(float(canvas_bounds[3]))
        else:
            canvas_x_min = 0
            canvas_y_min = 0
            canvas_x_max = width
            canvas_y_max = height
        
        # Expand rectangle from center
        rect_bounds = _expand_rectangle_from_center(
            x, y,
            edges_array,
            existing_rooms,
            width, height,
            canvas_x_min, canvas_y_min, canvas_x_max, canvas_y_max,
            scale_factor,
            step_size
        )
        
        if not rect_bounds:
            return (None, "Could not determine room boundaries")
        
        x_min, y_min, x_max, y_max = rect_bounds
        
        # Scale back to original coordinates if needed
        if scale_factor < 1.0:
            x_min = x_min / scale_factor
            y_min = y_min / scale_factor
            x_max = x_max / scale_factor
            y_max = y_max / scale_factor
        
        # Create rectangular polygon
        polygon = [
            [x_min, y_min],
            [x_max, y_min],
            [x_max, y_max],
            [x_min, y_max]
        ]
        
        return (polygon, None)
        
    except Exception as e:
        logger.error(f"Error generating rectangular room: {str(e)}", exc_info=True)
        return (None, f"Error during rectangular expansion: {str(e)}")


def _expand_rectangle_from_center(
    center_x: int,
    center_y: int,
    edges_array: Any,
    existing_rooms: List[Dict[str, Any]],
    width: int,
    height: int,
    canvas_x_min: int,
    canvas_y_min: int,
    canvas_x_max: int,
    canvas_y_max: int,
    scale_factor: float,
    step_size: int,
    edge_tolerance: int = 3  # Pixels of tolerance for edge detection noise
) -> Optional[Tuple[int, int, int, int]]:
    """
    Expand a rectangle from center point until hitting boundaries.
    
    Returns:
        Tuple of (x_min, y_min, x_max, y_max) or None if expansion fails
    """
    # Start with a small rectangle around center (ensure all are integers)
    x_min = int(max(canvas_x_min, center_x - step_size))
    x_max = int(min(canvas_x_max, center_x + step_size))
    y_min = int(max(canvas_y_min, center_y - step_size))
    y_max = int(min(canvas_y_max, center_y + step_size))
    
    # Expand in each direction until hitting a boundary
    max_iterations = max(width, height) // step_size  # Safety limit
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        expanded = False
        
        # Try to expand North (decrease y_min)
        if y_min > canvas_y_min:
            # Check if we can expand north
            can_expand_north = True
            check_y = int(y_min - step_size)
            # Check multiple points across the edge with tolerance
            edge_pixels_found = 0
            total_checks = 0
            for check_x in range(x_min, x_max + 1, max(1, step_size // 2)):
                if check_x < 0 or check_x >= width or check_y < 0 or check_y >= height:
                    can_expand_north = False
                    break
                total_checks += 1
                # Check for edge with tolerance (check nearby pixels too)
                has_edge = False
                for offset_x in range(-edge_tolerance, edge_tolerance + 1):
                    for offset_y in range(-edge_tolerance, edge_tolerance + 1):
                        tx = check_x + offset_x
                        ty = check_y + offset_y
                        if 0 <= tx < width and 0 <= ty < height:
                            if edges_array[tx, ty] != 0:
                                has_edge = True
                                break
                    if has_edge:
                        break
                if has_edge:
                    edge_pixels_found += 1
                # Check for existing room
                if _is_point_in_existing_room(check_x, check_y, existing_rooms, scale_factor):
                    can_expand_north = False
                    break
            # Allow expansion if less than 30% of checked pixels have edges (noise tolerance)
            if total_checks > 0 and edge_pixels_found / total_checks > 0.3:
                can_expand_north = False
            
            if can_expand_north:
                y_min = int(max(canvas_y_min, y_min - step_size))
                expanded = True
        
        # Try to expand South (increase y_max)
        if y_max < canvas_y_max:
            can_expand_south = True
            check_y = int(y_max + step_size)
            edge_pixels_found = 0
            total_checks = 0
            for check_x in range(x_min, x_max + 1, max(1, step_size // 2)):
                if check_x < 0 or check_x >= width or check_y < 0 or check_y >= height:
                    can_expand_south = False
                    break
                total_checks += 1
                has_edge = False
                for offset_x in range(-edge_tolerance, edge_tolerance + 1):
                    for offset_y in range(-edge_tolerance, edge_tolerance + 1):
                        tx = check_x + offset_x
                        ty = check_y + offset_y
                        if 0 <= tx < width and 0 <= ty < height:
                            if edges_array[tx, ty] != 0:
                                has_edge = True
                                break
                    if has_edge:
                        break
                if has_edge:
                    edge_pixels_found += 1
                if _is_point_in_existing_room(check_x, check_y, existing_rooms, scale_factor):
                    can_expand_south = False
                    break
            if total_checks > 0 and edge_pixels_found / total_checks > 0.3:
                can_expand_south = False
            
            if can_expand_south:
                y_max = int(min(canvas_y_max, y_max + step_size))
                expanded = True
        
        # Try to expand East (increase x_max)
        if x_max < canvas_x_max:
            can_expand_east = True
            check_x = int(x_max + step_size)
            edge_pixels_found = 0
            total_checks = 0
            for check_y in range(y_min, y_max + 1, max(1, step_size // 2)):
                if check_x < 0 or check_x >= width or check_y < 0 or check_y >= height:
                    can_expand_east = False
                    break
                total_checks += 1
                has_edge = False
                for offset_x in range(-edge_tolerance, edge_tolerance + 1):
                    for offset_y in range(-edge_tolerance, edge_tolerance + 1):
                        tx = check_x + offset_x
                        ty = check_y + offset_y
                        if 0 <= tx < width and 0 <= ty < height:
                            if edges_array[tx, ty] != 0:
                                has_edge = True
                                break
                    if has_edge:
                        break
                if has_edge:
                    edge_pixels_found += 1
                if _is_point_in_existing_room(check_x, check_y, existing_rooms, scale_factor):
                    can_expand_east = False
                    break
            if total_checks > 0 and edge_pixels_found / total_checks > 0.3:
                can_expand_east = False
            
            if can_expand_east:
                x_max = int(min(canvas_x_max, x_max + step_size))
                expanded = True
        
        # Try to expand West (decrease x_min)
        if x_min > canvas_x_min:
            can_expand_west = True
            check_x = int(x_min - step_size)
            edge_pixels_found = 0
            total_checks = 0
            for check_y in range(y_min, y_max + 1, max(1, step_size // 2)):
                if check_x < 0 or check_x >= width or check_y < 0 or check_y >= height:
                    can_expand_west = False
                    break
                total_checks += 1
                has_edge = False
                for offset_x in range(-edge_tolerance, edge_tolerance + 1):
                    for offset_y in range(-edge_tolerance, edge_tolerance + 1):
                        tx = check_x + offset_x
                        ty = check_y + offset_y
                        if 0 <= tx < width and 0 <= ty < height:
                            if edges_array[tx, ty] != 0:
                                has_edge = True
                                break
                    if has_edge:
                        break
                if has_edge:
                    edge_pixels_found += 1
                if _is_point_in_existing_room(check_x, check_y, existing_rooms, scale_factor):
                    can_expand_west = False
                    break
            if total_checks > 0 and edge_pixels_found / total_checks > 0.3:
                can_expand_west = False
            
            if can_expand_west:
                x_min = int(max(canvas_x_min, x_min - step_size))
                expanded = True
        
        # If we couldn't expand in any direction, we're done
        if not expanded:
            break
    
    # Validate rectangle
    if x_max <= x_min or y_max <= y_min:
        return None
    
    if x_min < canvas_x_min or x_max > canvas_x_max or y_min < canvas_y_min or y_max > canvas_y_max:
        return None
    
    return (x_min, y_min, x_max, y_max)


def _is_point_in_existing_room(
    x: int,
    y: int,
    existing_rooms: List[Dict[str, Any]],
    scale_factor: float
) -> bool:
    """Check if point is inside any existing room."""
    for room in existing_rooms:
        polygon = room.get('polygon')
        if polygon:
            # Convert Decimal to float and scale polygon if needed
            if scale_factor < 1.0:
                scaled_polygon = [[float(p[0]) * scale_factor, float(p[1]) * scale_factor] for p in polygon]
            else:
                scaled_polygon = [[float(p[0]), float(p[1])] for p in polygon]
            
            if _is_point_in_polygon(x, y, scaled_polygon):
                return True
        else:
            # Use bounding box
            bbox = room.get('bounding_box', [])
            if len(bbox) == 4:
                # Convert Decimal to float
                if scale_factor < 1.0:
                    bbox = [float(b) * scale_factor for b in bbox]
                else:
                    bbox = [float(b) for b in bbox]
                x_min, y_min, x_max, y_max = bbox
                if x_min <= x <= x_max and y_min <= y <= y_max:
                    return True
    return False


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


def _calculate_adaptive_threshold(edges_image) -> int:
    """Calculate adaptive threshold for edge detection."""
    import statistics
    
    # Sample edge values from image
    width, height = edges_image.size
    sample_size = min(1000, width * height)
    step = max(1, (width * height) // sample_size)
    
    values = []
    pixels = edges_image.load()
    for y in range(0, height, step):
        for x in range(0, width, step):
            values.append(pixels[x, y])
    
    if not values:
        return 50  # Default threshold
    
    # Use median + standard deviation as threshold
    median = statistics.median(values)
    if len(values) > 1:
        std_dev = statistics.stdev(values)
        threshold = int(median + std_dev * 0.5)
    else:
        threshold = int(median)
    
    return max(10, min(100, threshold))

