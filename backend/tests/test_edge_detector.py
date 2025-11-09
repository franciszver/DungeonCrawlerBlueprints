"""
Unit tests for edge detector dispatcher (OpenCV + PIL fallback).
"""
import pytest
import base64
import sys
import os
from io import BytesIO
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from edge_detector import refine_room_boundaries


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestEdgeDetectorDispatcher:
    """Test the edge detector dispatcher logic"""
    
    def create_test_image(self, width=200, height=200):
        """Create a test image"""
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        draw.rectangle([50, 50, 150, 150], outline='black', width=3)
        return image
    
    def image_to_base64(self, image):
        """Convert PIL image to base64 string"""
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def test_refine_room_boundaries_pil_fallback(self):
        """Test that PIL is used when OpenCV is not available"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        # Mock OpenCV as unavailable
        with patch('edge_detector.OPENCV_AVAILABLE', False):
            result = refine_room_boundaries(
                image_base64,
                rooms,
                threshold=50
            )
        
        assert result['success'] is True
        assert result.get('method') == 'PIL'
    
    def test_refine_room_boundaries_opencv_preferred(self):
        """Test that OpenCV is preferred when available"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        # Mock OpenCV as available and working
        with patch('edge_detector.OPENCV_AVAILABLE', True):
            with patch('edge_detector.refine_room_boundaries_opencv') as mock_opencv:
                mock_opencv.return_value = {
                    'success': True,
                    'refined_rooms': rooms,
                    'stats': {'total_rooms': 1, 'refined_rooms': 1, 'vertices_snapped': 4},
                    'method': 'OpenCV'
                }
                
                result = refine_room_boundaries(
                    image_base64,
                    rooms,
                    threshold=50
                )
        
        assert result['success'] is True
        assert result.get('method') == 'OpenCV'
        mock_opencv.assert_called_once()
    
    def test_refine_room_boundaries_opencv_fallback_to_pil(self):
        """Test that PIL is used when OpenCV fails"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        # Mock OpenCV as available but failing
        with patch('edge_detector.OPENCV_AVAILABLE', True):
            with patch('edge_detector.refine_room_boundaries_opencv') as mock_opencv:
                mock_opencv.return_value = {
                    'success': False,
                    'error': 'OpenCV processing failed'
                }
                
                result = refine_room_boundaries(
                    image_base64,
                    rooms,
                    threshold=50
                )
        
        # Should fall back to PIL
        assert result['success'] is True
        assert result.get('method') == 'PIL'
    
    def test_refine_room_boundaries_opencv_exception_fallback(self):
        """Test that PIL is used when OpenCV raises exception"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        # Mock OpenCV as available but raising exception
        with patch('edge_detector.OPENCV_AVAILABLE', True):
            with patch('edge_detector.refine_room_boundaries_opencv') as mock_opencv:
                mock_opencv.side_effect = Exception("OpenCV error")
                
                result = refine_room_boundaries(
                    image_base64,
                    rooms,
                    threshold=50
                )
        
        # Should fall back to PIL
        assert result['success'] is True
        assert result.get('method') == 'PIL'
    
    def test_refine_room_boundaries_no_libraries_available(self):
        """Test error when neither PIL nor OpenCV is available"""
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        # Mock both as unavailable
        with patch('edge_detector.OPENCV_AVAILABLE', False):
            with patch('edge_detector.PIL_AVAILABLE', False):
                result = refine_room_boundaries(
                    "dummy_base64",
                    rooms,
                    threshold=50
                )
        
        assert result['success'] is False
        assert 'error' in result
        assert 'PIL' in result['error'] or 'Pillow' in result['error']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

