"""Core room detection logic with multi-model validation."""
import json
import base64
from typing import Dict, Any, List
import sys
import os

# Add shared module to path if not already there
shared_path = os.path.join(os.path.dirname(__file__))
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from openrouter_client import detect_rooms_with_validation, normalize_coordinates
from training_data_loader import get_training_data_loader
from detection_validator import validate_and_enhance_detection, should_retry_with_strict_mode


def process_blueprint_image(image_data: bytes, image_format: str = 'png') -> Dict[str, Any]:
    """
    Process a blueprint image and detect rooms with multi-model validation.
    
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
                "rooms": [],
                "doors": []
            }
        
        # Convert image to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Load few-shot training examples
        training_loader = get_training_data_loader()
        few_shot_examples = training_loader.get_few_shot_examples()
        
        if few_shot_examples:
            print(f"Using {len(few_shot_examples)} few-shot training examples")
        
        # Detect rooms using multi-model validation
        detection_result = detect_rooms_with_validation(
            image_base64, 
            image_format,
            few_shot_examples=few_shot_examples
        )
        
        if not detection_result.get("success", False):
            return {
                **detection_result,
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "image_dimensions": {"width": 1000, "height": 1000}
            }
        
        rooms = detection_result.get("rooms", [])
        doors = detection_result.get("doors", [])
        detection_metadata = detection_result.get("detection_metadata", {})
        
        # Normalize coordinates if they're in pixel space
        if rooms:
            sample_bbox = rooms[0].get('bounding_box', [])
            if sample_bbox and max(sample_bbox) > 1000:
                # Coordinates are in pixel space, normalize them
                rooms = normalize_coordinates(rooms, 1000, 1000)
        
        # Validate detection results
        rooms, validation_results = validate_and_enhance_detection(rooms, doors, image_base64)
        
        # If validation fails and we haven't retried yet, retry with strict mode
        if should_retry_with_strict_mode(validation_results) and detection_metadata.get("retry_count", 0) == 0:
            print("Validation failed, retrying with strict mode...")
            
            # Retry detection with strict mode enabled
            retry_result = detect_rooms_with_validation(
                image_base64,
                image_format,
                few_shot_examples=few_shot_examples,
                strict_mode=True
            )
            
            if retry_result.get("success", False):
                retry_rooms = retry_result.get("rooms", [])
                retry_doors = retry_result.get("doors", [])
                
                # Normalize if needed
                if retry_rooms:
                    sample_bbox = retry_rooms[0].get('bounding_box', [])
                    if sample_bbox and max(sample_bbox) > 1000:
                        retry_rooms = normalize_coordinates(retry_rooms, 1000, 1000)
                
                # Validate retry results
                retry_rooms, retry_validation = validate_and_enhance_detection(retry_rooms, retry_doors, image_base64)
                
                # Use retry results if they're better
                if retry_validation.get("coverage_score", 0) > validation_results.get("coverage_score", 0):
                    rooms = retry_rooms
                    doors = retry_doors
                    detection_metadata = retry_result.get("detection_metadata", {})
                    detection_metadata["strict_mode_retry"] = True
                    validation_results = retry_validation
                    print(f"Strict mode improved coverage from {validation_results.get('coverage_score', 0):.1%} to {retry_validation.get('coverage_score', 0):.1%}")
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Build comprehensive metadata
        metadata = {
            "models_used": detection_metadata.get("models_used", []),
            "retry_count": detection_metadata.get("retry_count", 0),
            "primary_confidence": detection_metadata.get("primary_confidence", 0.0),
            "final_confidence": detection_metadata.get("final_confidence", 0.0),
            "detection_type": detection_metadata.get("detection_type", "bounding_box"),
            "primary_model": detection_metadata.get("primary_model", "unknown"),
            "processing_time_ms": processing_time_ms,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "few_shot_examples_used": len(few_shot_examples) if few_shot_examples else 0,
            "validation": {
                "coverage_score": validation_results.get("coverage_score", 0.0),
                "validation_passed": validation_results.get("validation_passed", False),
                "warnings": validation_results.get("warnings", []),
                "strict_mode_retry": detection_metadata.get("strict_mode_retry", False)
            }
        }
        
        return {
            "success": True,
            "rooms": rooms,
            "doors": doors,
            "confidence": detection_result.get("confidence", 0.0),
            "processing_time_ms": processing_time_ms,
            "image_dimensions": {"width": 1000, "height": 1000},
            "metadata": metadata
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Processing error: {str(e)}",
            "error_code": "PROCESSING_ERROR",
            "rooms": [],
            "doors": [],
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }

