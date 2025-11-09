import type { Polygon, Room } from '../types';

/**
 * Convert polygon vertices to SVG path string
 */
export const polygonToSVGPath = (polygon: Polygon): string => {
  if (!polygon || polygon.length === 0) return '';
  
  const points = polygon.map((point, index) => {
    const command = index === 0 ? 'M' : 'L';
    return `${command} ${point[0]} ${point[1]}`;
  }).join(' ');
  
  return `${points} Z`; // Z closes the path
};

/**
 * Convert bounding box to rectangle properties
 */
export const bboxToRect = (bbox: [number, number, number, number]): {
  x: number;
  y: number;
  width: number;
  height: number;
} => {
  const [x_min, y_min, x_max, y_max] = bbox;
  return {
    x: x_min,
    y: y_min,
    width: x_max - x_min,
    height: y_max - y_min,
  };
};

/**
 * Check if two bounding boxes overlap
 */
export const bboxesOverlap = (
  bbox1: [number, number, number, number],
  bbox2: [number, number, number, number]
): boolean => {
  const [x1_min, y1_min, x1_max, y1_max] = bbox1;
  const [x2_min, y2_min, x2_max, y2_max] = bbox2;
  
  // No overlap if one is to the left of the other
  if (x1_max <= x2_min || x2_max <= x1_min) return false;
  
  // No overlap if one is above the other
  if (y1_max <= y2_min || y2_max <= y1_min) return false;
  
  return true;
};

/**
 * Check if two polygons overlap (simplified check using bounding boxes)
 */
export const polygonsOverlap = (poly1: Polygon, poly2: Polygon): boolean => {
  const bbox1 = polygonToBbox(poly1);
  const bbox2 = polygonToBbox(poly2);
  return bboxesOverlap(bbox1, bbox2);
};

/**
 * Convert polygon to bounding box
 */
export const polygonToBbox = (polygon: Polygon): [number, number, number, number] => {
  if (!polygon || polygon.length === 0) return [0, 0, 0, 0];
  
  const xCoords = polygon.map(p => p[0]);
  const yCoords = polygon.map(p => p[1]);
  
  return [
    Math.min(...xCoords),
    Math.min(...yCoords),
    Math.max(...xCoords),
    Math.max(...yCoords),
  ];
};

/**
 * Get the center point of a polygon
 */
export const getPolygonCenter = (polygon: Polygon): [number, number] => {
  if (!polygon || polygon.length === 0) return [0, 0];
  
  const sumX = polygon.reduce((sum, point) => sum + point[0], 0);
  const sumY = polygon.reduce((sum, point) => sum + point[1], 0);
  
  return [sumX / polygon.length, sumY / polygon.length];
};

/**
 * Get the center point of a bounding box
 */
export const getBboxCenter = (bbox: [number, number, number, number]): [number, number] => {
  const [x_min, y_min, x_max, y_max] = bbox;
  return [(x_min + x_max) / 2, (y_min + y_max) / 2];
};

/**
 * Resize a polygon by dragging a corner
 */
export const resizePolygon = (
  polygon: Polygon,
  cornerIndex: number,
  newPosition: [number, number]
): Polygon => {
  const newPolygon = [...polygon];
  newPolygon[cornerIndex] = newPosition;
  return newPolygon;
};

/**
 * Translate (move) an entire polygon by deltaX and deltaY
 */
export const translatePolygon = (
  polygon: Polygon,
  deltaX: number,
  deltaY: number
): Polygon => {
  return polygon.map(point => [point[0] + deltaX, point[1] + deltaY]);
};

/**
 * Find the nearest corner of a polygon to a point
 */
export const findNearestCorner = (
  polygon: Polygon,
  point: [number, number],
  threshold: number = 20
): number | null => {
  let nearestIndex: number | null = null;
  let nearestDistance = threshold;
  
  polygon.forEach((corner, index) => {
    const distance = Math.sqrt(
      Math.pow(corner[0] - point[0], 2) + Math.pow(corner[1] - point[1], 2)
    );
    
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestIndex = index;
    }
  });
  
  return nearestIndex;
};

/**
 * Normalize coordinates from one range to another
 */
export const normalizeCoordinates = (
  coords: [number, number],
  fromWidth: number,
  fromHeight: number,
  toWidth: number,
  toHeight: number
): [number, number] => {
  const [x, y] = coords;
  return [
    (x / fromWidth) * toWidth,
    (y / fromHeight) * toHeight,
  ];
};

/**
 * Clamp a value between min and max
 */
export const clamp = (value: number, min: number, max: number): number => {
  return Math.min(Math.max(value, min), max);
};

/**
 * Clamp polygon vertices to canvas bounds
 */
export const clampPolygon = (
  polygon: Polygon,
  maxWidth: number,
  maxHeight: number
): Polygon => {
  return polygon.map(point => [
    clamp(point[0], 0, maxWidth),
    clamp(point[1], 0, maxHeight),
  ]);
};

/**
 * Check if a point is inside a polygon (ray casting algorithm)
 */
export const isPointInPolygon = (point: [number, number], polygon: Polygon): boolean => {
  const [x, y] = point;
  let inside = false;
  
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i][0], yi = polygon[i][1];
    const xj = polygon[j][0], yj = polygon[j][1];
    
    const intersect = ((yi > y) !== (yj > y)) &&
      (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    
    if (intersect) inside = !inside;
  }
  
  return inside;
};

/**
 * Calculate the area of a polygon
 */
export const calculatePolygonArea = (polygon: Polygon): number => {
  if (polygon.length < 3) return 0;
  
  let area = 0;
  for (let i = 0; i < polygon.length; i++) {
    const j = (i + 1) % polygon.length;
    area += polygon[i][0] * polygon[j][1];
    area -= polygon[j][0] * polygon[i][1];
  }
  
  return Math.abs(area / 2);
};

/**
 * Get room display color based on type
 */
export const getRoomColor = (room: Room): string => {
  if (room.is_extended) return '#16a34a'; // Green for extended rooms
  if (room.is_modified) return '#f59e0b'; // Orange/Yellow for modified original rooms
  return '#3b82f6'; // Blue for detected rooms
};

/**
 * Get confidence badge color
 */
export const getConfidenceBadgeColor = (confidence: number): string => {
  if (confidence >= 0.85) return 'bg-green-100 text-green-800';
  if (confidence >= 0.70) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
};

/**
 * Format confidence as percentage
 */
export const formatConfidence = (confidence: number): string => {
  return `${Math.round(confidence * 100)}%`;
};

/**
 * Convert SVG coordinates to canvas coordinates
 */
export const svgToCanvasCoords = (
  svgX: number,
  svgY: number,
  svgElement: SVGSVGElement
): [number, number] => {
  const pt = svgElement.createSVGPoint();
  pt.x = svgX;
  pt.y = svgY;
  const transformed = pt.matrixTransform(svgElement.getScreenCTM()?.inverse());
  return [transformed.x, transformed.y];
};

/**
 * Scale polygon to fit within bounds while maintaining aspect ratio
 */
export const scalePolygonToFit = (
  polygon: Polygon,
  maxWidth: number,
  maxHeight: number
): Polygon => {
  const bbox = polygonToBbox(polygon);
  const [x_min, y_min, x_max, y_max] = bbox;
  const width = x_max - x_min;
  const height = y_max - y_min;
  
  const scaleX = maxWidth / width;
  const scaleY = maxHeight / height;
  const scale = Math.min(scaleX, scaleY);
  
  return polygon.map(point => [
    (point[0] - x_min) * scale,
    (point[1] - y_min) * scale,
  ]);
};

/**
 * Find the nearest edge of a polygon to a point
 * Returns the edge index (edge is between points[index] and points[(index+1)%length])
 */
export const findNearestEdge = (
  polygon: Polygon,
  point: [number, number],
  threshold: number = 10
): { edgeIndex: number; distance: number; closestPoint: [number, number] } | null => {
  let nearestEdge: { edgeIndex: number; distance: number; closestPoint: [number, number] } | null = null;
  let nearestDistance = threshold;
  
  for (let i = 0; i < polygon.length; i++) {
    const p1 = polygon[i];
    const p2 = polygon[(i + 1) % polygon.length];
    
    // Calculate distance from point to line segment
    const A = point[0] - p1[0];
    const B = point[1] - p1[1];
    const C = p2[0] - p1[0];
    const D = p2[1] - p1[1];
    
    const dot = A * C + B * D;
    const lenSq = C * C + D * D;
    let param = -1;
    
    if (lenSq !== 0) {
      param = dot / lenSq;
    }
    
    let xx: number, yy: number;
    
    if (param < 0) {
      xx = p1[0];
      yy = p1[1];
    } else if (param > 1) {
      xx = p2[0];
      yy = p2[1];
    } else {
      xx = p1[0] + param * C;
      yy = p1[1] + param * D;
    }
    
    const dx = point[0] - xx;
    const dy = point[1] - yy;
    const distance = Math.sqrt(dx * dx + dy * dy);
    
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestEdge = {
        edgeIndex: i,
        distance,
        closestPoint: [xx, yy] as [number, number],
      };
    }
  }
  
  return nearestEdge;
};

/**
 * Calculate door direction (N/S/E/W) from an edge
 */
export const calculateEdgeDirection = (
  edgeStart: [number, number],
  edgeEnd: [number, number]
): 'N' | 'S' | 'E' | 'W' => {
  const dx = edgeEnd[0] - edgeStart[0];
  const dy = edgeEnd[1] - edgeStart[1];
  
  // Determine primary direction based on larger component
  if (Math.abs(dx) > Math.abs(dy)) {
    // Horizontal edge
    return dx > 0 ? 'E' : 'W';
  } else {
    // Vertical edge
    return dy > 0 ? 'S' : 'N';
  }
};

