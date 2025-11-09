import React from 'react';
import { polygonToSVGPath, bboxToRect } from '../utils/geometryHelpers';
import type { Room } from '../types';

interface MinimapProps {
  rooms: Room[];
  blueprintImage: string;
  imageWidth: number;
  imageHeight: number;
  viewportBounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  onNavigate: (x: number, y: number) => void;
  isVisible: boolean;
  onToggle: () => void;
}

export default function Minimap({
  rooms,
  blueprintImage,
  imageWidth,
  imageHeight,
  viewportBounds,
  onNavigate,
  isVisible,
  onToggle,
}: MinimapProps) {
  const minimapSize = 200;
  const scale = Math.min(minimapSize / imageWidth, minimapSize / imageHeight);
  const scaledWidth = imageWidth * scale;
  const scaledHeight = imageHeight * scale;

  const handleClick = (event: React.MouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - rect.left) / scale;
    const y = (event.clientY - rect.top) / scale;
    
    // Center viewport on clicked position
    onNavigate(x - viewportBounds.width / 2, y - viewportBounds.height / 2);
  };

  // Calculate viewport indicator position and size in minimap coordinates
  const viewportX = viewportBounds.x * scale;
  const viewportY = viewportBounds.y * scale;
  const viewportW = viewportBounds.width * scale;
  const viewportH = viewportBounds.height * scale;

  return (
    <div className="absolute bottom-4 right-4 z-10">
      {isVisible && (
        <div className="bg-white rounded-lg shadow-lg p-2 border border-gray-300">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-gray-700">Minimap</h3>
            <button
              onClick={onToggle}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Hide
            </button>
          </div>
          <svg
            width={scaledWidth}
            height={scaledHeight}
            viewBox={`0 0 ${imageWidth} ${imageHeight}`}
            className="border border-gray-300 rounded cursor-pointer"
            onClick={handleClick}
            style={{ maxWidth: minimapSize, maxHeight: minimapSize }}
          >
            {/* Miniature blueprint */}
            {blueprintImage && (
              <image
                href={blueprintImage}
                x="0"
                y="0"
                width={imageWidth}
                height={imageHeight}
                opacity="0.3"
              />
            )}

            {/* Rooms */}
            {rooms.map((room) => {
              if (room.polygon && room.polygon.length > 0) {
                return (
                  <path
                    key={room.id}
                    d={polygonToSVGPath(room.polygon)}
                    fill="rgba(59, 130, 246, 0.3)"
                    stroke="rgba(59, 130, 246, 0.6)"
                    strokeWidth="1"
                  />
                );
              } else if (room.bounding_box) {
                const rect = bboxToRect(room.bounding_box);
                return (
                  <rect
                    key={room.id}
                    x={rect.x}
                    y={rect.y}
                    width={rect.width}
                    height={rect.height}
                    fill="rgba(59, 130, 246, 0.3)"
                    stroke="rgba(59, 130, 246, 0.6)"
                    strokeWidth="1"
                  />
                );
              }
              return null;
            })}

            {/* Viewport indicator */}
            <rect
              x={viewportX}
              y={viewportY}
              width={viewportW}
              height={viewportH}
              fill="none"
              stroke="rgba(239, 68, 68, 0.8)"
              strokeWidth="2"
              strokeDasharray="3,3"
            />
          </svg>
        </div>
      )}
      {!isVisible && (
        <button
          onClick={onToggle}
          className="bg-white rounded-lg shadow-lg px-3 py-2 text-xs text-gray-700 hover:bg-gray-50"
        >
          Show Map
        </button>
      )}
    </div>
  );
}

