"""Lambda handler for interactive room extension."""
import json
import boto3
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from room_generator import generate_room, validate_room_placement, smart_room_placement
from openrouter_client import suggest_room_type
from config import DYNAMODB_TABLE_NAME, ENABLE_SMART_PLACEMENT
from cors import cors_response, handle_options_request

dynamodb = boto3.resource('dynamodb')


def _get_dimensions_for_room_type(room_type: str, mode: str) -> Dict[str, float]:
    """Get default dimensions for a room type (simplified version)."""
    if mode == "fantasy":
        dimensions_map = {
            "Treasure Room": {"width": 250, "height": 250},
            "Boss Chamber": {"width": 400, "height": 400},
            "Corridor": {"width": 150, "height": 400},
            "Secret Room": {"width": 200, "height": 200},
            "Trap Room": {"width": 300, "height": 300},
            "Storage": {"width": 200, "height": 250},
            "Guard Post": {"width": 250, "height": 250},
        }
    else:
        dimensions_map = {
            "Bedroom": {"width": 350, "height": 400},
            "Bathroom": {"width": 250, "height": 300},
            "Kitchen": {"width": 400, "height": 350},
            "Living Room": {"width": 500, "height": 450},
            "Dining Room": {"width": 400, "height": 400},
            "Hallway": {"width": 150, "height": 400},
            "Closet": {"width": 200, "height": 150},
            "Office": {"width": 350, "height": 350},
            "Garage": {"width": 600, "height": 600},
            "Pantry": {"width": 200, "height": 250},
        }
    
    return dimensions_map.get(room_type, {"width": 300, "height": 300})


def convert_floats_to_decimal(obj):
    """Convert all float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle room extension request.
    
    Expected event:
    {
        "pathParameters": {
            "id": "job_id"
        },
        "body": {
            "action": "generate" | "suggest" | "validate",
            "door_location": [x, y],
            "door_direction": "N/S/E/W",
            "current_room_type": "Kitchen",
            "room_type": "optional",
            "mode": "realistic" | "fantasy"
        }
    }
    """
    # Handle OPTIONS preflight request
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return handle_options_request()
    
    try:
        job_id = event.get('pathParameters', {}).get('id')
        
        if not job_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing job ID',
                    'error_code': 'MISSING_JOB_ID'
                })
            }
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        action = body.get('action', 'generate')
        door_location = body.get('door_location')
        door_direction = body.get('door_direction')
        current_room_type = body.get('current_room_type', 'Room')
        room_type = body.get('room_type')
        mode = body.get('mode', 'realistic')
        
        # Get job from DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        response = table.get_item(Key={'job_id': job_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Job not found',
                    'error_code': 'JOB_NOT_FOUND'
                })
            }
        
        job = response['Item']
        existing_rooms = job.get('results', [])
        extended_rooms = job.get('extended_rooms', [])
        all_rooms = existing_rooms + extended_rooms
        
        # Handle different actions
        if action == 'suggest':
            # Get room type suggestions
            if not door_direction or not current_room_type:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Missing door_direction or current_room_type',
                        'error_code': 'MISSING_PARAMETERS'
                    })
                }
            
            suggestions_result = suggest_room_type(current_room_type, door_direction, mode)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'suggestions': suggestions_result.get('suggestions', [])
                })
            }
        
        elif action == 'generate':
            # Generate a new room
            if not door_location or not door_direction:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Missing door_location or door_direction',
                        'error_code': 'MISSING_PARAMETERS'
                    })
                }
            
            # Get room type and dimensions
            if room_type is None:
                suggestions_result = suggest_room_type(current_room_type, door_direction, mode)
                if suggestions_result.get("success") and suggestions_result.get("suggestions"):
                    suggestions = suggestions_result["suggestions"]
                    suggestions.sort(key=lambda x: x.get("probability", 0), reverse=True)
                    room_type = suggestions[0]["room_type"]
                    dimensions = suggestions[0].get("typical_dimensions", {"width": 300, "height": 300})
                else:
                    room_type = "Room"
                    dimensions = {"width": 300, "height": 300}
            else:
                dimensions = _get_dimensions_for_room_type(room_type, mode)
            
            # Use smart placement if enabled
            if ENABLE_SMART_PLACEMENT:
                # Get all existing rooms (including modified)
                modified_rooms = job.get('modified_rooms', [])
                all_existing_rooms = existing_rooms + extended_rooms + modified_rooms
                
                polygon = smart_room_placement(
                    door_location,
                    door_direction,
                    dimensions,
                    all_existing_rooms,
                    room_type,
                    mode
                )
                
                if polygon is None:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': 'No valid placement found for room. Try a different door or adjust existing rooms.',
                            'error_code': 'NO_VALID_PLACEMENT'
                        })
                    }
                
                # Create room from polygon
                import uuid
                room_id = f"extended_{uuid.uuid4().hex[:8]}"
                bounding_box = [
                    min(p[0] for p in polygon),
                    min(p[1] for p in polygon),
                    max(p[0] for p in polygon),
                    max(p[1] for p in polygon)
                ]
                
                new_room = {
                    "id": room_id,
                    "polygon": polygon,
                    "bounding_box": bounding_box,
                    "name_hint": room_type,
                    "confidence": 0.95,
                    "is_extended": True,
                    "connected_door": {
                        "location": door_location,
                        "direction": door_direction
                    }
                }
            else:
                # Use standard generation
                generation_result = generate_room(
                    door_location,
                    door_direction,
                    current_room_type,
                    mode,
                    room_type
                )
                
                if not generation_result.get('success'):
                    return {
                        'statusCode': 500,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': generation_result.get('error', 'Generation failed'),
                            'error_code': generation_result.get('error_code', 'GENERATION_ERROR')
                        })
                    }
                
                new_room = generation_result['room']
                
                # Validate placement
                validation_result = validate_room_placement(
                    new_room['polygon'],
                    all_rooms
                )
                
                if not validation_result.get('valid'):
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'error': validation_result.get('error', 'Invalid placement'),
                            'error_code': 'INVALID_PLACEMENT',
                            'overlapping_room_id': validation_result.get('overlapping_room_id')
                        })
                    }
            
            # Add to extended rooms
            extended_rooms.append(new_room)
            
            # Update job in DynamoDB
            table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET extended_rooms = :extended, updated_at = :updated',
                ExpressionAttributeValues={
                    ':extended': convert_floats_to_decimal(extended_rooms),
                    ':updated': datetime.utcnow().isoformat()
                }
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'room': new_room,
                    'message': 'Room generated successfully'
                })
            }
        
        elif action == 'validate':
            # Validate a room placement
            room_polygon = body.get('room_polygon')
            
            if not room_polygon:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Missing room_polygon',
                        'error_code': 'MISSING_PARAMETERS'
                    })
                }
            
            validation_result = validate_room_placement(room_polygon, all_rooms)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'valid': validation_result.get('valid', False),
                    'error': validation_result.get('error'),
                    'overlapping_room_id': validation_result.get('overlapping_room_id')
                })
            }
        
        elif action == 'update_plan':
            # Update modified rooms, extended rooms, and doors
            modified_rooms = body.get('modified_rooms')
            updated_extended_rooms = body.get('extended_rooms')
            updated_doors = body.get('doors')
            
            update_expression_parts = ['updated_at = :updated']
            expression_values = {':updated': datetime.utcnow().isoformat()}
            
            # Only update fields that are explicitly provided
            if modified_rooms is not None:
                update_expression_parts.append('modified_rooms = :modified')
                expression_values[':modified'] = convert_floats_to_decimal(modified_rooms)
            
            if updated_extended_rooms is not None:
                update_expression_parts.append('extended_rooms = :extended')
                expression_values[':extended'] = convert_floats_to_decimal(updated_extended_rooms)
            
            if updated_doors is not None:
                update_expression_parts.append('doors = :doors')
                expression_values[':doors'] = convert_floats_to_decimal(updated_doors)
            
            # Only update if there's something to update
            if len(update_expression_parts) > 1:
                # Update job in DynamoDB
                table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression=f'SET {", ".join(update_expression_parts)}',
                    ExpressionAttributeValues=expression_values
                )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'message': 'Plan updated successfully'
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'Unknown action: {action}',
                    'error_code': 'UNKNOWN_ACTION'
                })
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'error_code': 'EXTENSION_ERROR'
            })
        }

