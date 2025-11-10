import { useState, useCallback, useRef, useEffect } from 'react';
import { 
  findNearestCorner, 
  resizePolygon, 
  translatePolygon, 
  isPointInPolygon, 
  polygonToBbox, 
  bboxesOverlap, 
  snapPointToGrid,
  findNearestEdge,
  insertVertexInPolygon,
  getEdgePerpendicularVector
} from '../utils/geometryHelpers';
import type { Room } from '../types';

interface UseCanvasInteractionProps {
  rooms: Room[];
  onRoomModified: (room: Room) => void;
  isInteractive: boolean;
  onOverlapWarning?: (hasOverlap: boolean) => void;
  snapToGrid?: boolean;
  gridSize?: number;
  addCornerMode?: boolean;
  strictMode?: boolean;
  onCornerAdded?: (room: Room, vertexIndex: number) => void;
  svgRef?: React.RefObject<SVGSVGElement>;
}

export const useCanvasInteraction = ({
  rooms: _rooms,
  onRoomModified,
  isInteractive,
  onOverlapWarning,
  snapToGrid = false,
  gridSize = 20,
  addCornerMode = false,
  strictMode = false,
  onCornerAdded,
  svgRef: externalSvgRef,
}: UseCanvasInteractionProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [draggedRoom, setDraggedRoom] = useState<Room | null>(null);
  const [dragPreview, setDragPreview] = useState<Room | null>(null);
  const [draggedCornerIndex, setDraggedCornerIndex] = useState<number | null>(null);
  const [draggedEdgeIndex, setDraggedEdgeIndex] = useState<number | null>(null);
  const [isMovingRoom, setIsMovingRoom] = useState(false);
  const [dragStartPos, setDragStartPos] = useState<[number, number] | null>(null);
  const [hoveredRoom, setHoveredRoom] = useState<Room | null>(null);
  const [hoveredDoor, setHoveredDoor] = useState<string | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<{ roomId: string; edgeIndex: number } | null>(null);
  
  const internalSvgRef = useRef<SVGSVGElement>(null);
  const svgRef = externalSvgRef || internalSvgRef;

  const handleMouseDown = useCallback((
    event: React.MouseEvent<SVGElement>,
    room: Room
  ) => {
    if (!isInteractive || !room.polygon) return;

    const svg = svgRef.current;
    if (!svg) return;

    // Check if click is on a door (don't interfere with door clicks)
    const target = event.target as SVGElement;
    // Check if target or any parent has the door-marker class
    let element: SVGElement | null = target;
    while (element && element !== svg) {
      if (element.classList?.contains('door-marker') || element.getAttribute('class')?.includes('door-marker')) {
        return; // Let door click handler process this
      }
      element = element.parentElement as SVGElement | null;
    }

    // Prevent text selection and default drag behavior
    event.preventDefault();
    event.stopPropagation();

    // Get mouse position in SVG coordinates
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    let mousePos: [number, number] = [svgP.x, svgP.y];
    
    // Apply snap to grid if enabled
    if (snapToGrid) {
      mousePos = snapPointToGrid(mousePos, gridSize);
    }

    // Add Corner Mode: Insert vertex on edge click
    if (addCornerMode) {
      const edgeInfo = findNearestEdge(room.polygon, mousePos, 50);
      if (edgeInfo) {
        // Insert vertex at click position
        const newPolygon = insertVertexInPolygon(room.polygon, edgeInfo.edgeIndex, edgeInfo.closestPoint);
        const newBbox = polygonToBbox(newPolygon);
        
        const updatedRoom: Room = {
          ...room,
          polygon: newPolygon,
          bounding_box: newBbox,
        };
        
        // Notify parent that corner was added
        if (onCornerAdded) {
          onCornerAdded(updatedRoom, edgeInfo.edgeIndex + 1);
        }
        
        // Immediately start dragging the new vertex
        setIsDragging(true);
        setDraggedRoom(updatedRoom);
        setDraggedCornerIndex(edgeInfo.edgeIndex + 1);
        setIsMovingRoom(false);
        setDraggedEdgeIndex(null);
        return;
      }
      return; // Don't do anything else in Add Corner mode if not on edge
    }

    // Find nearest corner (within 30px threshold for easier clicking)
    const cornerIndex = findNearestCorner(room.polygon, mousePos, 30);
    
    // Priority 1: Corner dragging (highest priority)
    if (cornerIndex !== null) {
      setIsDragging(true);
      setDraggedRoom(room);
      setDraggedCornerIndex(cornerIndex);
      setDraggedEdgeIndex(null);
      setIsMovingRoom(false);
      event.stopPropagation();
      return;
    }
    
    // Priority 2: Edge dragging (check before body drag)
    const edgeInfo = findNearestEdge(room.polygon, mousePos, 30);
    if (edgeInfo && !addCornerMode) {
      // Strict Mode: Perpendicular edge dragging
      if (strictMode) {
        setIsDragging(true);
        setDraggedRoom(room);
        setDraggedCornerIndex(null);
        setDraggedEdgeIndex(edgeInfo.edgeIndex);
        setIsMovingRoom(false);
        setDragStartPos(mousePos);
        event.stopPropagation();
        return;
      }
      // Normal edge dragging: resize by moving entire edge
      else {
        setIsDragging(true);
        setDraggedRoom(room);
        setDraggedCornerIndex(null);
        setDraggedEdgeIndex(edgeInfo.edgeIndex);
        setIsMovingRoom(false);
        setDragStartPos(mousePos);
        event.stopPropagation();
        return;
      }
    }
    
    // Priority 3: Body drag = move (only if not on corner or edge)
    if (isPointInPolygon(mousePos, room.polygon)) {
      setIsDragging(true);
      setDraggedRoom(room);
      setDraggedCornerIndex(null);
      setDraggedEdgeIndex(null);
      setIsMovingRoom(true);
      setDragStartPos(mousePos);
      event.stopPropagation();
    }
  }, [isInteractive, addCornerMode, strictMode, snapToGrid, gridSize, onCornerAdded]);

  const handleMouseMove = useCallback((event: React.MouseEvent<SVGElement>) => {
    if (!isDragging || !draggedRoom || !draggedRoom.polygon) return;

    const svg = svgRef.current;
    if (!svg) return;

    // Get mouse position in SVG coordinates
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    let currentPos: [number, number] = [svgP.x, svgP.y];

    // Apply snap to grid if enabled
    if (snapToGrid) {
      currentPos = snapPointToGrid(currentPos, gridSize);
    }

    let updatedRoom: Room;

    // Edge dragging: resize by moving entire edge
    if (draggedEdgeIndex !== null && dragStartPos) {
      const edgeStart = draggedRoom.polygon[draggedEdgeIndex];
      const edgeEnd = draggedRoom.polygon[(draggedEdgeIndex + 1) % draggedRoom.polygon.length];
      
      // Calculate movement vector
      const deltaX = currentPos[0] - dragStartPos[0];
      const deltaY = currentPos[1] - dragStartPos[1];
      
      if (strictMode) {
        // Strict Mode: Perpendicular edge dragging
        // Get perpendicular direction
        const perpDir = getEdgePerpendicularVector(edgeStart, edgeEnd);
        
        // Project movement onto perpendicular direction
        const perpMovement = deltaX * perpDir[0] + deltaY * perpDir[1];
        
        // Move both vertices of the edge perpendicularly
        const newPolygon = [...draggedRoom.polygon];
        newPolygon[draggedEdgeIndex] = [
          edgeStart[0] + perpMovement * perpDir[0],
          edgeStart[1] + perpMovement * perpDir[1]
        ];
        newPolygon[(draggedEdgeIndex + 1) % newPolygon.length] = [
          edgeEnd[0] + perpMovement * perpDir[0],
          edgeEnd[1] + perpMovement * perpDir[1]
        ];
        
        // Update bounding box
        const newBbox = polygonToBbox(newPolygon);
        
        updatedRoom = {
          ...draggedRoom,
          polygon: newPolygon,
          bounding_box: newBbox,
        };
      } else {
        // Normal edge dragging: move entire edge freely
        const newPolygon = [...draggedRoom.polygon];
        newPolygon[draggedEdgeIndex] = [
          edgeStart[0] + deltaX,
          edgeStart[1] + deltaY
        ];
        newPolygon[(draggedEdgeIndex + 1) % newPolygon.length] = [
          edgeEnd[0] + deltaX,
          edgeEnd[1] + deltaY
        ];
        
        // Update bounding box
        const newBbox = polygonToBbox(newPolygon);
        
        updatedRoom = {
          ...draggedRoom,
          polygon: newPolygon,
          bounding_box: newBbox,
        };
      }
    } else if (isMovingRoom && dragStartPos) {
      // Moving entire room
      const deltaX = currentPos[0] - dragStartPos[0];
      const deltaY = currentPos[1] - dragStartPos[1];
      
      const newPolygon = translatePolygon(draggedRoom.polygon, deltaX, deltaY);
      
      // Update bounding box
      const xCoords = newPolygon.map(p => p[0]);
      const yCoords = newPolygon.map(p => p[1]);
      const newBbox: [number, number, number, number] = [
        Math.min(...xCoords),
        Math.min(...yCoords),
        Math.max(...xCoords),
        Math.max(...yCoords),
      ];

      // Check for overlaps with other rooms
      let hasOverlap = false;
      if (onOverlapWarning) {
        for (const room of _rooms) {
          if (room.id !== draggedRoom.id && room.polygon) {
            const roomBbox = polygonToBbox(room.polygon);
            if (bboxesOverlap(newBbox, roomBbox)) {
              hasOverlap = true;
              break;
            }
          }
        }
        onOverlapWarning(hasOverlap);
      }

      // Update doors if they exist (move them with the room)
      const updatedDoors = draggedRoom.doors?.map(door => ({
        ...door,
        location: [door.location[0] + deltaX, door.location[1] + deltaY] as [number, number],
      }));

      updatedRoom = {
        ...draggedRoom,
        polygon: newPolygon,
        bounding_box: newBbox,
        doors: updatedDoors,
      };
    } else if (draggedCornerIndex !== null) {
      // Resizing room (corner drag)
      const newPolygon = resizePolygon(draggedRoom.polygon, draggedCornerIndex, currentPos);
      
      // Update bounding box
      const xCoords = newPolygon.map(p => p[0]);
      const yCoords = newPolygon.map(p => p[1]);
      const newBbox: [number, number, number, number] = [
        Math.min(...xCoords),
        Math.min(...yCoords),
        Math.max(...xCoords),
        Math.max(...yCoords),
      ];

      updatedRoom = {
        ...draggedRoom,
        polygon: newPolygon,
        bounding_box: newBbox,
      };
    } else {
      return; // Should not happen
    }
    
    // Update drag preview
    setDragPreview(updatedRoom);
  }, [isDragging, draggedRoom, draggedCornerIndex, draggedEdgeIndex, isMovingRoom, dragStartPos, strictMode, snapToGrid, gridSize, _rooms, onOverlapWarning]);

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      // Apply the drag preview if it exists
      if (dragPreview) {
        onRoomModified(dragPreview);
      }
      
      setIsDragging(false);
      setDraggedRoom(null);
      setDragPreview(null);
      setDraggedCornerIndex(null);
      setDraggedEdgeIndex(null);
      setIsMovingRoom(false);
      setDragStartPos(null);
      if (onOverlapWarning) {
        onOverlapWarning(false);
      }
    }
  }, [isDragging, dragPreview, onRoomModified, onOverlapWarning]);

  // Handle edge hover for Add Corner mode and normal edge dragging
  const handleEdgeHover = useCallback((
    event: React.MouseEvent<SVGElement>,
    room: Room
  ) => {
    // Disable hover interactions while dragging
    if (isDragging) {
      return;
    }
    
    if (!isInteractive || !room.polygon) {
      setHoveredEdge(null);
      return;
    }

    const svg = svgRef.current;
    if (!svg) return;

    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    const mousePos: [number, number] = [svgP.x, svgP.y];

    // Check if we're near a corner first (corners take priority)
    const cornerIndex = findNearestCorner(room.polygon, mousePos, 20);
    if (cornerIndex !== null) {
      setHoveredEdge(null);
      return;
    }

    // Check if we're inside the polygon (body takes priority over edge)
    if (isPointInPolygon(mousePos, room.polygon)) {
      setHoveredEdge(null);
      return;
    }

    // Check if we're near an edge (for dragging or adding corner)
    const edgeInfo = findNearestEdge(room.polygon, mousePos, 30);
    if (edgeInfo) {
      setHoveredEdge({ roomId: room.id, edgeIndex: edgeInfo.edgeIndex });
    } else {
      setHoveredEdge(null);
    }
  }, [isInteractive, isDragging]);

  const handleRoomHover = useCallback((room: Room | null) => {
    // Disable hover interactions while dragging
    if (isDragging) {
      return;
    }
    
    if (!isInteractive) return;
    setHoveredRoom(room);
  }, [isInteractive, isDragging]);

  const handleDoorHover = useCallback((doorId: string | null) => {
    if (!isInteractive) return;
    setHoveredDoor(doorId);
  }, [isInteractive]);

  // Add global mouse up listener
  useEffect(() => {
    if (isDragging) {
      const handleGlobalMouseUp = () => handleMouseUp();
      window.addEventListener('mouseup', handleGlobalMouseUp);
      return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
    }
  }, [isDragging, handleMouseUp]);

  // Reset state when interactive mode is disabled
  useEffect(() => {
    if (!isInteractive) {
      setIsDragging(false);
      setDraggedRoom(null);
      setDragPreview(null);
      setDraggedCornerIndex(null);
      setDraggedEdgeIndex(null);
      setIsMovingRoom(false);
      setDragStartPos(null);
      setHoveredRoom(null);
      setHoveredDoor(null);
      setHoveredEdge(null);
    }
  }, [isInteractive]);

  return {
    svgRef,
    isDragging,
    draggedRoom,
    dragPreview,
    hoveredRoom,
    hoveredDoor,
    hoveredEdge,
    isMovingRoom,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleRoomHover,
    handleDoorHover,
    handleEdgeHover,
  };
};

