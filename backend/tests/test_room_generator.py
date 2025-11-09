"""
Unit tests for room_generator.py
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from room_generator import (
    generate_room_polygon,
    suggest_room_types,
    validate_room_placement,
    calculate_room_dimensions
)


class TestRoomGenerator:
    """Test suite for procedural room generation"""
    
    def test_generate_room_polygon_basic(self):
        """Test basic room polygon generation"""
        door_location = [500, 500]
        room_type = "Bedroom"
        mode = "realistic"
        
        polygon = generate_room_polygon(door_location, room_type, mode)
        
        assert polygon is not None
        assert len(polygon) >= 4  # At least a rectangle
        assert all(isinstance(p, list) and len(p) == 2 for p in polygon)
    
    def test_generate_room_polygon_fantasy_mode(self):
        """Test room generation in fantasy mode"""
        door_location = [500, 500]
        room_type = "Throne Room"
        mode = "fantasy"
        
        polygon = generate_room_polygon(door_location, room_type, mode)
        
        assert polygon is not None
        # Fantasy rooms might have more complex shapes
        assert len(polygon) >= 4
    
    def test_suggest_room_types_realistic(self):
        """Test room type suggestions in realistic mode"""
        current_room_type = "Hallway"
        mode = "realistic"
        
        suggestions = suggest_room_types(current_room_type, mode)
        
        assert len(suggestions) > 0
        assert all('room_type' in s for s in suggestions)
        assert all('confidence' in s for s in suggestions)
        assert all('reasoning' in s for s in suggestions)
    
    def test_suggest_room_types_fantasy(self):
        """Test room type suggestions in fantasy mode"""
        current_room_type = "Great Hall"
        mode = "fantasy"
        
        suggestions = suggest_room_types(current_room_type, mode)
        
        assert len(suggestions) > 0
        # Fantasy suggestions should include fantasy-appropriate rooms
        room_types = [s['room_type'] for s in suggestions]
        assert any('treasure' in rt.lower() or 'throne' in rt.lower() 
                  for rt in room_types)
    
    def test_validate_room_placement_no_overlap(self):
        """Test validation with no overlaps"""
        new_room = {
            'polygon': [[100, 100], [200, 100], [200, 200], [100, 200]],
            'bounding_box': [100, 100, 200, 200]
        }
        existing_rooms = [
            {
                'polygon': [[300, 300], [400, 300], [400, 400], [300, 400]],
                'bounding_box': [300, 300, 400, 400]
            }
        ]
        
        validation = validate_room_placement(new_room, existing_rooms)
        
        assert validation['is_valid'] is True
        assert len(validation['overlaps']) == 0
    
    def test_validate_room_placement_with_overlap(self):
        """Test validation detects overlaps"""
        new_room = {
            'polygon': [[100, 100], [200, 100], [200, 200], [100, 200]],
            'bounding_box': [100, 100, 200, 200]
        }
        existing_rooms = [
            {
                'id': 'room_001',
                'polygon': [[150, 150], [250, 150], [250, 250], [150, 250]],
                'bounding_box': [150, 150, 250, 250]
            }
        ]
        
        validation = validate_room_placement(new_room, existing_rooms)
        
        assert validation['is_valid'] is False
        assert len(validation['overlaps']) > 0
        assert validation['overlaps'][0] == 'room_001'
    
    def test_calculate_room_dimensions_realistic(self):
        """Test dimension calculation for realistic rooms"""
        room_type = "Bedroom"
        mode = "realistic"
        
        dimensions = calculate_room_dimensions(room_type, mode)
        
        assert 'width' in dimensions
        assert 'height' in dimensions
        assert dimensions['width'] > 0
        assert dimensions['height'] > 0
        # Realistic bedrooms should be reasonably sized
        assert 100 <= dimensions['width'] <= 300
        assert 100 <= dimensions['height'] <= 300
    
    def test_calculate_room_dimensions_fantasy(self):
        """Test dimension calculation for fantasy rooms"""
        room_type = "Throne Room"
        mode = "fantasy"
        
        dimensions = calculate_room_dimensions(room_type, mode)
        
        assert 'width' in dimensions
        assert 'height' in dimensions
        # Fantasy rooms can be larger
        assert dimensions['width'] > 0
        assert dimensions['height'] > 0


class TestAdjacencyPatterns:
    """Test adjacency pattern logic"""
    
    def test_get_adjacent_room_types_residential(self):
        """Test adjacency patterns for residential rooms"""
        from adjacency_patterns import get_adjacent_room_types
        
        adjacent = get_adjacent_room_types("Bedroom", "realistic")
        
        assert len(adjacent) > 0
        assert "Bathroom" in adjacent or "Hallway" in adjacent
    
    def test_get_adjacent_room_types_fantasy(self):
        """Test adjacency patterns for fantasy rooms"""
        from adjacency_patterns import get_adjacent_room_types
        
        adjacent = get_adjacent_room_types("Throne Room", "fantasy")
        
        assert len(adjacent) > 0
        # Throne rooms typically connect to grand spaces
        assert any('hall' in r.lower() or 'court' in r.lower() 
                  for r in adjacent)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

