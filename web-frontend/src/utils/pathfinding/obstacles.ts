// src/utils/pathfinding/obstacles.ts
import { Point, Rect } from "./types";

import { CanvasItem } from "@/components/Canvas/types";
import { calculateAspectFit } from "@/utils/layout";

/**
 * Extract obstacle rectangles from canvas items
 */
export function getObstacleRects(items: CanvasItem[]): Rect[] {
  return items.map((item) => {
    // Use the same aspect fit calculation as the rendering system
    const {
      x: renderX,
      y: renderY,
      width: renderWidth,
      height: renderHeight,
    } = calculateAspectFit(
      item.width,
      item.height,
      item.naturalWidth || item.width,
      item.naturalHeight || item.height,
    );

    return {
      x: item.x + renderX,
      y: item.y + renderY,
      width: renderWidth,
      height: renderHeight,
    };
  });
}

export function getPaddedObstacleRects(items: CanvasItem[], padding: number = 20): Rect[] {
  return getObstacleRects(items).map(rect => ({
    x: rect.x - padding,
    y: rect.y - padding,
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  }));
}

/**
 * Check if a line segment intersects with any obstacle
 */
export function segmentHitsObstacle(
  p1: Point,
  p2: Point,
  obstacles: Rect[],
): boolean {
  const minX = Math.min(p1.x, p2.x);
  const maxX = Math.max(p1.x, p2.x);
  const minY = Math.min(p1.y, p2.y);
  const maxY = Math.max(p1.y, p2.y);

  for (const obstacle of obstacles) {
    if (
      maxX >= obstacle.x &&
      minX <= obstacle.x + obstacle.width &&
      maxY >= obstacle.y &&
      minY <= obstacle.y + obstacle.height
    ) {
      return true;
    }
  }

  return false;
}

/**
 * Check if an orthogonal line segment intersects with any obstacle
 * Uses stricter orthogonal check instead of coarse bounding box overlap
 */
export function orthogonalSegmentHitsObstacle(
  p1: Point,
  p2: Point,
  obstacles: Rect[]
): boolean {
  for (const r of obstacles) {
    if (Math.abs(p1.x - p2.x) < 1) { // practically vertical
      const x = p1.x;
      const minY = Math.min(p1.y, p2.y);
      const maxY = Math.max(p1.y, p2.y);

      // Strict intersection: x is inside horizontally, and vertical line spans the rect y bounds
      if (
        x > r.x &&
        x < r.x + r.width &&
        maxY > r.y &&
        minY < r.y + r.height
      ) {
        return true;
      }
    } else {
      // horizontal line
      const y = p1.y;
      const minX = Math.min(p1.x, p2.x);
      const maxX = Math.max(p1.x, p2.x);

      if (
        y > r.y &&
        y < r.y + r.height &&
        maxX > r.x &&
        minX < r.x + r.width
      ) {
        return true;
      }
    }
  }
  return false;
}

/**
 * Validate an entire path against obstacles
 */
export function pathHitsObstacle(path: Point[], obstacles: Rect[]): boolean {
  for (let i = 0; i < path.length - 1; i++) {
    if (orthogonalSegmentHitsObstacle(path[i], path[i + 1], obstacles)) {
      return true;
    }
  }
  return false;
}

/**
 * Apply standoff distance to a point based on grip side
 */
export function applyStandoff(
  point: Point,
  grip: any,
  standoffDistance: number = 20,
): Point {
  if (!grip) return point;

  // Determine closest side based on grip position
  const distLeft = grip.x;
  const distRight = 100 - grip.x;
  const distTop = 100 - grip.y; // y=100 is top
  const distBottom = grip.y; // y=0 is bottom

  const min = Math.min(distLeft, distRight, distTop, distBottom);

  if (min === distLeft) {
    return { x: point.x - standoffDistance, y: point.y }; // Left
  } else if (min === distRight) {
    return { x: point.x + standoffDistance, y: point.y }; // Right
  } else if (min === distTop) {
    return { x: point.x, y: point.y - standoffDistance }; // Top
  } else {
    return { x: point.x, y: point.y + standoffDistance }; // Bottom
  }
}
