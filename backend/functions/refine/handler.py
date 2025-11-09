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
from cors import get_cors_headers, handle_options_request
from config import get_dynamodb_table, get_s3_bucket
from refinement_cache import get_cached_refinement, cache_refinement, get_image_hash

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
    # Handle OPTIONS preflight request
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return handle_options_request()
    
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
        
        threshold = body.get('threshold', 25)  # Reduced default from 50 to 25 for more precise snapping
        
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
        
        # Check cache first
        image_hash = get_image_hash(image_base64)
        cached_result = get_cached_refinement(job_id, threshold, image_hash)
        
        if cached_result:
            # Return cached result
            refined_rooms = cached_result.get('refined_rooms', all_rooms)
            num_original = len(rooms)
            num_extended = len(extended_rooms)
            num_modified = len(modified_rooms)
            
            refined_original = refined_rooms[:num_original]
            refined_extended = refined_rooms[num_original:num_original + num_extended]
            refined_modified = refined_rooms[num_original + num_extended:]
            
            response_body = {
                'success': True,
                'rooms': refined_original,
                'extended_rooms': refined_extended,
                'modified_rooms': refined_modified,
                'stats': cached_result.get('stats', {}),
                'cached': True
            }
            
            if 'method' in cached_result:
                response_body['method'] = cached_result['method']
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps(response_body, default=str)
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
        
        # Cache the result for future requests
        cache_refinement(
            job_id,
            threshold,
            image_hash,
            {
                'refined_rooms': refined_rooms,
                'stats': result['stats'],
                'method': result.get('method', 'PIL')
            }
        )
        
        # Return refined rooms
        response_body = {
            'success': True,
            'rooms': refined_original,
            'extended_rooms': refined_extended,
            'modified_rooms': refined_modified,
            'stats': result['stats'],
            'cached': False
        }
        
        # Include method if available (PIL or OpenCV)
        if 'method' in result:
            response_body['method'] = result['method']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(response_body, default=str)
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

