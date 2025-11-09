"""Lambda handler for room detection."""
import json
import boto3
import sys
import os
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from room_detector import process_blueprint_image
from config import S3_BUCKET_NAME, DYNAMODB_TABLE_NAME

s3_client = boto3.client('s3')
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
    Handle room detection request.
    
    Expected event:
    {
        "body": {
            "blueprint_id": "string",
            "job_id": "string (optional)"
        }
    }
    """
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        blueprint_id = body.get('blueprint_id')
        job_id = body.get('job_id')
        
        if not blueprint_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing blueprint_id',
                    'error_code': 'MISSING_BLUEPRINT_ID'
                })
            }
        
        # Get table
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        
        # Find job or create new one
        if job_id:
            try:
                response = table.get_item(Key={'job_id': job_id})
                job = response.get('Item')
                if not job or job.get('blueprint_id') != blueprint_id:
                    job_id = None
            except:
                job_id = None
        
        if not job_id:
            # Find latest job for blueprint_id
            # Note: For MVP, we'll use a simple scan (can optimize with GSI later)
            response = table.scan(
                FilterExpression='blueprint_id = :bid',
                ExpressionAttributeValues={':bid': blueprint_id}
            )
            items = response.get('Items', [])
            if items:
                # Get most recent
                job = max(items, key=lambda x: x.get('created_at', ''))
                job_id = job['job_id']
            else:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Blueprint not found',
                        'error_code': 'BLUEPRINT_NOT_FOUND'
                    })
                }
        
        # Get S3 key from job
        job_response = table.get_item(Key={'job_id': job_id})
        job = job_response.get('Item')
        s3_key = job.get('s3_key')
        
        if not s3_key:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'S3 key not found for blueprint',
                    'error_code': 'S3_KEY_NOT_FOUND'
                })
            }
        
        # Update job status
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, updated_at = :updated',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'processing',
                ':updated': datetime.utcnow().isoformat()
            }
        )
        
        # Download image from S3
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        image_data = response['Body'].read()
        
        # Determine image format
        file_ext = s3_key.split('.')[-1].lower()
        image_format = 'png' if file_ext == 'png' else 'jpg'
        
        # Process image
        detection_result = process_blueprint_image(image_data, image_format)
        
        # Store results
        if detection_result.get('success'):
            # Convert floats to Decimal for DynamoDB
            rooms = convert_floats_to_decimal(detection_result.get('rooms', []))
            metadata = convert_floats_to_decimal(detection_result.get('metadata', {}))
            
            table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, results = :results, metadata = :metadata, updated_at = :updated',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':results': rooms,
                    ':metadata': metadata,
                    ':updated': datetime.utcnow().isoformat()
                }
            )
        else:
            table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status, #error = :error, error_code = :error_code, updated_at = :updated',
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#error': 'error'  # 'error' is a DynamoDB reserved keyword
                },
                ExpressionAttributeValues={
                    ':status': 'failed',
                    ':error': detection_result.get('error', 'Unknown error'),
                    ':error_code': detection_result.get('error_code', 'UNKNOWN'),
                    ':updated': datetime.utcnow().isoformat()
                }
            )
        
        # Return response
        if detection_result.get('success'):
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'blueprint_id': blueprint_id,
                    'status': 'completed',
                    'rooms': detection_result.get('rooms', []),
                    'metadata': detection_result.get('metadata', {})
                })
            }
        else:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'blueprint_id': blueprint_id,
                    'status': 'failed',
                    'error': detection_result.get('error', 'Unknown error'),
                    'error_code': detection_result.get('error_code', 'UNKNOWN'),
                    'partial_results': detection_result.get('rooms', [])
                })
            }
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Detection error: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'error_code': 'DETECTION_ERROR',
                'traceback': error_trace
            })
        }

