import React from 'react';
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
  onDoorDelete?: (doorId: string) => void;
  addDoorMode?: boolean;
  svgRef?: React.RefObject<SVGSVGElement>;
  hoveredEdge?: { roomId: string; edgeIndex: number } | null;
  onRoomMouseMove?: (event: React.MouseEvent<SVGElement>, room: Room) => void;
  zoom?: number;
  panX?: number;
  panY?: number;
  onPanStart?: (event: React.MouseEvent<SVGElement>) => void;
  onPanMove?: (event: React.MouseEvent<SVGElement>) => void;
  onPanEnd?: () => void;
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
  onDoorDelete,
  addDoorMode = false,
  svgRef,
  hoveredEdge,
  dragPreview,
  isDragging,
  isMovingRoom,
  onRoomMouseMove,
  zoom = 1,
  panX = 0,
  panY = 0,
  onPanStart,
  onPanMove,
  onPanEnd,
}: RoomCanvasProps & { dragPreview?: any; isDragging?: boolean; isMovingRoom?: boolean }) {
  const [imageDimensions, setImageDimensions] = React.useState({ width: 1000, height: 1000 });
  const imageRef = React.useRef<SVGImageElement>(null);

  // Load image dimensions when blueprint changes
  React.useEffect(() => {
    if (blueprintImage) {
      const img = new Image();
      img.onload = () => {
        setImageDimensions({ width: img.width, height: img.height });
      };
      img.src = blueprintImage;
    }
  }, [blueprintImage]);
  
  const getRoomOpacity = (room: Room) => {
    if (!isInteractive) return 0.3;
    if (hoveredRoom?.id === room.id) return 0.5;
    return 0.3;
  };

  const getRoomStrokeWidth = (room: Room) => {
    if (hoveredRoom?.id === room.id) return 3;
    return 2;
  };

  // Determine cursor based on state
  const getCursor = () => {
    if (!isInteractive) return 'default';
    if (addDoorMode) return 'crosshair';
    if (isDragging) {
      return isMovingRoom ? 'move' : 'nwse-resize';
    }
    if (hoveredRoom) return 'move';
    return 'default';
  };

  // Calculate viewBox with zoom and pan
  const viewBoxWidth = imageDimensions.width / zoom;
  const viewBoxHeight = imageDimensions.height / zoom;
  const viewBox = `${panX} ${panY} ${viewBoxWidth} ${viewBoxHeight}`;

  // Handle mouse events - combine pan and room interactions
  const handleMouseDown = (event: React.MouseEvent<SVGElement>, room?: Room) => {
    // Check if this is a pan gesture (middle mouse)
    // Spacebar panning is handled via keyboard events in useZoomPan hook
    if (onPanStart && event.button === 1) {
      onPanStart(event);
    } else if (room && onMouseDown) {
      onMouseDown(event, room);
    }
  };

  const handleMouseMove = (event: React.MouseEvent<SVGElement>) => {
    if (onPanMove) {
      onPanMove(event);
    }
    if (onMouseMove) {
      onMouseMove(event);
    }
  };

  const handleMouseUp = () => {
    if (onPanEnd) {
      onPanEnd();
    }
    if (onMouseUp) {
      onMouseUp();
    }
  };

  return (
    <div className="relative w-full h-full bg-gray-100" style={{ userSelect: 'none', WebkitUserSelect: 'none' }}>
      <svg
        ref={svgRef}
        viewBox={viewBox}
        className="w-full h-full"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseDown={(e) => {
          // Find room under mouse if any
          const target = e.target as SVGElement;
          const roomElement = target.closest('[data-room-id]');
          if (roomElement) {
            const roomId = roomElement.getAttribute('data-room-id');
            const room = rooms.find(r => r.id === roomId);
            if (room) {
              handleMouseDown(e, room);
            } else {
              handleMouseDown(e);
            }
          } else {
            handleMouseDown(e);
          }
        }}
        onDragStart={(e) => e.preventDefault()}
        onContextMenu={(e) => {
          // Prevent context menu on middle mouse
          if (e.button === 1) {
            e.preventDefault();
          }
        }}
        style={{ 
          cursor: getCursor(),
          userSelect: 'none',
          WebkitUserSelect: 'none',
          MozUserSelect: 'none',
          msUserSelect: 'none'
        }}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Background blueprint image */}
        {blueprintImage && (
          <image
            ref={imageRef}
            href={blueprintImage}
            x="0"
            y="0"
            width={imageDimensions.width}
            height={imageDimensions.height}
            opacity="0.5"
            preserveAspectRatio="none"
            style={{ pointerEvents: 'none', userSelect: 'none' }}
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
        <rect width={imageDimensions.width} height={imageDimensions.height} fill="url(#grid)" />

        {/* Drag Preview */}
        {dragPreview && isDragging && (
          <g opacity="0.5">
            {dragPreview.polygon && dragPreview.polygon.length > 0 ? (
              <path
                d={polygonToSVGPath(dragPreview.polygon)}
                fill={getRoomColor(dragPreview)}
                stroke="#3b82f6"
                strokeWidth="3"
                strokeDasharray="5,5"
                opacity="0.6"
              />
            ) : dragPreview.bounding_box ? (
              <rect
                {...bboxToRect(dragPreview.bounding_box)}
                fill={getRoomColor(dragPreview)}
                stroke="#3b82f6"
                strokeWidth="3"
                strokeDasharray="5,5"
                opacity="0.6"
              />
            ) : null}
          </g>
        )}

        {/* Rooms */}
        {rooms.map((room) => {
          const color = getRoomColor(room);
          const opacity = getRoomOpacity(room);
          const strokeWidth = getRoomStrokeWidth(room);

          return (
            <g
              key={room.id}
              data-room-id={room.id}
              onMouseEnter={() => onRoomHover(room)}
              onMouseLeave={() => onRoomHover(null)}
              onMouseMove={(e) => {
                e.stopPropagation();
                onRoomMouseMove?.(e, room);
              }}
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

              {/* Edge highlighting in Add Door mode */}
              {addDoorMode && room.polygon && hoveredEdge?.roomId === room.id && (
                <line
                  key={`${room.id}-edge-${hoveredEdge.edgeIndex}`}
                  x1={room.polygon[hoveredEdge.edgeIndex][0]}
                  y1={room.polygon[hoveredEdge.edgeIndex][1]}
                  x2={room.polygon[(hoveredEdge.edgeIndex + 1) % room.polygon.length][0]}
                  y2={room.polygon[(hoveredEdge.edgeIndex + 1) % room.polygon.length][1]}
                  stroke="#3b82f6"
                  strokeWidth="4"
                  opacity="0.6"
                  pointerEvents="none"
                />
              )}

              {/* Corner handles for interactive mode */}
              {isInteractive && !addDoorMode && room.polygon && room.polygon.map((point, index) => (
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
            onDelete={onDoorDelete ? () => onDoorDelete(door.id) : undefined}
            showDeleteButton={!addDoorMode}
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

