import { useState, useCallback, useEffect } from 'react';
import type { Room, HistoryAction } from '../types';

interface UseUndoRedoProps {
  onUndo?: (action: HistoryAction) => void;
  onRedo?: (action: HistoryAction) => void;
}

export const useUndoRedo = ({ onUndo, onRedo }: UseUndoRedoProps = {}) => {
  const [history, setHistory] = useState<HistoryAction[]>([]);
  const [historyIndex, setHistoryIndex] = useState(0);

  const canUndo = historyIndex > 0;
  const canRedo = historyIndex < history.length;

  const addAction = useCallback((action: HistoryAction) => {
    setHistory(prev => {
      // Remove any actions after current index (they're being replaced)
      const newHistory = prev.slice(0, historyIndex);
      return [...newHistory, action];
    });
    setHistoryIndex(prev => prev + 1);
  }, [historyIndex]);

  const undo = useCallback(() => {
    if (!canUndo) return;
    
    const action = history[historyIndex - 1];
    setHistoryIndex(prev => prev - 1);
    onUndo?.(action);
  }, [canUndo, history, historyIndex, onUndo]);

  const redo = useCallback(() => {
    if (!canRedo) return;
    
    const action = history[historyIndex];
    setHistoryIndex(prev => prev + 1);
    onRedo?.(action);
  }, [canRedo, history, historyIndex, onRedo]);

  const clear = useCallback(() => {
    setHistory([]);
    setHistoryIndex(0);
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        e.preventDefault();
        redo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);

  return {
    addAction,
    undo,
    redo,
    clear,
    canUndo,
    canRedo,
    history,
    historyIndex,
  };
};

// Helper functions to create history actions
export const createAddAction = (room: Room): HistoryAction => ({
  type: 'add',
  room,
  timestamp: Date.now(),
});

export const createModifyAction = (room: Room, previousState: Room): HistoryAction => ({
  type: 'modify',
  room,
  previousState,
  timestamp: Date.now(),
});

export const createDeleteAction = (room: Room): HistoryAction => ({
  type: 'delete',
  room,
  timestamp: Date.now(),
});

