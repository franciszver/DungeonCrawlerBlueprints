"""Lambda handler for health check."""
import json
import sys
import os
from typing import Dict, Any

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from config import OPENROUTER_MODEL


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle health check request.
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'status': 'healthy',
            'models': {
                'room_detection': OPENROUTER_MODEL
            },
            'service': 'DungeonCrawlerBlueprints'
        })
    }

