"""Core room detection logic with multi-model validation."""
import json
import base64
from typing import Dict, Any, List
import sys
import os
import requests

# Add shared module to path if not already there
shared_path = os.path.join(os.path.dirname(__file__))
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from openrouter_client import detect_rooms_with_validation, normalize_coordinates
from training_data_loader import get_training_data_loader
from detection_validator import validate_and_enhance_detection, should_retry_with_strict_mode
from edge_detector import refine_room_boundaries
from text_extractor import (
    extract_text_labels_from_blueprint, 
    match_text_labels_to_rooms,
    add_numerical_differentiators,
    filter_room_labels
)
from config import ENABLE_TEXT_EXTRACTION, ENABLE_AUTO_EDGE_REFINEMENT, MAX_PROCESSING_TIME_SECONDS


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
                "image_dimensions": {"width": actual_image_width, "height": actual_image_height}
            }
        
        rooms = detection_result.get("rooms", [])
        doors = detection_result.get("doors", [])
        detection_metadata = detection_result.get("detection_metadata", {})
        
        # Get actual image dimensions for normalization
        try:
            from PIL import Image
            from io import BytesIO
            image_for_size = Image.open(BytesIO(image_data))
            actual_image_width, actual_image_height = image_for_size.size
        except Exception:
            # Fallback to 1000x1000 if we can't determine size
            actual_image_width, actual_image_height = 1000, 1000
        
        # Normalize coordinates if they're in pixel space
        if rooms:
            sample_bbox = rooms[0].get('bounding_box', [])
            if sample_bbox and max(sample_bbox) > 1000:
                # Coordinates are in pixel space, normalize them using actual image dimensions
                rooms = normalize_coordinates(rooms, actual_image_width, actual_image_height)
        
        # Validate detection results
        rooms, validation_results = validate_and_enhance_detection(rooms, doors, image_base64)
        
        # Track time after detection to see how much time remains for refinement steps
        detection_time = time.time() - start_time
        time_remaining = MAX_PROCESSING_TIME_SECONDS - detection_time
        
        # Extract text labels from blueprint and match to rooms (with timeout and time check)
        text_labels = []
        
        if ENABLE_TEXT_EXTRACTION and rooms and image_base64 and time_remaining > 8:
            try:
                print(f"Extracting text labels from blueprint (time remaining: {time_remaining:.1f}s)...")
                # Use a faster model and shorter timeout for text extraction
                raw_text_labels = extract_text_labels_from_blueprint(image_base64, image_format)
                if raw_text_labels:
                    # Filter to only room labels
                    text_labels = filter_room_labels(raw_text_labels)
                    # Add numerical differentiators for duplicates
                    text_labels = add_numerical_differentiators(text_labels)
                    # Match labels to detected rooms
                    rooms = match_text_labels_to_rooms(rooms, text_labels)
                    print(f"Extracted {len(text_labels)} room labels, matched {len([r for r in rooms if r.get('name_source') == 'blueprint_text'])} room(s) to blueprint text labels")
                else:
                    text_labels = []
            except requests.Timeout:
                print("Text extraction timed out (non-fatal), continuing without text labels")
                text_labels = []
            except Exception as e:
                print(f"Text extraction failed (non-fatal): {str(e)}")
                # Continue with AI-detected names if extraction fails
                text_labels = []
        elif not ENABLE_TEXT_EXTRACTION:
            print("Text extraction disabled (ENABLE_TEXT_EXTRACTION=false)")
            text_labels = []
        elif time_remaining <= 8:
            print(f"Skipping text extraction (insufficient time remaining: {time_remaining:.1f}s)")
            text_labels = []
        
        # Automatically refine room boundaries to match blueprint using edge detection
        elapsed_time = time.time() - start_time
        time_remaining = MAX_PROCESSING_TIME_SECONDS - elapsed_time
        
        if ENABLE_AUTO_EDGE_REFINEMENT and rooms and image_base64 and time_remaining > 5:
            try:
                print(f"Automatically refining room boundaries (time remaining: {time_remaining:.1f}s)...")
                refinement_result = refine_room_boundaries(image_base64, rooms, threshold=25, image_format=image_format)
                if refinement_result.get('success') and refinement_result.get('refined_rooms'):
                    rooms = refinement_result['refined_rooms']
                    print(f"Refined {refinement_result.get('stats', {}).get('refined_rooms', 0)} room(s) to match blueprint boundaries")
            except Exception as e:
                print(f"Edge detection refinement failed (non-fatal): {str(e)}")
                # Continue with original rooms if refinement fails
        elif not ENABLE_AUTO_EDGE_REFINEMENT:
            print("Edge refinement disabled (ENABLE_AUTO_EDGE_REFINEMENT=false)")
        elif time_remaining <= 5:
            print(f"Skipping edge refinement (insufficient time remaining: {time_remaining:.1f}s)")
        
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
                
                # Normalize if needed (use same image dimensions)
                if retry_rooms:
                    sample_bbox = retry_rooms[0].get('bounding_box', [])
                    if sample_bbox and max(sample_bbox) > 1000:
                        retry_rooms = normalize_coordinates(retry_rooms, actual_image_width, actual_image_height)
                
                # Validate retry results
                retry_rooms, retry_validation = validate_and_enhance_detection(retry_rooms, retry_doors, image_base64)
                
                # Extract text labels for retry rooms too (if not already extracted and time permits)
                elapsed_time = time.time() - start_time
                time_remaining = MAX_PROCESSING_TIME_SECONDS - elapsed_time
                
                if ENABLE_TEXT_EXTRACTION and retry_rooms and image_base64 and not text_labels and time_remaining > 8:
                    try:
                        retry_text_labels = extract_text_labels_from_blueprint(image_base64, image_format)
                        if retry_text_labels:
                            text_labels = retry_text_labels
                            retry_rooms = match_text_labels_to_rooms(retry_rooms, text_labels)
                    except Exception as e:
                        print(f"Text extraction failed for retry (non-fatal): {str(e)}")
                
                # Automatically refine retry rooms too (if time permits)
                elapsed_time = time.time() - start_time
                time_remaining = MAX_PROCESSING_TIME_SECONDS - elapsed_time
                
                if ENABLE_AUTO_EDGE_REFINEMENT and retry_rooms and image_base64 and time_remaining > 5:
                    try:
                        refinement_result = refine_room_boundaries(image_base64, retry_rooms, threshold=25, image_format=image_format)
                        if refinement_result.get('success') and refinement_result.get('refined_rooms'):
                            retry_rooms = refinement_result['refined_rooms']
                    except Exception as e:
                        print(f"Edge detection refinement failed for retry (non-fatal): {str(e)}")
                
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
            "text_labels": text_labels,  # Store extracted labels for later use
            "retry_count": detection_metadata.get("retry_count", 0),
            "primary_confidence": detection_metadata.get("primary_confidence", 0.0),
            "final_confidence": detection_metadata.get("final_confidence", 0.0),
            "detection_type": detection_metadata.get("detection_type", "bounding_box"),
            "primary_model": detection_metadata.get("primary_model", "unknown"),
            "processing_time_ms": processing_time_ms,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "few_shot_examples_used": len(few_shot_examples) if few_shot_examples else 0,
            "text_labels": text_labels,  # Store text labels for room placement
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

