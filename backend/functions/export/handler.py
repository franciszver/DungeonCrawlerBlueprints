"""Lambda handler for exporting results."""
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
    Handle export request.
    
    Expected event:
    {
        "pathParameters": {
            "id": "job_id"
        },
        "queryStringParameters": {
            "format": "json" | "svg"
        }
    }
    """
    try:
        job_id = event.get('pathParameters', {}).get('id')
        export_format = event.get('queryStringParameters', {}).get('format', 'json')
        
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
        
        if job.get('status') != 'completed':
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Job not completed',
                    'error_code': 'JOB_NOT_COMPLETED'
                })
            }
        
        rooms = job.get('results', [])
        doors = job.get('doors', [])
        extended_rooms = job.get('extended_rooms', [])
        all_rooms = rooms + extended_rooms
        
        if export_format == 'svg':
            # Generate SVG overlay with polygons and doors
            svg_content = generate_svg_overlay(all_rooms, doors)
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'image/svg+xml',
                    'Content-Disposition': f'attachment; filename="blueprint_{job_id}.svg"',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': svg_content
            }
        else:
            # JSON export
            export_data = {
                'job_id': job_id,
                'blueprint_id': job.get('blueprint_id'),
                'rooms': rooms,
                'doors': doors,
                'extended_rooms': extended_rooms,
                'confidence': float(job.get('confidence', 0.0)) if job.get('confidence') else 0.0,
                'metadata': job.get('metadata', {}),
                'exported_at': job.get('updated_at')
            }
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Content-Disposition': f'attachment; filename="blueprint_{job_id}.json"',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(export_data, indent=2)
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
                'error_code': 'EXPORT_ERROR'
            })
        }


def generate_svg_overlay(rooms: list, doors: list = None) -> str:
    """Generate SVG overlay with polygons, bounding boxes, and doors."""
    svg_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 1000 1000">',
        '  <style>',
        '    .room-polygon { fill: rgba(59, 130, 246, 0.1); stroke: #3b82f6; stroke-width: 2; }',
        '    .room-box { fill: none; stroke: #3b82f6; stroke-width: 2; stroke-dasharray: 5,5; }',
        '    .room-label { font-family: Arial; font-size: 12; fill: #1e40af; }',
        '    .door { fill: #ef4444; stroke: #991b1b; stroke-width: 1; }',
        '    .extended-room { fill: rgba(34, 197, 94, 0.1); stroke: #16a34a; stroke-width: 2; }',
        '  </style>'
    ]
    
    for room in rooms:
        is_extended = room.get('is_extended', False)
        room_class = 'extended-room' if is_extended else 'room-polygon'
        
        # Draw polygon if available
        if 'polygon' in room and room['polygon']:
            points = ' '.join([f"{p[0]},{p[1]}" for p in room['polygon']])
            svg_lines.append(f'  <polygon class="{room_class}" points="{points}"/>')
        else:
            # Fallback to bounding box
            bbox = room.get('bounding_box', [])
            if len(bbox) == 4:
                x_min, y_min, x_max, y_max = bbox
                width = x_max - x_min
                height = y_max - y_min
                svg_lines.append(f'  <rect class="room-box" x="{x_min}" y="{y_min}" width="{width}" height="{height}"/>')
        
        # Add label
        name_hint = room.get('name_hint', room.get('id', ''))
        if name_hint:
            bbox = room.get('bounding_box', [])
            if len(bbox) == 4:
                x_min, y_min = bbox[0], bbox[1]
                svg_lines.append(f'  <text class="room-label" x="{x_min + 5}" y="{y_min + 15}">{name_hint}</text>')
    
    # Draw doors
    if doors:
        for door in doors:
            location = door.get('location', [])
            if len(location) == 2:
                x, y = location
                # Draw door as a small circle
                svg_lines.append(f'  <circle class="door" cx="{x}" cy="{y}" r="5"/>')
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)

