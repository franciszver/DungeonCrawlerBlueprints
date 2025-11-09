"""Lambda handler for interactive room extension."""
import json
import boto3
import sys
import os
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from room_generator import generate_room, validate_room_placement
from openrouter_client import suggest_room_type
from config import DYNAMODB_TABLE_NAME
from cors import cors_response, handle_options_request

dynamodb = boto3.resource('dynamodb')


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
            
            # Generate room
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

