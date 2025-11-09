"""Lambda handler for retrieving detection results."""
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


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts Decimal to float."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle results retrieval request.
    
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
        
        # Format response
        result = {
            'job_id': job['job_id'],
            'blueprint_id': job.get('blueprint_id'),
            'status': job.get('status', 'unknown'),
            'created_at': job.get('created_at'),
            'updated_at': job.get('updated_at')
        }
        
        if job.get('status') == 'completed':
            result['rooms'] = job.get('results', [])
            result['doors'] = job.get('doors', [])
            result['confidence'] = float(job.get('confidence', 0.0)) if job.get('confidence') else 0.0
            result['metadata'] = job.get('metadata', {})
            result['extended_rooms'] = job.get('extended_rooms', [])
            result['modified_rooms'] = job.get('modified_rooms', [])
        elif job.get('status') == 'failed':
            result['error'] = job.get('error', 'Unknown error')
            result['error_code'] = job.get('error_code', 'UNKNOWN')
            result['partial_results'] = job.get('results', [])
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, cls=DecimalEncoder)
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
                'error_code': 'RESULTS_ERROR'
            }, cls=DecimalEncoder)
        }

