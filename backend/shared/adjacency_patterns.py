"""Room adjacency patterns for realistic and fantasy floor plans."""
from typing import Dict, List, Tuple

# Realistic architectural adjacency patterns
# Format: {room_type: {direction: [(connected_room_type, probability), ...]}}
REALISTIC_ADJACENCY = {
    "Kitchen": {
        "N": [("Dining Room", 0.4), ("Pantry", 0.3), ("Hallway", 0.3)],
        "S": [("Garage", 0.3), ("Backyard", 0.3), ("Utility Room", 0.2), ("Hallway", 0.2)],
        "E": [("Dining Room", 0.4), ("Living Room", 0.3), ("Hallway", 0.3)],
        "W": [("Pantry", 0.4), ("Utility Room", 0.3), ("Hallway", 0.3)]
    },
    "Living Room": {
        "N": [("Hallway", 0.4), ("Bedroom", 0.3), ("Office", 0.3)],
        "S": [("Patio", 0.4), ("Deck", 0.3), ("Hallway", 0.3)],
        "E": [("Dining Room", 0.4), ("Kitchen", 0.3), ("Hallway", 0.3)],
        "W": [("Hallway", 0.4), ("Office", 0.3), ("Bedroom", 0.3)]
    },
    "Bedroom": {
        "N": [("Closet", 0.4), ("Bathroom", 0.3), ("Hallway", 0.3)],
        "S": [("Hallway", 0.5), ("Bathroom", 0.3), ("Closet", 0.2)],
        "E": [("Bathroom", 0.4), ("Closet", 0.3), ("Hallway", 0.3)],
        "W": [("Hallway", 0.4), ("Closet", 0.3), ("Bathroom", 0.3)]
    },
    "Bathroom": {
        "N": [("Hallway", 0.5), ("Bedroom", 0.5)],
        "S": [("Hallway", 0.5), ("Bedroom", 0.5)],
        "E": [("Bedroom", 0.6), ("Hallway", 0.4)],
        "W": [("Bedroom", 0.6), ("Hallway", 0.4)]
    },
    "Hallway": {
        "N": [("Bedroom", 0.3), ("Bathroom", 0.2), ("Office", 0.2), ("Hallway", 0.3)],
        "S": [("Living Room", 0.3), ("Kitchen", 0.2), ("Hallway", 0.3), ("Garage", 0.2)],
        "E": [("Bedroom", 0.3), ("Bathroom", 0.2), ("Closet", 0.2), ("Hallway", 0.3)],
        "W": [("Bedroom", 0.3), ("Office", 0.2), ("Storage", 0.2), ("Hallway", 0.3)]
    },
    "Dining Room": {
        "N": [("Hallway", 0.4), ("Kitchen", 0.3), ("Living Room", 0.3)],
        "S": [("Patio", 0.4), ("Kitchen", 0.3), ("Hallway", 0.3)],
        "E": [("Living Room", 0.5), ("Hallway", 0.5)],
        "W": [("Kitchen", 0.6), ("Hallway", 0.4)]
    },
    "Office": {
        "N": [("Hallway", 0.5), ("Closet", 0.3), ("Bathroom", 0.2)],
        "S": [("Hallway", 0.5), ("Living Room", 0.3), ("Patio", 0.2)],
        "E": [("Hallway", 0.6), ("Closet", 0.4)],
        "W": [("Hallway", 0.6), ("Storage", 0.4)]
    },
    "Garage": {
        "N": [("Kitchen", 0.4), ("Utility Room", 0.3), ("Hallway", 0.3)],
        "S": [("Driveway", 0.8), ("Storage", 0.2)],
        "E": [("Hallway", 0.5), ("Storage", 0.3), ("Utility Room", 0.2)],
        "W": [("Storage", 0.5), ("Hallway", 0.5)]
    }
}

# Fantasy/dungeon adjacency patterns
FANTASY_ADJACENCY = {
    "Entrance Hall": {
        "N": [("Corridor", 0.4), ("Guard Post", 0.3), ("Main Chamber", 0.3)],
        "S": [("Exit", 0.6), ("Trap Room", 0.4)],
        "E": [("Corridor", 0.5), ("Side Room", 0.5)],
        "W": [("Corridor", 0.5), ("Side Room", 0.5)]
    },
    "Corridor": {
        "N": [("Chamber", 0.3), ("Corridor", 0.3), ("Secret Room", 0.2), ("Trap Room", 0.2)],
        "S": [("Chamber", 0.3), ("Corridor", 0.3), ("Storage", 0.2), ("Guard Post", 0.2)],
        "E": [("Chamber", 0.3), ("Corridor", 0.3), ("Side Room", 0.2), ("Secret Room", 0.2)],
        "W": [("Chamber", 0.3), ("Corridor", 0.3), ("Side Room", 0.2), ("Storage", 0.2)]
    },
    "Boss Chamber": {
        "N": [("Treasure Room", 0.5), ("Secret Room", 0.3), ("Exit", 0.2)],
        "S": [("Corridor", 0.6), ("Trap Room", 0.4)],
        "E": [("Treasure Room", 0.4), ("Secret Room", 0.3), ("Corridor", 0.3)],
        "W": [("Treasure Room", 0.4), ("Secret Room", 0.3), ("Corridor", 0.3)]
    },
    "Treasure Room": {
        "N": [("Secret Room", 0.5), ("Boss Chamber", 0.5)],
        "S": [("Trap Room", 0.5), ("Corridor", 0.5)],
        "E": [("Secret Room", 0.6), ("Corridor", 0.4)],
        "W": [("Secret Room", 0.6), ("Corridor", 0.4)]
    },
    "Guard Post": {
        "N": [("Corridor", 0.5), ("Barracks", 0.3), ("Armory", 0.2)],
        "S": [("Corridor", 0.6), ("Entrance Hall", 0.4)],
        "E": [("Corridor", 0.5), ("Storage", 0.3), ("Barracks", 0.2)],
        "W": [("Corridor", 0.5), ("Armory", 0.3), ("Storage", 0.2)]
    },
    "Trap Room": {
        "N": [("Treasure Room", 0.4), ("Corridor", 0.4), ("Secret Room", 0.2)],
        "S": [("Corridor", 0.6), ("Pit", 0.4)],
        "E": [("Corridor", 0.5), ("Side Room", 0.3), ("Secret Room", 0.2)],
        "W": [("Corridor", 0.5), ("Side Room", 0.3), ("Secret Room", 0.2)]
    },
    "Secret Room": {
        "N": [("Treasure Room", 0.5), ("Boss Chamber", 0.3), ("Hidden Passage", 0.2)],
        "S": [("Corridor", 0.5), ("Trap Room", 0.3), ("Hidden Passage", 0.2)],
        "E": [("Treasure Room", 0.4), ("Corridor", 0.4), ("Hidden Passage", 0.2)],
        "W": [("Treasure Room", 0.4), ("Corridor", 0.4), ("Hidden Passage", 0.2)]
    },
    "Chamber": {
        "N": [("Corridor", 0.4), ("Side Room", 0.3), ("Storage", 0.3)],
        "S": [("Corridor", 0.5), ("Trap Room", 0.3), ("Exit", 0.2)],
        "E": [("Corridor", 0.5), ("Side Room", 0.3), ("Secret Room", 0.2)],
        "W": [("Corridor", 0.5), ("Side Room", 0.3), ("Storage", 0.2)]
    }
}


def get_adjacency_suggestions(room_type: str, direction: str, mode: str = "realistic") -> List[Tuple[str, float]]:
    """
    Get room type suggestions based on adjacency patterns.
    
    Args:
        room_type: Current room type
        direction: Door direction (N/S/E/W)
        mode: "realistic" or "fantasy"
        
    Returns:
        List of (room_type, probability) tuples
    """
    patterns = FANTASY_ADJACENCY if mode == "fantasy" else REALISTIC_ADJACENCY
    
    # Get patterns for this room type and direction
    if room_type in patterns and direction in patterns[room_type]:
        return patterns[room_type][direction]
    
    # Fallback suggestions
    if mode == "fantasy":
        return [
            ("Corridor", 0.4),
            ("Chamber", 0.3),
            ("Side Room", 0.3)
        ]
    else:
        return [
            ("Hallway", 0.4),
            ("Room", 0.3),
            ("Storage", 0.3)
        ]

