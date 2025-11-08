"""Lambda handler for retrieving detection results."""
import json
import boto3
import sys
import os
from typing import Dict, Any

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from config import DYNAMODB_TABLE_NAME

dynamodb = boto3.resource('dynamodb')


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
            result['metadata'] = job.get('metadata', {})
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
            'body': json.dumps(result)
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
            })
        }

