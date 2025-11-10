"""Lambda handler for exporting results."""
import json
import boto3
import sys
import os
from typing import Dict, Any
from decimal import Decimal

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from config import DYNAMODB_TABLE_NAME
from cors import cors_response, handle_options_request

dynamodb = boto3.resource('dynamodb')


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle export request.
    
    Expected event:
    {
        "pathParameters": {
            "id": "job_id"
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
        
        if job.get('status') != 'completed':
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Job not completed',
                    'error_code': 'JOB_NOT_COMPLETED'
                })
            }
        
        rooms = job.get('results', [])
        extended_rooms = job.get('extended_rooms', [])
        modified_rooms = job.get('modified_rooms', [])
        
        # Convert Decimal to float for JSON serialization
        rooms = decimal_to_float(rooms)
        extended_rooms = decimal_to_float(extended_rooms)
        modified_rooms = decimal_to_float(modified_rooms)
        
        all_rooms = rooms + modified_rooms + extended_rooms
        
        # Format rooms according to specification
        # Output format: [{"id": "room_001", "bounding_box": [x_min, y_min, x_max, y_max], "name_hint": "Entry Hall"}, ...]
        formatted_rooms = []
        for room in all_rooms:
            formatted_room = {
                'id': room.get('id'),
                'bounding_box': room.get('bounding_box', []),
                'name_hint': room.get('name_hint', '')
            }
            formatted_rooms.append(formatted_room)
        
        # JSON export with simplified format (array of rooms only)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Content-Disposition': f'attachment; filename="blueprint_{job_id}.json"',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(formatted_rooms, indent=2)
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
                'error_code': 'EXPORT_ERROR'
            })
        }

