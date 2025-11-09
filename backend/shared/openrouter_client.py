"""OpenRouter API client for room detection."""
import json
import requests
import base64
from typing import Dict, Any, List, Optional
import sys
import os

# Add shared module to path if not already there
shared_path = os.path.join(os.path.dirname(__file__))
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from config import OPENROUTER_API_URL, OPENROUTER_MODEL, get_openrouter_api_key


def detect_rooms_from_image(image_base64: str, image_format: str = 'png') -> Dict[str, Any]:
    """
    Use OpenRouter GPT-4 Vision to detect rooms in a blueprint image.
    
    Args:
        image_base64: Base64-encoded image data
        image_format: Image format (png, jpg, etc.)
    
    Returns:
        Dictionary with detected rooms and metadata
    """
    api_key = get_openrouter_api_key()
    
    # Construct the image URL for base64 data
    image_url = f"data:image/{image_format};base64,{image_base64}"
    
    # Prepare the prompt for room detection
    prompt = """Analyze this architectural blueprint and detect all distinct rooms/spaces.

Return a JSON array of detected rooms with the following structure:
{
  "rooms": [
    {
      "id": "room_001",
      "bounding_box": [x_min, y_min, x_max, y_max],
      "confidence": 0.0-1.0,
      "name_hint": "suggested room name"
    }
  ]
}

Requirements:
- Normalize all coordinates to 0-1000 range (top-left is 0,0)
- Bounding boxes: [x_min, y_min, x_max, y_max] format
- Confidence should reflect detection certainty
- Include all enclosed spaces (rooms, hallways, etc.)
- Only return valid JSON, no markdown formatting"""

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2000
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
            timeout=25  # Leave buffer for Lambda timeout
        )
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Extract JSON from response (handle markdown code blocks if present)
        content = content.strip()
        if content.startswith('```'):
            # Remove markdown code blocks
            lines = content.split('\n')
            content = '\n'.join([line for line in lines if not line.strip().startswith('```')])
        
        # Parse JSON response
        detection_result = json.loads(content)
        
        return {
            "success": True,
            "rooms": detection_result.get("rooms", []),
            "model_used": OPENROUTER_MODEL,
            "raw_response": result
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"OpenRouter API error: {str(e)}",
            "error_code": "OPENROUTER_API_ERROR",
            "rooms": []
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse OpenRouter response: {str(e)}",
            "error_code": "PARSE_ERROR",
            "rooms": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR",
            "rooms": []
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
    from .config import COORDINATE_MAX
    
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
        
        normalized_rooms.append(room)
    
    return normalized_rooms

