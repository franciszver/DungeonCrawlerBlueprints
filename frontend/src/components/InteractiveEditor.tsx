import { useState, useCallback, useEffect, useRef } from 'react';
import RoomCanvas from './RoomCanvas';
import RoomSuggestionPanel from './RoomSuggestionPanel';
import { useRoomExtension } from '../hooks/useRoomExtension';
import { useUndoRedo, createAddAction, createModifyAction } from '../hooks/useUndoRedo';
import { useCanvasInteraction } from '../hooks/useCanvasInteraction';
import { findNearestEdge, calculateEdgeDirection } from '../utils/geometryHelpers';
import { updatePlan } from '../services/api';
import type { Room, Door, HistoryAction } from '../types';

interface InteractiveEditorProps {
  jobId: string;
  rooms: Room[];
  doors: Door[];
  blueprintImage: string;
  initialExtendedRooms?: Room[];
  initialModifiedRooms?: Room[];
  onExtendedRoomsChange?: (extendedRooms: Room[]) => void;
}

export default function InteractiveEditor({
  jobId,
  rooms,
  doors,
  blueprintImage,
  initialExtendedRooms = [],
  initialModifiedRooms = [],
  onExtendedRoomsChange,
}: InteractiveEditorProps) {
  const [extendedRooms, setExtendedRooms] = useState<Room[]>(initialExtendedRooms);
  const [modifiedOriginalRooms, setModifiedOriginalRooms] = useState<Room[]>(initialModifiedRooms);
  const [mode, setMode] = useState<'normal' | 'addDoor'>('normal');
  const [allDoors, setAllDoors] = useState<Door[]>(doors || []);
  
  // Combine rooms: unmodified originals + modified originals + extended rooms
  const allRooms = [
    ...rooms.filter(r => !modifiedOriginalRooms.find(m => m.id === r.id)),
    ...modifiedOriginalRooms,
    ...extendedRooms
  ];

  // Handle room added
  const handleRoomAdded = useCallback((room: Room) => {
    setExtendedRooms(prev => {
      const newRooms = [...prev, room];
      onExtendedRoomsChange?.(newRooms);
      return newRooms;
    });
    undoRedo.addAction(createAddAction(room));
  }, [onExtendedRoomsChange]);

  // Handle room modified
  const handleRoomModified = useCallback((updatedRoom: Room) => {
    const previousRoom = allRooms.find(r => r.id === updatedRoom.id);
    if (!previousRoom) return;

    // Check if this is an original room (not extended)
    const isOriginalRoom = rooms.some(r => r.id === updatedRoom.id);
    
    if (updatedRoom.is_extended) {
      // Extended room modification
      setExtendedRooms(prev => {
        const newRooms = prev.map(r => r.id === updatedRoom.id ? updatedRoom : r);
        onExtendedRoomsChange?.(newRooms);
        return newRooms;
      });
    } else if (isOriginalRoom) {
      // Original room modification - mark as modified and move to modifiedOriginalRooms
      const modifiedRoom = { ...updatedRoom, is_modified: true };
      setModifiedOriginalRooms(prev => {
        const existingIndex = prev.findIndex(r => r.id === modifiedRoom.id);
        if (existingIndex >= 0) {
          return prev.map(r => r.id === modifiedRoom.id ? modifiedRoom : r);
        } else {
          return [...prev, modifiedRoom];
        }
      });
    }
    
    undoRedo.addAction(createModifyAction(updatedRoom, previousRoom));
  }, [allRooms, rooms, onExtendedRoomsChange]);

  // Undo/Redo handlers
  const handleUndo = useCallback((action: HistoryAction) => {
    if (action.type === 'add' && action.room) {
      setExtendedRooms(prev => prev.filter(r => r.id !== action.room!.id));
    } else if (action.type === 'modify' && action.previousState) {
      if (action.previousState.is_extended) {
        setExtendedRooms(prev => prev.map(r => 
          r.id === action.previousState!.id ? action.previousState! : r
        ).filter((r): r is Room => r !== undefined));
      } else {
        // Check if this was a modified original room
        const isOriginalRoom = rooms.some(r => r.id === action.previousState!.id);
        if (isOriginalRoom) {
          // If restoring to original state, remove from modified list
          const originalRoom = rooms.find(r => r.id === action.previousState!.id);
          if (originalRoom && JSON.stringify(originalRoom) === JSON.stringify(action.previousState)) {
            // Room is back to original state, remove from modified list
            setModifiedOriginalRooms(prev => prev.filter(r => r.id !== action.previousState!.id));
          } else {
            // Update modified room
            setModifiedOriginalRooms(prev => prev.map(r => 
              r.id === action.previousState!.id ? action.previousState! : r
            ).filter((r): r is Room => r !== undefined));
          }
        }
      }
    } else if (action.type === 'delete' && action.room) {
      if (action.room.is_extended) {
        setExtendedRooms(prev => [...prev, action.room!]);
      }
    }
  }, [rooms]);

  const handleRedo = useCallback((action: HistoryAction) => {
    if (action.type === 'add' && action.room) {
      setExtendedRooms(prev => [...prev, action.room!]);
    } else if (action.type === 'modify' && action.room) {
      if (action.room.is_extended) {
        setExtendedRooms(prev => prev.map(r => 
          r.id === action.room!.id ? action.room! : r
        ).filter((r): r is Room => r !== undefined));
      } else {
        // Check if this is a modified original room
        const isOriginalRoom = rooms.some(r => r.id === action.room!.id);
        if (isOriginalRoom && action.room.is_modified) {
          setModifiedOriginalRooms(prev => {
            const existingIndex = prev.findIndex(r => r.id === action.room!.id);
            if (existingIndex >= 0) {
              return prev.map(r => r.id === action.room!.id ? action.room! : r);
            } else {
              return [...prev, action.room!];
            }
          });
        }
      }
    } else if (action.type === 'delete' && action.room) {
      if (action.room.is_extended) {
        setExtendedRooms(prev => prev.filter(r => r.id !== action.room!.id));
      }
    }
  }, [rooms]);

  // Initialize hooks
  const roomExtension = useRoomExtension({
    jobId,
    existingRooms: allRooms,
    onRoomAdded: handleRoomAdded,
  });

  const undoRedo = useUndoRedo({
    onUndo: handleUndo,
    onRedo: handleRedo,
  });

  // Handle room deleted (TODO: Wire up to UI)
  // const handleRoomDeleted = useCallback((roomId: string) => {
  //   const room = extendedRooms.find(r => r.id === roomId);
  //   if (!room) return;

  //   setExtendedRooms(prev => {
  //     const newRooms = prev.filter(r => r.id !== roomId);
  //     onExtendedRoomsChange?.(newRooms);
  //     return newRooms;
  //   });
  //   undoRedo.addAction(createDeleteAction(room));
  // }, [extendedRooms, onExtendedRoomsChange, undoRedo]);

  const [overlapWarning, setOverlapWarning] = useState(false);

  const canvas = useCanvasInteraction({
    rooms: allRooms,
    onRoomModified: handleRoomModified,
    isInteractive: true,
    onOverlapWarning: setOverlapWarning,
  });

  // Handle door click
  const handleDoorClick = (door: Door) => {
    // Don't open room generation panel if in addDoor mode
    if (mode === 'addDoor') return;
    
    // Find which room this door belongs to
    const room = allRooms.find(r => 
      r.doors?.some(d => d.id === door.id)
    );
    const roomType = room?.name_hint || 'Room';
    roomExtension.openDoorPanel(door, roomType);
  };

  // Handle room generation
  const handleGenerate = (roomType: string) => {
    if (!roomExtension.selectedDoor) return;
    
    const room = allRooms.find(r => 
      r.doors?.some(d => d.id === roomExtension.selectedDoor!.id)
    );
    const currentRoomType = room?.name_hint || 'Room';
    
    roomExtension.generate(
      roomExtension.selectedDoor,
      currentRoomType,
      roomType
    );
  };

  // Handle edge click for door addition
  const handleEdgeClick = useCallback((event: React.MouseEvent<SVGElement>, room: Room) => {
    if (mode !== 'addDoor' || !room.polygon) return;

    const svg = canvas.svgRef.current;
    if (!svg) return;

    // Get mouse position in SVG coordinates
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    const mousePos: [number, number] = [svgP.x, svgP.y];

    // Find nearest edge
    const edgeInfo = findNearestEdge(room.polygon, mousePos, 10);
    if (!edgeInfo) return;

    // Calculate door direction
    const edgeStart = room.polygon[edgeInfo.edgeIndex];
    const edgeEnd = room.polygon[(edgeInfo.edgeIndex + 1) % room.polygon.length];
    const direction = calculateEdgeDirection(edgeStart, edgeEnd);

    // Generate unique door ID
    const doorId = `door_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const newDoor: Door = {
      id: doorId,
      location: edgeInfo.closestPoint,
      direction,
    };

    // Add door to room
    const updatedDoors = [...(room.doors || []), newDoor];
    const updatedRoom = {
      ...room,
      doors: updatedDoors,
    };

    // Update room in appropriate state
    if (room.is_extended) {
      setExtendedRooms(prev => prev.map(r => r.id === room.id ? updatedRoom : r));
    } else if (modifiedOriginalRooms.some(r => r.id === room.id)) {
      setModifiedOriginalRooms(prev => prev.map(r => r.id === room.id ? updatedRoom : r));
    } else {
      // Original room - add to modified list
      const modifiedRoom = { ...updatedRoom, is_modified: true };
      setModifiedOriginalRooms(prev => {
        const existingIndex = prev.findIndex(r => r.id === modifiedRoom.id);
        if (existingIndex >= 0) {
          return prev.map(r => r.id === modifiedRoom.id ? modifiedRoom : r);
        } else {
          return [...prev, modifiedRoom];
        }
      });
    }

    // Add door to all doors list
    setAllDoors(prev => [...prev, newDoor]);

    // Add to undo/redo
    undoRedo.addAction(createModifyAction(updatedRoom, room));

    event.stopPropagation();
  }, [mode, canvas, modifiedOriginalRooms, undoRedo]);

  // Handle door deletion
  const handleDoorDelete = useCallback((doorId: string) => {
    // Find room(s) containing this door
    const roomsWithDoor = allRooms.filter(r => r.doors?.some(d => d.id === doorId));
    
    roomsWithDoor.forEach(room => {
      const updatedDoors = room.doors?.filter(d => d.id !== doorId) || [];
      const updatedRoom = {
        ...room,
        doors: updatedDoors,
      };

      // Update room in appropriate state
      if (room.is_extended) {
        setExtendedRooms(prev => prev.map(r => r.id === room.id ? updatedRoom : r));
      } else if (modifiedOriginalRooms.some(r => r.id === room.id)) {
        setModifiedOriginalRooms(prev => prev.map(r => r.id === room.id ? updatedRoom : r));
      } else {
        // Original room - add to modified list
        const modifiedRoom = { ...updatedRoom, is_modified: true };
        setModifiedOriginalRooms(prev => {
          const existingIndex = prev.findIndex(r => r.id === modifiedRoom.id);
          if (existingIndex >= 0) {
            return prev.map(r => r.id === modifiedRoom.id ? modifiedRoom : r);
          } else {
            return [...prev, modifiedRoom];
          }
        });
      }

      // Add to undo/redo
      undoRedo.addAction(createModifyAction(updatedRoom, room));
    });

    // Remove door from all doors list
    setAllDoors(prev => prev.filter(d => d.id !== doorId));
  }, [allRooms, modifiedOriginalRooms, undoRedo]);

  // Update allDoors when doors prop changes
  useEffect(() => {
    setAllDoors(doors || []);
  }, [doors]);

  // Debounced persistence to backend
  const persistTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const persistToBackend = useCallback(() => {
    if (persistTimeoutRef.current) {
      clearTimeout(persistTimeoutRef.current);
    }
    
    persistTimeoutRef.current = setTimeout(async () => {
      try {
        await updatePlan(
          jobId,
          modifiedOriginalRooms,
          extendedRooms,
          allDoors
        );
      } catch (error) {
        console.error('Failed to persist changes to backend:', error);
        // Don't show error to user - changes are still in local state
      }
    }, 2000); // Debounce for 2 seconds
  }, [jobId, modifiedOriginalRooms, extendedRooms, allDoors]);

  // Persist when modified rooms, extended rooms, or doors change
  useEffect(() => {
    if (modifiedOriginalRooms.length > 0 || extendedRooms.length > 0) {
      persistToBackend();
    }
  }, [modifiedOriginalRooms, extendedRooms, allDoors, persistToBackend]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (persistTimeoutRef.current) {
        clearTimeout(persistTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="relative w-full h-full">
      {/* Top Controls */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        {/* Undo/Redo */}
        <div className="bg-white rounded-lg shadow-lg p-2 flex gap-2">
          <button
            onClick={undoRedo.undo}
            disabled={!undoRedo.canUndo}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed rounded transition-colors"
            title="Undo (Ctrl+Z)"
          >
            ↶ Undo
          </button>
          <button
            onClick={undoRedo.redo}
            disabled={!undoRedo.canRedo}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed rounded transition-colors"
            title="Redo (Ctrl+Y)"
          >
            ↷ Redo
          </button>
        </div>

        {/* Generation Mode Toggle */}
        <div className="bg-white rounded-lg shadow-lg p-2">
          <button
            onClick={roomExtension.toggleMode}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded transition-colors flex items-center gap-2"
          >
            <span className="text-sm font-medium">
              Mode: {roomExtension.mode === 'realistic' ? '🏢 Realistic' : '🏰 Fantasy'}
            </span>
          </button>
        </div>

        {/* Add Door Mode Toggle */}
        <div className="bg-white rounded-lg shadow-lg p-2">
          <button
            onClick={() => setMode(mode === 'addDoor' ? 'normal' : 'addDoor')}
            className={`px-3 py-2 rounded transition-colors flex items-center gap-2 ${
              mode === 'addDoor' 
                ? 'bg-blue-600 text-white' 
                : 'bg-gray-100 hover:bg-gray-200'
            }`}
          >
            <span className="text-sm font-medium">
              {mode === 'addDoor' ? '✓ Add Door' : '➕ Add Door'}
            </span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-lg p-3 text-sm">
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600">Original Rooms:</span>
            <span className="font-semibold">{rooms.length}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600">Modified:</span>
            <span className="font-semibold text-amber-600">{modifiedOriginalRooms.length}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600">Extended Rooms:</span>
            <span className="font-semibold text-green-600">{extendedRooms.length}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600">Total:</span>
            <span className="font-semibold">{allRooms.length}</span>
          </div>
        </div>
      </div>

      {/* Canvas */}
      <RoomCanvas
        rooms={allRooms}
        doors={allDoors}
        blueprintImage={blueprintImage}
        isInteractive={true}
        selectedDoorId={roomExtension.selectedDoor?.id}
        hoveredDoorId={canvas.hoveredDoor}
        hoveredRoom={canvas.hoveredRoom}
        onDoorClick={handleDoorClick}
        onDoorHover={canvas.handleDoorHover}
        onRoomHover={canvas.handleRoomHover}
        onMouseDown={mode === 'addDoor' ? (e, room) => handleEdgeClick(e, room) : canvas.handleMouseDown}
        onMouseMove={canvas.handleMouseMove}
        onMouseUp={canvas.handleMouseUp}
        onDoorDelete={handleDoorDelete}
        addDoorMode={mode === 'addDoor'}
        svgRef={canvas.svgRef}
      />

      {/* Room Suggestion Panel */}
      {roomExtension.selectedDoor && (
        <RoomSuggestionPanel
          door={roomExtension.selectedDoor}
          currentRoomType={allRooms.find(r => 
            r.doors?.some(d => d.id === roomExtension.selectedDoor!.id)
          )?.name_hint || 'Room'}
          suggestions={roomExtension.suggestions}
          mode={roomExtension.mode}
          isLoading={roomExtension.isGenerating || roomExtension.isFetchingSuggestions}
          error={roomExtension.error}
          onGenerate={handleGenerate}
          onCancel={roomExtension.closeDoorPanel}
          onToggleMode={roomExtension.toggleMode}
        />
      )}

      {/* Overlap Warning */}
      {overlapWarning && (
        <div className="absolute top-20 left-4 z-10 bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded-lg shadow-lg">
          <p className="font-semibold text-sm">⚠️ Room Overlap Detected</p>
        </div>
      )}

      {/* Help Text */}
      <div className="absolute bottom-20 left-4 bg-white rounded-lg shadow-lg p-3 text-sm text-gray-600 max-w-xs">
        <p className="font-semibold mb-1">💡 Interactive Mode Active</p>
        <ul className="space-y-1 text-xs">
          <li>• Click red dots to add rooms</li>
          <li>• Drag room body to move</li>
          <li>• Drag corners to resize</li>
          {mode === 'addDoor' && <li className="text-blue-600 font-semibold">• Click room edge to add door</li>}
          <li>• Hover doors to delete</li>
          <li>• Use Ctrl+Z / Ctrl+Y to undo/redo</li>
        </ul>
      </div>
    </div>
  );
}

