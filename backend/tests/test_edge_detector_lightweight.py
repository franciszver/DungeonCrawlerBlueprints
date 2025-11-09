"""
Unit tests for lightweight edge detection (PIL-based).
"""
import pytest
import base64
import sys
import os
from io import BytesIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from edge_detector_lightweight import (
    refine_room_boundaries_lightweight,
    _detect_lines_pil,
    _snap_polygon_to_edges_pil,
    _find_nearest_edge_point_pil,
    _point_to_line_segment_distance_pil,
    _polygon_to_bbox
)


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestEdgeDetectorLightweight:
    """Test suite for PIL-based edge detection"""
    
    def create_test_image(self, width=200, height=200, draw_rectangle=True):
        """Create a test image with optional rectangle"""
        image = Image.new('RGB', (width, height), color='white')
        if draw_rectangle:
            draw = ImageDraw.Draw(image)
            # Draw a rectangle (simulating a room boundary)
            draw.rectangle([50, 50, 150, 150], outline='black', width=3)
        return image
    
    def image_to_base64(self, image):
        """Convert PIL image to base64 string"""
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def test_refine_room_boundaries_success(self):
        """Test successful refinement with valid input"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        result = refine_room_boundaries_lightweight(
            image_base64,
            rooms,
            threshold=50
        )
        
        assert result['success'] is True
        assert 'refined_rooms' in result
        assert 'stats' in result
        assert result['method'] == 'PIL'
        assert len(result['refined_rooms']) == 1
        assert 'refined_rooms' in result['stats']
    
    def test_refine_room_boundaries_empty_rooms(self):
        """Test with empty rooms list"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        result = refine_room_boundaries_lightweight(
            image_base64,
            [],
            threshold=50
        )
        
        assert result['success'] is True
        assert result['stats']['total_rooms'] == 0
        assert len(result['refined_rooms']) == 0
    
    def test_refine_room_boundaries_invalid_polygon(self):
        """Test with invalid polygon (too few points)"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60]],  # Only 2 points (invalid)
            'bounding_box': [60, 60, 140, 60]
        }]
        
        result = refine_room_boundaries_lightweight(
            image_base64,
            rooms,
            threshold=50
        )
        
        # Should succeed but keep room as-is
        assert result['success'] is True
        assert len(result['refined_rooms']) == 1
    
    def test_refine_room_boundaries_no_polygon(self):
        """Test with room missing polygon"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'bounding_box': [60, 60, 140, 140]
        }]
        
        result = refine_room_boundaries_lightweight(
            image_base64,
            rooms,
            threshold=50
        )
        
        # Should succeed but keep room as-is
        assert result['success'] is True
        assert len(result['refined_rooms']) == 1
    
    def test_refine_room_boundaries_invalid_image(self):
        """Test with invalid base64 image data"""
        invalid_base64 = "not_valid_base64"
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        result = refine_room_boundaries_lightweight(
            invalid_base64,
            rooms,
            threshold=50
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert 'refined_rooms' in result  # Should return original rooms
    
    def test_refine_room_boundaries_custom_threshold(self):
        """Test with custom threshold value"""
        image = self.create_test_image()
        image_base64 = self.image_to_base64(image)
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        result = refine_room_boundaries_lightweight(
            image_base64,
            rooms,
            threshold=100  # Larger threshold
        )
        
        assert result['success'] is True
        assert result['stats']['total_rooms'] == 1
    
    def test_refine_room_boundaries_multiple_rooms(self):
        """Test with multiple rooms"""
        image = self.create_test_image(width=400, height=400)
        draw = ImageDraw.Draw(image)
        # Draw two rectangles
        draw.rectangle([50, 50, 150, 150], outline='black', width=3)
        draw.rectangle([200, 200, 300, 300], outline='black', width=3)
        
        image_base64 = self.image_to_base64(image)
        
        rooms = [
            {
                'id': 'room1',
                'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
                'bounding_box': [60, 60, 140, 140]
            },
            {
                'id': 'room2',
                'polygon': [[210, 210], [290, 210], [290, 290], [210, 290]],
                'bounding_box': [210, 210, 290, 290]
            }
        ]
        
        result = refine_room_boundaries_lightweight(
            image_base64,
            rooms,
            threshold=50
        )
        
        assert result['success'] is True
        assert len(result['refined_rooms']) == 2
        assert result['stats']['total_rooms'] == 2


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestEdgeDetectionHelpers:
    """Test helper functions for edge detection"""
    
    def test_polygon_to_bbox(self):
        """Test polygon to bounding box conversion"""
        polygon = [[10, 20], [100, 20], [100, 80], [10, 80]]
        bbox = _polygon_to_bbox(polygon)
        
        assert bbox == [10, 20, 100, 80]
    
    def test_polygon_to_bbox_empty(self):
        """Test polygon to bbox with empty polygon"""
        bbox = _polygon_to_bbox([])
        assert bbox == [0, 0, 0, 0]
    
    def test_point_to_line_segment_distance(self):
        """Test point to line segment distance calculation"""
        # Point at (0, 0), line from (0, 10) to (10, 10)
        point, distance = _point_to_line_segment_distance_pil(
            0, 0, 0, 10, 10, 10
        )
        
        assert distance == 10.0  # Distance from (0,0) to line y=10
        assert point == (0, 10)  # Closest point on line
    
    def test_point_to_line_segment_distance_on_line(self):
        """Test point that lies on the line segment"""
        point, distance = _point_to_line_segment_distance_pil(
            5, 10, 0, 10, 10, 10
        )
        
        assert distance == 0.0  # Point is on the line
        assert point == (5, 10)
    
    def test_point_to_line_segment_distance_degenerate(self):
        """Test with degenerate line (point)"""
        point, distance = _point_to_line_segment_distance_pil(
            5, 5, 10, 10, 10, 10  # Line is a single point
        )
        
        # Should return distance to that point
        assert distance > 0
        assert point == (10, 10)


@pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not available")
class TestEdgeDetectionEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_refine_with_very_large_image(self):
        """Test with very large image (should handle gracefully)"""
        # Create a large image
        image = Image.new('RGB', (5000, 5000), color='white')
        image_base64 = base64.b64encode(
            BytesIO().write(image.tobytes())
        ).decode('utf-8')
        
        # This might fail or be slow, but shouldn't crash
        rooms = [{
            'id': 'room1',
            'polygon': [[100, 100], [200, 100], [200, 200], [100, 200]],
            'bounding_box': [100, 100, 200, 200]
        }]
        
        # Should either succeed or return a clear error
        result = refine_room_boundaries_lightweight(
            image_base64,
            rooms,
            threshold=50
        )
        
        # Result should have success flag
        assert 'success' in result
    
    def test_refine_with_very_small_threshold(self):
        """Test with very small threshold (should still work)"""
        image = Image.new('RGB', (200, 200), color='white')
        draw = ImageDraw.Draw(image)
        draw.rectangle([50, 50, 150, 150], outline='black', width=3)
        
        image_base64 = base64.b64encode(
            BytesIO(image.tobytes()).getvalue()
        ).decode('utf-8')
        
        rooms = [{
            'id': 'room1',
            'polygon': [[60, 60], [140, 60], [140, 140], [60, 140]],
            'bounding_box': [60, 60, 140, 140]
        }]
        
        result = refine_room_boundaries_lightweight(
            image_base64,
            rooms,
            threshold=1  # Very small threshold
        )
        
        assert result['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

