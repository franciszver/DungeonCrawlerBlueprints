/**
 * Unit tests for geometry helper functions
 */
import { describe, it, expect } from 'vitest';
import {
  polygonToSVGPath,
  bboxToRect,
  calculatePolygonArea,
  checkPolygonOverlap,
  getBboxCenter,
  getRoomColor,
  formatConfidence,
} from '../utils/geometryHelpers';

describe('geometryHelpers', () => {
  describe('polygonToSVGPath', () => {
    it('should convert polygon to SVG path', () => {
      const polygon: [number, number][] = [
        [0, 0],
        [100, 0],
        [100, 100],
        [0, 100],
      ];
      const path = polygonToSVGPath(polygon);
      expect(path).toBe('M 0 0 L 100 0 L 100 100 L 0 100 Z');
    });

    it('should handle empty polygon', () => {
      const polygon: [number, number][] = [];
      const path = polygonToSVGPath(polygon);
      expect(path).toBe('');
    });
  });

  describe('bboxToRect', () => {
    it('should convert bounding box to rectangle', () => {
      const bbox = [10, 20, 110, 120];
      const rect = bboxToRect(bbox);
      expect(rect).toEqual({
        x: 10,
        y: 20,
        width: 100,
        height: 100,
      });
    });

    it('should handle invalid bounding box', () => {
      const bbox = [10, 20];
      const rect = bboxToRect(bbox);
      expect(rect).toEqual({
        x: 0,
        y: 0,
        width: 0,
        height: 0,
      });
    });
  });

  describe('calculatePolygonArea', () => {
    it('should calculate area of rectangle', () => {
      const polygon: [number, number][] = [
        [0, 0],
        [100, 0],
        [100, 100],
        [0, 100],
      ];
      const area = calculatePolygonArea(polygon);
      expect(area).toBe(10000);
    });

    it('should return 0 for invalid polygon', () => {
      const polygon: [number, number][] = [[0, 0], [100, 0]];
      const area = calculatePolygonArea(polygon);
      expect(area).toBe(0);
    });
  });

  describe('checkPolygonOverlap', () => {
    it('should detect overlapping polygons', () => {
      const poly1: [number, number][] = [
        [0, 0],
        [100, 0],
        [100, 100],
        [0, 100],
      ];
      const poly2: [number, number][] = [
        [50, 50],
        [150, 50],
        [150, 150],
        [50, 150],
      ];
      expect(checkPolygonOverlap(poly1, poly2)).toBe(true);
    });

    it('should detect non-overlapping polygons', () => {
      const poly1: [number, number][] = [
        [0, 0],
        [100, 0],
        [100, 100],
        [0, 100],
      ];
      const poly2: [number, number][] = [
        [200, 200],
        [300, 200],
        [300, 300],
        [200, 300],
      ];
      expect(checkPolygonOverlap(poly1, poly2)).toBe(false);
    });
  });

  describe('getBboxCenter', () => {
    it('should calculate bounding box center', () => {
      const bbox = [0, 0, 100, 100];
      const center = getBboxCenter(bbox);
      expect(center).toEqual([50, 50]);
    });

    it('should handle invalid bounding box', () => {
      const bbox = [0, 0];
      const center = getBboxCenter(bbox);
      expect(center).toEqual([0, 0]);
    });
  });

  describe('getRoomColor', () => {
    it('should return blue for regular rooms', () => {
      const room = {
        id: 'room_001',
        bounding_box: [0, 0, 100, 100],
        confidence: 0.9,
      };
      const color = getRoomColor(room);
      expect(color).toBe('#3b82f6');
    });

    it('should return green for extended rooms', () => {
      const room = {
        id: 'room_001',
        bounding_box: [0, 0, 100, 100],
        confidence: 0.9,
        is_extended: true,
      };
      const color = getRoomColor(room);
      expect(color).toBe('#16a34a');
    });
  });

  describe('formatConfidence', () => {
    it('should format confidence as percentage', () => {
      expect(formatConfidence(0.856)).toBe('86%');
      expect(formatConfidence(0.9)).toBe('90%');
      expect(formatConfidence(1.0)).toBe('100%');
    });

    it('should handle edge cases', () => {
      expect(formatConfidence(0)).toBe('0%');
      expect(formatConfidence(undefined)).toBe('N/A');
    });
  });
});

