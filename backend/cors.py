"""CORS helper functions for Lambda responses."""
from typing import Dict, Any


def get_cors_headers() -> Dict[str, str]:
    """Get standard CORS headers for API responses."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,x-api-key,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Max-Age': '600'
    }


def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a CORS-enabled Lambda response."""
    import json
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            **get_cors_headers()
        },
        'body': json.dumps(body)
    }


def handle_options_request() -> Dict[str, Any]:
    """Handle OPTIONS preflight request."""
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': ''
    }

