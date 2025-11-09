import { polygonToSVGPath, bboxToRect, getRoomColor, getBboxCenter, formatConfidence } from '../utils/geometryHelpers';
import DoorMarker from './DoorMarker';
import type { Room, Door } from '../types';

interface RoomCanvasProps {
  rooms: Room[];
  doors: Door[];
  blueprintImage: string;
  isInteractive: boolean;
  selectedDoorId?: string | null;
  hoveredDoorId?: string | null;
  hoveredRoom?: Room | null;
  onDoorClick: (door: Door) => void;
  onDoorHover: (doorId: string | null) => void;
  onRoomHover: (room: Room | null) => void;
  onMouseDown?: (event: React.MouseEvent<SVGElement>, room: Room) => void;
  onMouseMove?: (event: React.MouseEvent<SVGElement>) => void;
  onMouseUp?: () => void;
  svgRef?: React.RefObject<SVGSVGElement>;
}

export default function RoomCanvas({
  rooms,
  doors,
  blueprintImage,
  isInteractive,
  selectedDoorId,
  hoveredDoorId,
  hoveredRoom,
  onDoorClick,
  onDoorHover,
  onRoomHover,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  svgRef,
}: RoomCanvasProps) {
  
  const getRoomOpacity = (room: Room) => {
    if (!isInteractive) return 0.3;
    if (hoveredRoom?.id === room.id) return 0.5;
    return 0.3;
  };

  const getRoomStrokeWidth = (room: Room) => {
    if (hoveredRoom?.id === room.id) return 3;
    return 2;
  };

  return (
    <div className="relative w-full h-full bg-gray-100">
      <svg
        ref={svgRef}
        viewBox="0 0 1000 1000"
        className="w-full h-full"
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        style={{ cursor: isInteractive ? 'crosshair' : 'default' }}
      >
        {/* Background blueprint image */}
        {blueprintImage && (
          <image
            href={blueprintImage}
            x="0"
            y="0"
            width="1000"
            height="1000"
            opacity="0.5"
            preserveAspectRatio="xMidYMid meet"
          />
        )}

        {/* Grid for reference (optional) */}
        <defs>
          <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
            <path
              d="M 100 0 L 0 0 0 100"
              fill="none"
              stroke="rgba(0,0,0,0.05)"
              strokeWidth="1"
            />
          </pattern>
        </defs>
        <rect width="1000" height="1000" fill="url(#grid)" />

        {/* Rooms */}
        {rooms.map((room) => {
          const color = getRoomColor(room);
          const opacity = getRoomOpacity(room);
          const strokeWidth = getRoomStrokeWidth(room);

          return (
            <g
              key={room.id}
              onMouseEnter={() => onRoomHover(room)}
              onMouseLeave={() => onRoomHover(null)}
              onMouseDown={(e) => onMouseDown?.(e, room)}
              className={isInteractive ? 'cursor-pointer' : ''}
            >
              {/* Render polygon if available, otherwise bounding box */}
              {room.polygon && room.polygon.length > 0 ? (
                <path
                  d={polygonToSVGPath(room.polygon)}
                  fill={color}
                  fillOpacity={opacity}
                  stroke={color}
                  strokeWidth={strokeWidth}
                  className="transition-all duration-200"
                />
              ) : (
                (() => {
                  const rect = bboxToRect(room.bounding_box);
                  return (
                    <rect
                      x={rect.x}
                      y={rect.y}
                      width={rect.width}
                      height={rect.height}
                      fill={color}
                      fillOpacity={opacity}
                      stroke={color}
                      strokeWidth={strokeWidth}
                      strokeDasharray="5,5"
                      className="transition-all duration-200"
                    />
                  );
                })()
              )}

              {/* Room label */}
              {room.name_hint && (() => {
                const center = room.polygon 
                  ? getBboxCenter([
                      Math.min(...room.polygon.map(p => p[0])),
                      Math.min(...room.polygon.map(p => p[1])),
                      Math.max(...room.polygon.map(p => p[0])),
                      Math.max(...room.polygon.map(p => p[1])),
                    ])
                  : getBboxCenter(room.bounding_box);
                
                return (
                  <text
                    x={center[0]}
                    y={center[1]}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="#1e40af"
                    fontSize="14"
                    fontWeight="600"
                    fontFamily="Arial, sans-serif"
                    pointerEvents="none"
                  >
                    {room.name_hint}
                  </text>
                );
              })()}

              {/* Confidence badge */}
              {room.confidence !== undefined && (() => {
                const center = room.polygon 
                  ? getBboxCenter([
                      Math.min(...room.polygon.map(p => p[0])),
                      Math.min(...room.polygon.map(p => p[1])),
                      Math.max(...room.polygon.map(p => p[0])),
                      Math.max(...room.polygon.map(p => p[1])),
                    ])
                  : getBboxCenter(room.bounding_box);
                
                return (
                  <text
                    x={center[0]}
                    y={center[1] + 18}
                    textAnchor="middle"
                    fill="#64748b"
                    fontSize="11"
                    fontFamily="Arial, sans-serif"
                    pointerEvents="none"
                  >
                    {formatConfidence(room.confidence)}
                  </text>
                );
              })()}

              {/* Corner handles for interactive mode */}
              {isInteractive && room.polygon && room.polygon.map((point, index) => (
                <circle
                  key={`${room.id}-corner-${index}`}
                  cx={point[0]}
                  cy={point[1]}
                  r="5"
                  fill="white"
                  stroke={color}
                  strokeWidth="2"
                  className="cursor-move"
                  style={{ display: hoveredRoom?.id === room.id ? 'block' : 'none' }}
                />
              ))}
            </g>
          );
        })}

        {/* Doors */}
        {isInteractive && doors.map((door) => (
          <DoorMarker
            key={door.id}
            door={door}
            onClick={() => onDoorClick(door)}
            isActive={selectedDoorId === door.id}
            isHovered={hoveredDoorId === door.id}
            onHover={(hovered) => onDoorHover(hovered ? door.id : null)}
          />
        ))}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg p-3 text-sm">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-500 rounded"></div>
            <span>Detected Rooms</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span>Extended Rooms</span>
          </div>
          {isInteractive && (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded-full"></div>
              <span>Doors (click to add room)</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

