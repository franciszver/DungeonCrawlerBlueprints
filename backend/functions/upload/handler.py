"""Lambda handler for blueprint upload."""
import json
import boto3
import uuid
from datetime import datetime
from typing import Dict, Any
import sys
import os

from cors import cors_response, handle_options_request, get_cors_headers

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# These will be set by SAM template
S3_BUCKET = None
DYNAMODB_TABLE = None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle blueprint upload request.
    
    Expected event:
    {
        "body": base64-encoded multipart form data or JSON,
        "headers": {...}
    }
    """
    import os
    global S3_BUCKET, DYNAMODB_TABLE
    
    # Handle OPTIONS preflight request
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return handle_options_request()
    
    if not S3_BUCKET:
        S3_BUCKET = os.environ.get('S3_BUCKET_NAME', '')
    if not DYNAMODB_TABLE:
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', '')
        DYNAMODB_TABLE = dynamodb.Table(table_name) if table_name else None
    
    try:
        # Parse request body
        if event.get('isBase64Encoded'):
            import base64
            body = base64.b64decode(event['body']).decode('utf-8')
        else:
            body = event.get('body', '{}')
        
        # Handle multipart form data or JSON
        if event.get('headers', {}).get('content-type', '').startswith('multipart/form-data'):
            # For MVP, expect JSON with base64 image
            body_json = json.loads(body)
            file_data = body_json.get('file')
            source_type = body_json.get('source_type', 'image')
        else:
            body_json = json.loads(body) if isinstance(body, str) else body
            file_data = body_json.get('file')
            source_type = body_json.get('source_type', 'image')
        
        if not file_data:
            return cors_response(400, {
                'error': 'Missing file data',
                'error_code': 'MISSING_FILE'
            })
        
        # Generate blueprint ID
        blueprint_id = body_json.get('blueprint_id') or str(uuid.uuid4())
        
        # Determine file extension
        if source_type == 'image':
            # Assume PNG if not specified
            file_ext = 'png'
            if isinstance(file_data, str):
                # Base64 encoded
                import base64
                file_bytes = base64.b64decode(file_data)
            else:
                file_bytes = file_data
        else:
            # Vector/JSON data
            file_ext = 'json'
            file_bytes = json.dumps(file_data).encode('utf-8') if isinstance(file_data, dict) else str(file_data).encode('utf-8')
        
        # Upload to S3
        s3_key = f"blueprints/{blueprint_id}/original.{file_ext}"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=file_bytes,
            ContentType='image/png' if file_ext == 'png' else 'application/json'
        )
        
        # Create job record in DynamoDB
        job_id = str(uuid.uuid4())
        if DYNAMODB_TABLE:
            DYNAMODB_TABLE.put_item(
                Item={
                    'job_id': job_id,
                    'blueprint_id': blueprint_id,
                    'status': 'uploaded',
                    's3_key': s3_key,
                    'source_type': source_type,
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat()
                }
            )
        
        return cors_response(200, {
            'job_id': job_id,
            'blueprint_id': blueprint_id,
            'status': 'uploaded',
            's3_key': s3_key,
            'message': 'Blueprint uploaded successfully'
        })
        
    except Exception as e:
        return cors_response(500, {
            'error': str(e),
            'error_code': 'UPLOAD_ERROR'
        })

