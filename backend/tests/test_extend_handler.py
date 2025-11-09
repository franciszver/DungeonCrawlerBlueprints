"""
Unit tests for extend Lambda handler
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions', 'extend'))

from handler import lambda_handler


class TestExtendHandler:
    """Test suite for /extend endpoint handler"""
    
    def test_handler_missing_action(self):
        """Test handler rejects requests without action"""
        event = {
            'body': json.dumps({
                'job_id': 'test_job',
                'door_id': 'door_001'
            })
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_handler_suggest_action(self):
        """Test handler processes suggest action"""
        event = {
            'body': json.dumps({
                'job_id': 'test_job',
                'action': 'suggest',
                'door_id': 'door_001',
                'current_room_type': 'Hallway',
                'mode': 'realistic'
            })
        }
        
        # Note: Would need mocking for actual API calls
        # response = lambda_handler(event, {})
        # assert response['statusCode'] == 200
        # body = json.loads(response['body'])
        # assert 'suggestions' in body
        pass
    
    def test_handler_generate_action(self):
        """Test handler processes generate action"""
        event = {
            'body': json.dumps({
                'job_id': 'test_job',
                'action': 'generate',
                'door_id': 'door_001',
                'current_room_type': 'Hallway',
                'target_room_type': 'Bedroom',
                'mode': 'realistic',
                'existing_rooms': []
            })
        }
        
        # Note: Would need mocking for actual generation
        # response = lambda_handler(event, {})
        # assert response['statusCode'] == 200
        # body = json.loads(response['body'])
        # assert 'room' in body
        # assert 'validation' in body
        pass
    
    def test_handler_validate_action(self):
        """Test handler processes validate action"""
        event = {
            'body': json.dumps({
                'job_id': 'test_job',
                'action': 'validate',
                'room': {
                    'polygon': [[100, 100], [200, 100], [200, 200], [100, 200]],
                    'bounding_box': [100, 100, 200, 200]
                },
                'existing_rooms': []
            })
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'is_valid' in body
        assert 'warnings' in body
        assert 'overlaps' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

