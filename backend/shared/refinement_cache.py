"""Caching module for refinement results to improve performance and reduce costs."""
import hashlib
import json
import boto3
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

# Cache TTL: 24 hours
CACHE_TTL_HOURS = 24

# Get cache table name from environment or use default
def get_cache_table_name() -> str:
    """Get refinement cache table name from environment."""
    return os.environ.get('REFINEMENT_CACHE_TABLE', 'RefinementCache')

dynamodb = boto3.resource('dynamodb')


def get_cache_key(job_id: str, threshold: int, image_hash: str) -> str:
    """
    Generate cache key from job_id, threshold, and image hash.
    
    Args:
        job_id: Job identifier
        threshold: Refinement threshold value
        image_hash: Hash of the image data
        
    Returns:
        Cache key string
    """
    key_data = f"{job_id}:{threshold}:{image_hash}"
    return hashlib.sha256(key_data.encode()).hexdigest()


def get_image_hash(image_base64: str) -> str:
    """
    Generate hash of image data for cache key.
    
    Args:
        image_base64: Base64-encoded image
        
    Returns:
        SHA256 hash of image data
    """
    return hashlib.sha256(image_base64.encode()).hexdigest()


def get_cached_refinement(job_id: str, threshold: int, image_hash: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached refinement result if available and not expired.
    
    Args:
        job_id: Job identifier
        threshold: Refinement threshold
        image_hash: Hash of image data
        
    Returns:
        Cached refinement result or None if not found/expired
    """
    try:
        cache_key = get_cache_key(job_id, threshold, image_hash)
        table_name = get_cache_table_name()
        
        # Try to get cache table (may not exist yet)
        try:
            table = dynamodb.Table(table_name)
            response = table.get_item(Key={'cache_key': cache_key})
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            
            # Check if cache is expired
            ttl = item.get('ttl')
            if ttl:
                current_time = int(datetime.utcnow().timestamp())
                if current_time > ttl:
                    # Cache expired, delete it
                    table.delete_item(Key={'cache_key': cache_key})
                    return None
            
            # Return cached result
            result = item.get('result', {})
            
            # Convert Decimal back to float for JSON serialization
            def convert_decimal_to_float(obj):
                if isinstance(obj, list):
                    return [convert_decimal_to_float(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: convert_decimal_to_float(v) for k, v in obj.items()}
                elif isinstance(obj, Decimal):
                    return float(obj)
                return obj
            
            return convert_decimal_to_float(result)
            
        except Exception as e:
            # Table doesn't exist or other error - cache miss
            return None
            
    except Exception:
        # Any error means cache miss
        return None


def cache_refinement(
    job_id: str,
    threshold: int,
    image_hash: str,
    result: Dict[str, Any]
) -> bool:
    """
    Cache refinement result with TTL.
    
    Args:
        job_id: Job identifier
        threshold: Refinement threshold
        image_hash: Hash of image data
        result: Refinement result to cache
        
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        cache_key = get_cache_key(job_id, threshold, image_hash)
        table_name = get_cache_table_name()
        
        # Calculate TTL (24 hours from now)
        ttl_timestamp = int((datetime.utcnow() + timedelta(hours=CACHE_TTL_HOURS)).timestamp())
        
        # Convert floats to Decimal for DynamoDB
        def convert_floats_to_decimal(obj):
            if isinstance(obj, list):
                return [convert_floats_to_decimal(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, float):
                return Decimal(str(obj))
            return obj
        
        cached_result = convert_floats_to_decimal(result)
        
        # Try to write to cache table
        try:
            table = dynamodb.Table(table_name)
            table.put_item(
                Item={
                    'cache_key': cache_key,
                    'job_id': job_id,
                    'threshold': threshold,
                    'image_hash': image_hash,
                    'result': cached_result,
                    'ttl': ttl_timestamp,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            return True
        except Exception:
            # Table doesn't exist or write failed - that's okay
            return False
            
    except Exception:
        # Any error means cache write failed
        return False

