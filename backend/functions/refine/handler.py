"""Lambda handler for refining room boundaries using edge detection."""
import json
import boto3
import os
import sys
from typing import Dict, Any

# Add shared module to path
shared_path = os.path.join(os.path.dirname(__file__), '..', '..', 'shared')
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)

from edge_detector import refine_room_boundaries
from cors import get_cors_headers
from config import get_dynamodb_table, get_s3_bucket

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Refine room boundaries using edge detection.
    
    Path: POST /refine/{job_id}
    Body: {
        "threshold": 50  // Optional: max snap distance in pixels
    }
    """
    try:
        # Get job_id from path
        job_id = event.get('pathParameters', {}).get('job_id')
        if not job_id:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Missing job_id'})
            }
        
        # Parse request body
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])
        
        threshold = body.get('threshold', 50)
        
        # Get job from DynamoDB
        table = get_dynamodb_table()
        response = table.get_item(Key={'job_id': job_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Job not found'})
            }
        
        job = response['Item']
        
        # Check job status
        if job.get('status') != 'completed':
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Job must be completed before refinement',
                    'status': job.get('status')
                })
            }
        
        # Get image from S3
        s3_key = job.get('s3_key')
        if not s3_key:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'No image found for job'})
            }
        
        bucket_name = get_s3_bucket()
        s3_response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        image_data = s3_response['Body'].read()
        
        # Convert to base64
        import base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get rooms to refine (include all room types)
        rooms = job.get('results', [])  # Original detected rooms
        extended_rooms = job.get('extended_rooms', [])
        modified_rooms = job.get('modified_rooms', [])
        
        all_rooms = list(rooms) + list(extended_rooms) + list(modified_rooms)
        
        if not all_rooms:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'No rooms found to refine'})
            }
        
        # Perform edge detection refinement
        result = refine_room_boundaries(
            image_base64,
            all_rooms,
            threshold=threshold,
            image_format='png'  # Assume PNG, could detect from s3_key
        )
        
        if not result.get('success'):
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': result.get('error', 'Refinement failed')
                })
            }
        
        # Separate refined rooms back into categories
        refined_rooms = result['refined_rooms']
        num_original = len(rooms)
        num_extended = len(extended_rooms)
        num_modified = len(modified_rooms)
        
        refined_original = refined_rooms[:num_original]
        refined_extended = refined_rooms[num_original:num_original + num_extended]
        refined_modified = refined_rooms[num_original + num_extended:]
        
        # Update DynamoDB with refined rooms
        from decimal import Decimal
        
        def convert_floats_to_decimal(obj):
            """Convert float values to Decimal for DynamoDB."""
            if isinstance(obj, list):
                return [convert_floats_to_decimal(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, float):
                return Decimal(str(obj))
            return obj
        
        update_expression = "SET results = :results"
        expression_values = {
            ':results': convert_floats_to_decimal(refined_original)
        }
        
        if refined_extended:
            update_expression += ", extended_rooms = :extended_rooms"
            expression_values[':extended_rooms'] = convert_floats_to_decimal(refined_extended)
        
        if refined_modified:
            update_expression += ", modified_rooms = :modified_rooms"
            expression_values[':modified_rooms'] = convert_floats_to_decimal(refined_modified)
        
        # Add refinement metadata
        update_expression += ", refinement_applied = :refinement_applied, refinement_stats = :stats"
        expression_values[':refinement_applied'] = True
        expression_values[':stats'] = convert_floats_to_decimal(result['stats'])
        
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        # Return refined rooms
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'success': True,
                'rooms': refined_original,
                'extended_rooms': refined_extended,
                'modified_rooms': refined_modified,
                'stats': result['stats']
            }, default=str)
        }
        
    except Exception as e:
        print(f"Error in refine handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        }

