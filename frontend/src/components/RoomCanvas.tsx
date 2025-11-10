import React from 'react';
import { polygonToSVGPath, bboxToRect, getRoomColor, getBboxCenter, formatConfidence } from '../utils/geometryHelpers';
import DoorMarker from './DoorMarker';
import type { Room, Door } from '../types';

interface TextLabel {
  text: string;
  bbox: [number, number, number, number];
  confidence?: number;
  original_text?: string;
}

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
  onCanvasClick?: (event: React.MouseEvent<SVGElement>) => void;
  onDoorDelete?: (doorId: string) => void;
  onRoomDelete?: (roomId: string) => void;
  textLabels?: TextLabel[]; // Labels to display on blueprint
  onLabelClick?: (labelIndex: number) => void; // Click handler for labels
  labelOffsets?: Map<number, { x: number; y: number }>; // User-adjusted label positions
  onLabelDragStart?: (labelIndex: number, event: React.MouseEvent) => void;
  onLabelDrag?: (event: React.MouseEvent) => void;
  onLabelDragEnd?: () => void;
  draggingLabel?: number | null;
  labelDragStartPos?: { x: number; y: number } | null;
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
  onCanvasClick,
  onDoorDelete,
  onRoomDelete,
  textLabels = [],
  onLabelClick,
  labelOffsets = new Map(),
  onLabelDragStart,
  onLabelDrag,
  onLabelDragEnd,
  draggingLabel = null,
  labelDragStartPos = null,
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
  const [imageLoaded, setImageLoaded] = React.useState(false);
  const imageRef = React.useRef<SVGImageElement>(null);
  const labelWasDragged = React.useRef<boolean>(false);

  // Load image dimensions when blueprint changes
  React.useEffect(() => {
    if (blueprintImage) {
      setImageLoaded(false);
      const img = new Image();
      img.onload = () => {
        console.log('Image loaded with natural dimensions:', img.width, 'x', img.height);
        setImageDimensions({ width: img.width, height: img.height });
        setImageLoaded(true);
      };
      img.onerror = () => {
        console.error('Failed to load image');
        setImageLoaded(true); // Still set to true to avoid blocking
      };
      img.src = blueprintImage;
    }
  }, [blueprintImage]);
  
  // Update dimensions when SVG image element loads (to get actual displayed size)
  React.useEffect(() => {
    const svgImage = imageRef.current;
    if (svgImage && imageLoaded) {
      const updateDimensions = () => {
        const displayedWidth = svgImage.width?.baseVal?.value;
        const displayedHeight = svgImage.height?.baseVal?.value;
        
        if (displayedWidth && displayedHeight) {
          console.log('SVG image element dimensions:', displayedWidth, 'x', displayedHeight);
          // Use the SVG element's dimensions if they differ from natural size
          if (displayedWidth !== imageDimensions.width || displayedHeight !== imageDimensions.height) {
            console.log('Updating to displayed dimensions');
            setImageDimensions({ width: displayedWidth, height: displayedHeight });
          }
        }
      };
      
      // Check immediately and also on load
      // SVG images don't have a 'complete' property, so just call updateDimensions
      updateDimensions();
      svgImage.addEventListener('load', updateDimensions);
      return () => svgImage.removeEventListener('load', updateDimensions);
    }
  }, [imageLoaded, imageDimensions]);
  
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
    if (hoveredEdge && !addDoorMode) return 'ns-resize'; // indicate edge can be dragged
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
    // Handle label dragging first
    if (onLabelDrag && draggingLabel !== null) {
      // Check if mouse moved significantly (more than 3 pixels)
      if (labelDragStartPos) {
        const dx = event.clientX - labelDragStartPos.x;
        const dy = event.clientY - labelDragStartPos.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        if (distance > 3) {
          labelWasDragged.current = true;
        }
      }
      onLabelDrag(event);
    }
    
    if (onPanMove) {
      onPanMove(event);
    }
    if (onMouseMove) {
      onMouseMove(event);
    }
  };

  const handleMouseUp = () => {
    // End label dragging first
    if (onLabelDragEnd && draggingLabel !== null) {
      onLabelDragEnd();
      // Reset drag flag after a short delay to allow onClick to check it
      setTimeout(() => {
        labelWasDragged.current = false;
      }, 10);
    }
    
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
        onClick={(e) => {
          // Handle canvas click for manual label addition
          if (onCanvasClick) {
            const target = e.target as SVGElement;
            // Only trigger if clicking on the background (not on rooms, doors, or labels)
            if (target.tagName === 'svg' || target.tagName === 'image' || target.classList.contains('canvas-background')) {
              onCanvasClick(e);
            }
          }
        }}
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
              onMouseEnter={() => {
                // Disable hover for other rooms while dragging
                if (!isDragging) {
                  onRoomHover(room);
                }
              }}
              onMouseLeave={() => {
                // Disable hover for other rooms while dragging
                if (!isDragging) {
                  onRoomHover(null);
                }
              }}
              onMouseMove={(e) => {
                // Disable hover for other rooms while dragging
                if (!isDragging) {
                  e.stopPropagation();
                  onRoomMouseMove?.(e, room);
                }
              }}
              className={isInteractive && !isDragging ? 'cursor-pointer' : ''}
              style={{ pointerEvents: isDragging ? 'none' : 'auto' }}
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
                  r={hoveredRoom?.id === room.id ? "8" : "6"}
                  fill="white"
                  stroke={color}
                  strokeWidth={hoveredRoom?.id === room.id ? "3" : "2"}
                  className="cursor-nwse-resize"
                  style={{ opacity: hoveredRoom?.id === room.id ? 1 : 0.7 }}
                />
              ))}

              {/* Delete button for generated/extended rooms */}
              {isInteractive && onRoomDelete && room.is_extended && hoveredRoom?.id === room.id && (
                (() => {
                  const center = room.polygon 
                    ? getBboxCenter([
                        Math.min(...room.polygon.map(p => p[0])),
                        Math.min(...room.polygon.map(p => p[1])),
                        Math.max(...room.polygon.map(p => p[0])),
                        Math.max(...room.polygon.map(p => p[1])),
                      ])
                    : getBboxCenter(room.bounding_box);
                  
                  return (
                    <g 
                      onClick={(e) => {
                        e.stopPropagation();
                        onRoomDelete(room.id);
                      }}
                      className="cursor-pointer"
                    >
                      {/* Invisible larger clickable area */}
                      <circle
                        cx={center[0] + 20}
                        cy={center[1] - 20}
                        r={12}
                        fill="transparent"
                        pointerEvents="all"
                      />
                      {/* Visible delete button */}
                      <circle
                        cx={center[0] + 20}
                        cy={center[1] - 20}
                        r={8}
                        fill="#ef4444"
                        stroke="white"
                        strokeWidth={2}
                        pointerEvents="none"
                      />
                      <line
                        x1={center[0] + 16}
                        y1={center[1] - 20}
                        x2={center[0] + 24}
                        y2={center[1] - 20}
                        stroke="white"
                        strokeWidth={2}
                        strokeLinecap="round"
                        pointerEvents="none"
                      />
                    </g>
                  );
                })()
              )}
            </g>
          );
        })}

        {/* Text Labels (overlaid on blueprint - always visible) */}
        {isInteractive && imageLoaded && textLabels && textLabels.length > 0 && textLabels.map((label, idx) => {
          // Check if this label has a generated room
          const hasGeneratedRoom = rooms.some(
            r => r.is_extended && (r as any).label_index === idx
          );
          
          // Calculate label center from bbox
          // Backend returns coordinates in actual image pixel space
          const [x_min, y_min, x_max, y_max] = label.bbox;
          let labelX = (x_min + x_max) / 2;
          let labelY = (y_min + y_max) / 2;
          
          // Apply user drag offset if exists
          const offset = labelOffsets.get(idx);
          if (offset) {
            labelX += offset.x;
            labelY += offset.y;
          }
          
          const isDragging = draggingLabel === idx;
          
          return (
            <g
              key={`label-${idx}`}
              onClick={(e) => {
                e.stopPropagation();
                // Only trigger click if label wasn't dragged
                if (onLabelClick && !hasGeneratedRoom && !labelWasDragged.current) {
                  onLabelClick(idx);
                }
              }}
              onMouseDown={(e) => {
                if (onLabelDragStart && !hasGeneratedRoom) {
                  labelWasDragged.current = false; // Reset on mouse down
                  onLabelDragStart(idx, e);
                }
              }}
              className={hasGeneratedRoom ? "" : "cursor-move"}
              style={{ opacity: isDragging ? 0.6 : 0.85 }}
            >
              {/* Background circle for label - reduced size and opacity */}
              <circle
                cx={labelX}
                cy={labelY}
                r={15}
                fill={hasGeneratedRoom ? "rgba(34, 197, 94, 0.15)" : "rgba(59, 130, 246, 0.15)"}
                stroke={hasGeneratedRoom ? "#22c55e" : "#3b82f6"}
                strokeWidth={1.5}
                className={hasGeneratedRoom ? "" : "hover:fill-blue-300 transition-colors"}
              />
              {/* Label text - smaller and more subtle */}
              <text
                x={labelX}
                y={labelY}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={hasGeneratedRoom ? "#15803d" : "#1e40af"}
                fontSize="10"
                fontWeight="500"
                fontFamily="Arial, sans-serif"
                pointerEvents="none"
                style={{ textShadow: '0 0 2px white' }}
              >
                {label.text}
              </text>
              {/* Status indicator - smaller */}
              <text
                x={labelX}
                y={labelY + 18}
                textAnchor="middle"
                fill={hasGeneratedRoom ? "#22c55e" : "#64748b"}
                fontSize="8"
                fontFamily="Arial, sans-serif"
                pointerEvents="none"
                style={{ textShadow: '0 0 2px white' }}
              >
                {hasGeneratedRoom ? "✓" : "○"}
              </text>
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

    </div>
  );
}

