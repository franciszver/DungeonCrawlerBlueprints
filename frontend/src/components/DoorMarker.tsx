import type { Door } from '../types';

interface DoorMarkerProps {
  door: Door;
  onClick: () => void;
  isActive: boolean;
  isHovered: boolean;
  onHover: (hovered: boolean) => void;
}

export default function DoorMarker({ door, onClick, isActive, isHovered, onHover }: DoorMarkerProps) {
  const [x, y] = door.location;
  
  return (
    <g
      className="door-marker cursor-pointer"
      onClick={onClick}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
    >
      {/* Door circle */}
      <circle
        cx={x}
        cy={y}
        r={isHovered || isActive ? 8 : 6}
        fill="#ef4444"
        stroke="#991b1b"
        strokeWidth={2}
        className="transition-all duration-200"
      />
      
      {/* Plus icon when hovered or active */}
      {(isHovered || isActive) && (
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
      
      {/* Tooltip */}
      {isHovered && !isActive && (
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

