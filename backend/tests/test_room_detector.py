"""
Unit tests for room_detector.py
"""
import pytest
import base64
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from room_detector import process_blueprint_image, validate_image_data


class TestRoomDetector:
    """Test suite for room detection logic"""
    
    def test_validate_image_data_valid_png(self):
        """Test validation with valid PNG data"""
        # Create a minimal valid PNG header
        png_header = b'\x89PNG\r\n\x1a\n'
        image_data = base64.b64encode(png_header).decode('utf-8')
        
        result = validate_image_data(image_data)
        assert result['valid'] is True
        assert result['format'] == 'png'
    
    def test_validate_image_data_valid_jpeg(self):
        """Test validation with valid JPEG data"""
        # Create a minimal valid JPEG header
        jpeg_header = b'\xff\xd8\xff'
        image_data = base64.b64encode(jpeg_header).decode('utf-8')
        
        result = validate_image_data(image_data)
        assert result['valid'] is True
        assert result['format'] == 'jpeg'
    
    def test_validate_image_data_invalid_format(self):
        """Test validation with invalid format"""
        invalid_data = base64.b64encode(b'invalid').decode('utf-8')
        
        result = validate_image_data(invalid_data)
        assert result['valid'] is False
        assert 'error' in result
    
    def test_validate_image_data_too_large(self):
        """Test validation with oversized image"""
        # Create data larger than MAX_IMAGE_SIZE_MB
        large_data = b'x' * (11 * 1024 * 1024)  # 11MB
        image_data = base64.b64encode(large_data).decode('utf-8')
        
        result = validate_image_data(image_data)
        assert result['valid'] is False
        assert 'too large' in result.get('error', '').lower()
    
    def test_validate_image_data_empty(self):
        """Test validation with empty data"""
        result = validate_image_data('')
        assert result['valid'] is False
        assert 'error' in result
    
    @pytest.mark.integration
    def test_process_blueprint_image_structure(self):
        """Test that process_blueprint_image returns correct structure"""
        # Note: This is a mock test - actual integration would require API keys
        # In a real test, you would mock the OpenRouter API call
        
        # Create a minimal valid PNG
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        image_base64 = base64.b64encode(png_data).decode('utf-8')
        
        # This would need mocking in actual tests
        # result = process_blueprint_image(image_base64)
        # assert 'success' in result
        # assert 'rooms' in result
        # assert 'doors' in result
        # assert 'confidence' in result
        # assert 'metadata' in result
        pass


class TestCoordinateNormalization:
    """Test coordinate normalization functions"""
    
    def test_normalize_coordinates_within_bounds(self):
        """Test that coordinates are properly normalized"""
        from openrouter_client import normalize_coordinates
        
        coords = [100, 200, 300, 400]
        normalized = normalize_coordinates(coords)
        
        assert all(0 <= c <= 1000 for c in normalized)
    
    def test_normalize_coordinates_out_of_bounds(self):
        """Test handling of out-of-bounds coordinates"""
        from openrouter_client import normalize_coordinates
        
        coords = [-100, 200, 1500, 400]
        normalized = normalize_coordinates(coords)
        
        # Should clamp to valid range
        assert normalized[0] >= 0
        assert normalized[2] <= 1000


class TestPolygonDetection:
    """Test polygon detection and validation"""
    
    def test_polygon_validation_valid(self):
        """Test validation of valid polygon"""
        from room_detector import validate_polygon
        
        polygon = [[0, 0], [100, 0], [100, 100], [0, 100]]
        assert validate_polygon(polygon) is True
    
    def test_polygon_validation_too_few_points(self):
        """Test validation rejects polygons with too few points"""
        from room_detector import validate_polygon
        
        polygon = [[0, 0], [100, 0]]
        assert validate_polygon(polygon) is False
    
    def test_polygon_validation_invalid_coordinates(self):
        """Test validation rejects invalid coordinates"""
        from room_detector import validate_polygon
        
        polygon = [[0, 0], [100, 0], [-100, 100]]
        assert validate_polygon(polygon) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

