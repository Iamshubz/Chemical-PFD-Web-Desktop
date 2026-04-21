// src/utils/pathfinding/optimize.ts
import { Point } from "./types";

/**
 * Compress straight line segments in a grid path
 * Removes intermediate points that lie on straight lines
 */
export function compressPath(path: Point[]): Point[] {
  if (path.length <= 2) {
    return path;
  }

  const compressed: Point[] = [path[0]];

  for (let i = 1; i < path.length - 1; i++) {
    const prev = compressed[compressed.length - 1];
    const current = path[i];
    const next = path[i + 1];

    // Check if we need to change direction
    const prevDirX = Math.sign(current.x - prev.x);
    const prevDirY = Math.sign(current.y - prev.y);
    const nextDirX = Math.sign(next.x - current.x);
    const nextDirY = Math.sign(next.y - current.y);

    // If direction changes, keep this point
    if (prevDirX !== nextDirX || prevDirY !== nextDirY) {
      compressed.push(current);
    }
  }

  compressed.push(path[path.length - 1]);

  return compressed;
}


/**
 * Create orthogonal line segments from waypoints
 * Ensures all segments are either horizontal or vertical
 */
export function createOrthogonalSegments(points: Point[]): Point[] {
  if (points.length < 2) return points;

  const segments: Point[] = [points[0]];

  for (let i = 1; i < points.length; i++) {
    const current = points[i];
    const previous = segments[segments.length - 1];

    // If points are not already orthogonal, insert intermediate point
    if (current.x !== previous.x && current.y !== previous.y) {
      // Create L-shaped path: horizontal then vertical, or vertical then horizontal
      // Choose the direction that creates shorter total path
      const horizontalFirst = [
        { x: current.x, y: previous.y }, // Horizontal move
        current, // Vertical move
      ];

      // Both should be the same length, so just pick horizontal first
      segments.push(horizontalFirst[0], horizontalFirst[1]);
    } else {
      segments.push(current);
    }
  }

  return segments;
}

/**
 * Full path optimization pipeline
 */
export function optimizePath(path: Point[]): Point[] {
  // Compress straight segments
  const compressed = compressPath(path);

  // Ensure orthogonal segments for safety
  return createOrthogonalSegments(compressed);
}
