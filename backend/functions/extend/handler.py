"""Lambda handler for interactive room extension."""
import json
import boto3
import base64
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from decimal import Decimal

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from room_generator import generate_room, validate_room_placement, smart_room_placement, _calculate_scale_factor_from_existing_rooms
from openrouter_client import suggest_room_type
from text_extractor import find_label_position_for_room_type, find_detected_room_for_type
from config import DYNAMODB_TABLE_NAME, ENABLE_SMART_PLACEMENT, S3_BUCKET_NAME
from cors import cors_response, handle_options_request

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


def _get_dimensions_for_room_type(room_type: str, mode: str) -> Dict[str, float]:
    """Get default dimensions for a room type (simplified version)."""
    if mode == "fantasy":
        dimensions_map = {
            "Treasure Room": {"width": 250, "height": 250},
            "Boss Chamber": {"width": 400, "height": 400},
            "Corridor": {"width": 150, "height": 400},
            "Secret Room": {"width": 200, "height": 200},
            "Trap Room": {"width": 300, "height": 300},
            "Storage": {"width": 200, "height": 250},
            "Guard Post": {"width": 250, "height": 250},
        }
    else:
        dimensions_map = {
            "Bedroom": {"width": 350, "height": 400},
            "Bathroom": {"width": 250, "height": 300},
            "Kitchen": {"width": 400, "height": 350},
            "Living Room": {"width": 500, "height": 450},
            "Dining Room": {"width": 400, "height": 400},
            "Hallway": {"width": 150, "height": 400},
            "Closet": {"width": 200, "height": 150},
            "Office": {"width": 350, "height": 350},
            "Garage": {"width": 600, "height": 600},
            "Pantry": {"width": 200, "height": 250},
        }
    
    return dimensions_map.get(room_type, {"width": 300, "height": 300})


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
    Handle room extension request.
    
    Expected event:
    {
        "pathParameters": {
            "id": "job_id"
        },
        "body": {
            "action": "generate" | "suggest" | "validate",
            "door_location": [x, y],
            "door_direction": "N/S/E/W",
            "current_room_type": "Kitchen",
            "room_type": "optional",
            "mode": "realistic" | "fantasy"
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
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        action = body.get('action', 'generate')
        door_location = body.get('door_location')
        door_direction = body.get('door_direction')
        current_room_type = body.get('current_room_type', 'Room')
        room_type = body.get('room_type')
        mode = body.get('mode', 'realistic')
        
        # Get job from DynamoDB
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
        existing_rooms = job.get('results', [])
        extended_rooms = job.get('extended_rooms', [])
        all_rooms = existing_rooms + extended_rooms
        
        # Handle different actions
        if action == 'generate-from-labels':
            # Generate rooms from selected text labels
            from label_room_generator import generate_rooms_from_selected_labels
            from config import MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT
            
            selected_label_indices = body.get('selected_label_indices', [])
            generate_all = body.get('generate_all', False)
            label_position_adjustments = body.get('label_position_adjustments', {})
            manual_labels = body.get('manual_labels', {})  # Manual labels from frontend
            
            # Get text labels from job metadata
            metadata = job.get('metadata', {})
            text_labels = list(metadata.get('text_labels', []))  # Convert to list for modification
            
            # Merge manual labels into text_labels list
            # Manual labels are sent as a dict with index as key
            for idx_str, manual_label in manual_labels.items():
                idx = int(idx_str)
                # Extend text_labels list if needed
                while len(text_labels) <= idx:
                    text_labels.append(None)
                # Insert manual label at the correct index
                text_labels[idx] = manual_label
            
            if not text_labels or all(label is None for label in text_labels):
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'No text labels found in job metadata. Please ensure detection completed successfully.',
                        'error_code': 'NO_TEXT_LABELS'
                    })
                }
            
            # Filter out labels already matched to detected rooms
            matched_label_texts = set()
            for room in existing_rooms:
                if room.get('name_source') == 'blueprint_text':
                    matched_label_texts.add(room.get('name_hint', '').lower())
            
            # Filter labels - skip those already matched, None, or manual labels
            available_labels = []
            for idx, label in enumerate(text_labels):
                if label is None:
                    continue
                # Skip manual labels for "generate all" - they should be generated individually
                is_manual = label.get('is_manual', False)
                if is_manual and generate_all:
                    continue
                label_text = label.get('text', '').lower()
                # Check if this label was already matched (check original_text if available)
                original_text = label.get('original_text', label_text).lower()
                if original_text not in matched_label_texts and label_text not in matched_label_texts:
                    available_labels.append((idx, label))
            
            if not available_labels:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'All labels have already been matched to detected rooms',
                        'error_code': 'NO_AVAILABLE_LABELS'
                    })
                }
            
            # Determine which labels to generate
            if generate_all:
                label_indices_to_generate = [idx for idx, _ in available_labels]
            else:
                # Use selected indices, but filter to only available labels
                available_indices = {idx for idx, _ in available_labels}
                label_indices_to_generate = [idx for idx in selected_label_indices if idx in available_indices]
            
            if not label_indices_to_generate:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'No valid labels selected for generation',
                        'error_code': 'NO_LABELS_SELECTED'
                    })
                }
            
            # Get image from S3 for edge detection
            s3_key = job.get('s3_key')
            if not s3_key:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Image not found in job',
                        'error_code': 'IMAGE_NOT_FOUND'
                    })
                }
            
            # Download image
            s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            image_data = s3_response['Body'].read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Determine image format
            file_ext = s3_key.split('.')[-1].lower()
            image_format = 'png' if file_ext == 'png' else 'jpg'
            
            # Canvas bounds
            canvas_bounds = [0, 0, MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT]
            
            # Generate rooms from selected labels
            result = generate_rooms_from_selected_labels(
                image_base64,
                label_indices_to_generate,
                text_labels,
                all_rooms,
                canvas_bounds,
                label_position_adjustments
            )
            
            generated_rooms = result.get('rooms', [])
            warnings = result.get('warnings', [])
            
            # Add generated rooms to extended_rooms
            new_extended_rooms = extended_rooms + generated_rooms
            
            # Update job in DynamoDB
            update_expression = 'SET extended_rooms = :extended_rooms, updated_at = :updated'
            expression_values = {
                ':extended_rooms': convert_floats_to_decimal(new_extended_rooms),
                ':updated': datetime.utcnow().isoformat()
            }
            
            table.update_item(
                Key={'job_id': job_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'extended_rooms': new_extended_rooms,
                    'generated_count': len(generated_rooms),
                    'warnings': warnings
                }, default=str)
            }
        
        elif action == 'suggest':
            # Get room type suggestions
            if not door_direction or not current_room_type:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Missing door_direction or current_room_type',
                        'error_code': 'MISSING_PARAMETERS'
                    })
                }
            
            suggestions_result = suggest_room_type(current_room_type, door_direction, mode)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'suggestions': suggestions_result.get('suggestions', [])
                })
            }
        
        elif action == 'generate':
            # Generate a new room from door
            # Uses blueprint-first approach: check surrounding boundaries first, use generic if none
            if not door_location or not door_direction:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Missing door_location or door_direction',
                        'error_code': 'MISSING_PARAMETERS'
                    })
                }
            
            # Get room type if not provided
            if room_type is None:
                suggestions_result = suggest_room_type(current_room_type, door_direction, mode)
                if suggestions_result.get("success") and suggestions_result.get("suggestions"):
                    suggestions = suggestions_result["suggestions"]
                    suggestions.sort(key=lambda x: x.get("probability", 0), reverse=True)
                    room_type = suggestions[0]["room_type"]
                else:
                    room_type = "Room"
            
            # Get image from S3 for boundary detection
            s3_key = job.get('s3_key')
            if not s3_key:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Image not found in job',
                        'error_code': 'IMAGE_NOT_FOUND'
                    })
                }
            
            # Download image
            s3_response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            image_data = s3_response['Body'].read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Determine image format
            file_ext = s3_key.split('.')[-1].lower()
            image_format = 'png' if file_ext == 'png' else 'jpg'
            
            # Get all existing rooms (including modified)
            modified_rooms = job.get('modified_rooms', [])
            all_existing_rooms = existing_rooms + extended_rooms + modified_rooms
            
            # Canvas bounds
            from config import MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT
            canvas_bounds = [0, 0, MAX_CANVAS_WIDTH, MAX_CANVAS_HEIGHT]
            
            # Use label-based room generator which checks boundaries first
            from label_room_generator import generate_room_from_door
            
            generation_result = generate_room_from_door(
                door_location,
                door_direction,
                room_type,
                image_base64,
                all_existing_rooms,
                canvas_bounds,
                mode
            )
            
            if not generation_result.get('success'):
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': generation_result.get('error', 'Generation failed'),
                        'error_code': 'GENERATION_ERROR'
                    })
                }
            
            new_room = generation_result['room']
            
            # Validate placement (check for overlaps)
            validation_result = validate_room_placement(
                new_room['polygon'],
                all_existing_rooms
            )
            
            if not validation_result.get('valid'):
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': validation_result.get('error', 'Invalid placement'),
                        'error_code': 'INVALID_PLACEMENT',
                        'overlapping_room_id': validation_result.get('overlapping_room_id')
                    })
                }
            
            # Add to extended rooms
            extended_rooms.append(new_room)
            
            # Update job in DynamoDB
            table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET extended_rooms = :extended, updated_at = :updated',
                ExpressionAttributeValues={
                    ':extended': convert_floats_to_decimal(extended_rooms),
                    ':updated': datetime.utcnow().isoformat()
                }
            )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'room': new_room,
                    'message': 'Room generated successfully'
                })
            }
        
        elif action == 'validate':
            # Validate a room placement
            room_polygon = body.get('room_polygon')
            
            if not room_polygon:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Missing room_polygon',
                        'error_code': 'MISSING_PARAMETERS'
                    })
                }
            
            validation_result = validate_room_placement(room_polygon, all_rooms)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'valid': validation_result.get('valid', False),
                    'error': validation_result.get('error'),
                    'overlapping_room_id': validation_result.get('overlapping_room_id')
                })
            }
        
        elif action == 'update_plan':
            # Update modified rooms, extended rooms, and doors
            modified_rooms = body.get('modified_rooms')
            updated_extended_rooms = body.get('extended_rooms')
            updated_doors = body.get('doors')
            
            update_expression_parts = ['updated_at = :updated']
            expression_values = {':updated': datetime.utcnow().isoformat()}
            
            # Only update fields that are explicitly provided
            if modified_rooms is not None:
                update_expression_parts.append('modified_rooms = :modified')
                expression_values[':modified'] = convert_floats_to_decimal(modified_rooms)
            
            if updated_extended_rooms is not None:
                update_expression_parts.append('extended_rooms = :extended')
                expression_values[':extended'] = convert_floats_to_decimal(updated_extended_rooms)
            
            if updated_doors is not None:
                update_expression_parts.append('doors = :doors')
                expression_values[':doors'] = convert_floats_to_decimal(updated_doors)
            
            # Only update if there's something to update
            if len(update_expression_parts) > 1:
                # Update job in DynamoDB
                table.update_item(
                    Key={'job_id': job_id},
                    UpdateExpression=f'SET {", ".join(update_expression_parts)}',
                    ExpressionAttributeValues=expression_values
                )
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'job_id': job_id,
                    'message': 'Plan updated successfully'
                })
            }
        
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f'Unknown action: {action}',
                    'error_code': 'UNKNOWN_ACTION'
                })
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
                'error_code': 'EXTENSION_ERROR'
            })
        }

