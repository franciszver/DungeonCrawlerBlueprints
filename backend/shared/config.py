"""Configuration and environment management."""
import os
import json
from typing import Dict, Any

# AWS Resources
DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME', 'DungeonCrawlerBlueprints-Jobs')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')
SECRETS_MANAGER_SECRET_NAME = os.environ.get('SECRETS_MANAGER_SECRET_NAME', 'dungeoncrawler/openrouter-api-key')

# OpenRouter Configuration
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-4o')
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Coordinate System
COORDINATE_MAX = 1000
COORDINATE_MIN = 0

# Processing Limits
MAX_IMAGE_SIZE_MB = 10
MAX_PROCESSING_TIME_SECONDS = 30

def get_openrouter_api_key() -> str:
    """Retrieve OpenRouter API key from AWS Secrets Manager."""
    import boto3
    client = boto3.client('secretsmanager')
    try:
        response = client.get_secret_value(SecretId=SECRETS_MANAGER_SECRET_NAME)
        secret = json.loads(response['SecretString'])
        return secret.get('api_key') or secret.get('OPENROUTER_API_KEY', '')
    except Exception as e:
        raise ValueError(f"Failed to retrieve OpenRouter API key: {str(e)}")

