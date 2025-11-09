"""Text extraction and room label matching from blueprint images."""
from typing import List, Dict, Any, Tuple, Optional
import json
import base64
import logging
import sys
import os

# Add shared module to path
shared_path = os.path.dirname(__file__)
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

import requests
from config import OPENROUTER_API_URL, get_openrouter_api_key

logger = logging.getLogger(__name__)


def extract_text_labels_from_blueprint(image_base64: str, image_format: str = 'png') -> List[Dict[str, Any]]:
    """
    Extract text labels from blueprint image using AI vision model.
    
    Args:
        image_base64: Base64-encoded blueprint image
        image_format: Image format (png, jpg, etc.)
        
    Returns:
        List of text labels with bounding boxes: [{"text": "Living Room", "bbox": [x_min, y_min, x_max, y_max], "confidence": 0.9}, ...]
    """
    try:
        api_key = get_openrouter_api_key()
        
        # Build prompt for text extraction with comprehensive room name list
        prompt = """Analyze this architectural blueprint and extract ALL text labels that identify rooms or spaces.

Focus on common American and British English room names:
- Living Room, Family Room, Great Room, Den
- Master Bedroom, Bedroom, Guest Bedroom, Children's Bedroom
- Kitchen, Dining Room, Breakfast Nook
- Bathroom, Master Bathroom, Ensuite, Powder Room, Half Bath
- Office, Study, Library, Home Office
- Laundry Room, Utility Room, Mud Room
- Closet, Walk-in Closet, Pantry, Storage
- Garage, Workshop, Basement, Attic
- Hallway, Corridor, Foyer, Entry
- Any other room or space labels

IGNORE:
- Dimension numbers (e.g., "12'", "10.5")
- Door numbers or symbols
- Window labels
- Structural notes
- Any non-room text

For each text label found, provide:
- The exact text as it appears (case-sensitive if visible)
- The bounding box coordinates where the text appears [x_min, y_min, x_max, y_max]
- A confidence score (0.0-1.0) for how certain you are this is a room label

Return a JSON object with this structure:
{
  "text_labels": [
    {
      "text": "Living Room",
      "bbox": [x_min, y_min, x_max, y_max],
      "confidence": 0.95
    },
    ...
  ]
}

For bounding box coordinates, use the actual pixel coordinates of the image.
The image will be automatically normalized, so provide coordinates in pixel space (e.g., if image is 2000x1500 pixels, coordinates can range from 0-2000 for x and 0-1500 for y).
Extract ALL room labels, not just obvious ones."""

        # Prepare image URL
        image_url = f"data:image/{image_format};base64,{image_base64}"
        
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        }]
        
        payload = {
            "model": "openai/gpt-4o-mini",  # Use faster, cheaper model for text extraction
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1000  # Reduced for faster response
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/DungeonCrawlerBlueprints",
            "X-Title": "DungeonCrawlerBlueprints"
        }
        
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=10  # Reduced timeout for faster failure
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
        extraction_result = json.loads(content)
        text_labels = extraction_result.get("text_labels", [])
        
        # Get actual image dimensions to normalize coordinates
        # Images are sent to AI model at original size, but we need to normalize coordinates
        # to match the room coordinate system (0-1000)
        try:
            from PIL import Image
            from io import BytesIO
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data))
            image_width, image_height = image.size
            
            # Normalize text label coordinates to 0-1000 range to match room coordinates
            from config import COORDINATE_MAX
            normalized_labels = []
            for label in text_labels:
                bbox = label.get('bbox', [])
                if len(bbox) == 4:
                    x_min, y_min, x_max, y_max = bbox
                    # Normalize to 0-1000 range
                    norm_x_min = (x_min / image_width) * COORDINATE_MAX
                    norm_y_min = (y_min / image_height) * COORDINATE_MAX
                    norm_x_max = (x_max / image_width) * COORDINATE_MAX
                    norm_y_max = (y_max / image_height) * COORDINATE_MAX
                    
                    normalized_label = label.copy()
                    normalized_label['bbox'] = [
                        max(0, min(COORDINATE_MAX, norm_x_min)),
                        max(0, min(COORDINATE_MAX, norm_y_min)),
                        max(0, min(COORDINATE_MAX, norm_x_max)),
                        max(0, min(COORDINATE_MAX, norm_y_max))
                    ]
                    normalized_labels.append(normalized_label)
                else:
                    # Invalid bbox, skip
                    logger.warning(f"Label '{label.get('text')}' has invalid bbox: {bbox}")
                    normalized_labels.append(label)
            
            text_labels = normalized_labels
            logger.info(f"Extracted and normalized {len(text_labels)} text labels from blueprint (image size: {image_width}x{image_height})")
        except Exception as e:
            logger.warning(f"Could not normalize text label coordinates: {str(e)}. Using coordinates as-is.")
            logger.info(f"Extracted {len(text_labels)} text labels from blueprint")
        
        return text_labels
        
    except Exception as e:
        logger.error(f"Error extracting text labels: {str(e)}")
        return []


def match_text_labels_to_rooms(
    rooms: List[Dict[str, Any]], 
    text_labels: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Match extracted text labels to detected rooms based on proximity.
    Each label can only match one room (prevents duplicates).
    
    Args:
        rooms: List of detected rooms
        text_labels: List of extracted text labels with bounding boxes
        
    Returns:
        Updated rooms list with matched name_hint from text labels
    """
    if not text_labels:
        return rooms
    
    # Track which labels have been used to prevent duplicate matches
    used_labels = set()
    
    # Create updated rooms list
    updated_rooms = []
    
    for room in rooms:
        room_bbox = room.get('bounding_box', [])
        if len(room_bbox) != 4:
            updated_rooms.append(room)
            continue
        
        # Find the closest text label to this room
        best_match = None
        best_match_id = None
        best_distance = float('inf')
        
        room_center = [
            (room_bbox[0] + room_bbox[2]) / 2,
            (room_bbox[1] + room_bbox[3]) / 2
        ]
        
        for label in text_labels:
            # Skip labels that have already been matched to another room
            label_text = label.get('text', '')
            label_id = f"{label_text}_{label.get('bbox', [])}"
            if label_id in used_labels:
                continue
            
            label_bbox = label.get('bbox', [])
            if len(label_bbox) != 4:
                continue
            
            # Calculate distance from room center to label center
            label_center = [
                (label_bbox[0] + label_bbox[2]) / 2,
                (label_bbox[1] + label_bbox[3]) / 2
            ]
            
            distance = ((room_center[0] - label_center[0]) ** 2 + 
                       (room_center[1] - label_center[1]) ** 2) ** 0.5
            
            # Check if label is inside or very close to room
            label_inside_room = (
                label_bbox[0] >= room_bbox[0] and
                label_bbox[1] >= room_bbox[1] and
                label_bbox[2] <= room_bbox[2] and
                label_bbox[3] <= room_bbox[3]
            )
            
            # Prefer labels inside the room, or very close ones
            if label_inside_room:
                distance *= 0.1  # Heavily favor labels inside room
            
            # Also check if label overlaps significantly with room
            overlap_ratio = _calculate_bbox_overlap_ratio(room_bbox, label_bbox)
            if overlap_ratio > 0.3:  # 30% overlap
                distance *= 0.5  # Favor overlapping labels
            
            if distance < best_distance:
                best_distance = distance
                best_match = label
                best_match_id = label_id
        
        # Update room name if we found a good match
        if best_match and best_match_id and best_distance < 200:  # Within 200 pixels
            updated_room = room.copy()
            updated_room['name_hint'] = best_match['text']
            updated_room['name_source'] = 'blueprint_text'  # Mark as from blueprint
            
            # Store the original label position for accurate overlay
            label_bbox = best_match.get('bbox', [])
            if len(label_bbox) == 4:
                label_center_x = (label_bbox[0] + label_bbox[2]) / 2
                label_center_y = (label_bbox[1] + label_bbox[3]) / 2
                updated_room['label_position'] = [label_center_x, label_center_y]
            
            updated_rooms.append(updated_room)
            used_labels.add(best_match_id)  # Mark label as used
            logger.info(f"Matched room {room.get('id')} to label '{best_match['text']}' (distance: {best_distance:.1f})")
        else:
            updated_rooms.append(room)
    
    return updated_rooms


def _calculate_bbox_overlap_ratio(bbox1: List[float], bbox2: List[float]) -> float:
    """Calculate overlap ratio between two bounding boxes."""
    x1_min, y1_min, x1_max, y1_max = bbox1
    x2_min, y2_min, x2_max, y2_max = bbox2
    
    # Calculate intersection
    x_overlap = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
    y_overlap = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
    overlap_area = x_overlap * y_overlap
    
    # Calculate areas
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    
    if area1 == 0 or area2 == 0:
        return 0.0
    
    # Return ratio of overlap to smaller box
    return overlap_area / min(area1, area2)


def find_label_position_for_room_type(
    room_type: str,
    text_labels: List[Dict[str, Any]]
) -> Optional[List[float]]:
    """
    Find the position of a text label matching the room type.
    
    Args:
        room_type: Type of room to find (e.g., "Living Room", "Bedroom")
        text_labels: List of extracted text labels from blueprint
        
    Returns:
        Center position [x, y] of matching label, or None if not found
    """
    if not text_labels:
        return None
    
    # Normalize room type for matching (case-insensitive, remove extra spaces)
    room_type_normalized = room_type.lower().strip()
    
    for label in text_labels:
        label_text = label.get('text', '').lower().strip()
        
        # Check for exact match or partial match
        if (room_type_normalized == label_text or 
            room_type_normalized in label_text or 
            label_text in room_type_normalized):
            
            bbox = label.get('bbox', [])
            if len(bbox) == 4:
                # Return center of label bounding box
                center_x = (bbox[0] + bbox[2]) / 2
                center_y = (bbox[1] + bbox[3]) / 2
                logger.info(f"Found label position for '{room_type}': [{center_x:.1f}, {center_y:.1f}]")
                return [center_x, center_y]
    
    return None


def find_detected_room_for_type(
    room_type: str,
    detected_rooms: List[Dict[str, Any]],
    door_location: Optional[List[float]] = None
) -> Optional[Dict[str, Any]]:
    """
    Find a detected room that matches the room type (by name_hint).
    If multiple rooms match, returns the one closest to door_location.
    
    Args:
        room_type: Type of room to find (e.g., "Living Room", "Laundry")
        detected_rooms: List of detected rooms from blueprint
        door_location: Optional [x, y] coordinates to find closest matching room
        
    Returns:
        Matching detected room (closest to door if multiple matches), or None if not found
    """
    if not detected_rooms:
        return None
    
    # Normalize room type for matching
    room_type_normalized = room_type.lower().strip()
    
    matching_rooms = []
    for room in detected_rooms:
        name_hint = room.get('name_hint', '').lower().strip()
        
        # Check for exact match or partial match
        if (room_type_normalized == name_hint or 
            room_type_normalized in name_hint or 
            name_hint in room_type_normalized):
            matching_rooms.append(room)
    
    if not matching_rooms:
        return None
    
    # If only one match, return it
    if len(matching_rooms) == 1:
        logger.info(f"Found single detected room for '{room_type}': {matching_rooms[0].get('id')}")
        return matching_rooms[0]
    
    # If multiple matches and door location provided, find closest
    if door_location and len(door_location) == 2:
        door_x, door_y = door_location
        best_room = None
        best_distance = float('inf')
        
        for room in matching_rooms:
            bbox = room.get('bounding_box', [])
            if len(bbox) == 4:
                room_center_x = (bbox[0] + bbox[2]) / 2
                room_center_y = (bbox[1] + bbox[3]) / 2
                distance = ((door_x - room_center_x) ** 2 + (door_y - room_center_y) ** 2) ** 0.5
                
                if distance < best_distance:
                    best_distance = distance
                    best_room = room
        
        if best_room:
            logger.info(f"Found closest detected room for '{room_type}' (distance: {best_distance:.1f}): {best_room.get('id')}")
            return best_room
    
    # If no door location or can't calculate distance, return first match
    logger.info(f"Found {len(matching_rooms)} detected rooms for '{room_type}', using first: {matching_rooms[0].get('id')}")
    return matching_rooms[0]


def add_numerical_differentiators(text_labels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add numerical differentiators to duplicate room names (e.g., "Bathroom 1", "Bathroom 2").
    
    Args:
        text_labels: List of text labels with 'text' field
        
    Returns:
        Updated text labels with numerical differentiators for duplicates
    """
    if not text_labels:
        return text_labels
    
    # Group labels by normalized text (case-insensitive)
    label_groups = {}
    for label in text_labels:
        normalized_text = label.get('text', '').lower().strip()
        if normalized_text not in label_groups:
            label_groups[normalized_text] = []
        label_groups[normalized_text].append(label)
    
    # Add numerical differentiators to duplicates
    updated_labels = []
    for normalized_text, labels in label_groups.items():
        if len(labels) == 1:
            # No duplicates, keep original
            updated_labels.append(labels[0])
        else:
            # Multiple labels with same name, add numbers
            for idx, label in enumerate(labels, start=1):
                updated_label = label.copy()
                original_text = label.get('text', '')
                updated_label['text'] = f"{original_text} {idx}"
                updated_label['original_text'] = original_text  # Preserve original for matching
                updated_labels.append(updated_label)
                logger.info(f"Added numerical differentiator: '{original_text}' -> '{updated_label['text']}'")
    
    return updated_labels


def filter_room_labels(text_labels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter text labels to only include room-related labels using a whitelist.
    
    Args:
        text_labels: List of extracted text labels
        
    Returns:
        Filtered list containing only room-related labels
    """
    if not text_labels:
        return text_labels
    
    # Whitelist of common room terms (case-insensitive matching)
    room_terms = {
        'living room', 'family room', 'great room', 'den', 'lounge',
        'master bedroom', 'bedroom', 'guest bedroom', "children's bedroom", 'kids bedroom',
        'kitchen', 'dining room', 'breakfast nook', 'dining',
        'bathroom', 'master bathroom', 'ensuite', 'powder room', 'half bath', 'wc',
        'office', 'study', 'library', 'home office',
        'laundry room', 'utility room', 'mud room', 'mudroom',
        'closet', 'walk-in closet', 'walk in closet', 'pantry', 'storage',
        'garage', 'workshop', 'basement', 'attic',
        'hallway', 'corridor', 'foyer', 'entry', 'entrance',
        'balcony', 'patio', 'deck', 'porch',
        'game room', 'playroom', 'media room', 'theater', 'theatre',
        'gym', 'exercise room', 'fitness room'
    }
    
    filtered_labels = []
    for label in text_labels:
        label_text = label.get('text', '').lower().strip()
        
        # Check if label text contains any room term
        is_room_label = False
        for term in room_terms:
            if term in label_text or label_text in term:
                is_room_label = True
                break
        
        # Also check if it's a numbered room (e.g., "Bedroom 1")
        if not is_room_label:
            # Remove numbers and check again
            text_without_numbers = ''.join(c for c in label_text if not c.isdigit()).strip()
            for term in room_terms:
                if term in text_without_numbers or text_without_numbers in term:
                    is_room_label = True
                    break
        
        if is_room_label:
            filtered_labels.append(label)
        else:
            logger.debug(f"Filtered out non-room label: '{label.get('text')}'")
    
    logger.info(f"Filtered {len(text_labels)} labels to {len(filtered_labels)} room labels")
    return filtered_labels

