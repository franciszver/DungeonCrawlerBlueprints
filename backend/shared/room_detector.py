"""Core room detection logic."""
import json
import base64
from typing import Dict, Any, List
import sys
import os

# Add shared module to path if not already there
shared_path = os.path.join(os.path.dirname(__file__))
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from openrouter_client import detect_rooms_from_image, normalize_coordinates


def process_blueprint_image(image_data: bytes, image_format: str = 'png') -> Dict[str, Any]:
    """
    Process a blueprint image and detect rooms.
    
    Args:
        image_data: Raw image bytes
        image_format: Image format (png, jpg, etc.)
    
    Returns:
        Dictionary with detection results and metadata
    """
    import time
    start_time = time.time()
    
    try:
        # Validate image size
        image_size_mb = len(image_data) / (1024 * 1024)
        if image_size_mb > 10:
            return {
                "success": False,
                "error": f"Image too large: {image_size_mb:.2f}MB (max 10MB)",
                "error_code": "IMAGE_TOO_LARGE",
                "rooms": []
            }
        
        # Convert image to base64 (no PIL needed)
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Estimate dimensions (will be determined by OpenRouter)
        image_width, image_height = 1000, 1000  # Default normalized dimensions
        
        # Detect rooms using OpenRouter
        detection_result = detect_rooms_from_image(image_base64, image_format)
        
        if not detection_result.get("success", False):
            return {
                **detection_result,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "image_dimensions": {"width": image_width, "height": image_height}
            }
        
        rooms = detection_result.get("rooms", [])
        
        # Normalize coordinates if they're in pixel space
        # Check if coordinates are already normalized (0-1000 range)
        if rooms:
            sample_bbox = rooms[0].get('bounding_box', [])
            if sample_bbox and max(sample_bbox) > 1000:
                # Coordinates are in pixel space, normalize them
                rooms = normalize_coordinates(rooms, image_width, image_height)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "rooms": rooms,
            "processing_time_ms": processing_time_ms,
            "image_dimensions": {"width": image_width, "height": image_height},
            "model_used": detection_result.get("model_used", "unknown"),
            "metadata": {
                "model_used": detection_result.get("model_used", "unknown"),
                "processing_time_ms": processing_time_ms,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Processing error: {str(e)}",
            "error_code": "PROCESSING_ERROR",
            "rooms": [],
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }

