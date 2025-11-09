"""OpenRouter API client for room detection with multi-model validation."""
import json
import requests
import base64
from typing import Dict, Any, List, Optional, Tuple
import sys
import os

# Add shared module to path if not already there
shared_path = os.path.dirname(__file__)
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from config import (
    OPENROUTER_API_URL, OPENROUTER_MODEL, get_openrouter_api_key,
    VALIDATION_MODELS, CONFIDENCE_THRESHOLD, MAX_RETRY_ATTEMPTS,
    ENABLE_POLYGON_DETECTION, ENABLE_DOOR_DETECTION, COORDINATE_MAX
)


def detect_rooms_with_validation(image_base64: str, image_format: str = 'png',
                                 few_shot_examples: Optional[List[Dict]] = None,
                                 strict_mode: bool = False) -> Dict[str, Any]:
    """
    Detect rooms with multi-model validation and confidence-based retry.
    
    Args:
        image_base64: Base64-encoded image data
        image_format: Image format (png, jpg, etc.)
        few_shot_examples: Optional list of training examples for few-shot learning
        strict_mode: Whether to use strict mode for maximum accuracy
        
    Returns:
        Dictionary with detected rooms, metadata, and confidence scores
    """
    api_key = get_openrouter_api_key()
    
    # Track models used and attempts
    models_used = []
    retry_count = 0
    best_result = None
    best_confidence = 0.0
    
    # Try primary model first (with polygon detection if enabled)
    primary_result = _detect_with_model(
        OPENROUTER_MODEL, 
        image_base64, 
        image_format,
        api_key,
        few_shot_examples,
        enable_polygon=ENABLE_POLYGON_DETECTION,
        enable_doors=ENABLE_DOOR_DETECTION,
        strict_mode=strict_mode
    )
    
    models_used.append(OPENROUTER_MODEL)
    primary_confidence = primary_result.get('confidence', 0.0)
    best_result = primary_result
    best_confidence = primary_confidence
    
    # If confidence is below threshold and we have retry attempts, validate with other models
    if primary_confidence < CONFIDENCE_THRESHOLD and retry_count < MAX_RETRY_ATTEMPTS:
        for validation_model in VALIDATION_MODELS:
            if retry_count >= MAX_RETRY_ATTEMPTS:
                break
                
            retry_count += 1
            
            # Try validation model
            validation_result = _detect_with_model(
                validation_model,
                image_base64,
                image_format,
                api_key,
                few_shot_examples,
                enable_polygon=ENABLE_POLYGON_DETECTION,
                enable_doors=ENABLE_DOOR_DETECTION,
                strict_mode=strict_mode
            )
            
            models_used.append(validation_model)
            validation_confidence = validation_result.get('confidence', 0.0)
            
            # If this result is better, use it
            if validation_confidence > best_confidence:
                best_result = validation_result
                best_confidence = validation_confidence
            
            # If we've reached acceptable confidence, stop
            if best_confidence >= CONFIDENCE_THRESHOLD:
                break
    
    # If polygon detection failed, fallback to bounding boxes
    detection_type = "polygon" if best_result.get('has_polygons') else "bounding_box"
    if ENABLE_POLYGON_DETECTION and not best_result.get('has_polygons'):
        # Retry with bounding box only
        fallback_result = _detect_with_model(
            OPENROUTER_MODEL,
            image_base64,
            image_format,
            api_key,
            few_shot_examples,
            enable_polygon=False,
            enable_doors=ENABLE_DOOR_DETECTION,
            strict_mode=strict_mode
        )
        if fallback_result.get('success'):
            best_result = fallback_result
            detection_type = "bounding_box"
    
    # Build final result with metadata
    return {
        "success": best_result.get('success', False),
        "rooms": best_result.get('rooms', []),
        "doors": best_result.get('doors', []) if ENABLE_DOOR_DETECTION else [],
        "confidence": best_confidence,
        "detection_metadata": {
            "models_used": models_used,
            "retry_count": retry_count,
            "primary_confidence": primary_confidence,
            "final_confidence": best_confidence,
            "detection_type": detection_type,
            "primary_model": OPENROUTER_MODEL
        },
        "error": best_result.get('error') if not best_result.get('success') else None,
        "error_code": best_result.get('error_code') if not best_result.get('success') else None
    }


def _detect_with_model(model: str, image_base64: str, image_format: str,
                      api_key: str, few_shot_examples: Optional[List[Dict]] = None,
                      enable_polygon: bool = True, enable_doors: bool = True,
                      strict_mode: bool = False) -> Dict[str, Any]:
    """
    Detect rooms using a specific model.
    
    Args:
        model: Model identifier (e.g., 'openai/gpt-4o')
        image_base64: Base64-encoded image data
        image_format: Image format
        api_key: OpenRouter API key
        few_shot_examples: Optional training examples
        enable_polygon: Whether to detect polygon boundaries
        enable_doors: Whether to detect doors
        strict_mode: Whether to use strict mode for maximum accuracy
        
    Returns:
        Detection result dictionary
    """
    # Build prompt
    prompt = _build_detection_prompt(enable_polygon, enable_doors, few_shot_examples, strict_mode)
    
    # Construct image URL
    image_url = f"data:image/{image_format};base64,{image_base64}"
    
    # Build messages
    messages = []
    
    # Add few-shot examples if provided
    if few_shot_examples:
        for example in few_shot_examples:
            example_image_url = f"data:image/{example.get('image_format', 'png')};base64,{example['image_base64']}"
            annotation = example.get('annotation', {})
            
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Example floor plan:"},
                    {"type": "image_url", "image_url": {"url": example_image_url}}
                ]
            })
            messages.append({
                "role": "assistant",
                "content": json.dumps(annotation)
            })
    
    # Add current image
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    })
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 3000
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/DungeonCrawlerBlueprints",
        "X-Title": "DungeonCrawlerBlueprints"
    }
    
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=25
        )
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Extract JSON from response
        content = content.strip()
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join([line for line in lines if not line.strip().startswith('```')])
        
        # Parse JSON response
        detection_result = json.loads(content)
        
        # Extract rooms and calculate confidence
        rooms = detection_result.get("rooms", [])
        doors = detection_result.get("doors", []) if enable_doors else []
        
        # Check if we have polygons
        has_polygons = any('polygon' in room for room in rooms)
        
        # Ensure bounding boxes exist (compute from polygon if needed)
        for room in rooms:
            if 'polygon' in room and 'bounding_box' not in room:
                room['bounding_box'] = _polygon_to_bbox(room['polygon'])
            elif 'bounding_box' not in room:
                room['bounding_box'] = [0, 0, 0, 0]
        
        # Calculate overall confidence
        confidence = calculate_confidence_score(rooms)
        
        return {
            "success": True,
            "rooms": rooms,
            "doors": doors,
            "confidence": confidence,
            "has_polygons": has_polygons,
            "model_used": model
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"API error: {str(e)}",
            "error_code": "API_ERROR",
            "rooms": [],
            "doors": [],
            "confidence": 0.0,
            "has_polygons": False
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse response: {str(e)}",
            "error_code": "PARSE_ERROR",
            "rooms": [],
            "doors": [],
            "confidence": 0.0,
            "has_polygons": False
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
            "rooms": [],
            "doors": [],
            "confidence": 0.0,
            "has_polygons": False
        }


def _build_detection_prompt(enable_polygon: bool, enable_doors: bool,
                           few_shot_examples: Optional[List[Dict]] = None,
                           strict_mode: bool = False) -> str:
    """Build the detection prompt based on enabled features."""
    
    if few_shot_examples:
        prompt = "Analyze this architectural blueprint following the examples above.\n\n"
    else:
        prompt = "Analyze this architectural blueprint and detect all distinct rooms/spaces.\n\n"
    
    # Add strict mode instructions for maximum accuracy
    if strict_mode:
        prompt += "STRICT MODE - Maximum Accuracy Required:\n"
        prompt += "Follow this systematic approach:\n"
        prompt += "1. Scan the entire blueprint from top-left to bottom-right\n"
        prompt += "2. Identify EVERY enclosed space, including small rooms in corners\n"
        prompt += "3. Trace boundaries along interior wall edges with ±5% precision\n"
        prompt += "4. Verify that 85%+ of the blueprint area is accounted for\n"
        prompt += "5. Double-check for any missed rooms before finalizing\n\n"
    
    prompt += "Return a JSON object with the following structure:\n{\n"
    
    if enable_polygon:
        prompt += '  "rooms": [\n'
        prompt += '    {\n'
        prompt += '      "id": "room_001",\n'
        prompt += '      "polygon": [[x1,y1], [x2,y2], [x3,y3], ...],\n'
        prompt += '      "bounding_box": [x_min, y_min, x_max, y_max],\n'
        prompt += '      "confidence": 0.0-1.0,\n'
        prompt += '      "name_hint": "suggested room name"\n'
        prompt += '    }\n'
        prompt += '  ]'
    else:
        prompt += '  "rooms": [\n'
        prompt += '    {\n'
        prompt += '      "id": "room_001",\n'
        prompt += '      "bounding_box": [x_min, y_min, x_max, y_max],\n'
        prompt += '      "confidence": 0.0-1.0,\n'
        prompt += '      "name_hint": "suggested room name"\n'
        prompt += '    }\n'
        prompt += '  ]'
    
    if enable_doors:
        prompt += ',\n  "doors": [\n'
        prompt += '    {\n'
        prompt += '      "id": "door_001",\n'
        prompt += '      "location": [x, y],\n'
        prompt += '      "direction": "N/S/E/W",\n'
        prompt += '      "connects": ["room_001", "room_002"]\n'
        prompt += '    }\n'
        prompt += '  ]'
    
    prompt += '\n}\n\n'
    prompt += 'Requirements:\n'
    prompt += '- Normalize all coordinates to 0-1000 range (top-left is 0,0)\n'
    
    if enable_polygon:
        prompt += '- Polygon vertices in clockwise order\n'
        prompt += '- Include bounding_box for each room (can be computed from polygon)\n'
    else:
        prompt += '- Bounding boxes: [x_min, y_min, x_max, y_max] format\n'
    
    prompt += '- Confidence should reflect detection certainty (0.0-1.0)\n'
    prompt += '- CRITICAL: Include ALL enclosed spaces (rooms, hallways, closets, bathrooms, etc.)\n'
    prompt += '- Boundaries must follow interior wall edges precisely\n'
    prompt += '- Maintain accurate proportions relative to the full blueprint\n'
    
    if strict_mode:
        prompt += '- Verify complete coverage: no large gaps should remain undetected\n'
        prompt += '- Pay special attention to rooms in corners and edges\n'
        prompt += '- Small rooms (closets, bathrooms) are just as important as large ones\n'
    
    if enable_doors:
        prompt += '- Detect all doors and openings between rooms\n'
        prompt += '- Direction: N (north/top), S (south/bottom), E (east/right), W (west/left)\n'
    
    prompt += '- Only return valid JSON, no markdown formatting'
    
    return prompt


def calculate_confidence_score(rooms: List[Dict]) -> float:
    """
    Calculate overall confidence score from room detections.
    
    Args:
        rooms: List of detected rooms with confidence scores
        
    Returns:
        Overall confidence score (0.0-1.0)
    """
    if not rooms:
        return 0.0
    
    # Average confidence across all rooms
    confidences = [room.get('confidence', 0.5) for room in rooms]
    avg_confidence = sum(confidences) / len(confidences)
    
    # Penalize if too few rooms detected (likely incomplete)
    if len(rooms) < 2:
        avg_confidence *= 0.8
    
    return min(1.0, max(0.0, avg_confidence))


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


def suggest_room_type(current_room_type: str, door_direction: str,
                     mode: str = "realistic") -> Dict[str, Any]:
    """
    Suggest likely room types for a new room connection.
    
    Args:
        current_room_type: Type of the current room
        door_direction: Direction of the door (N/S/E/W)
        mode: "realistic" or "fantasy"
        
    Returns:
        Dictionary with room suggestions and probabilities
    """
    api_key = get_openrouter_api_key()
    
    # Build prompt based on mode
    if mode == "fantasy":
        prompt = f"""Given a {current_room_type} in a dungeon/fantasy setting with a door facing {door_direction},
suggest the 3 most likely room types that would be connected through this door.

For each suggestion, provide:
- room_type: Name of the room type
- probability: Likelihood (0.0-1.0)
- typical_dimensions: Suggested width and height in normalized coordinates (0-1000)

Return as JSON:
{{
  "suggestions": [
    {{"room_type": "...", "probability": 0.0-1.0, "typical_dimensions": {{"width": 0-1000, "height": 0-1000}}}}
  ]
}}

Consider fantasy/game design conventions. Be creative but logical."""
    else:
        prompt = f"""Given a {current_room_type} with a door facing {door_direction},
suggest the 3 most likely room types that would be connected through this door in a realistic architectural floor plan.

For each suggestion, provide:
- room_type: Name of the room type
- probability: Likelihood (0.0-1.0)
- typical_dimensions: Suggested width and height in normalized coordinates (0-1000)

Return as JSON:
{{
  "suggestions": [
    {{"room_type": "...", "probability": 0.0-1.0, "typical_dimensions": {{"width": 0-1000, "height": 0-1000}}}}
  ]
}}

Consider standard architectural practices and building codes."""
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/DungeonCrawlerBlueprints",
        "X-Title": "DungeonCrawlerBlueprints"
    }
    
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Extract JSON
        content = content.strip()
        if content.startswith('```'):
            lines = content.split('\n')
            content = '\n'.join([line for line in lines if not line.strip().startswith('```')])
        
        suggestions_data = json.loads(content)
        
        return {
            "success": True,
            "suggestions": suggestions_data.get("suggestions", [])
        }
        
    except Exception as e:
        # Fallback suggestions
        return {
            "success": False,
            "error": str(e),
            "suggestions": [
                {"room_type": "Hallway", "probability": 0.4, "typical_dimensions": {"width": 150, "height": 300}},
                {"room_type": "Storage", "probability": 0.3, "typical_dimensions": {"width": 200, "height": 200}},
                {"room_type": "Room", "probability": 0.3, "typical_dimensions": {"width": 300, "height": 300}}
            ]
        }


# Legacy function for backward compatibility
def detect_rooms_from_image(image_base64: str, image_format: str = 'png') -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Uses new multi-model detection but returns simplified format.
    """
    result = detect_rooms_with_validation(image_base64, image_format)
    
    return {
        "success": result.get("success", False),
        "rooms": result.get("rooms", []),
        "model_used": result.get("detection_metadata", {}).get("primary_model", OPENROUTER_MODEL),
        "error": result.get("error"),
        "error_code": result.get("error_code")
    }


def normalize_coordinates(rooms: List[Dict], image_width: int, image_height: int) -> List[Dict]:
    """
    Normalize room coordinates from pixel space to 0-1000 range.
    
    Args:
        rooms: List of room dictionaries with bounding_box in pixel coordinates
        image_width: Original image width in pixels
        image_height: Original image height in pixels
        
    Returns:
        List of rooms with normalized coordinates
    """
    normalized_rooms = []
    for room in rooms:
        bbox = room.get('bounding_box', [])
        if len(bbox) == 4:
            x_min, y_min, x_max, y_max = bbox
            
            # Normalize to 0-1000 range
            norm_x_min = int((x_min / image_width) * COORDINATE_MAX)
            norm_y_min = int((y_min / image_height) * COORDINATE_MAX)
            norm_x_max = int((x_max / image_width) * COORDINATE_MAX)
            norm_y_max = int((y_max / image_height) * COORDINATE_MAX)
            
            # Clamp to valid range
            norm_x_min = max(0, min(COORDINATE_MAX, norm_x_min))
            norm_y_min = max(0, min(COORDINATE_MAX, norm_y_min))
            norm_x_max = max(0, min(COORDINATE_MAX, norm_x_max))
            norm_y_max = max(0, min(COORDINATE_MAX, norm_y_max))
            
            room['bounding_box'] = [norm_x_min, norm_y_min, norm_x_max, norm_y_max]
        
        # Normalize polygon if present
        if 'polygon' in room:
            normalized_polygon = []
            for point in room['polygon']:
                if len(point) == 2:
                    norm_x = int((point[0] / image_width) * COORDINATE_MAX)
                    norm_y = int((point[1] / image_height) * COORDINATE_MAX)
                    norm_x = max(0, min(COORDINATE_MAX, norm_x))
                    norm_y = max(0, min(COORDINATE_MAX, norm_y))
                    normalized_polygon.append([norm_x, norm_y])
            room['polygon'] = normalized_polygon
        
        normalized_rooms.append(room)
    
    return normalized_rooms
