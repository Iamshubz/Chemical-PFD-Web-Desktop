// src/utils/pathfinding/optimize.ts
import { Point, Rect } from "./types";
import { pathHitsObstacle } from "./obstacles";

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

/**
 * Enforce a strict Manhattan shape (L or Z) on a path.
 * Collapses any noisily-routed path back to at most 3 waypoints:
 *   start → corner → end  (L-shape, horizontal-first)
 *
 * If start and end share an X or Y coordinate already (straight line),
 * the path is returned as-is with just those two points.
 */
export function enforceManhattanShape(path: Point[], obstacles: Rect[] = []): Point[] {
  if (path.length <= 2) return path;

  const start = path[0];
  const end = path[path.length - 1];

  // Already a straight line — check if it hits an obstacle
  if (start.x === end.x || start.y === end.y) {
    const straightPath = [start, end];
    if (!pathHitsObstacle(straightPath, obstacles)) {
      return straightPath;
    }
    return path; // Fallback to raw A* path
  }

  // Canonical L-shapes
  const option1 = [
    start,
    { x: end.x, y: start.y },
    end,
  ];

  const option2 = [
    start,
    { x: start.x, y: end.y },
    end,
  ];

  const valid1 = !pathHitsObstacle(option1, obstacles);
  const valid2 = !pathHitsObstacle(option2, obstacles);

  // Use the first valid L-shape
  if (valid1) return option1;
  if (valid2) return option2;

  // If both invalid -> fallback to A* path (already obstacle-safe)
  return path;
}
