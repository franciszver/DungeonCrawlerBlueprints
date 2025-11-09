import { useState, useCallback, useRef, useEffect } from 'react';
import { findNearestCorner, resizePolygon } from '../utils/geometryHelpers';
import type { Room } from '../types';

interface UseCanvasInteractionProps {
  rooms: Room[];
  onRoomModified: (room: Room) => void;
  isInteractive: boolean;
}

export const useCanvasInteraction = ({
  rooms: _rooms,
  onRoomModified,
  isInteractive,
}: UseCanvasInteractionProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [draggedRoom, setDraggedRoom] = useState<Room | null>(null);
  const [draggedCornerIndex, setDraggedCornerIndex] = useState<number | null>(null);
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

    // Find nearest corner
    const cornerIndex = findNearestCorner(room.polygon, mousePos, 20);
    
    if (cornerIndex !== null) {
      setIsDragging(true);
      setDraggedRoom(room);
      setDraggedCornerIndex(cornerIndex);
      event.stopPropagation();
    }
  }, [isInteractive]);

  const handleMouseMove = useCallback((event: React.MouseEvent<SVGElement>) => {
    if (!isDragging || !draggedRoom || draggedCornerIndex === null || !draggedRoom.polygon) return;

    const svg = svgRef.current;
    if (!svg) return;

    // Get mouse position in SVG coordinates
    const pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgP = pt.matrixTransform(svg.getScreenCTM()?.inverse());
    const newPosition: [number, number] = [svgP.x, svgP.y];

    // Update polygon
    const newPolygon = resizePolygon(draggedRoom.polygon, draggedCornerIndex, newPosition);
    
    // Update room with new polygon
    const updatedRoom = {
      ...draggedRoom,
      polygon: newPolygon,
    };
    
    onRoomModified(updatedRoom);
  }, [isDragging, draggedRoom, draggedCornerIndex, onRoomModified]);

  const handleMouseUp = useCallback(() => {
    if (isDragging) {
      setIsDragging(false);
      setDraggedRoom(null);
      setDraggedCornerIndex(null);
    }
  }, [isDragging]);

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

