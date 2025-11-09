import { useState, useCallback } from 'react';
import RoomCanvas from './RoomCanvas';
import RoomSuggestionPanel from './RoomSuggestionPanel';
import { useRoomExtension } from '../hooks/useRoomExtension';
import { useUndoRedo, createAddAction, createModifyAction } from '../hooks/useUndoRedo';
import { useCanvasInteraction } from '../hooks/useCanvasInteraction';
import type { Room, Door, HistoryAction } from '../types';

interface InteractiveEditorProps {
  jobId: string;
  rooms: Room[];
  doors: Door[];
  blueprintImage: string;
  onExtendedRoomsChange?: (extendedRooms: Room[]) => void;
}

export default function InteractiveEditor({
  jobId,
  rooms,
  doors,
  blueprintImage,
  onExtendedRoomsChange,
}: InteractiveEditorProps) {
  const [extendedRooms, setExtendedRooms] = useState<Room[]>([]);
  const allRooms = [...rooms, ...extendedRooms];

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

    if (updatedRoom.is_extended) {
      setExtendedRooms(prev => {
        const newRooms = prev.map(r => r.id === updatedRoom.id ? updatedRoom : r);
        onExtendedRoomsChange?.(newRooms);
        return newRooms;
      });
    }
    undoRedo.addAction(createModifyAction(updatedRoom, previousRoom));
  }, [allRooms, onExtendedRoomsChange]);

  // Undo/Redo handlers
  const handleUndo = useCallback((action: HistoryAction) => {
    if (action.type === 'add' && action.room) {
      setExtendedRooms(prev => prev.filter(r => r.id !== action.room!.id));
    } else if (action.type === 'modify' && action.previousState) {
      if (action.previousState.is_extended) {
        setExtendedRooms(prev => prev.map(r => 
          r.id === action.previousState!.id ? action.previousState! : r
        ).filter((r): r is Room => r !== undefined));
      }
    } else if (action.type === 'delete' && action.room) {
      setExtendedRooms(prev => [...prev, action.room!]);
    }
  }, []);

  const handleRedo = useCallback((action: HistoryAction) => {
    if (action.type === 'add' && action.room) {
      setExtendedRooms(prev => [...prev, action.room!]);
    } else if (action.type === 'modify' && action.room) {
      if (action.room.is_extended) {
        setExtendedRooms(prev => prev.map(r => 
          r.id === action.room!.id ? action.room! : r
        ).filter((r): r is Room => r !== undefined));
      }
    } else if (action.type === 'delete' && action.room) {
      setExtendedRooms(prev => prev.filter(r => r.id !== action.room!.id));
    }
  }, []);

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

  const canvas = useCanvasInteraction({
    rooms: allRooms,
    onRoomModified: handleRoomModified,
    isInteractive: true,
  });

  // Handle door click
  const handleDoorClick = (door: Door) => {
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

        {/* Mode Toggle */}
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
      </div>

      {/* Stats */}
      <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-lg p-3 text-sm">
        <div className="space-y-1">
          <div className="flex items-center justify-between gap-4">
            <span className="text-gray-600">Original Rooms:</span>
            <span className="font-semibold">{rooms.length}</span>
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
        doors={doors}
        blueprintImage={blueprintImage}
        isInteractive={true}
        selectedDoorId={roomExtension.selectedDoor?.id}
        hoveredDoorId={canvas.hoveredDoor}
        hoveredRoom={canvas.hoveredRoom}
        onDoorClick={handleDoorClick}
        onDoorHover={canvas.handleDoorHover}
        onRoomHover={canvas.handleRoomHover}
        onMouseDown={canvas.handleMouseDown}
        onMouseMove={canvas.handleMouseMove}
        onMouseUp={canvas.handleMouseUp}
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

      {/* Help Text */}
      <div className="absolute bottom-20 left-4 bg-white rounded-lg shadow-lg p-3 text-sm text-gray-600 max-w-xs">
        <p className="font-semibold mb-1">💡 Interactive Mode Active</p>
        <ul className="space-y-1 text-xs">
          <li>• Click red dots to add rooms</li>
          <li>• Hover over rooms to see corners</li>
          <li>• Drag corners to resize</li>
          <li>• Use Ctrl+Z / Ctrl+Y to undo/redo</li>
        </ul>
      </div>
    </div>
  );
}

