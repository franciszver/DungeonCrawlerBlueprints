import { useState, useCallback, useRef, useEffect } from 'react';
import { findNearestCorner, resizePolygon, translatePolygon, isPointInPolygon, polygonToBbox, bboxesOverlap } from '../utils/geometryHelpers';
import type { Room } from '../types';

interface UseCanvasInteractionProps {
  rooms: Room[];
  onRoomModified: (room: Room) => void;
  isInteractive: boolean;
  onOverlapWarning?: (hasOverlap: boolean) => void;
}

export const useCanvasInteraction = ({
  rooms: _rooms,
  onRoomModified,
  isInteractive,
  onOverlapWarning,
}: UseCanvasInteractionProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [draggedRoom, setDraggedRoom] = useState<Room | null>(null);
  const [draggedCornerIndex, setDraggedCornerIndex] = useState<number | null>(null);
  const [isMovingRoom, setIsMovingRoom] = useState(false);
  const [dragStartPos, setDragStartPos] = useState<[number, number] | null>(null);
  const [hoveredRoom, setHoveredRoom] = useState<Room | null>(null);
  const [hoveredDoor, setHoveredDoor] = useState<string | null>(null);
  
  const svgRef = useRef<SVGSVGElement>(null);

  const handleMouseDown = useCallback((
    event: React.MouseEvent<SVGElement>,
    room: Room
  ) => {
    if (!isInteractive || !room.polygon) return;

    const svg = svgRef.current;
    if (!svg) return;

    // Get mouse position in SVG coordinates
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    const mousePos: [number, number] = [svgP.x, svgP.y];

    // Find nearest corner (within 20px threshold)
    const cornerIndex = findNearestCorner(room.polygon, mousePos, 20);
    
    if (cornerIndex !== null) {
      // Corner drag = resize
      setIsDragging(true);
      setDraggedRoom(room);
      setDraggedCornerIndex(cornerIndex);
      setIsMovingRoom(false);
      event.stopPropagation();
    } else if (isPointInPolygon(mousePos, room.polygon)) {
      // Body drag = move
      setIsDragging(true);
      setDraggedRoom(room);
      setDraggedCornerIndex(null);
      setIsMovingRoom(true);
      setDragStartPos(mousePos);
      event.stopPropagation();
    }
  }, [isInteractive]);

  const handleMouseMove = useCallback((event: React.MouseEvent<SVGElement>) => {
    if (!isDragging || !draggedRoom || !draggedRoom.polygon) return;

    const svg = svgRef.current;
    if (!svg) return;

    // Get mouse position in SVG coordinates
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    const currentPos: [number, number] = [svgP.x, svgP.y];

    let updatedRoom: Room;

    if (isMovingRoom && dragStartPos) {
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
    
    onRoomModified(updatedRoom);
  }, [isDragging, draggedRoom, draggedCornerIndex, isMovingRoom, dragStartPos, onRoomModified, _rooms, onOverlapWarning]);

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
      setDraggedRoom(null);
      setDraggedCornerIndex(null);
      setIsMovingRoom(false);
      setDragStartPos(null);
      if (onOverlapWarning) {
        onOverlapWarning(false);
      }
    }
  }, [isDragging, onOverlapWarning]);

  const handleRoomHover = useCallback((room: Room | null) => {
    if (!isInteractive) return;
    setHoveredRoom(room);
  }, [isInteractive]);

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
      setDraggedCornerIndex(null);
      setIsMovingRoom(false);
      setDragStartPos(null);
      setHoveredRoom(null);
      setHoveredDoor(null);
    }
  }, [isInteractive]);

  return {
    svgRef,
    isDragging,
    draggedRoom,
    hoveredRoom,
    hoveredDoor,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleRoomHover,
    handleDoorHover,
  };
};

