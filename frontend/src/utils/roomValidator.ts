import type { Room, Polygon } from '../types';

export interface SizeWarning {
  type: 'size_mismatch' | 'unrealistic_ratio' | 'unrealistic_size';
  room1: Room;
  room2?: Room;
  message: string;
  severity: 'warning' | 'error';
}

/**
 * Calculate the area of a polygon in square units
 */
function calculatePolygonArea(polygon: Polygon): number {
  if (polygon.length < 3) return 0;
  
  let area = 0;
  for (let i = 0; i < polygon.length; i++) {
    const j = (i + 1) % polygon.length;
    area += polygon[i][0] * polygon[j][1];
    area -= polygon[j][0] * polygon[i][1];
  }
  return Math.abs(area) / 2;
}

/**
 * Get typical size ranges for room types (in square units)
 */
function getTypicalSizeRange(roomType: string): { min: number; max: number } | null {
  const roomTypeLower = roomType.toLowerCase();
  
  // Typical sizes in square units (assuming normalized coordinates 0-1000)
  const typicalSizes: Record<string, { min: number; max: number }> = {
    'bedroom': { min: 8000, max: 20000 },      // ~80-200 sq units
    'bathroom': { min: 3000, max: 8000 },      // ~30-80 sq units
    'kitchen': { min: 10000, max: 25000 },     // ~100-250 sq units
    'living room': { min: 20000, max: 50000 }, // ~200-500 sq units
    'dining room': { min: 12000, max: 30000 }, // ~120-300 sq units
    'hallway': { min: 2000, max: 10000 },      // ~20-100 sq units
    'closet': { min: 1000, max: 5000 },        // ~10-50 sq units
    'office': { min: 8000, max: 20000 },       // ~80-200 sq units
    'garage': { min: 30000, max: 80000 },      // ~300-800 sq units
    'pantry': { min: 2000, max: 6000 },        // ~20-60 sq units
  };
  
  // Check for partial matches
  for (const [key, value] of Object.entries(typicalSizes)) {
    if (roomTypeLower.includes(key)) {
      return value;
    }
  }
  
  return null;
}

/**
 * Compare two room types and check if their relative sizes make sense
 */
function checkRoomTypeRatio(room1: Room, room2: Room): SizeWarning | null {
  const type1 = room1.name_hint?.toLowerCase() || '';
  const type2 = room2.name_hint?.toLowerCase() || '';
  
  // Known problematic size relationships
  const problematicRatios: Array<[string[], string[], string]> = [
    [['kitchen'], ['living room', 'bedroom'], 'Kitchen should not be larger than living room or bedroom'],
    [['bathroom'], ['bedroom', 'living room'], 'Bathroom should not be larger than bedroom or living room'],
    [['closet'], ['bedroom', 'living room'], 'Closet should not be larger than bedroom or living room'],
    [['pantry'], ['kitchen'], 'Pantry should not be larger than kitchen'],
  ];
  
  for (const [types1, types2, message] of problematicRatios) {
    const matches1 = types1.some(t => type1.includes(t));
    const matches2 = types2.some(t => type2.includes(t));
    
    if (matches1 && matches2) {
      const area1 = calculatePolygonArea(room1.polygon || []);
      const area2 = calculatePolygonArea(room2.polygon || []);
      
      if (area1 > area2) {
        return {
          type: 'size_mismatch',
          room1,
          room2,
          message: `${message}: ${room1.name_hint} (${Math.round(area1)} sq units) is larger than ${room2.name_hint} (${Math.round(area2)} sq units)`,
          severity: 'warning',
        };
      }
    }
  }
  
  return null;
}

/**
 * Validate room sizes and return warnings
 */
export function validateRoomSizes(rooms: Room[]): SizeWarning[] {
  const warnings: SizeWarning[] = [];
  
  if (rooms.length < 2) return warnings;
  
  // Check each room against typical size ranges
  for (const room of rooms) {
    if (!room.polygon || room.polygon.length < 3) continue;
    
    const area = calculatePolygonArea(room.polygon);
    const roomType = room.name_hint || 'Room';
    const typicalRange = getTypicalSizeRange(roomType);
    
    if (typicalRange) {
      if (area < typicalRange.min * 0.5) {
        warnings.push({
          type: 'unrealistic_size',
          room1: room,
          message: `${roomType} (${Math.round(area)} sq units) seems unusually small. Typical range: ${typicalRange.min}-${typicalRange.max} sq units`,
          severity: 'warning',
        });
      } else if (area > typicalRange.max * 2) {
        warnings.push({
          type: 'unrealistic_size',
          room1: room,
          message: `${roomType} (${Math.round(area)} sq units) seems unusually large. Typical range: ${typicalRange.min}-${typicalRange.max} sq units`,
          severity: 'warning',
        });
      }
    }
  }
  
  // Compare rooms with each other
  for (let i = 0; i < rooms.length; i++) {
    for (let j = i + 1; j < rooms.length; j++) {
      const room1 = rooms[i];
      const room2 = rooms[j];
      
      if (!room1.polygon || !room2.polygon) continue;
      
      const ratioWarning = checkRoomTypeRatio(room1, room2);
      if (ratioWarning) {
        warnings.push(ratioWarning);
      }
    }
  }
  
  return warnings;
}

