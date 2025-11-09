import { useRef, useState, useEffect } from 'react';
import type { Door } from '../types';

interface DoorMarkerProps {
  door: Door;
  onClick: () => void;
  isActive: boolean;
  isHovered: boolean;
  onHover: (hovered: boolean) => void;
  onDelete?: () => void;
  showDeleteButton?: boolean;
}

export default function DoorMarker({ 
  door, 
  onClick, 
  isActive, 
  isHovered, 
  onHover,
  onDelete,
  showDeleteButton = true 
}: DoorMarkerProps) {
  const [x, y] = door.location;
  const [localHovered, setLocalHovered] = useState(false);
  const hoverTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Combine external hover state with local hover state
  const isActuallyHovered = isHovered || localHovered;
  
  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    setLocalHovered(true);
    onHover(true);
  };
  
  const handleMouseLeave = () => {
    // Add a small delay before hiding to allow moving to delete button
    hoverTimeoutRef.current = setTimeout(() => {
      setLocalHovered(false);
      onHover(false);
    }, 150);
  };
  
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);
  
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.();
  };
  
  // Create an invisible larger hover area that includes both door and delete button
  const hoverAreaSize = 40;
  const hoverAreaX = x - hoverAreaSize / 2;
  const hoverAreaY = y - hoverAreaSize - 5; // Extend upward to include delete button
  
  return (
    <g className="door-marker">
      {/* Invisible larger hover area */}
      <rect
        x={hoverAreaX}
        y={hoverAreaY}
        width={hoverAreaSize}
        height={hoverAreaSize + 25}
        fill="transparent"
        pointerEvents="all"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      />
      
      {/* Door marker group */}
      <g
        className="cursor-pointer"
        onClick={onClick}
      >
        {/* Door circle */}
        <circle
          cx={x}
          cy={y}
          r={isActuallyHovered || isActive ? 8 : 6}
          fill="#ef4444"
          stroke="#991b1b"
          strokeWidth={2}
          className="transition-all duration-200"
        />
        
        {/* Plus icon when hovered or active */}
        {(isActuallyHovered || isActive) && (
        <g>
          <line
            x1={x}
            y1={y - 4}
            x2={x}
            y2={y + 4}
            stroke="white"
            strokeWidth={2}
            strokeLinecap="round"
          />
          <line
            x1={x - 4}
            y1={y}
            x2={x + 4}
            y2={y}
            stroke="white"
            strokeWidth={2}
            strokeLinecap="round"
          />
          </g>
        )}
      </g>
      
      {/* Delete button */}
      {showDeleteButton && isActuallyHovered && onDelete && (
        <g onClick={handleDeleteClick} className="cursor-pointer">
          {/* Larger invisible clickable area for delete button */}
          <circle
            cx={x + 15}
            cy={y - 15}
            r={12}
            fill="transparent"
            pointerEvents="all"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          />
          {/* Visible delete button */}
          <circle
            cx={x + 15}
            cy={y - 15}
            r={8}
            fill="#ef4444"
            stroke="white"
            strokeWidth={2}
            pointerEvents="none"
          />
          <line
            x1={x + 11}
            y1={y - 15}
            x2={x + 19}
            y2={y - 15}
            stroke="white"
            strokeWidth={2}
            strokeLinecap="round"
            pointerEvents="none"
          />
        </g>
      )}
      
      {/* Tooltip */}
      {isActuallyHovered && !isActive && (
        <g>
          <rect
            x={x + 12}
            y={y - 15}
            width={80}
            height={30}
            rx={4}
            fill="rgba(0, 0, 0, 0.8)"
          />
          <text
            x={x + 52}
            y={y + 2}
            textAnchor="middle"
            fill="white"
            fontSize={12}
            fontFamily="Arial, sans-serif"
          >
            Add Room
          </text>
        </g>
      )}
    </g>
  );
}

