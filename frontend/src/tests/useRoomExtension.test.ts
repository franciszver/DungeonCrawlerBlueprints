/**
 * Unit tests for useRoomExtension hook
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRoomExtension } from '../hooks/useRoomExtension';
import * as api from '../services/api';

// Mock the API
vi.mock('../services/api');

describe('useRoomExtension', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with default state', () => {
    const { result } = renderHook(() =>
      useRoomExtension({
        jobId: 'test_job',
        existingRooms: [],
        onRoomAdded: vi.fn(),
      })
    );

    expect(result.current.selectedDoor).toBeNull();
    expect(result.current.suggestions).toEqual([]);
    expect(result.current.mode).toBe('realistic');
    expect(result.current.isGenerating).toBe(false);
    expect(result.current.isFetchingSuggestions).toBe(false);
  });

  it('should toggle mode between realistic and fantasy', () => {
    const { result } = renderHook(() =>
      useRoomExtension({
        jobId: 'test_job',
        existingRooms: [],
        onRoomAdded: vi.fn(),
      })
    );

    expect(result.current.mode).toBe('realistic');

    act(() => {
      result.current.toggleMode();
    });

    expect(result.current.mode).toBe('fantasy');

    act(() => {
      result.current.toggleMode();
    });

    expect(result.current.mode).toBe('realistic');
  });

  it('should open door panel and fetch suggestions', async () => {
    const mockSuggestions = [
      { room_type: 'Bedroom', confidence: 0.85, reasoning: 'Test' },
    ];
    vi.mocked(api.getRoomSuggestions).mockResolvedValue(mockSuggestions);

    const { result } = renderHook(() =>
      useRoomExtension({
        jobId: 'test_job',
        existingRooms: [],
        onRoomAdded: vi.fn(),
      })
    );

    const door = { id: 'door_001', location: [100, 100] as [number, number] };

    await act(async () => {
      await result.current.openDoorPanel(door, 'Hallway');
    });

    expect(result.current.selectedDoor).toEqual(door);
    expect(result.current.suggestions).toEqual(mockSuggestions);
    expect(api.getRoomSuggestions).toHaveBeenCalledWith(
      'test_job',
      'door_001',
      'Hallway',
      'realistic'
    );
  });

  it('should handle suggestion fetch errors', async () => {
    vi.mocked(api.getRoomSuggestions).mockRejectedValue(
      new Error('API Error')
    );

    const { result } = renderHook(() =>
      useRoomExtension({
        jobId: 'test_job',
        existingRooms: [],
        onRoomAdded: vi.fn(),
      })
    );

    const door = { id: 'door_001', location: [100, 100] as [number, number] };

    await act(async () => {
      await result.current.openDoorPanel(door, 'Hallway');
    });

    expect(result.current.error).toBeTruthy();
  });

  it('should generate room and call onRoomAdded', async () => {
    const mockRoom = {
      id: 'extended_001',
      bounding_box: [100, 100, 200, 200],
      polygon: [[100, 100], [200, 100], [200, 200], [100, 200]] as [number, number][],
      name_hint: 'Bedroom',
      confidence: 0.8,
      is_extended: true,
    };
    vi.mocked(api.generateRoom).mockResolvedValue({
      room: mockRoom,
      validation: { is_valid: true, warnings: [], overlaps: [] },
    });

    const onRoomAdded = vi.fn();
    const { result } = renderHook(() =>
      useRoomExtension({
        jobId: 'test_job',
        existingRooms: [],
        onRoomAdded,
      })
    );

    const door = { id: 'door_001', location: [100, 100] as [number, number] };

    await act(async () => {
      await result.current.generate(door, 'Hallway', 'Bedroom');
    });

    expect(onRoomAdded).toHaveBeenCalledWith(mockRoom);
    expect(result.current.selectedDoor).toBeNull();
  });

  it('should close door panel', () => {
    const { result } = renderHook(() =>
      useRoomExtension({
        jobId: 'test_job',
        existingRooms: [],
        onRoomAdded: vi.fn(),
      })
    );

    act(() => {
      result.current.closeDoorPanel();
    });

    expect(result.current.selectedDoor).toBeNull();
    expect(result.current.suggestions).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

