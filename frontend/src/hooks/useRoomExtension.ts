import { useState } from 'react';
import { generateRoom, getRoomSuggestions, validateRoomPlacement } from '../services/api';
import type { Room, RoomSuggestion, GenerationMode, Door } from '../types';

interface UseRoomExtensionProps {
  jobId: string;
  existingRooms: Room[];
  onRoomAdded: (room: Room) => void;
}

export const useRoomExtension = ({ jobId, existingRooms, onRoomAdded }: UseRoomExtensionProps) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<RoomSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedDoor, setSelectedDoor] = useState<Door | null>(null);
  const [mode, setMode] = useState<GenerationMode>('realistic');

  const fetchSuggestions = async (
    door: Door,
    currentRoomType: string
  ) => {
    setIsFetchingSuggestions(true);
    setError(null);
    
    try {
      const response = await getRoomSuggestions(
        jobId,
        door.direction,
        currentRoomType,
        mode
      );
      
      if (response.suggestions) {
        setSuggestions(response.suggestions);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch suggestions');
      setSuggestions([]);
    } finally {
      setIsFetchingSuggestions(false);
    }
  };

  const generate = async (
    door: Door,
    currentRoomType: string,
    roomType?: string
  ) => {
    setIsGenerating(true);
    setError(null);
    
    try {
      const response = await generateRoom(
        jobId,
        door.location,
        door.direction,
        currentRoomType,
        roomType,
        mode
      );
      
      if (response.room) {
        onRoomAdded(response.room);
        setSelectedDoor(null);
        setSuggestions([]);
      } else if (response.error) {
        setError(response.error);
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate room');
    } finally {
      setIsGenerating(false);
    }
  };

  const validate = async (roomPolygon: [number, number][]) => {
    try {
      const response = await validateRoomPlacement(jobId, roomPolygon);
      return response.valid || false;
    } catch (err) {
      return false;
    }
  };

  const openDoorPanel = (door: Door, currentRoomType: string) => {
    setSelectedDoor(door);
    fetchSuggestions(door, currentRoomType);
  };

  const closeDoorPanel = () => {
    setSelectedDoor(null);
    setSuggestions([]);
    setError(null);
  };

  const toggleMode = () => {
    setMode(prev => prev === 'realistic' ? 'fantasy' : 'realistic');
    // Re-fetch suggestions if door is selected
    if (selectedDoor) {
      const currentRoom = existingRooms.find(r => 
        r.doors?.some(d => d.id === selectedDoor.id)
      );
      if (currentRoom) {
        fetchSuggestions(selectedDoor, currentRoom.name_hint || 'Room');
      }
    }
  };

  return {
    isGenerating,
    isFetchingSuggestions,
    suggestions,
    error,
    selectedDoor,
    mode,
    fetchSuggestions,
    generate,
    validate,
    openDoorPanel,
    closeDoorPanel,
    toggleMode,
  };
};

