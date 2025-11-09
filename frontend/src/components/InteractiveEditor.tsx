import { useState, useCallback, useEffect, useRef } from 'react';
import RoomCanvas from './RoomCanvas';
import RoomSuggestionPanel from './RoomSuggestionPanel';
import RoomLabelPanel from './RoomLabelPanel';
import Minimap from './Minimap';
import { useRoomExtension } from '../hooks/useRoomExtension';
import { useUndoRedo, createAddAction, createModifyAction } from '../hooks/useUndoRedo';
import { useCanvasInteraction } from '../hooks/useCanvasInteraction';
import { useZoomPan } from '../hooks/useZoomPan';
import { findNearestEdge, calculateEdgeDirection } from '../utils/geometryHelpers';
import { updatePlan, refineRoomBoundaries, getResults } from '../services/api';
import { validateRoomSizes, type SizeWarning } from '../utils/roomValidator';
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
  const [mode, setMode] = useState<'normal' | 'addDoor' | 'addCorner' | 'strictMode'>('normal');
  const [allDoors, setAllDoors] = useState<Door[]>(doors || []);
  const [isRefining, setIsRefining] = useState(false);
  const [refineError, setRefineError] = useState<string | null>(null);
  const [refineSuccess, setRefineSuccess] = useState<string | null>(null);
  const [sizeWarnings, setSizeWarnings] = useState<SizeWarning[]>([]);
  const [dismissedWarnings, setDismissedWarnings] = useState<Set<string>>(new Set());
  const [minimapVisible, setMinimapVisible] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 1000, height: 1000 });
  const [controlsMenuOpen, setControlsMenuOpen] = useState(false);
  const [textLabels, setTextLabels] = useState<any[]>([]);
  const [labelPanelCollapsed, setLabelPanelCollapsed] = useState(false);
  const [labelGenerationWarnings, setLabelGenerationWarnings] = useState<string[]>([]);
  
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
  const [snapEnabled, setSnapEnabled] = useState(false);
  const [gridSize, setGridSize] = useState(20); // 20 units grid
  const [hoveredEdge, setHoveredEdge] = useState<{ roomId: string; edgeIndex: number } | null>(null);

  // Handle corner added callback
  const handleCornerAdded = useCallback((room: Room, _vertexIndex: number) => {
    // Update room in appropriate state
    if (room.is_extended) {
      setExtendedRooms(prev => prev.map(r => r.id === room.id ? room : r));
    } else if (modifiedOriginalRooms.some(r => r.id === room.id)) {
      setModifiedOriginalRooms(prev => prev.map(r => r.id === room.id ? room : r));
    } else {
      // Original room - mark as modified
      const modifiedRoom = { ...room, is_modified: true };
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
    const previousRoom = allRooms.find(r => r.id === room.id);
    if (previousRoom) {
      undoRedo.addAction(createModifyAction(room, previousRoom));
    }
  }, [allRooms, modifiedOriginalRooms, undoRedo]);

  const zoomPan = useZoomPan({
    minZoom: 0.5,
    maxZoom: 2.0,
    initialZoom: 1.0,
  });

  const canvas = useCanvasInteraction({
    rooms: allRooms,
    onRoomModified: handleRoomModified,
    isInteractive: true,
    onOverlapWarning: setOverlapWarning,
    snapToGrid: snapEnabled,
    gridSize: gridSize,
    addCornerMode: mode === 'addCorner',
    strictMode: mode === 'strictMode',
    onCornerAdded: handleCornerAdded,
    svgRef: zoomPan.svgRef,
  });

  // Load image dimensions
  useEffect(() => {
    if (blueprintImage) {
      const img = new Image();
      img.onload = () => {
        setImageDimensions({ width: img.width, height: img.height });
      };
      img.src = blueprintImage;
    }
  }, [blueprintImage]);

  // Calculate viewport bounds for minimap
  const viewportBounds = {
    x: zoomPan.state.panX,
    y: zoomPan.state.panY,
    width: imageDimensions.width / zoomPan.state.zoom,
    height: imageDimensions.height / zoomPan.state.zoom,
  };

  // Handle minimap navigation
  const handleMinimapNavigate = useCallback((_x: number, _y: number) => {
    // For now, just reset zoom/pan and let user manually navigate
    // TODO: Add setPan function to useZoomPan hook
    zoomPan.resetZoom();
  }, [zoomPan]);

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

  // Handle room hover/move in Add Door mode for edge highlighting (no door creation)
  const handleRoomMoveInAddDoorMode = useCallback((event: React.MouseEvent<SVGElement>, room: Room) => {
    if (mode !== 'addDoor' || !room.polygon) {
      setHoveredEdge(null);
      return;
    }

    const svg = canvas.svgRef.current;
    if (!svg) return;

    // Get mouse position in SVG coordinates
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    const mousePos: [number, number] = [svgP.x, svgP.y];

    // Find nearest edge for highlighting only
    const edgeInfo = findNearestEdge(room.polygon, mousePos, 50);
    if (edgeInfo) {
      setHoveredEdge({ roomId: room.id, edgeIndex: edgeInfo.edgeIndex });
    } else {
      setHoveredEdge(null);
    }
  }, [mode, canvas, setHoveredEdge]);

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
    const edgeInfo = findNearestEdge(room.polygon, mousePos, 50);
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

  // Fetch text labels from job metadata
  useEffect(() => {
    const fetchTextLabels = async () => {
      try {
        const result = await getResults(jobId);
        const labels = result.metadata?.text_labels || [];
        setTextLabels(labels);
      } catch (error) {
        console.error('Error fetching text labels:', error);
        setTextLabels([]);
      }
    };
    
    if (jobId) {
      fetchTextLabels();
    }
  }, [jobId]);

  // Handler for generating rooms from selected labels
  const handleGenerateFromLabels = useCallback(async (selectedIndices: number[]): Promise<void> => {
    setLabelGenerationWarnings([]);
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/extend/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': import.meta.env.VITE_API_KEY || '',
        },
        body: JSON.stringify({
          action: 'generate-from-labels',
          selected_label_indices: selectedIndices,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate rooms');
      }
      
      const data = await response.json();
      
      // Update extended rooms
      if (data.extended_rooms) {
        setExtendedRooms(data.extended_rooms);
        onExtendedRoomsChange?.(data.extended_rooms);
      }
      
      // Show warnings if any
      if (data.warnings && data.warnings.length > 0) {
        setLabelGenerationWarnings(data.warnings);
      }
    } catch (error) {
      console.error('Error generating rooms from labels:', error);
      setLabelGenerationWarnings([error instanceof Error ? error.message : 'Failed to generate rooms']);
      throw error; // Re-throw so panel can handle it
    }
  }, [jobId, onExtendedRoomsChange]);

  // Handler for generating all rooms from labels
  const handleGenerateAllFromLabels = useCallback(async (): Promise<void> => {
    setLabelGenerationWarnings([]);
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/extend/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': import.meta.env.VITE_API_KEY || '',
        },
        body: JSON.stringify({
          action: 'generate-from-labels',
          generate_all: true,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate rooms');
      }
      
      const data = await response.json();
      
      // Update extended rooms
      if (data.extended_rooms) {
        setExtendedRooms(data.extended_rooms);
        onExtendedRoomsChange?.(data.extended_rooms);
      }
      
      // Show warnings if any
      if (data.warnings && data.warnings.length > 0) {
        setLabelGenerationWarnings(data.warnings);
      }
    } catch (error) {
      console.error('Error generating all rooms from labels:', error);
      setLabelGenerationWarnings([error instanceof Error ? error.message : 'Failed to generate rooms']);
      throw error; // Re-throw so panel can handle it
    }
  }, [jobId, onExtendedRoomsChange]);

  // Debounced persistence to backend
  const persistTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
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

  // Debounced size validation (2-3 seconds after edits)
  const validationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  useEffect(() => {
    if (validationTimeoutRef.current) {
      clearTimeout(validationTimeoutRef.current);
    }
    
    validationTimeoutRef.current = setTimeout(() => {
      const warnings = validateRoomSizes(allRooms);
      // Filter out dismissed warnings
      const activeWarnings = warnings.filter(w => {
        const warningKey = `${w.room1.id}-${w.type}-${w.room2?.id || ''}`;
        return !dismissedWarnings.has(warningKey);
      });
      setSizeWarnings(activeWarnings);
    }, 2500); // 2.5 seconds debounce
    
    return () => {
      if (validationTimeoutRef.current) {
        clearTimeout(validationTimeoutRef.current);
      }
    };
  }, [allRooms, dismissedWarnings]);

  // Handle refine boundaries
  const handleRefineBoundaries = useCallback(async () => {
    setIsRefining(true);
    setRefineError(null);
    setRefineSuccess(null);

    try {
      const result = await refineRoomBoundaries(jobId, 50);
      
      if (result.success) {
        // Update extended and modified rooms with refined versions
        if (result.extended_rooms && result.extended_rooms.length > 0) {
          setExtendedRooms(result.extended_rooms);
        }
        
        if (result.modified_rooms && result.modified_rooms.length > 0) {
          setModifiedOriginalRooms(result.modified_rooms);
        }

        // Show success message
        const stats = result.stats;
        setRefineSuccess(
          `✓ Refined ${stats.refined_rooms} rooms (${stats.vertices_snapped} vertices snapped)`
        );

        // Clear success message after 5 seconds
        setTimeout(() => setRefineSuccess(null), 5000);
      } else {
        setRefineError('Refinement failed. Please try again.');
      }
    } catch (error: any) {
      console.error('Error refining boundaries:', error);
      setRefineError(error.response?.data?.error || 'Failed to refine boundaries');
    } finally {
      setIsRefining(false);
    }
  }, [jobId]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (persistTimeoutRef.current) {
        clearTimeout(persistTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="relative w-full h-full" style={{ userSelect: 'none', WebkitUserSelect: 'none' }}>
      {/* Left Vertical Controls */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 w-[140px]">
        {/* Controls Menu Toggle */}
        <button
          onClick={() => setControlsMenuOpen(!controlsMenuOpen)}
          className="bg-white rounded-lg shadow-lg px-3 py-2 hover:bg-gray-50 transition-colors text-left flex items-center justify-between w-full"
          title={controlsMenuOpen ? "Collapse menu" : "Expand menu"}
        >
          <div className="text-sm font-medium text-gray-700">
            🛠️ Tools
          </div>
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${controlsMenuOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Collapsible Controls Menu */}
        {controlsMenuOpen && (
          <div className="bg-white rounded-lg shadow-lg p-2 flex flex-col gap-2 w-full">
            {/* Add Door Mode Toggle */}
            <button
              onClick={() => setMode(mode === 'addDoor' ? 'normal' : 'addDoor')}
              className={`rounded-md px-3 py-2 transition-colors text-left ${
                mode === 'addDoor' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-50 hover:bg-gray-100'
              }`}
              title="Toggle Add Door Mode"
            >
              <div className={`text-sm font-medium ${mode === 'addDoor' ? 'text-white' : 'text-gray-700'}`}>
                {mode === 'addDoor' ? '✓ Add Door' : '➕ Add Door'}
              </div>
            </button>

            {/* Snap to Grid Toggle */}
            <button
              onClick={() => setSnapEnabled(!snapEnabled)}
              className={`rounded-md px-3 py-2 transition-colors text-left ${
                snapEnabled
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-50 hover:bg-gray-100'
              }`}
              title={`Snap to Grid (${gridSize}px)`}
            >
              <div className={`flex items-center gap-2 text-sm font-medium ${snapEnabled ? 'text-white' : 'text-gray-700'}`}>
                <svg 
                  className="w-4 h-4" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M4 4h4v4H4V4zm6 0h4v4h-4V4zm6 0h4v4h-4V4zM4 10h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4zM4 16h4v4H4v-4zm6 0h4v4h-4v-4zm6 0h4v4h-4v-4z" 
                  />
                </svg>
                {snapEnabled ? 'Snap ON' : 'Snap OFF'}
              </div>
            </button>

            {/* Grid Size Control */}
            {snapEnabled && (
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-md">
                <label className="text-xs text-gray-600 whitespace-nowrap">Grid:</label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  step="5"
                  value={gridSize}
                  onChange={(e) => {
                    const value = parseInt(e.target.value, 10);
                    if (!isNaN(value) && value >= 5 && value <= 100) {
                      setGridSize(value);
                    }
                  }}
                  className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                  title="Grid size in pixels"
                />
                <span className="text-xs text-gray-500">px</span>
              </div>
            )}

            {/* Refine Boundaries Button */}
            <button
              onClick={handleRefineBoundaries}
              disabled={isRefining || allRooms.length === 0}
              className={`rounded-md px-3 py-2 transition-colors text-left ${
                isRefining
                  ? 'bg-gray-300 cursor-wait'
                  : 'bg-gray-50 hover:bg-gray-100 disabled:bg-gray-100 disabled:cursor-not-allowed'
              }`}
              title="Refine room boundaries using edge detection"
            >
              <div className={`flex items-center gap-2 text-sm font-medium ${isRefining ? 'text-gray-600' : 'text-gray-700'}`}>
                {isRefining ? (
                  <>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Refining...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Refine Boundaries
                  </>
                )}
              </div>
            </button>

            {/* Add Corner Mode Toggle */}
            <button
              onClick={() => setMode(mode === 'addCorner' ? 'normal' : 'addCorner')}
              className={`rounded-md px-3 py-2 transition-colors text-left ${
                mode === 'addCorner' 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-50 hover:bg-gray-100'
              }`}
              title="Toggle Add Corner Mode"
            >
              <div className={`text-sm font-medium ${mode === 'addCorner' ? 'text-white' : 'text-gray-700'}`}>
                {mode === 'addCorner' ? '✓ Add Corner' : '📐 Add Corner'}
              </div>
            </button>

            {/* Strict Mode Toggle */}
            <button
              onClick={() => setMode(mode === 'strictMode' ? 'normal' : 'strictMode')}
              className={`rounded-md px-3 py-2 transition-colors text-left ${
                mode === 'strictMode' 
                  ? 'bg-indigo-600 text-white' 
                  : 'bg-gray-50 hover:bg-gray-100'
              }`}
              title="Toggle Strict Mode (perpendicular edge dragging)"
            >
              <div className={`text-sm font-medium ${mode === 'strictMode' ? 'text-white' : 'text-gray-700'}`}>
                {mode === 'strictMode' ? '✓ Strict Mode' : '⊥ Strict Mode'}
              </div>
            </button>
          </div>
        )}

        {/* Undo/Redo */}
        <div className="bg-white rounded-lg shadow-lg p-2 flex gap-1 w-full">
          <button
            onClick={undoRedo.undo}
            disabled={!undoRedo.canUndo}
            className="flex-1 px-2 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed rounded transition-colors text-xs"
            title="Undo (Ctrl+Z)"
          >
            ↶
          </button>
          <button
            onClick={undoRedo.redo}
            disabled={!undoRedo.canRedo}
            className="flex-1 px-2 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed rounded transition-colors text-xs"
            title="Redo (Ctrl+Y)"
          >
            ↷
          </button>
        </div>

        {/* Room Count Stats */}
        <div className="bg-white rounded-lg shadow-lg p-3 text-sm w-full">
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-4">
              <span className="text-gray-600">Original:</span>
              <span className="font-semibold">{rooms.length}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-gray-600">Modified:</span>
              <span className="font-semibold text-amber-600">{modifiedOriginalRooms.length}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-gray-600">Extended:</span>
              <span className="font-semibold text-green-600">{extendedRooms.length}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-gray-600">Total:</span>
              <span className="font-semibold">{allRooms.length}</span>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="bg-white rounded-lg shadow-lg p-2 text-xs w-full">
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-blue-500 rounded flex-shrink-0"></div>
              <span className="text-gray-700">Detected</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-green-500 rounded flex-shrink-0"></div>
              <span className="text-gray-700">Extended</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 bg-red-500 rounded-full flex-shrink-0"></div>
              <span className="text-gray-700">Doors</span>
            </div>
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
        onRoomMouseMove={
          mode === 'addDoor' 
            ? handleRoomMoveInAddDoorMode 
            : canvas.handleEdgeHover
        }
        onMouseDown={mode === 'addDoor' ? handleEdgeClick : canvas.handleMouseDown}
        onMouseMove={canvas.handleMouseMove}
        onMouseUp={canvas.handleMouseUp}
        onDoorDelete={handleDoorDelete}
        addDoorMode={mode === 'addDoor'}
        hoveredEdge={hoveredEdge}
        dragPreview={canvas.dragPreview}
        isDragging={canvas.isDragging}
        isMovingRoom={canvas.isMovingRoom}
        svgRef={zoomPan.svgRef}
        zoom={zoomPan.state.zoom}
        panX={zoomPan.state.panX}
        panY={zoomPan.state.panY}
        onPanStart={zoomPan.handlePanStart}
        onPanMove={zoomPan.handlePanMove}
        onPanEnd={zoomPan.handlePanEnd}
      />

      {/* Room Label Panel */}
      {textLabels.length > 0 && (
        <RoomLabelPanel
          textLabels={textLabels}
          existingRooms={rooms}
          jobId={jobId}
          onGenerate={handleGenerateFromLabels}
          onGenerateAll={handleGenerateAllFromLabels}
          isCollapsed={labelPanelCollapsed}
          onToggleCollapse={() => setLabelPanelCollapsed(!labelPanelCollapsed)}
          warnings={labelGenerationWarnings}
        />
      )}

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

      {/* Refine Success Message */}
      {refineSuccess && (
        <div className="absolute top-20 left-4 z-10 bg-green-100 border border-green-400 text-green-700 px-4 py-2 rounded-lg shadow-lg">
          <p className="font-semibold text-sm">{refineSuccess}</p>
        </div>
      )}

      {/* Refine Error Message */}
      {refineError && (
        <div className="absolute top-20 left-4 z-10 bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded-lg shadow-lg">
          <p className="font-semibold text-sm">❌ {refineError}</p>
          <button
            onClick={() => setRefineError(null)}
            className="text-xs underline mt-1"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Panning Controls (always visible) and Minimap */}
      <div className="absolute bottom-4 left-4 z-10 flex items-end gap-2">
        {/* Panning Controls - Always visible */}
        <div className="bg-white rounded-lg shadow-lg p-2 border border-gray-300 w-[140px]">
          {/* Zoom Controls Row */}
          <div className="flex items-center gap-2 mb-2">
            <button
              onClick={zoomPan.zoomOut}
              className="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded transition-colors text-sm font-semibold"
              title="Zoom Out (Ctrl+-)"
            >
              −
            </button>
            <div className="text-xs text-gray-600 font-medium px-2 min-w-[3rem] text-center">
              {Math.round(zoomPan.state.zoom * 100)}%
            </div>
            <button
              onClick={zoomPan.zoomIn}
              className="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded transition-colors text-sm font-semibold"
              title="Zoom In (Ctrl++)"
            >
              +
            </button>
          </div>
          {/* Fit Button Row */}
          <div className="flex items-center mb-2">
            <button
              onClick={zoomPan.resetZoom}
              className="w-full h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded transition-colors text-xs font-medium"
              title="Fit to Screen (Ctrl+0)"
            >
              Fit
            </button>
          </div>
          {/* Show Map Button Row */}
          <div className="flex items-center">
            <button
              onClick={() => setMinimapVisible(!minimapVisible)}
              className={`w-full h-8 flex items-center justify-center px-3 text-xs rounded transition-colors font-medium ${
                minimapVisible
                  ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              title={minimapVisible ? 'Hide Map' : 'Show Map'}
            >
              {minimapVisible ? 'Hide Map' : 'Show Map'}
            </button>
          </div>
        </div>

        {/* Minimap - Shown when toggled */}
        <Minimap
          rooms={allRooms}
          blueprintImage={blueprintImage}
          imageWidth={imageDimensions.width}
          imageHeight={imageDimensions.height}
          viewportBounds={viewportBounds}
          onNavigate={handleMinimapNavigate}
          isVisible={minimapVisible}
          onToggle={() => setMinimapVisible(!minimapVisible)}
        />
      </div>

      {/* Size Warnings Panel */}
      {sizeWarnings.length > 0 && (
        <div className="absolute top-4 right-4 z-10 bg-yellow-50 border border-yellow-400 rounded-lg shadow-lg p-3 max-w-sm">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-sm text-yellow-800">
              ⚠️ Size Warnings ({sizeWarnings.length})
            </h3>
            <button
              onClick={() => setSizeWarnings([])}
              className="text-xs text-yellow-600 hover:text-yellow-800"
            >
              Clear All
            </button>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {sizeWarnings.map((warning, index) => {
              const warningKey = `${warning.room1.id}-${warning.type}-${warning.room2?.id || ''}`;
              return (
                <div
                  key={warningKey}
                  className="bg-white rounded p-2 text-xs border border-yellow-300"
                >
                  <p className="text-yellow-800 mb-1">{warning.message}</p>
                  <div className="flex gap-2 mt-1">
                    <button
                      onClick={() => {
                        setDismissedWarnings(prev => new Set(prev).add(warningKey));
                        setSizeWarnings(prev => prev.filter((_, i) => i !== index));
                      }}
                      className="text-yellow-600 hover:text-yellow-800 underline"
                    >
                      Dismiss
                    </button>
                    {warning.room2 && (
                      <button
                        onClick={() => {
                          // Swap room types (simple implementation)
                          const tempType = warning.room1.name_hint;
                          handleRoomModified({ ...warning.room1, name_hint: warning.room2!.name_hint });
                          handleRoomModified({ ...warning.room2!, name_hint: tempType });
                        }}
                        className="text-yellow-600 hover:text-yellow-800 underline"
                      >
                        Swap Types
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Help Text - Positioned on right to avoid overlapping with legend */}
      <div className="absolute bottom-4 right-4 bg-white rounded-lg shadow-lg p-3 text-sm text-gray-600 max-w-xs z-10">
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

