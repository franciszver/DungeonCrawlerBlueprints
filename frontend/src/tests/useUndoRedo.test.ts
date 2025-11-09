/**
 * Unit tests for useUndoRedo hook
 */
import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUndoRedo, createAddAction, createModifyAction, createDeleteAction } from '../hooks/useUndoRedo';

describe('useUndoRedo', () => {
  it('should initialize with empty history', () => {
    const { result } = renderHook(() =>
      useUndoRedo({
        onUndo: vi.fn(),
        onRedo: vi.fn(),
      })
    );

    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
  });

  it('should add action to history', () => {
    const { result } = renderHook(() =>
      useUndoRedo({
        onUndo: vi.fn(),
        onRedo: vi.fn(),
      })
    );

    const room = {
      id: 'room_001',
      bounding_box: [0, 0, 100, 100],
      confidence: 0.9,
    };

    act(() => {
      result.current.addAction(createAddAction(room));
    });

    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
  });

  it('should undo action', () => {
    const onUndo = vi.fn();
    const { result } = renderHook(() =>
      useUndoRedo({
        onUndo,
        onRedo: vi.fn(),
      })
    );

    const room = {
      id: 'room_001',
      bounding_box: [0, 0, 100, 100],
      confidence: 0.9,
    };
    const action = createAddAction(room);

    act(() => {
      result.current.addAction(action);
    });

    act(() => {
      result.current.undo();
    });

    expect(onUndo).toHaveBeenCalledWith(action);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
  });

  it('should redo action', () => {
    const onRedo = vi.fn();
    const { result } = renderHook(() =>
      useUndoRedo({
        onUndo: vi.fn(),
        onRedo,
      })
    );

    const room = {
      id: 'room_001',
      bounding_box: [0, 0, 100, 100],
      confidence: 0.9,
    };
    const action = createAddAction(room);

    act(() => {
      result.current.addAction(action);
    });

    act(() => {
      result.current.undo();
    });

    act(() => {
      result.current.redo();
    });

    expect(onRedo).toHaveBeenCalledWith(action);
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
  });

  it('should clear redo stack when new action is added', () => {
    const { result } = renderHook(() =>
      useUndoRedo({
        onUndo: vi.fn(),
        onRedo: vi.fn(),
      })
    );

    const room1 = {
      id: 'room_001',
      bounding_box: [0, 0, 100, 100],
      confidence: 0.9,
    };
    const room2 = {
      id: 'room_002',
      bounding_box: [200, 200, 300, 300],
      confidence: 0.8,
    };

    act(() => {
      result.current.addAction(createAddAction(room1));
    });

    act(() => {
      result.current.undo();
    });

    expect(result.current.canRedo).toBe(true);

    act(() => {
      result.current.addAction(createAddAction(room2));
    });

    expect(result.current.canRedo).toBe(false);
  });

  it('should create modify action with previous state', () => {
    const room = {
      id: 'room_001',
      bounding_box: [0, 0, 100, 100],
      confidence: 0.9,
    };
    const previousRoom = {
      id: 'room_001',
      bounding_box: [0, 0, 50, 50],
      confidence: 0.8,
    };

    const action = createModifyAction(room, previousRoom);

    expect(action.type).toBe('modify');
    expect(action.room).toEqual(room);
    expect(action.previousState).toEqual(previousRoom);
  });

  it('should create delete action', () => {
    const room = {
      id: 'room_001',
      bounding_box: [0, 0, 100, 100],
      confidence: 0.9,
    };

    const action = createDeleteAction(room);

    expect(action.type).toBe('delete');
    expect(action.room).toEqual(room);
  });
});

